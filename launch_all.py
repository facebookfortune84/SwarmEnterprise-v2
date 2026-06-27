#!/usr/bin/env python3
"""
Sovereign Unified Launch Sequence - SwarmEnterprise v2
Enhanced with auto-discovery for Ollama, Docker, and other services.
"""

import os
import subprocess
import time
import logging
import requests
import socket

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Launcher")


class ServiceManager:
    """Manages external service dependencies (Docker, Ollama, etc.)"""

    @staticmethod
    def is_port_open(port, host="127.0.0.1"):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex((host, port)) == 0

    @staticmethod
    def find_ollama():
        """Search for Ollama on common ports and environment variables"""
        env_url = os.getenv("OLLAMA_URL")
        if env_url:
            try:
                r = requests.get(f"{env_url.rstrip('/')}/api/tags", timeout=2)
                if r.status_code == 200:
                    return env_url
            except Exception:
                pass

        common_ports = [11434, 11435, 11436]
        for port in common_ports:
            url = f"http://127.0.0.1:{port}"
            try:
                r = requests.get(f"{url}/api/tags", timeout=1)
                if r.status_code == 200:
                    logger.info(f"Ollama discovered at {url}")
                    return url
            except Exception:
                continue
        return None

    @classmethod
    def ensure_ollama(cls):
        """Ensure Ollama is running, start if possible"""
        url = cls.find_ollama()
        if url:
            os.environ["OLLAMA_URL"] = url
            return True

        logger.warning("Ollama not found. Attempting to start Ollama...")
        try:
            # Try to start ollama serve in background
            subprocess.Popen(
                "ollama serve", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            # Wait for it to spin up
            for _ in range(10):
                time.sleep(2)
                url = cls.find_ollama()
                if url:
                    os.environ["OLLAMA_URL"] = url
                    return True
        except Exception as e:
            logger.error(f"Failed to start Ollama: {e}")

        return False

    @classmethod
    def ensure_docker(cls):
        """Check for docker/docker-compose and attempt to start if in WSL"""
        try:
            subprocess.run("docker --version", shell=True, check=True, stdout=subprocess.DEVNULL)
            return True
        except Exception:
            logger.warning("Docker command not found.")
            if os.name != "nt":  # Likely WSL or Linux
                logger.info("Checking for Docker Desktop WSL integration...")
                # We can't easily 'start' docker desktop from within WSL if not integrated,
                # but we can check if the service is available.
                try:
                    subprocess.run("sudo service docker start", shell=True)
                    time.sleep(2)
                    subprocess.run("docker --version", shell=True, check=True)
                    return True
                except Exception:
                    logger.error(
                        "Docker is not accessible. Please ensure Docker Desktop is running and WSL integration is enabled."
                    )
            return False


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
        return None


def main():
    logger.info("=" * 60)
    logger.info("SWARMENTERPRISE V2 - UNIFIED LAUNCH SEQUENCE")
    logger.info("=" * 60)

    # 1. Environment Check
    if not os.path.exists(".env"):
        logger.warning(".env file missing! Creating from .env.example...")
        run_command("cp .env.example .env", "Create .env")

    # 2. Service Verification (Ollama & Docker)
    if not ServiceManager.ensure_docker():
        logger.error(
            "🛑 DOCKER CRITICAL FAILURE: Swarm cannot proceed without Docker infrastructure."
        )
        # Proceeding with caution, but some things will fail.

    if not ServiceManager.ensure_ollama():
        logger.warning(
            "⚠️ OLLAMA NOT FOUND: Local intelligence will be unavailable. Swarm will attempt cloud fallback if configured."
        )

    # 3. Persistence Layer
    run_command("mkdir -p pg_data output/storage output/src logs", "Prepare directories")

    # 4. Docker Infrastructure
    logger.info("Starting Docker infrastructure (Redis, Postgres)...")
    infra = run_command("docker compose up -d", "Docker Compose Up")
    if not infra:
        logger.error(
            "🛑 INFRASTRUCTURE FAILURE: Could not start Redis/Postgres. Check Docker status."
        )

    # 5. Database Initialization
    logger.info("Initializing Database...")
    os.environ["PYTHONPATH"] = os.getcwd()
    run_command("python3 -c 'from backend.db.session import init_db; init_db()'", "DB Init")

    # 6. Start Backend API
    logger.info("Launching Swarm API...")
    api_proc = run_command(
        "uvicorn backend.main:app --host 0.0.0.0 --port 8000 --log-level info",
        "Swarm API",
        background=True,
    )

    # 7. Start Specialized Workers
    logger.info("Launching Discovery Workers...")
    discovery_proc = run_command(
        "python3 -c 'import asyncio; from agents.marketing.lead_discovery import lead_discovery_agent; asyncio.run(lead_discovery_agent.run_discovery_cycle())'",
        "Lead Discovery Task",
        background=True,
    )

    logger.info("=" * 60)
    logger.info("✅ SWARM OPERATIONAL")
    logger.info("📡 API: http://localhost:8000")
    logger.info("📊 Metrics: http://localhost:8000/metrics")
    logger.info("📄 Docs: http://localhost:8000/docs")
    if os.getenv("OLLAMA_URL"):
        logger.info(f"🧠 Intelligence: Ollama active at {os.getenv('OLLAMA_URL')}")
    logger.info("=" * 60)
    logger.info("Press Ctrl+C to shutdown.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down processes...")
        if api_proc:
            api_proc.terminate()
        if discovery_proc:
            discovery_proc.terminate()
        logger.info("Goodbye.")


if __name__ == "__main__":
    main()
