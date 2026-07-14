from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime


# ────────────────────────────────────────────────────────────
# 文档元数据
# ────────────────────────────────────────────────────────────
class DocMeta(BaseModel):
    doc_id: str
    title: str
    tags: List[str] = []
    category: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    size_bytes: int = 0


# ────────────────────────────────────────────────────────────
# 大纲节点
# ────────────────────────────────────────────────────────────
class OutlineNode(BaseModel):
    level: int                   # 1=H1, 2=H2, 3=H3 …
    title: str
    line_start: int
    line_end: Optional[int] = None
    children: List["OutlineNode"] = []

OutlineNode.model_rebuild()


# ────────────────────────────────────────────────────────────
# 新建文档
# ────────────────────────────────────────────────────────────
class DocCreate(BaseModel):
    title: str = Field(..., description="文档标题")
    content: str = Field(default="", description="初始正文内容（Markdown）")
    tags: List[str] = Field(default=[], description="标签列表")
    category: Optional[str] = Field(default=None, description="分类")


# ────────────────────────────────────────────────────────────
# 全量覆盖
# ────────────────────────────────────────────────────────────
class DocReplace(BaseModel):
    content: str = Field(..., description="新的完整 Markdown 内容")
    commit_message: Optional[str] = None


# ────────────────────────────────────────────────────────────
# 增量修改（PATCH）
# ────────────────────────────────────────────────────────────
class DocPatch(BaseModel):
    action: Literal["append", "replace_block", "prepend"] = Field(
        ..., description="append=末尾追加 | prepend=头部插入 | replace_block=替换指定行范围"
    )
    content: str = Field(..., description="要写入的 Markdown 内容")
    line_start: Optional[int] = Field(default=None, description="replace_block 时的起始行（1-indexed）")
    line_end: Optional[int] = Field(default=None, description="replace_block 时的结束行（含，1-indexed）")
    commit_message: Optional[str] = None


# ────────────────────────────────────────────────────────────
# 元数据修改（PATCH /meta）
# ────────────────────────────────────────────────────────────
class MetaPatch(BaseModel):
    action: Literal["add_tags", "remove_tags", "update_title", "update_category"] = Field(
        ..., description="元数据操作类型"
    )
    tags: Optional[List[str]] = None
    title: Optional[str] = None
    category: Optional[str] = None


# ────────────────────────────────────────────────────────────
# 关键词检索请求
# ────────────────────────────────────────────────────────────
class SearchRequest(BaseModel):
    query: str = Field(..., description="关键词或正则表达式")
    regex: bool = Field(default=False, description="是否以正则模式匹配")
    limit: int = Field(default=20, ge=1, le=100)


class SearchResult(BaseModel):
    doc_id: str
    title: str
    snippet: str
    line_number: int


# ────────────────────────────────────────────────────────────
# Git 历史记录条目
# ────────────────────────────────────────────────────────────
class CommitRecord(BaseModel):
    commit_hash: str
    short_hash: str
    message: str
    author: str
    timestamp: datetime


# ────────────────────────────────────────────────────────────
# 回滚请求
# ────────────────────────────────────────────────────────────
class RollbackRequest(BaseModel):
    commit_hash: str = Field(..., description="目标 commit hash（完整或短格式均可）")


# ────────────────────────────────────────────────────────────
# 公网发布
# ────────────────────────────────────────────────────────────
class PublishRequest(BaseModel):
    doc_id: str
    publish_token: str = Field(..., description="由 POST /api/v1/open/authenticator 颁发的一次性 token")
    expire_in_hours: Optional[int] = Field(
        default=None, description="有效期（小时），None 表示永久"
    )


class ShareRecord(BaseModel):
    uuid: str
    doc_id: str
    title: str
    url: str
    published_at: datetime
    expires_at: Optional[datetime] = None


# ────────────────────────────────────────────────────────────
# 通用响应
# ────────────────────────────────────────────────────────────
class MessageResponse(BaseModel):
    message: str
    commit_hash: Optional[str] = None
