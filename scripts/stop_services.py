#!/usr/bin/env python3
"""
scripts/stop_services.py
Cross-platform replacement for `bash stop.sh`.
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    stop_sh = PROJECT_ROOT / "stop.sh"

    if sys.platform != "win32" and stop_sh.exists():
        result = subprocess.run(["bash", str(stop_sh)], cwd=str(PROJECT_ROOT))
        return result.returncode

    compose_file = str(PROJECT_ROOT / "docker-compose.yml")
    cmd = ["docker", "compose", "-f", compose_file, "down"]
    print(f"[stop_services] {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
