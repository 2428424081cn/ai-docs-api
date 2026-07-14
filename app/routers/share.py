"""
公网分享接口：
  POST   /api/v1/share/publish   发布文档为静态 HTML
  GET    /api/v1/share            获取已发布列表
  DELETE /api/v1/share/{uuid}    撤销公开链接
"""
import json
import uuid as _uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException

from app.config import SHARED_DIR, PUBLIC_BASE_URL
from app.models.schemas import PublishRequest, ShareRecord, MessageResponse
from app.services import totp_service as ts
from app.services import file_service as fs
from app.services import markdown_service as md_svc

router = APIRouter(prefix="/api/v1/share", tags=["公网分享"])

# 分享记录索引文件
_INDEX_FILE = SHARED_DIR / "_share_index.json"


def _load_index() -> dict:
    if _INDEX_FILE.exists():
        return json.loads(_INDEX_FILE.read_text(encoding="utf-8"))
    return {}


def _save_index(index: dict) -> None:
    _INDEX_FILE.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


# ── 发布 ─────────────────────────────────────────────────────────────────

@router.post("/publish", response_model=ShareRecord, status_code=201, summary="发布文档到只读公网区（需携带 publish_token）")
def publish_doc(body: PublishRequest):
    # ── TOTP Token 校验 ──────────────────────────────────────────────────
    if not body.publish_token:
        raise HTTPException(
            status_code=403,
            detail="发布需要先通过 TOTP 验证：POST /api/v1/open/authenticator 获取 publish_token",
        )
    if not ts.validate_publish_token(body.publish_token):
        raise HTTPException(
            status_code=403,
            detail="publish_token 无效或已过期（有效期5分钟，且仅限使用一次）",
        )
    # ────────────────────────────────────────────────────────────────────
    meta = fs.get_doc_meta(body.doc_id)
    content = fs.get_doc_content(body.doc_id)

    # 生成 UUID 并渲染 HTML
    share_uuid = _uuid.uuid4().hex[:8]
    html_content = md_svc.render_html(meta.title, content)
    html_path = SHARED_DIR / f"{share_uuid}.html"
    html_path.write_text(html_content, encoding="utf-8")

    # 计算过期时间
    now = datetime.now(tz=timezone.utc)
    expires_at: Optional[datetime] = None
    if body.expire_in_hours:
        expires_at = now + timedelta(hours=body.expire_in_hours)

    # 写入索引
    index = _load_index()
    index[share_uuid] = {
        "doc_id": body.doc_id,
        "title": meta.title,
        "published_at": now.isoformat(),
        "expires_at": expires_at.isoformat() if expires_at else None,
    }
    _save_index(index)

    url = f"{PUBLIC_BASE_URL}/{share_uuid}.html"
    return ShareRecord(
        uuid=share_uuid,
        doc_id=body.doc_id,
        title=meta.title,
        url=url,
        published_at=now,
        expires_at=expires_at,
    )


# ── 列表 ─────────────────────────────────────────────────────────────────

@router.get("", response_model=List[ShareRecord], summary="获取已发布文档列表")
def list_shares():
    index = _load_index()
    records: List[ShareRecord] = []
    now = datetime.now(tz=timezone.utc)

    for share_uuid, info in index.items():
        # 跳过已过期（但不自动删文件，保留到主动撤销）
        expires_at = None
        if info.get("expires_at"):
            expires_at = datetime.fromisoformat(info["expires_at"])

        records.append(ShareRecord(
            uuid=share_uuid,
            doc_id=info["doc_id"],
            title=info["title"],
            url=f"{PUBLIC_BASE_URL}/{share_uuid}.html",
            published_at=datetime.fromisoformat(info["published_at"]),
            expires_at=expires_at,
        ))

    return sorted(records, key=lambda r: r.published_at, reverse=True)


# ── 撤销 ─────────────────────────────────────────────────────────────────

@router.delete("/{share_uuid}", response_model=MessageResponse, summary="撤销公开链接")
def revoke_share(share_uuid: str):
    index = _load_index()
    if share_uuid not in index:
        raise HTTPException(status_code=404, detail=f"分享记录 '{share_uuid}' 不存在")

    # 删除 HTML 静态文件
    html_path = SHARED_DIR / f"{share_uuid}.html"
    if html_path.exists():
        html_path.unlink()

    # 从索引中移除
    del index[share_uuid]
    _save_index(index)

    return MessageResponse(message=f"链接 {share_uuid} 已撤销，静态文件已删除")
