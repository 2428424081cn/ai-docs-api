"""
Markdown 服务层 —— 大纲解析、HTML 渲染、Front-matter 操作。
"""
import re
from pathlib import Path
from typing import List, Tuple

import frontmatter
import markdown as md_lib

from app.models.schemas import OutlineNode


# ── Front-matter 读写 ──────────────────────────────────────────────────────

def load_post(file_path: Path) -> frontmatter.Post:
    """读取文件，返回 frontmatter.Post 对象（.metadata + .content）。"""
    return frontmatter.load(str(file_path))


def save_post(file_path: Path, post: frontmatter.Post) -> None:
    """将 frontmatter.Post 写回文件（YAML front-matter + Markdown 正文）。"""
    file_path.write_bytes(frontmatter.dumps(post).encode("utf-8"))


# ── 大纲解析 ───────────────────────────────────────────────────────────────

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)")


def extract_outline(content: str) -> List[OutlineNode]:
    """
    从 Markdown 文本中提取标题结构，返回树形列表（仅 H1~H3）。
    同时记录每个标题所在的起始行号（1-indexed）。
    """
    lines = content.splitlines()
    flat: List[Tuple[int, int, str]] = []  # (level, line_no, title)

    for i, line in enumerate(lines, start=1):
        m = _HEADING_RE.match(line)
        if m:
            level = len(m.group(1))
            if level <= 3:
                flat.append((level, i, m.group(2).strip()))

    # 填充 line_end
    nodes: List[OutlineNode] = []
    for idx, (level, line_start, title) in enumerate(flat):
        line_end = flat[idx + 1][1] - 1 if idx + 1 < len(flat) else len(lines)
        nodes.append(OutlineNode(level=level, title=title,
                                 line_start=line_start, line_end=line_end))

    # 构建树（简单栈算法）
    return _build_tree(nodes)


def _build_tree(nodes: List[OutlineNode]) -> List[OutlineNode]:
    root: List[OutlineNode] = []
    stack: List[OutlineNode] = []
    for node in nodes:
        while stack and stack[-1].level >= node.level:
            stack.pop()
        if stack:
            stack[-1].children.append(node)
        else:
            root.append(node)
        stack.append(node)
    return root


# ── 按行号读取块 ───────────────────────────────────────────────────────────

def extract_block(content: str, line_start: int, line_end: int) -> str:
    """
    按行号（1-indexed）截取内容块。
    line_end=-1 表示到文档末尾。
    """
    lines = content.splitlines(keepends=True)
    total = len(lines)
    s = max(0, line_start - 1)
    e = total if line_end == -1 else min(line_end, total)
    return "".join(lines[s:e])


# ── 局部替换 ───────────────────────────────────────────────────────────────

def replace_block(content: str, line_start: int, line_end: int, new_content: str) -> str:
    """将 [line_start, line_end]（1-indexed，含端点）替换为 new_content。"""
    lines = content.splitlines(keepends=True)
    s = max(0, line_start - 1)
    e = min(line_end, len(lines))
    replacement = new_content if new_content.endswith("\n") else new_content + "\n"
    lines[s:e] = [replacement]
    return "".join(lines)


# ── Markdown → HTML ────────────────────────────────────────────────────────

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    body {{ font-family: "Helvetica Neue", Arial, sans-serif;
            max-width: 860px; margin: 40px auto; padding: 0 20px;
            line-height: 1.7; color: #222; }}
    pre  {{ background:#f6f8fa; border-radius:6px; padding:16px; overflow:auto; }}
    code {{ font-family: monospace; }}
    h1,h2,h3 {{ border-bottom: 1px solid #eee; padding-bottom:.3em; }}
    blockquote {{ border-left:4px solid #ddd; margin:0; padding-left:1em; color:#555; }}
  </style>
</head>
<body>
{body}
</body>
</html>
"""


def render_html(title: str, content: str) -> str:
    """将 Markdown 正文渲染为完整的 HTML 页面字符串。"""
    extensions = ["tables", "fenced_code", "toc", "nl2br"]
    body = md_lib.markdown(content, extensions=extensions)
    return _HTML_TEMPLATE.format(title=title, body=body)
