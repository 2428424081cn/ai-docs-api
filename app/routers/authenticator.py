"""
TOTP 认证接口：
  GET  /api/v1/open/authenticator   获取 secret 和 otpauth URI（初始配置用）
  POST /api/v1/open/authenticator   提交动态码，验证通过返回 publish_token
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services import totp_service as ts

router = APIRouter(prefix="/api/v1/open", tags=["TOTP 认证"])


# ── 响应模型 ──────────────────────────────────────────────────────────────

class AuthenticatorInfo(BaseModel):
    secret: str
    otpauth_uri: str
    tip: str


class VerifyRequest(BaseModel):
    code: str


class TokenResponse(BaseModel):
    publish_token: str
    expires_in_seconds: int


# ── 获取配置信息 ──────────────────────────────────────────────────────────

@router.get(
    "/authenticator",
    response_model=AuthenticatorInfo,
    summary="获取 TOTP 配置信息（初次使用时调用，将 secret 录入 Authenticator App）",
)
def get_authenticator_info():
    secret = ts.get_or_create_secret()
    uri = ts.get_totp_uri(secret)
    return AuthenticatorInfo(
        secret=secret,
        otpauth_uri=uri,
        tip="请将 secret 手动录入 Google Authenticator / Authy / 1Password 等 TOTP App，"
            "或将 otpauth_uri 复制到支持导入 URI 的 App。",
    )


# ── 提交动态码，换取 publish_token ────────────────────────────────────────

@router.post(
    "/authenticator",
    response_model=TokenResponse,
    summary="提交 TOTP 动态码，验证通过后返回一次性 publish_token",
)
def verify_totp(body: VerifyRequest):
    token = ts.verify_totp_and_issue_token(body.code)
    if token is None:
        raise HTTPException(status_code=401, detail="动态码错误或已过期，请重新获取")
    return TokenResponse(
        publish_token=token,
        expires_in_seconds=ts.TOKEN_TTL_MINUTES * 60,
    )
