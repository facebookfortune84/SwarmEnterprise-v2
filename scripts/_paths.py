"""Repo-relative paths for codegen scripts."""

import os

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def repo_root() -> str:
    return os.environ.get("SWARM_REPO_ROOT", _REPO_ROOT)


def output_dir() -> str:
    return os.environ.get("SWARM_OUTPUT_DIR", os.path.join(repo_root(), "output"))


def output_src_dir() -> str:
    return os.path.join(output_dir(), "src")
