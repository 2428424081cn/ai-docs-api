"""
TOTP 认证服务层（纯 API，无二维码）。

流程：
  1. GET  /api/v1/open/authenticator  → 返回 secret + otpauth_uri（录入 Authenticator App）
  2. POST /api/v1/open/authenticator  → 提交动态码 → 返回一次性 publish_token（5分钟有效）
  3. POST /api/v1/share/publish       → 携带 publish_token → 校验通过才允许发布
"""
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import pyotp

from app.config import BASE_DIR

# ── Secret 持久化 ──────────────────────────────────────────────────────────
_SECRET_FILE = BASE_DIR / ".totp_secret"


def get_or_create_secret() -> str:
    """读取或生成 TOTP Base32 密钥，持久化到项目根目录的 .totp_secret 文件。"""
    if _SECRET_FILE.exists():
        return _SECRET_FILE.read_text(encoding="utf-8").strip()
    secret = pyotp.random_base32()
    _SECRET_FILE.write_text(secret, encoding="utf-8")
    return secret


def get_totp_uri(secret: str, account: str = "AI文档系统") -> str:
    """生成 otpauth:// URI，可手动录入 Google Authenticator / Authy 等 App。"""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=account, issuer_name="AI-Docs")


# ── Token 内存缓存（一次性，5 分钟有效） ────────────────────────────────────
_valid_tokens: dict[str, datetime] = {}
TOKEN_TTL_MINUTES = 5


def _purge_expired() -> None:
    now = datetime.now(tz=timezone.utc)
    expired = [t for t, exp in _valid_tokens.items() if exp < now]
    for t in expired:
        del _valid_tokens[t]


def verify_totp_and_issue_token(code: str) -> Optional[str]:
    """
    验证 TOTP 动态码（允许 ±30s 窗口容错）。
    验证通过 → 生成并缓存 publish_token，返回 token 字符串。
    验证失败 → 返回 None。
    """
    secret = get_or_create_secret()
    totp = pyotp.TOTP(secret)
    if not totp.verify(code, valid_window=1):
        return None

    _purge_expired()
    token = uuid.uuid4().hex
    _valid_tokens[token] = datetime.now(tz=timezone.utc) + timedelta(minutes=TOKEN_TTL_MINUTES)
    return token


def validate_publish_token(token: str) -> bool:
    """
    校验 publish_token 是否有效（存在且未过期）。
    通过后立即销毁——一次性使用。
    """
    _purge_expired()
    exp = _valid_tokens.get(token)
    if exp is None:
        return False
    del _valid_tokens[token]
    return True
