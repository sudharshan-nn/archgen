"""Repository loader - supports local path and GitHub URL."""

import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Optional

try:
    from git import Repo
    from git.exc import GitCommandError
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False


GITHUB_URL_PATTERN = re.compile(
    r"^(?:https?://)?(?:www\.)?github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$",
    re.IGNORECASE,
)


def is_github_url(source: str) -> bool:
    """Check if the source is a GitHub URL."""
    return bool(GITHUB_URL_PATTERN.match(source.strip()))


def parse_github_url(url: str) -> Optional[tuple[str, str]]:
    """Parse GitHub URL into (owner, repo_name)."""
    match = GITHUB_URL_PATTERN.match(url.strip())
    if match:
        return match.group(1), match.group(2).rstrip("/")
    return None


def get_repo_path(source: str, temp_dir: Optional[Path] = None) -> Path:
    """
    Get the path to a repository from either a local path or GitHub URL.
    
    Returns the path to the repository. If GitHub URL, clones to temp dir.
    Caller is responsible for cleanup of temp dir if needed.
    """
    source = source.strip()
    
    if is_github_url(source):
        if not GIT_AVAILABLE:
            raise ImportError(
                "GitPython is required for GitHub URLs. Install with: pip install GitPython"
            )
        parsed = parse_github_url(source)
        if not parsed:
            raise ValueError(f"Invalid GitHub URL: {source}")
        owner, repo_name = parsed
        clone_url = f"https://github.com/{owner}/{repo_name}.git"
        
        # Use provided temp_dir, or temp_repos in cwd (sandbox-friendly), or system temp
        if temp_dir is not None:
            target = Path(temp_dir)
        else:
            cwd = Path.cwd()
            workspace_temp = cwd / "temp_repos"
            workspace_temp.mkdir(parents=True, exist_ok=True)
            target = workspace_temp
        target_path = target / repo_name
        
        if target_path.exists():
            shutil.rmtree(target_path)
        
        try:
            Repo.clone_from(clone_url, target_path, depth=1)
        except GitCommandError as e:
            raise RuntimeError(f"Failed to clone repository: {e}") from e
        
        return target_path
    
    # Local path
    path = Path(source).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")
    if not path.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {path}")
    
    # Check if it's a git repo
    if (path / ".git").exists():
        return path
    
    # Allow non-git directories too (e.g. extracted archives)
    return path
