"""
Filesystem tools the agents use to read and edit the target repo.

Every path is interpreted relative to the cloned target repo and confined to it.
Traversal outside the repo are refused.
These are plain functions. The Planner/Coder nodes bind them as LangChain tools.
"""

import logging
import re
from pathlib import Path

from langchain.tools import tool

from crew.core.config import settings

logger = logging.getLogger(__name__)

# Cap search output so a broad query can't flood the agent's context.
MAX_SEARCH_RESULTS = 100

# Cap a single file read so a large file can't blow up the context window.
MAX_FILE_BYTES = 256 * 1024

# Files the crew must not see.
BLOCKED_FILES = ["docs/ANSWER_KEY.md"]

# Directories the crew must not see or search
EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
}


def _root() -> Path:
    return settings.REPO_PATH.resolve()


def _resolve(path: str) -> Path:
    """Resolve a path relative to repo, refusing path references (../),
    files outside the repo and restricted files."""
    root = _root()
    target = (root / path).resolve()
    if not target.is_relative_to(root):
        raise ValueError(f"Path escapes the repository: {path!r}")
    rel_path = target.relative_to(root).as_posix()
    if rel_path in BLOCKED_FILES or rel_path.startswith(".git/"):
        raise ValueError(f"Access to {path!r} is not allowed")
    return target


def is_excluded(path: Path) -> bool:
    """Return True if path is a blocked file or lives under an excluded directory."""
    rel = path.resolve().relative_to(_root())
    if rel.as_posix() in BLOCKED_FILES:
        return True
    return any(part in EXCLUDE_DIRS for part in rel.parts)


def _iter_files(path: Path):
    for p in sorted(path.rglob("*")):
        if p.is_file() and not is_excluded(p):
            yield p


@tool
def list_dir(directory: str = ".") -> str:
    """List files in the repository recursively.

    Args:
        subdir: (Optional) sub-directory to scope the listed files to; Defaults to repo root (".")
    """

    root = _root()
    base = root if directory in ("", ".") else _resolve(directory)
    if not base.is_dir():
        raise FileNotFoundError(f"Invalid directory: {directory!r}")
    paths = [p.relative_to(root).as_posix() for p in _iter_files(base)]
    return "\n".join(paths) if paths else "Directory is empty (no files found)."


@tool
def read_file(path: str, offset: int = 0, limit: int = 500) -> str:
    """Read a file from the repository.

    Args:
        path: Repo-relative path, e.g. "src/taskvault/tasks.py".
        offset: (0-based) line to start reading at.
        limit: Max number of lines to return.

    Relative paths are resolved against the repository.
    Raises ValueError if the resolved path escapes the workspace directory.
    """
    p = _resolve(path)
    if p.is_dir():
        return f"{path!r} is a directory. Use `list_dir()` to list files in a directory."
    if not p.is_file():
        return f"File {path!r} does not exist."
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    window = lines[offset : offset + limit]
    content = "\n".join(window)
    if offset + limit < len(lines):
        content += (
            f"\n... ({len(lines) - offset - limit} more lines; call with `offset={offset + limit}`)"
        )
    return content


@tool
def write_file(path: str, content: str) -> str:
    """Write content to a file, truncating it first if it exists. Creates parent
    directories as needed.

    Args:
        path: Repo-relative path of the file to write.
        content: Full content to write to the file.
    """
    target = _resolve(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} characters to {path!r}."


@tool
def search(query: str, subdir: str = ".") -> str:
    """Search the repository for lines matching a regular expression (grep-like).

    Args:
        query: Regular expression to search for.
        subdir: Optional sub-directory to scope the search to.

    Returns matching lines formatted as "path:line_number: line".
    """
    try:
        pattern = re.compile(query)
    except re.error as e:
        raise ValueError(f"Invalid search pattern {query!r}: {e}") from e

    root = _root()
    base = root if subdir in ("", ".") else _resolve(subdir)
    if not base.is_dir():
        raise FileNotFoundError(f"Invalid directory: {subdir!r}")

    matches: list[str] = []
    for p in _iter_files(base):
        rel = p.relative_to(root).as_posix()
        try:
            with p.open(encoding="utf-8") as file:
                for line_num, line in enumerate(file, start=1):
                    if pattern.search(line):
                        matches.append(f"{rel}:{line_num}: {line.strip()}")
                        if len(matches) >= MAX_SEARCH_RESULTS:
                            matches.append(f"... (truncated at {MAX_SEARCH_RESULTS} matches)")
                            return "\n".join(matches)
        except (UnicodeDecodeError, OSError):
            continue  # skip binary/unreadable files

    return "\n".join(matches) if matches else f"No matches found for {query!r}."


@tool
def edit_file(path: str, old_string: str, new_string: str, replace_all: bool = False) -> str:
    """Replace text in a file.

    Args:
        path: Repo-relative path of the file to edit.
        old_string: Exact text to replace. Must be unique unless replace_all is True.
        new_string: Text to replace it with.
        replace_all: Replace every occurrence instead of requiring a unique match.
    """
    target = _resolve(path)
    if not target.is_file():
        raise FileNotFoundError(f"File {path!r} does not exist.")

    text = target.read_text(encoding="utf-8")
    count = text.count(old_string)
    if count == 0:
        raise ValueError(f"old_string not found in {path!r}.")
    if count > 1 and not replace_all:
        raise ValueError(
            f"old_string is not unique in {path!r} ({count} occurrences); "
            "pass replace_all=True or provide more surrounding context."
        )

    text = text.replace(old_string, new_string)
    target.write_text(text, encoding="utf-8")
    return f"Replaced {count} occurrence(s) in {path!r}."
