"""
文件服务层 —— 统一管理 docs/ 目录下文件的增删查改。
doc_id 就是文件名（不含 .md 后缀），URL-safe。
"""
import re
import uuid
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional

import frontmatter

from app.config import DOCS_DIR, TRASH_DIR
from app.models.schemas import DocMeta
from app.services import markdown_service as md_svc


# ── ID / Path 辅助 ────────────────────────────────────────────────────────

def _doc_path(doc_id: str) -> Path:
    return DOCS_DIR / f"{doc_id}.md"


def _sanitize_id(title: str) -> str:
    """将标题转换为合法的文件名（ASCII slug 或原汉字保留）。"""
    slug = re.sub(r'[\\/:*?"<>|]', "_", title).strip()
    return slug if slug else str(uuid.uuid4())


def _new_doc_id(title: str) -> str:
    """生成唯一 doc_id：title-slug + 短 uuid（防重名）。"""
    base = _sanitize_id(title)[:40]
    suffix = uuid.uuid4().hex[:6]
    return f"{base}-{suffix}"


# ── 读操作 ────────────────────────────────────────────────────────────────

def list_docs(
    page: int = 1,
    limit: int = 20,
    tags: Optional[List[str]] = None,
    category: Optional[str] = None,
    sort_by: str = "updated_at",
) -> List[DocMeta]:
    """列出 docs/ 下所有（未删除）文档的元数据。"""
    results: List[DocMeta] = []
    for md_file in DOCS_DIR.glob("*.md"):
        try:
            post = md_svc.load_post(md_file)
        except Exception:
            continue

        meta = _build_meta(md_file, post)

        # 标签过滤
        if tags and not any(t in meta.tags for t in tags):
            continue
        # 分类过滤
        if category and meta.category != category:
            continue

        results.append(meta)

    # 排序
    key_fn = {
        "updated_at": lambda m: m.updated_at or datetime.min.replace(tzinfo=timezone.utc),
        "created_at": lambda m: m.created_at or datetime.min.replace(tzinfo=timezone.utc),
        "title": lambda m: m.title,
    }.get(sort_by, lambda m: m.updated_at or datetime.min.replace(tzinfo=timezone.utc))

    results.sort(key=key_fn, reverse=(sort_by != "title"))

    # 分页
    start = (page - 1) * limit
    return results[start: start + limit]


def get_doc_content(doc_id: str) -> str:
    """读取文档正文（不含 front-matter）。"""
    path = _require_file(doc_id)
    post = md_svc.load_post(path)
    return post.content


def get_doc_meta(doc_id: str) -> DocMeta:
    path = _require_file(doc_id)
    post = md_svc.load_post(path)
    return _build_meta(path, post)


# ── 写操作 ────────────────────────────────────────────────────────────────

def create_doc(title: str, content: str, tags: List[str], category: Optional[str]) -> str:
    """新建文档，返回生成的 doc_id。"""
    doc_id = _new_doc_id(title)
    path = _doc_path(doc_id)

    now = datetime.now(tz=timezone.utc).isoformat()
    post = frontmatter.Post(
        content,
        title=title,
        tags=tags,
        category=category or "",
        created_at=now,
        updated_at=now,
    )
    md_svc.save_post(path, post)
    return doc_id


def replace_doc(doc_id: str, content: str) -> None:
    """全量替换文档正文（保留 front-matter）。"""
    path = _require_file(doc_id)
    post = md_svc.load_post(path)
    post.content = content
    post.metadata["updated_at"] = datetime.now(tz=timezone.utc).isoformat()
    md_svc.save_post(path, post)


def patch_doc(
    doc_id: str,
    action: str,
    content: str,
    line_start: Optional[int] = None,
    line_end: Optional[int] = None,
) -> None:
    """增量修改：append / prepend / replace_block。"""
    path = _require_file(doc_id)
    post = md_svc.load_post(path)

    if action == "append":
        post.content = post.content.rstrip("\n") + "\n\n" + content
    elif action == "prepend":
        post.content = content + "\n\n" + post.content.lstrip("\n")
    elif action == "replace_block":
        if line_start is None or line_end is None:
            raise ValueError("replace_block 必须提供 line_start 和 line_end")
        post.content = md_svc.replace_block(post.content, line_start, line_end, content)
    else:
        raise ValueError(f"未知 action: {action}")

    post.metadata["updated_at"] = datetime.now(tz=timezone.utc).isoformat()
    md_svc.save_post(path, post)


def patch_meta(doc_id: str, action: str, **kwargs) -> None:
    """修改 front-matter 元数据，不触碰正文。"""
    path = _require_file(doc_id)
    post = md_svc.load_post(path)

    if action == "add_tags":
        existing = list(post.metadata.get("tags", []))
        for t in kwargs.get("tags", []):
            if t not in existing:
                existing.append(t)
        post.metadata["tags"] = existing
    elif action == "remove_tags":
        existing = list(post.metadata.get("tags", []))
        post.metadata["tags"] = [t for t in existing if t not in kwargs.get("tags", [])]
    elif action == "update_title":
        post.metadata["title"] = kwargs["title"]
    elif action == "update_category":
        post.metadata["category"] = kwargs["category"]
    else:
        raise ValueError(f"未知 meta action: {action}")

    post.metadata["updated_at"] = datetime.now(tz=timezone.utc).isoformat()
    md_svc.save_post(path, post)


def trash_doc(doc_id: str) -> Path:
    """逻辑删除：把文件移到 .trash/ 目录。"""
    path = _require_file(doc_id)
    dest = TRASH_DIR / path.name
    # 防重名
    if dest.exists():
        dest = TRASH_DIR / f"{path.stem}_{uuid.uuid4().hex[:4]}.md"
    shutil.move(str(path), str(dest))
    return dest


# ── 内部工具 ──────────────────────────────────────────────────────────────

def _require_file(doc_id: str) -> Path:
    path = _doc_path(doc_id)
    if not path.exists():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"文档 '{doc_id}' 不存在")
    return path


def _build_meta(md_file: Path, post: frontmatter.Post) -> DocMeta:
    m = post.metadata
    stat = md_file.stat()

    def _parse_dt(val) -> Optional[datetime]:
        if not val:
            return None
        if isinstance(val, datetime):
            return val
        try:
            return datetime.fromisoformat(str(val))
        except Exception:
            return None

    return DocMeta(
        doc_id=md_file.stem,
        title=m.get("title", md_file.stem),
        tags=list(m.get("tags", [])),
        category=m.get("category") or None,
        created_at=_parse_dt(m.get("created_at")) or datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc),
        updated_at=_parse_dt(m.get("updated_at")) or datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
        size_bytes=stat.st_size,
    )
