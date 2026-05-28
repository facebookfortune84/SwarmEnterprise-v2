#!/usr/bin/env python3
"""
Sovereign Unified Launch Sequence - SwarmEnterprise v2
One command to rule the factory.
"""

import os
import sys
import subprocess
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Launcher")

def run_command(cmd, description, background=False):
    logger.info(f"Executing: {description}...")
    try:
        if background:
            return subprocess.Popen(cmd, shell=True)
        else:
            result = subprocess.run(cmd, shell=True, check=True)
            return result
    except Exception as e:
        logger.error(f"Failed: {description}. Error: {e}")
        sys.exit(1)

def main():
    logger.info("=" * 60)
    logger.info("SWARMENTERPRISE V2 - UNIFIED LAUNCH SEQUENCE")
    logger.info("=" * 60)

    # 1. Environment Check
    if not os.path.exists(".env"):
        logger.warning(".env file missing! Creating from .env.example...")
        run_command("cp .env.example .env", "Create .env")

    # 2. Persistence Layer
    run_command("mkdir -p pg_data output/storage output/src logs", "Prepare directories")

    # 3. Docker Infrastructure
    logger.info("Starting Docker infrastructure (Redis, Postgres)...")
    run_command("docker compose up -d", "Docker Compose Up")

    # 4. Database Initialization
    logger.info("Initializing Database...")
    os.environ["PYTHONPATH"] = os.getcwd()
    run_command("python3 -c 'from backend.db.session import init_db; init_db()'", "DB Init")

    # 5. Start Backend API
    logger.info("Launching Swarm API...")
    api_proc = run_command(
        "uvicorn backend.main:app --host 0.0.0.0 --port 8000 --log-level info",
        "Swarm API",
        background=True
    )

    # 6. Start Specialized Workers
    logger.info("Launching Outreach & Discovery Workers...")
    # Outreach worker is started automatically by backend.main, but we can launch a separate process if needed.
    # Discovery worker (new)
    discovery_proc = run_command(
        "python3 -c 'import asyncio; from agents.marketing.lead_discovery import lead_discovery_agent; asyncio.run(lead_discovery_agent.run_discovery_cycle())'",
        "Lead Discovery Task",
        background=True
    )

    logger.info("=" * 60)
    logger.info("✅ SWARM OPERATIONAL")
    logger.info("📡 API: http://localhost:8000")
    logger.info("📊 Metrics: http://localhost:8000/metrics")
    logger.info("📄 Docs: http://localhost:8000/docs")
    logger.info("=" * 60)
    logger.info("Press Ctrl+C to shutdown (or run 'docker compose down' to stop infra)")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down processes...")
        api_proc.terminate()
        discovery_proc.terminate()
        logger.info("Goodbye.")

if __name__ == "__main__":
    main()
