import os
import subprocess
import sys

ROOT = os.getcwd()
_VENV_PY = os.path.join(ROOT, ".venv", "Scripts", "python.exe")
if os.name != "nt":
    _VENV_PY = os.path.join(ROOT, ".venv", "bin", "python")
PYTHON = _VENV_PY if os.path.isfile(_VENV_PY) else sys.executable

env = Environment(
    ENV={
        "PATH": os.environ["PATH"],
        "PYTHONPATH": ROOT,
    }
)


def run(cmd, check=True):
    print(f"[RUN] {cmd}")
    result = subprocess.run(cmd, shell=True)
    if check and result.returncode != 0:
        raise SystemExit(result.returncode)
    return result.returncode


def install_deps(target, source, env):
    run(f'"{PYTHON}" -m pip install --upgrade pip setuptools')
    run(f'"{PYTHON}" -m pip install -r requirements.txt')


env.Command("deps", ["requirements.txt"], install_deps)

LINT_PATHS = [
    "backend/api",
    "backend/core",
    "backend/connectors",
    "backend/db",
    "agents",
    "scripts",
    "tests",
]


def lint_ruff(target, source, env):
    ruff_paths = " ".join(LINT_PATHS)
    run(f'"{PYTHON}" -m ruff check {ruff_paths}')
    run(f'"{PYTHON}" -m black --check backend agents scripts tests')


env.Command("lint", ["deps"], lint_ruff)


def audit_deps(target, source, env):
    run(f'"{PYTHON}" scripts/pip_audit_gate.py')


env.Command("audit", ["deps"], audit_deps)


def build_agents(target, source, env):
    print("[AGENTS] No agent build step defined yet")


env.Command("agents", ["deps"], build_agents)


def run_tests(target, source, env):
    if os.path.exists("tests"):
        run(f'"{PYTHON}" -m pytest tests -q')
    else:
        print("[SKIP] No tests directory found")


env.Command("tests", ["deps"], run_tests)


def smoke_api(target, source, env):
    run(f'"{PYTHON}" -m pip install httpx')
    run(f'"{PYTHON}" scripts/smoke_api.py')


env.Command("smoke", ["deps"], smoke_api)

Default(["deps", "lint", "audit", "agents", "tests", "smoke"])
