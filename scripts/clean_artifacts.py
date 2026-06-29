#!/usr/bin/env python3
"""
scripts/clean_artifacts.py
Cross-platform replacement for the bash `find ... rm` clean recipe.
"""

import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Directories to delete recursively
DIR_PATTERNS = ["__pycache__", ".pytest_cache", ".ruff_cache", "htmlcov", "build", "dist"]
# Top-level files to delete
FILE_PATTERNS = [".coverage", "coverage.xml"]
# Glob patterns for top-level
GLOB_PATTERNS = ["*.egg-info", "coverage_*.xml", "*.pyc"]


def main() -> None:
    removed = 0

    # Remove named directories anywhere in the tree
    for pattern in ["__pycache__", ".pytest_cache", ".ruff_cache"]:
        for path in PROJECT_ROOT.rglob(pattern):
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
                removed += 1

    # Remove top-level directories
    for name in ["htmlcov", "build", "dist"]:
        p = PROJECT_ROOT / name
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
            removed += 1

    # Remove .egg-info directories anywhere
    for path in PROJECT_ROOT.rglob("*.egg-info"):
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
            removed += 1

    # Remove .pyc files anywhere
    for path in PROJECT_ROOT.rglob("*.pyc"):
        try:
            path.unlink()
            removed += 1
        except OSError:
            pass

    # Remove top-level files
    for name in [".coverage", "coverage.xml"]:
        p = PROJECT_ROOT / name
        if p.exists():
            p.unlink(missing_ok=True)
            removed += 1

    for pattern in ["coverage_*.xml"]:
        for p in PROJECT_ROOT.glob(pattern):
            p.unlink(missing_ok=True)
            removed += 1

    print(f"[clean] Removed {removed} items.")


if __name__ == "__main__":
    main()
    sys.exit(0)
