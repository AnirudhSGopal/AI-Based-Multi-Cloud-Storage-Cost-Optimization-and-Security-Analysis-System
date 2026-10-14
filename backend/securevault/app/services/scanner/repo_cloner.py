"""
Repository cloner.
Uses GitPython to do a shallow clone (depth=1) of a remote repository
into an isolated temporary directory under CLONE_BASE_DIR.
The caller is responsible for clean-up (use the context manager).
"""
import base64
import ipaddress
import logging
import os
import re
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator
from urllib.parse import urlsplit

from flask import current_app
from git import GitCommandError, InvalidGitRepositoryError, Repo

logger = logging.getLogger(__name__)


class CloneError(RuntimeError):
    """Raised when cloning fails for any reason."""


@contextmanager
def cloned_repo(repo_url: str, branch: str = "main") -> Generator[str, None, None]:
    """
    Context manager: clone *repo_url* at *branch* into a temp directory.

    Usage::
        with cloned_repo("https://github.com/org/repo", "main") as path:
            # path is the local directory
            ...
        # directory is deleted after the with-block

    Raises:
        CloneError on any git failure.
    """
    safe_repo_url = validate_repo_url(repo_url)
    safe_branch = validate_branch(branch)
    configured_base = current_app.config.get("CLONE_BASE_DIR")
    base_dir = (
        Path(configured_base).expanduser()
        if configured_base
        else Path(tempfile.gettempdir()) / "securevault_repos"
    ).resolve()
    base_dir.mkdir(parents=True, exist_ok=True)
    clone_dir = Path(tempfile.mkdtemp(dir=base_dir, prefix="sv_")).resolve()

    clone_env = {
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_ALLOW_PROTOCOL": "https",
        "GIT_CONFIG_NOSYSTEM": "1",
    }
    github_token = current_app.config.get("GITHUB_TOKEN")
    if github_token and github_token.strip() and github_token.strip() != "your_github_token_here":
        basic_auth = base64.b64encode(
            f"x-access-token:{github_token.strip()}".encode("utf-8")
        ).decode("ascii")
        clone_env.update({
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "http.https://github.com/.extraheader",
            "GIT_CONFIG_VALUE_0": f"AUTHORIZATION: basic {basic_auth}",
        })

    logger.info("Cloning repository %s", safe_repo_url)
    try:
        Repo.clone_from(
            safe_repo_url,
            str(clone_dir),
            depth=1,
            branch=safe_branch,
            env=clone_env,
            multi_options=["--config", "core.hooksPath=/dev/null", "--no-recurse-submodules"],
        )
        _check_size(str(clone_dir))
        yield str(clone_dir)
    except GitCommandError as exc:
        raise CloneError("Git clone failed for the validated GitHub repository") from exc
    except InvalidGitRepositoryError as exc:
        raise CloneError("The cloned GitHub repository is invalid") from exc
    finally:
        _cleanup(clone_dir, base_dir)


def validate_repo_url(repo_url: str) -> str:
    """Return a canonical GitHub HTTPS URL or reject untrusted input."""
    if not isinstance(repo_url, str) or not repo_url or repo_url.startswith("-"):
        raise CloneError("Repository URL is invalid")

    try:
        parsed = urlsplit(repo_url)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise CloneError("Repository URL is invalid") from exc

    if (
        parsed.scheme.lower() != "https"
        or hostname is None
        or hostname.lower() != "github.com"
        or parsed.username is not None
        or parsed.password is not None
        or port not in (None, 443)
        or parsed.query
        or parsed.fragment
    ):
        raise CloneError("Only credential-free HTTPS GitHub repository URLs are allowed")

    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        raise CloneError("IP-literal repository hosts are not allowed")

    if not re.fullmatch(r"/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?/?", parsed.path):
        raise CloneError("Repository URL must identify a GitHub owner and repository")

    return f"https://github.com{parsed.path.rstrip('/')}"


def validate_branch(branch: str) -> str:
    """Accept a simple Git branch/ref without option or revision syntax."""
    if (
        not isinstance(branch, str)
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,127}", branch)
        or ".." in branch
        or "//" in branch
        or "@{" in branch
        or branch.endswith(("/", ".", ".lock"))
        or any(part.startswith(".") or part.endswith(".") for part in branch.split("/"))
    ):
        raise CloneError("Repository branch is invalid")
    return branch


# ── Helpers ───────────────────────────────────────────────────────────────────

def _check_size(clone_dir: str):
    """Raise CloneError if the cloned repo exceeds the configured size limit."""
    max_mb = current_app.config.get("MAX_REPO_SIZE_MB", 500)
    
    # Highly optimized size calculation: skip .git and node_modules on Windows
    total_bytes = 0
    ignore_dirs = {'.git', 'node_modules', 'venv', '.venv'}
    for root, dirs, filenames in os.walk(clone_dir):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for fname in filenames:
            fpath = os.path.join(root, fname)
            try:
                total_bytes += os.path.getsize(fpath)
            except OSError as exc:
                raise CloneError(
                    "Unable to validate the cloned repository size"
                ) from exc
                
    total_mb = total_bytes / (1024 * 1024)
    if total_mb > max_mb:
        raise CloneError(
            f"Repository size {total_mb:.1f} MB exceeds the limit of {max_mb} MB."
        )


def _cleanup(clone_dir: Path, base_dir: Path):
    """Remove the clone directory, handling Windows read-only file lock issues."""
    import stat

    resolved_dir = clone_dir.resolve()
    if resolved_dir.parent != base_dir.resolve() or not resolved_dir.name.startswith("sv_"):
        logger.error("Refusing to clean up an unexpected clone path")
        return

    def remove_readonly(func, path, excinfo):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    try:
        shutil.rmtree(resolved_dir, onerror=remove_readonly)
        logger.debug("Cleaned up temporary repository clone")
    except Exception as exc:
        logger.warning("Failed to clean up temporary repository clone: %s", type(exc).__name__)