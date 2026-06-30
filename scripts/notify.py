#!/usr/bin/env python3
"""
notify.py — SwarmEnterprise v2 Deploy Notifier
RWV Techsolutions LLC · robertdemottojr50@gmail.com

Sends a deployment notification via:
  1. Structured log line (always)
  2. DEPLOY_WEBHOOK URL (if set) — generic HTTP POST
  3. SLACK_WEBHOOK_URL (if set)  — Slack incoming webhook

Usage:
  python scripts/notify.py                         # auto-detect env vars
  python scripts/notify.py --status success        # override status
  python scripts/notify.py --message "Deployed v2.1.0 to production"
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# ── helpers ───────────────────────────────────────────────────────────────────

def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


def _git_sha() -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5, check=False,
            cwd=str(ROOT),
        )
        return r.stdout.strip() if r.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def _git_branch() -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5, check=False,
            cwd=str(ROOT),
        )
        return r.stdout.strip() if r.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def _post(url: str, payload: dict) -> bool:
    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status < 400
    except Exception as e:
        print(f"  [notify] Webhook call failed: {e}", file=sys.stderr)
        return False


# ── notification senders ──────────────────────────────────────────────────────

def notify_log(event: dict) -> None:
    """Always log to stdout in structured format."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[deploy-notify] {ts} | status={event['status']} | "
          f"env={event['environment']} | sha={event['sha']} | "
          f"branch={event['branch']} | message={event['message']}")


def notify_webhook(event: dict, url: str) -> None:
    """POST to a generic webhook URL."""
    ok = _post(url, event)
    if ok:
        print(f"  [notify] Webhook delivered to {url[:60]}")
    else:
        print(f"  [notify] Webhook delivery failed for {url[:60]}", file=sys.stderr)


def notify_slack(event: dict, url: str) -> None:
    """Post to a Slack incoming webhook."""
    icon = ":white_check_mark:" if event["status"] == "success" else ":x:"
    env_label = event["environment"].upper()
    payload = {
        "text": f"{icon} *SwarmEnterprise v2 Deploy* — `{env_label}`",
        "attachments": [
            {
                "color": "good" if event["status"] == "success" else "danger",
                "fields": [
                    {"title": "Status",      "value": event["status"],      "short": True},
                    {"title": "Environment", "value": event["environment"], "short": True},
                    {"title": "SHA",         "value": f"`{event['sha']}`",  "short": True},
                    {"title": "Branch",      "value": event["branch"],      "short": True},
                    {"title": "Message",     "value": event["message"],     "short": False},
                ],
                "footer": "SwarmEnterprise CI/CD",
                "ts": int(datetime.now(timezone.utc).timestamp()),
            }
        ],
    }
    ok = _post(url, payload)
    if ok:
        print("  [notify] Slack notification sent")
    else:
        print("  [notify] Slack notification failed", file=sys.stderr)


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="SwarmEnterprise v2 deploy notifier")
    parser.add_argument("--status",  default="success",
                        choices=["success", "failure", "rollback", "started"],
                        help="Deployment outcome (default: success)")
    parser.add_argument("--message", default="",
                        help="Optional human-readable description")
    parser.add_argument("--env",     default="",
                        help="Environment name (default: reads ENV env var)")
    args = parser.parse_args()

    environment = args.env or _env("ENV") or _env("DEPLOY_PROFILE") or "development"
    sha         = _env("GITHUB_SHA", _git_sha())
    branch      = _env("GITHUB_REF_NAME", _git_branch())
    version     = (ROOT / "VERSION").read_text().strip() if (ROOT / "VERSION").exists() else "?"

    message = args.message or f"Deployed SwarmEnterprise v2 v{version} to {environment}"

    event = {
        "service":     "swarmenterprise-v2",
        "version":     version,
        "status":      args.status,
        "environment": environment,
        "sha":         sha,
        "branch":      branch,
        "message":     message,
        "timestamp":   datetime.now(timezone.utc).isoformat(),
    }

    notify_log(event)

    deploy_webhook = _env("DEPLOY_WEBHOOK")
    if deploy_webhook:
        notify_webhook(event, deploy_webhook)

    slack_webhook = _env("SLACK_WEBHOOK_URL")
    if slack_webhook:
        notify_slack(event, slack_webhook)

    if not deploy_webhook and not slack_webhook:
        print("  [notify] No DEPLOY_WEBHOOK or SLACK_WEBHOOK_URL configured — logging only.")
        print("  [notify] Set these in .env to enable external notifications.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
