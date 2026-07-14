"""
搜索接口：
  POST /api/v1/search/keyword   关键词（支持正则）全文检索
"""
from fastapi import APIRouter
from typing import List

from app.models.schemas import SearchRequest, SearchResult
from app.config import DOCS_DIR
from app.services import markdown_service as md_svc
import re

router = APIRouter(prefix="/api/v1/search", tags=["智能检索"])


@router.post("/keyword", response_model=List[SearchResult], summary="关键词全文检索")
def keyword_search(body: SearchRequest):
    results: List[SearchResult] = []

    try:
        if body.regex:
            pattern = re.compile(body.query, re.IGNORECASE)
        else:
            pattern = re.compile(re.escape(body.query), re.IGNORECASE)
    except re.error as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"正则表达式错误: {e}")

    for md_file in sorted(DOCS_DIR.glob("*.md")):
        try:
            import frontmatter
            post = frontmatter.load(str(md_file))
        except Exception:
            continue

        title = post.metadata.get("title", md_file.stem)
        lines = post.content.splitlines()

        for lineno, line in enumerate(lines, start=1):
            if pattern.search(line):
                # 生成摘要片段（前后各 60 字符）
                m = pattern.search(line)
                start = max(0, m.start() - 60)
                snippet = ("…" if start > 0 else "") + line[start:m.end() + 60].strip()
                results.append(SearchResult(
                    doc_id=md_file.stem,
                    title=title,
                    snippet=snippet,
                    line_number=lineno,
                ))
                if len(results) >= body.limit:
                    return results

    return results
