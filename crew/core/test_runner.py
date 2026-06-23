from dataclasses import dataclass
import logging
import os
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ET

from crew.core.config import settings


logger = logging.getLogger(__name__)


TEST_TIMEOUT: int = 300

_TAIL_CHARS: int = 4000


@dataclass
class TestResult:
    passed: bool
    returncode: int
    output: str  # combined stdout+stderr
    failures: list[str]  # ids of tests that failed or errored

    @property
    def summary(self) -> str:
        return "pytest PASSED" if self.passed else f"pytest FAILED (exit {self.returncode})"


def _setup_test_env(repo_path: Path) -> Path:
    """Create once (and reuse) a virtual env that has the target repo + `pytest`.

    The venv lives outside the cloned repo, so editable-install and cache
    artifacts never end up in the diff or the PR.
    """
    venv = settings.WORKSPACE_DIR / ".venvs" / repo_path.name
    bin = "Scripts" if os.name == "nt" else "bin"
    python = venv / bin / ("python.exe" if os.name == "nt" else "python")
    if not python.exists():
        logger.info("Creating test environment at %s", venv)
        subprocess.run(["uv", "venv", str(venv)], check=True, capture_output=True, text=True)
        # Install the target editable (-e)
        subprocess.run(
            ["uv", "pip", "install", "--python", str(python), "-e", str(repo_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        # Ensure `pytest` regardless of how the target declares its test dependencies
        subprocess.run(
            ["uv", "pip", "install", "--python", str(python), "pytest"],
            check=True,
            capture_output=True,
            text=True,
        )
    return python


def _parse_failures(test_report: Path) -> list[str]:
    if not test_report.exists():
        return []
    failures: list[str] = []
    for t in ET.parse(test_report).iter("testcase"):
        if any(child.tag in ("failure", "error") for child in t):
            class_name, name = t.get("classname", ""), t.get("name", "")
            failures.append(f"{class_name}::{name}" if class_name else name)
    return failures


def run_tests(repo_path: Path | None = None, target: str | None = None) -> TestResult:
    """Run pytest in the cloned target repo and return a structured result.

    Args:
        repo_path: path of repo to test; defaults to the active workspace clone.
        target: (optional) pytest path / node id to narrow the run (e.g `target="tests/test_stats.py"`)
    """
    repo_path = repo_path or settings.REPO_PATH
    python = _setup_test_env(repo_path)

    fd, name = tempfile.mkstemp(suffix=".xml")
    os.close(fd)
    report = Path(name)

    cmd = [str(python), "-m", "pytest", "-q", f"--junitxml={report}"]
    if target:
        cmd.append(target)

    logger.info("Running tests: pytest %s (cwd=%s)", target or "", repo_path)
    try:
        proc = subprocess.run(
            cmd, cwd=repo_path, capture_output=True, text=True, timeout=TEST_TIMEOUT
        )  # Don't `check=True` on the pytest call. Failing tests are the expected signal, not an exception
    except subprocess.TimeoutExpired:
        report.unlink(missing_ok=True)
        return TestResult(False, -1, f"Test run timed out after {TEST_TIMEOUT}s.", [])

    failures = _parse_failures(report)
    report.unlink(missing_ok=True)

    output = (proc.stdout or "") + (proc.stderr or "")
    if len(output) > _TAIL_CHARS:
        output = "... (truncated)\n" + output[-_TAIL_CHARS:]
    passed = proc.returncode == 0
    logger.info(
        "Tests %s (exit %d), %d failure(s)",
        "passed" if passed else "failed",
        proc.returncode,
        len(failures),
    )
    return TestResult(passed, proc.returncode, output, failures)
