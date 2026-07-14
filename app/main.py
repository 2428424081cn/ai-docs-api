"""
FastAPI 应用入口。
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import SHARED_DIR
from app.routers import docs, search, share, authenticator

app = FastAPI(
    title="AI 驱动文档管理系统",
    description=(
        "一个以 AI Agent 为核心用户的 Markdown 知识库 API。\n\n"
        "- 支持按块读取、大纲解析、增量修改（PATCH）\n"
        "- 底层 Git 全量历史，任意回滚\n"
        "- 静态 HTML 生成，对接 Nginx 公网发布\n"
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 允许本机 Agent/脚本跨域调用
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(docs.router)
app.include_router(search.router)
app.include_router(share.router)
app.include_router(authenticator.router)

# 挂载静态文件：发布的 HTML 页面可直接通过 /shared/{uuid}.html 访问
# 生产环境中可改由 Nginx 接管此目录
app.mount("/shared", StaticFiles(directory=str(SHARED_DIR)), name="shared")


@app.get("/", tags=["健康检查"])
def root():
    return {"status": "ok", "message": "AI 驱动文档管理系统运行中 🚀"}
