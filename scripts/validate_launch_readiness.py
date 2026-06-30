#!/usr/bin/env python3
"""
SwarmEnterprise v2 — Production Launch Validation Script

Verifies that all systems are ready for production deployment.
Run this BEFORE launch to catch configuration issues.

Usage:
  python scripts/validate_launch_readiness.py --full    # Full validation
  python scripts/validate_launch_readiness.py --quick   # Quick checks only
  python scripts/validate_launch_readiness.py --config  # Config only
"""

import os
import sys
import json
import urllib.request
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple

# Load .env file before importing anything
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Manual .env parsing
    env_file = Path(".env")
    if env_file.exists():
        for line in env_file.read_text().split("\n"):
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()


class LaunchValidator:
    """Comprehensive production launch validation."""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.checks_passed = 0
        self.checks_failed = 0
        self.warnings = 0
        self.results = {"passed": [], "failed": [], "warnings": []}

    def log(self, message: str, level: str = "INFO"):
        """Log message with level."""
        if self.verbose:
            levels = {"INFO": "[i]", "WARN": "[!]", "ERROR": "[X]", "OK": "[+]"}
            icon = levels.get(level, ".")
            print(f"{icon} {level}: {message}")

    def check_environment_variables(self) -> bool:
        """Verify all required environment variables are set."""
        self.log("Checking environment variables...", "INFO")

        required_vars = [
            "JWT_SECRET_KEY",
            "SECRET_KEY",
            "POSTGRES_PASSWORD",
            "ADMIN_PASSWORD",
        ]

        missing = []
        for var in required_vars:
            if not os.getenv(var):
                missing.append(var)

        if missing:
            self.log(f"Missing required vars: {', '.join(missing)}", "ERROR")
            self.checks_failed += 1
            self.results["failed"].append(f"Missing env vars: {missing}")
            return False
        else:
            self.log("All required environment variables are set", "OK")
            self.checks_passed += 1
            self.results["passed"].append("Environment variables")
            return True

    def check_docker_running(self) -> bool:
        """Verify Docker daemon is running."""
        self.log("Checking Docker daemon...", "INFO")

        try:
            result = subprocess.run(
                ["docker", "ps"],
                capture_output=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0:
                self.log("Docker daemon is running", "OK")
                self.checks_passed += 1
                self.results["passed"].append("Docker daemon")
                return True
            else:
                self.log("Docker daemon not accessible", "ERROR")
                self.checks_failed += 1
                self.results["failed"].append("Docker daemon")
                return False
        except Exception as e:
            self.log(f"Failed to check Docker: {e}", "ERROR")
            self.checks_failed += 1
            self.results["failed"].append(f"Docker check: {e}")
            return False

    def check_docker_compose(self) -> bool:
        """Verify Docker Compose is available."""
        self.log("Checking Docker Compose...", "INFO")

        try:
            result = subprocess.run(
                ["docker", "compose", "version"],
                capture_output=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0:
                self.log("Docker Compose is available", "OK")
                self.checks_passed += 1
                self.results["passed"].append("Docker Compose")
                return True
            else:
                self.log("Docker Compose not found or not working", "ERROR")
                self.checks_failed += 1
                self.results["failed"].append("Docker Compose")
                return False
        except Exception as e:
            self.log(f"Failed to check Docker Compose: {e}", "ERROR")
            self.checks_failed += 1
            self.results["failed"].append(f"Docker Compose: {e}")
            return False

    def check_docker_compose_files(self) -> bool:
        """Verify docker-compose files exist and are valid."""
        self.log("Checking docker-compose files...", "INFO")

        files = [
            "docker-compose.yml",
            "docker-compose.prod.yml",
        ]

        missing = [f for f in files if not Path(f).exists()]

        if missing:
            self.log(f"Missing compose files: {', '.join(missing)}", "ERROR")
            self.checks_failed += 1
            self.results["failed"].append(f"Missing compose files: {missing}")
            return False

        # Validate syntax
        try:
            result = subprocess.run(
                ["docker", "compose", "config"],
                capture_output=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0:
                self.log("Docker Compose files are valid", "OK")
                self.checks_passed += 1
                self.results["passed"].append("Docker Compose files")
                return True
            else:
                self.log(f"Docker Compose validation failed: {result.stderr.decode()}", "ERROR")
                self.checks_failed += 1
                self.results["failed"].append("Docker Compose validation")
                return False
        except Exception as e:
            self.log(f"Error validating compose files: {e}", "ERROR")
            self.checks_failed += 1
            self.results["failed"].append(f"Compose validation: {e}")
            return False

    def check_secrets_strength(self) -> bool:
        """Verify secrets are sufficiently strong (not default/weak)."""
        self.log("Checking secret key strength...", "INFO")

        jwt_key = os.getenv("JWT_SECRET_KEY", "")
        secret_key = os.getenv("SECRET_KEY", "")
        admin_pass = os.getenv("ADMIN_PASSWORD", "")

        issues = []

        if len(jwt_key) < 32:
            issues.append("JWT_SECRET_KEY is too short (< 32 chars)")
        if len(secret_key) < 32:
            issues.append("SECRET_KEY is too short (< 32 chars)")
        if len(admin_pass) < 12:
            issues.append("ADMIN_PASSWORD is too short (< 12 chars)")
        if admin_pass.lower() in ["password", "admin", "12345678", "changeme"]:
            issues.append("ADMIN_PASSWORD is a common/weak password")

        if issues:
            for issue in issues:
                self.log(issue, "WARN")
            self.warnings += len(issues)
            self.results["warnings"].extend(issues)
            return False
        else:
            self.log("All secrets appear strong", "OK")
            self.checks_passed += 1
            self.results["passed"].append("Secret strength")
            return True

    def check_database_connectivity(self) -> bool:
        """Verify database connection."""
        self.log("Checking database connectivity...", "INFO")

        db_url = os.getenv("DATABASE_URL", "")

        if not db_url:
            self.log("DATABASE_URL not set; skipping DB check", "WARN")
            self.warnings += 1
            return True  # Not required for local dev

        try:
            if db_url.startswith("postgresql"):
                # Try a quick connection
                from sqlalchemy import create_engine, text

                normalized_url = db_url.replace("+asyncpg", "")
                engine = create_engine(normalized_url, pool_pre_ping=True, connect_args={"timeout": 5})
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                engine.dispose()
                self.log("Database connection successful", "OK")
                self.checks_passed += 1
                self.results["passed"].append("Database connectivity")
                return True
            else:
                self.log("Non-PostgreSQL database; skipping connectivity check", "WARN")
                return True
        except Exception as e:
            self.log(f"Database connection failed: {e}", "ERROR")
            self.checks_failed += 1
            self.results["failed"].append(f"Database: {e}")
            return False

    def check_redis_connectivity(self) -> bool:
        """Verify Redis connection."""
        self.log("Checking Redis connectivity...", "INFO")

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

        try:
            import redis as _redis

            r = _redis.from_url(redis_url, socket_timeout=2)
            r.ping()
            self.log("Redis connection successful", "OK")
            self.checks_passed += 1
            self.results["passed"].append("Redis connectivity")
            return True
        except Exception as e:
            self.log(f"Redis connection failed (may be offline for local dev): {e}", "WARN")
            self.warnings += 1
            return True  # Not critical for initial setup

    def check_ollama_connectivity(self) -> bool:
        """Verify Ollama is accessible."""
        self.log("Checking Ollama connectivity...", "INFO")

        ollama_url = os.getenv("OLLAMA_URL", "").rstrip("/")

        if not ollama_url:
            self.log("OLLAMA_URL not set; skipping Ollama check", "WARN")
            self.warnings += 1
            return True

        try:
            req = urllib.request.Request(f"{ollama_url}/api/tags", method="GET", timeout=3)
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    self.log("Ollama is accessible", "OK")
                    self.checks_passed += 1
                    self.results["passed"].append("Ollama connectivity")
                    return True
        except Exception as e:
            self.log(f"Ollama not accessible: {e}", "WARN")
            self.warnings += 1
            return True  # Not critical

    def check_smtp_credentials(self) -> bool:
        """Verify SMTP settings are provided for production."""
        self.log("Checking email (SMTP) configuration...", "INFO")

        env = os.getenv("ENV", "development")
        smtp_server = os.getenv("SMTP_SERVER", "")

        if env == "production" and not smtp_server:
            self.log("Production environment but SMTP_SERVER not set", "WARN")
            self.warnings += 1
            self.results["warnings"].append("SMTP not configured for production")
            return True  # Warning only

        if smtp_server:
            self.log("SMTP settings configured", "OK")
            self.checks_passed += 1
            self.results["passed"].append("SMTP configuration")
        else:
            self.log("SMTP not configured (optional for development)", "INFO")

        return True

    def check_stripe_keys(self) -> bool:
        """Verify Stripe keys for production."""
        self.log("Checking Stripe configuration...", "INFO")

        env = os.getenv("ENV", "development")
        stripe_key = os.getenv("STRIPE_API_KEY", "")
        test_mode = os.getenv("STRIPE_TEST_MODE", "TRUE").upper() == "TRUE"

        if env == "production":
            if not stripe_key:
                self.log("Production but STRIPE_API_KEY not set", "WARN")
                self.warnings += 1
            elif test_mode:
                self.log("Production env but STRIPE_TEST_MODE=TRUE (should be FALSE)", "WARN")
                self.warnings += 1
            elif not stripe_key.startswith("sk_live_"):
                self.log("STRIPE_API_KEY is not a live key", "WARN")
                self.warnings += 1
            else:
                self.log("Stripe live keys configured", "OK")
                self.checks_passed += 1
        else:
            self.log("Development environment; Stripe keys optional", "INFO")

        return True

    def check_tls_ready(self) -> bool:
        """Verify TLS/HTTPS is configured for production."""
        self.log("Checking TLS/HTTPS readiness...", "INFO")

        env = os.getenv("ENV", "development")
        primary_domain = os.getenv("PRIMARY_DOMAIN", "")
        acme_email = os.getenv("ACME_EMAIL", "")

        if env == "production":
            if not primary_domain:
                self.log("Production but PRIMARY_DOMAIN not set", "ERROR")
                self.checks_failed += 1
                self.results["failed"].append("TLS: PRIMARY_DOMAIN not set")
                return False
            if not acme_email:
                self.log("Production but ACME_EMAIL not set (required for Let's Encrypt)", "WARN")
                self.warnings += 1
            else:
                self.log("TLS configuration ready", "OK")
                self.checks_passed += 1
                self.results["passed"].append("TLS/HTTPS readiness")
        else:
            self.log("Development environment; TLS optional", "INFO")

        return True

    def run_full_validation(self) -> Tuple[int, int, int]:
        """Run all validation checks."""
        print("\n" + "=" * 70)
        print("SwarmEnterprise v2 — Production Launch Validation")
        print("=" * 70 + "\n")

        self.check_environment_variables()
        self.check_docker_running()
        self.check_docker_compose()
        self.check_docker_compose_files()
        self.check_secrets_strength()
        self.check_database_connectivity()
        self.check_redis_connectivity()
        self.check_ollama_connectivity()
        self.check_smtp_credentials()
        self.check_stripe_keys()
        self.check_tls_ready()

        print("\n" + "=" * 70)
        print("VALIDATION SUMMARY")
        print("=" * 70)
        print(f"[+] Passed:   {self.checks_passed}")
        print(f"[X] Failed:   {self.checks_failed}")
        print(f"[!] Warnings: {self.warnings}")

        if self.checks_failed == 0 and self.warnings == 0:
            print("\n[OK] All checks passed! System is ready for launch.")
            return 0, self.checks_passed, 0
        elif self.checks_failed == 0:
            print(f"\n[!] {self.warnings} warning(s) found. Review above and proceed with caution.")
            return 0, self.checks_passed, self.warnings
        else:
            print(f"\n[X] {self.checks_failed} critical issue(s) found. Fix before launch.")
            return 1, self.checks_passed, self.checks_failed

    def export_results(self, filename: str = "launch_validation_report.json"):
        """Export results to JSON."""
        report = {
            "timestamp": str(Path.cwd()),
            "passed_count": self.checks_passed,
            "failed_count": self.checks_failed,
            "warning_count": self.warnings,
            "checks": self.results,
        }
        with open(filename, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n[OK] Report saved to {filename}")


if __name__ == "__main__":
    validator = LaunchValidator(verbose=True)
    exit_code, passed, failed = validator.run_full_validation()
    validator.export_results()
    sys.exit(exit_code)
