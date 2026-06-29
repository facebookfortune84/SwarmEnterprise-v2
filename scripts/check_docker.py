#!/usr/bin/env python3
"""
scripts/check_docker.py
Cross-platform Docker daemon availability check.

Replaces the fragile inline @powershell / bash check-docker recipe.
Works identically on Windows (cmd.exe / PowerShell) and Linux/macOS.
Exits 0 if Docker is running, 1 with a clear error message if not.
"""

import subprocess
import sys


def main() -> int:
    try:
        result = subprocess.run(
            ["docker", "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
        if result.returncode == 0:
            print("[check-docker] Docker is running.")
            return 0
        else:
            print(
                "ERROR: Docker is not running (docker info returned exit code "
                f"{result.returncode}).",
                file=sys.stderr,
            )
            print(
                "  -> Start Docker Desktop and wait for the icon to show 'Engine running'.",
                file=sys.stderr,
            )
            return 1
    except FileNotFoundError:
        print(
            "ERROR: 'docker' executable not found on PATH.",
            file=sys.stderr,
        )
        print(
            "  -> Install Docker Desktop: https://www.docker.com/products/docker-desktop/",
            file=sys.stderr,
        )
        return 1
    except subprocess.TimeoutExpired:
        print(
            "ERROR: 'docker info' timed out after 10 s — Docker daemon may be unresponsive.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
