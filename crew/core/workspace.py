import base64
import logging
import subprocess
from pathlib import Path

from crew.core.config import settings

logger = logging.getLogger(__name__)


class GitRepo:
    """Runs authenticated git commands against a local checkout at ``repo_path``."""

    def __init__(self, repo_path: str | Path) -> None:
        self.repo_path = Path(repo_path)

    # --- internals ----

    @staticmethod
    def _auth_args() -> list[str]:
        if not settings.GITHUB_TOKEN:
            return []
        access_token = base64.b64encode(f"x-access-token:{settings.GITHUB_TOKEN}".encode()).decode()
        return ["-c", f"http.extraHeader=Authorization: Basic {access_token}"]

    @classmethod
    def _run(cls, cwd: str | Path, *args: str) -> str:
        """Run a git command inside the repository and return its stdout.

        Raises subprocess.CalledProcessError if git exits non-zero.
        """
        cmd = ["git", *cls._auth_args(), *args]
        safe = ["******" if a.startswith("http.extraHeader") else a for a in cmd]
        logger.debug("Running: %s (cwd=%s)", " ".join(safe), cwd)
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    def _git(self, *args: str) -> str:
        return self._run(self.repo_path, *args)

    # --- lifecycle ---

    @classmethod
    def clone(cls, repo_url: str, repo_path: Path) -> "GitRepo":
        """Clone a repository into the workspace directory (git clone <repo>)"""
        logger.info("Cloning repository %s into workspace", repo_url)
        cls._run(settings.WORKSPACE_DIR, "clone", "--depth", "1", repo_url)
        return cls(repo_path)

    def exists(self) -> bool:
        """Check if a git repo exists at given path"""
        if not self.repo_path.is_dir():
            return False
        try:
            p = self._git("rev-parse", "--show-toplevel")
            return Path(p) == self.repo_path.resolve()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    # --- git operations ---

    @property
    def default_branch(self) -> str:
        """Return the remote's default branch (e.g. 'main'), falling back to 'main'."""
        try:
            ref = self._git("symbolic-ref", "refs/remotes/origin/HEAD")
            return ref.rsplit("/", 1)[-1]
        except subprocess.CalledProcessError:
            return "main"

    def pull(self) -> str:
        """Update the checkout to the latest remote state (git pull)."""
        logger.info("Pulling latest changes in %s", self.repo_path)
        return self._git("pull")

    def checkout(self, branch: str, create: bool = False) -> str:
        """Switch to `branch` (default).
        If `create=True`, create/reset branch (git checkout -B)."""
        args = ["checkout", "-B", branch] if create else ["checkout", branch]
        return self._git(*args)

    def delete_branch(self, branch: str) -> str:
        """Delete a local branch (git branch -d <branch>)."""
        return self._git("branch", "-d", branch)

    def diff(self) -> str:
        """Unified diff of all working-tree changes, including new files."""
        self._git("add", "-N", ".")  # `--intent-to-add` flag so untracked files show up
        return self._git("diff")

    def commit(self, message: str) -> str | None:
        """Stage everything and commit (git add -A && git commit -m <message>).
        Returns the new commit SHA, or None if clean.
        """
        self._git("add", "--all")
        if not self._git("status", "--porcelain"):
            logger.info("Nothing to commit in %s", self.repo_path)
            return None
        self._git(
            "-c", f"user.name={settings.GIT_AUTHOR_NAME}",
            "-c", f"user.email={settings.GIT_AUTHOR_EMAIL}",
            "commit", "-m", message,
        )
        return self._git("rev-parse", "HEAD")

    def push(self, branch: str) -> str:
        """Push changes to remote and set upstream remote tracking"""
        return self._git("push", "--set-upstream", "origin", branch)


def init_workspace(issue_number: int) -> tuple[GitRepo, str]:
    """Clone/pull the repo and create a checkout branch for the given issue."""
    repo = GitRepo(settings.REPO_PATH)
    if repo.exists():
        repo.checkout(repo.default_branch)
        repo.pull()
    else:
        repo_url = f"https://github.com/{settings.GITHUB_REPO}.git"
        repo = GitRepo.clone(repo_url, settings.REPO_PATH)

    # create branch with issue number
    branch = f"crew/issue-{issue_number}"
    repo.checkout(branch, create=True)

    return repo, branch
