# AI 驱动文档管理系统

以 AI Agent 为核心用户的轻量级 Markdown 知识库，底层 Git 保证数据安全。

## 目录结构

```
AI驱动文档/
├── app/
│   ├── main.py                  # FastAPI 入口
│   ├── config.py                # 路径/域名配置
│   ├── models/schemas.py        # Pydantic 数据模型
│   ├── routers/
│   │   ├── docs.py              # 文档管理（CRUD + 大纲 + 块读取 + 历史 + 回滚）
│   │   ├── search.py            # 关键词/正则检索
│   │   └── share.py             # 公网 HTML 发布
│   └── services/
│       ├── file_service.py      # 文件读写 + 逻辑删除
│       ├── git_service.py       # Git commit / log / rollback
│       └── markdown_service.py  # 大纲解析 / 块操作 / HTML 渲染
├── docs/                        # 文档根目录（自动 git init）
├── .trash/                      # 逻辑回收站
├── shared/                      # Nginx 静态文件目录
├── run.py                       # 快速启动
└── requirements.txt
```

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动服务（热重载）
python run.py

# 3. 打开交互式 API 文档
# http://localhost:8000/docs
```

## 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `PUBLIC_BASE_URL` | `http://localhost:8080` | Nginx 公网域名前缀 |
| `API_PORT` | `8000` | API 监听端口 |

## API 概览

### 文档管理 `/api/v1/docs`

| Method | Path | 说明 |
|--------|------|------|
| GET | `/api/v1/docs` | 列表（分页/标签/分类过滤） |
| POST | `/api/v1/docs` | 新建文档 |
| GET | `/api/v1/docs/{id}/outline` | 提取标题大纲树 |
| GET | `/api/v1/docs/{id}/content` | 获取全文 |
| GET | `/api/v1/docs/{id}/blocks` | 按行号读取块 |
| PUT | `/api/v1/docs/{id}` | 全量覆盖 |
| PATCH | `/api/v1/docs/{id}` | 增量追加/替换块 |
| PATCH | `/api/v1/docs/{id}/meta` | 修改元数据（tags/title） |
| DELETE | `/api/v1/docs/{id}` | 逻辑删除→回收站 |
| GET | `/api/v1/docs/{id}/history` | Git 提交历史 |
| POST | `/api/v1/docs/{id}/rollback` | 一键回滚到指定 commit |

### 检索 `/api/v1/search`

| Method | Path | 说明 |
|--------|------|------|
| POST | `/api/v1/search/keyword` | 关键词/正则全文检索 |

### 公网分享 `/api/v1/share`

| Method | Path | 说明 |
|--------|------|------|
| POST | `/api/v1/share/publish` | 渲染 HTML 并发布 |
| GET | `/api/v1/share` | 查看已发布列表 |
| DELETE | `/api/v1/share/{uuid}` | 撤销公开链接 |

## Nginx 配置参考

```nginx
server {
    listen 8080;
    root /path/to/AI驱动文档/shared;
    location / {
        try_files $uri $uri/ =404;
        add_header Cache-Control "no-store";
    }
}
```
