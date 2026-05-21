"""Audit installed packages; fail only on vulnerabilities in direct requirements."""

import json
import re
import subprocess
import sys
from pathlib import Path

# crewai==0.28.8 pins python-dotenv==1.0.0; tracked upstream constraint
_IGNORED = {("python-dotenv", "CVE-2026-28684")}


def _pinned_package_names() -> set[str]:
    """Only explicitly pinned (==) requirements are gated."""
    names: set[str] = set()
    req = Path(__file__).resolve().parents[1] / "requirements.txt"
    for line in req.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "==" not in line:
            continue
        match = re.match(r"^([A-Za-z0-9_.-]+)", line)
        if match:
            names.add(match.group(1).lower().replace("_", "-"))
    return names


def main() -> int:
    direct = _pinned_package_names()
    proc = subprocess.run(
        [sys.executable, "-m", "pip_audit", "-l", "-f", "json"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode not in (0, 1):
        print(proc.stderr or proc.stdout)
        return proc.returncode

    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        print(proc.stdout)
        print(proc.stderr)
        return 1

    failures = []
    for dep in payload.get("dependencies", []):
        name = dep.get("name", "").lower()
        vulns = dep.get("vulns") or []
        if not vulns or name not in direct:
            continue
        ids = []
        for vuln in vulns:
            vid = vuln.get("id")
            if vid and (name, vid) not in _IGNORED:
                ids.append(vid)
        if ids:
            failures.append((name, dep.get("version"), ids))

    if failures:
        print("[FAIL] Vulnerabilities in pinned requirements:")
        for name, version, ids in failures:
            print(f"  - {name} {version}: {', '.join(ids)}")
        return 1

    print("[OK] pip-audit: no vulnerabilities in pinned requirements.txt packages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
