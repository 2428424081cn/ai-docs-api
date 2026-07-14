"""
文档相关接口：
  GET    /api/v1/docs                     列表（分页/过滤）
  POST   /api/v1/docs                     新建
  GET    /api/v1/docs/{doc_id}/outline    大纲
  GET    /api/v1/docs/{doc_id}/content    全文
  GET    /api/v1/docs/{doc_id}/blocks     按行范围读取
  PUT    /api/v1/docs/{doc_id}            全量覆盖
  PATCH  /api/v1/docs/{doc_id}            增量修改
  PATCH  /api/v1/docs/{doc_id}/meta       元数据修改
  DELETE /api/v1/docs/{doc_id}            逻辑删除
  GET    /api/v1/docs/{doc_id}/history    Git 历史
  POST   /api/v1/docs/{doc_id}/rollback   回滚到指定 commit
"""
from typing import List, Optional

from fastapi import APIRouter, Query

from app.models.schemas import (
    DocMeta, DocCreate, DocReplace, DocPatch, MetaPatch,
    OutlineNode, CommitRecord, RollbackRequest, MessageResponse,
)
from app.services import file_service as fs
from app.services import git_service as gs
from app.services import markdown_service as md_svc

router = APIRouter(prefix="/api/v1/docs", tags=["文档管理"])


# ── 列表 ─────────────────────────────────────────────────────────────────

@router.get("", response_model=List[DocMeta], summary="获取文档列表")
def list_docs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    tags: Optional[str] = Query(None, description="逗号分隔的标签过滤，如 tag1,tag2"),
    category: Optional[str] = Query(None),
    sort_by: str = Query("updated_at", pattern="^(updated_at|created_at|title)$"),
):
    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    return fs.list_docs(page=page, limit=limit, tags=tag_list,
                        category=category, sort_by=sort_by)


# ── 新建 ─────────────────────────────────────────────────────────────────

@router.post("", response_model=MessageResponse, status_code=201, summary="新建文档")
def create_doc(body: DocCreate):
    doc_id = fs.create_doc(
        title=body.title,
        content=body.content,
        tags=body.tags,
        category=body.category,
    )
    path = fs._doc_path(doc_id)
    commit_hash = gs.commit(path, f"Agent 创建: {body.title}")
    return MessageResponse(message=f"文档已创建，doc_id={doc_id}", commit_hash=commit_hash)


# ── 大纲 ─────────────────────────────────────────────────────────────────

@router.get("/{doc_id}/outline", response_model=List[OutlineNode], summary="提取文档大纲")
def get_outline(doc_id: str):
    content = fs.get_doc_content(doc_id)
    return md_svc.extract_outline(content)


# ── 全文 ─────────────────────────────────────────────────────────────────

@router.get("/{doc_id}/content", summary="获取文档全文")
def get_content(doc_id: str):
    return {"doc_id": doc_id, "content": fs.get_doc_content(doc_id)}


# ── 按行范围读取块 ─────────────────────────────────────────────────────────

@router.get("/{doc_id}/blocks", summary="按行号范围读取内容块")
def get_blocks(
    doc_id: str,
    line_start: int = Query(..., ge=1, description="起始行号（1-indexed）"),
    line_end: int = Query(-1, description="结束行号（-1 表示到末尾）"),
):
    content = fs.get_doc_content(doc_id)
    block = md_svc.extract_block(content, line_start, line_end)
    return {"doc_id": doc_id, "line_start": line_start, "line_end": line_end, "content": block}


# ── 全量覆盖 ──────────────────────────────────────────────────────────────

@router.put("/{doc_id}", response_model=MessageResponse, summary="全量覆盖文档正文")
def replace_doc(doc_id: str, body: DocReplace):
    fs.replace_doc(doc_id, body.content)
    path = fs._doc_path(doc_id)
    msg = body.commit_message or f"Agent 全量替换: {doc_id}"
    commit_hash = gs.commit(path, msg)
    return MessageResponse(message="文档已全量覆盖", commit_hash=commit_hash)


# ── 增量修改 ──────────────────────────────────────────────────────────────

@router.patch("/{doc_id}", response_model=MessageResponse, summary="增量追加/修改文档")
def patch_doc(doc_id: str, body: DocPatch):
    fs.patch_doc(
        doc_id,
        action=body.action,
        content=body.content,
        line_start=body.line_start,
        line_end=body.line_end,
    )
    path = fs._doc_path(doc_id)
    msg = body.commit_message or f"Agent {body.action}: {doc_id}"
    commit_hash = gs.commit(path, msg)
    return MessageResponse(message=f"已执行 {body.action}", commit_hash=commit_hash)


# ── 元数据修改 ────────────────────────────────────────────────────────────

@router.patch("/{doc_id}/meta", response_model=MessageResponse, summary="修改文档元数据")
def patch_meta(doc_id: str, body: MetaPatch):
    fs.patch_meta(
        doc_id,
        action=body.action,
        tags=body.tags,
        title=body.title,
        category=body.category,
    )
    path = fs._doc_path(doc_id)
    commit_hash = gs.commit(path, f"Agent meta/{body.action}: {doc_id}")
    return MessageResponse(message=f"元数据已更新（{body.action}）", commit_hash=commit_hash)


# ── 逻辑删除 ──────────────────────────────────────────────────────────────

@router.delete("/{doc_id}", response_model=MessageResponse, summary="逻辑删除文档（移入回收站）")
def delete_doc(doc_id: str):
    trash_path = fs.trash_doc(doc_id)
    # 在 Git 中记录：删除原文件，添加 trash 文件
    try:
        commit_hash = gs.commit_multiple(
            [fs._doc_path(doc_id), trash_path],
            f"Agent 逻辑删除: {doc_id} -> .trash/",
        )
    except Exception:
        # trash 文件不在 DOCS_DIR 内，单独处理
        import git
        from app.config import DOCS_DIR
        repo = git.Repo(DOCS_DIR)
        repo.git.rm("--cached", "--ignore-unmatch", f"{doc_id}.md")
        c = repo.index.commit(f"Agent 逻辑删除: {doc_id}")
        commit_hash = c.hexsha[:7]
    return MessageResponse(message=f"文档 '{doc_id}' 已移入回收站", commit_hash=commit_hash)


# ── Git 历史 ──────────────────────────────────────────────────────────────

@router.get("/{doc_id}/history", response_model=List[CommitRecord], summary="查询文档修改历史")
def get_history(doc_id: str, max_count: int = Query(20, ge=1, le=200)):
    path = fs._require_file(doc_id)
    return gs.get_file_history(path, max_count=max_count)


# ── 回滚 ─────────────────────────────────────────────────────────────────

@router.post("/{doc_id}/rollback", response_model=MessageResponse, summary="回滚文档到指定 commit")
def rollback_doc(doc_id: str, body: RollbackRequest):
    path = fs._require_file(doc_id)
    new_hash = gs.rollback_file(path, body.commit_hash)
    return MessageResponse(
        message=f"已回滚到 {body.commit_hash[:7]}，新 commit={new_hash}",
        commit_hash=new_hash,
    )
