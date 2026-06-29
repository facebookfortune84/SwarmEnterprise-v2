#!/usr/bin/env python3
"""
scripts/launch_services.py
Cross-platform replacement for `bash start.sh`.

On Linux/macOS: runs start.sh if it exists.
On Windows: invokes docker compose directly (bash may not be on PATH).
"""

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    start_sh = PROJECT_ROOT / "start.sh"

    if sys.platform != "win32" and start_sh.exists():
        # Linux / macOS — prefer start.sh
        result = subprocess.run(["bash", str(start_sh)], cwd=str(PROJECT_ROOT))
        return result.returncode

    # Windows OR start.sh missing — use docker compose directly
    compose_file = str(PROJECT_ROOT / "docker-compose.yml")
    cmd = ["docker", "compose", "-f", compose_file, "up", "-d", "--remove-orphans"]
    print(f"[launch_services] {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
