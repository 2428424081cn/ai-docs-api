#!/usr/bin/env python
"""
快速启动脚本：直接运行 `python run.py` 即可。
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["app"],
    )
