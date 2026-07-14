import os
from pathlib import Path

# ── 项目根 ──────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# ── 文档存储根目录（Git 仓库） ───────────────────────────
DOCS_DIR = BASE_DIR / "docs"

# ── 逻辑回收站（不物理删除，只挪到这里） ──────────────────
TRASH_DIR = BASE_DIR / ".trash"

# ── Nginx 静态文件目录（公网分享 HTML） ────────────────────
SHARED_DIR = BASE_DIR / "shared"

# ── Whoosh 搜索索引目录 ────────────────────────────────────
INDEX_DIR = BASE_DIR / ".index"

# ── 公网访问域名前缀（如有 Nginx 配置，修改此处） ────────────
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000/shared")

# ── FastAPI 服务监听端口 ──────────────────────────────────
API_PORT = int(os.getenv("API_PORT", "8000"))

# ── 确保所有目录存在 ─────────────────────────────────────
for _d in [DOCS_DIR, TRASH_DIR, SHARED_DIR, INDEX_DIR]:
    _d.mkdir(parents=True, exist_ok=True)
