"""
Git 服务层 —— 封装所有 GitPython 操作。
每次文档写操作完成后调用 commit()，保证任意修改都有历史可回溯。
"""
from pathlib import Path
from datetime import datetime, timezone
from typing import List

import git

from app.config import DOCS_DIR
from app.models.schemas import CommitRecord


def _get_repo() -> git.Repo:
    """获取（或初始化）文档目录的 Git 仓库。"""
    try:
        return git.Repo(DOCS_DIR)
    except git.InvalidGitRepositoryError:
        repo = git.Repo.init(DOCS_DIR)
        # 写一个初始占位文件，保证第一次 commit 能成功
        readme = DOCS_DIR / ".gitkeep"
        readme.touch()
        repo.index.add([".gitkeep"])
        repo.index.commit("chore: init docs repository")
        return repo


def commit(file_path: Path, message: str) -> str:
    """
    对 file_path 执行 git add + git commit。
    返回新的 commit hash（短格式 7 位）。
    """
    repo = _get_repo()
    # 转换为相对于 DOCS_DIR 的路径
    try:
        rel = str(file_path.relative_to(DOCS_DIR))
    except ValueError:
        rel = str(file_path)

    repo.index.add([rel])
    c = repo.index.commit(message)
    return c.hexsha[:7]


def commit_multiple(file_paths: List[Path], message: str) -> str:
    """一次性提交多个文件。"""
    repo = _get_repo()
    rels = []
    for fp in file_paths:
        try:
            rels.append(str(fp.relative_to(DOCS_DIR)))
        except ValueError:
            rels.append(str(fp))
    repo.index.add(rels)
    c = repo.index.commit(message)
    return c.hexsha[:7]


def get_file_history(file_path: Path, max_count: int = 50) -> List[CommitRecord]:
    """查询某个文件的 Git 提交历史。"""
    repo = _get_repo()
    try:
        rel = str(file_path.relative_to(DOCS_DIR))
    except ValueError:
        rel = str(file_path)

    records: List[CommitRecord] = []
    for commit in repo.iter_commits(paths=rel, max_count=max_count):
        ts = datetime.fromtimestamp(commit.committed_date, tz=timezone.utc)
        records.append(CommitRecord(
            commit_hash=commit.hexsha,
            short_hash=commit.hexsha[:7],
            message=commit.message.strip(),
            author=str(commit.author),
            timestamp=ts,
        ))
    return records


def rollback_file(file_path: Path, commit_hash: str) -> str:
    """
    将指定文件回滚到 commit_hash 时的版本，
    然后生成一条新 commit 记录（不销毁历史）。
    返回新 commit 的短 hash。
    """
    repo = _get_repo()
    try:
        rel = str(file_path.relative_to(DOCS_DIR))
    except ValueError:
        rel = str(file_path)

    # checkout 指定版本的文件内容到工作区
    repo.git.checkout(commit_hash, "--", rel)
    # 重新 commit，保留完整历史
    repo.index.add([rel])
    c = repo.index.commit(
        f"rollback: restore {rel} to {commit_hash[:7]}"
    )
    return c.hexsha[:7]
