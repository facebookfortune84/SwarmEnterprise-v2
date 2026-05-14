Production runbook (SwarmOS)

1. Rotate secrets
   - Ensure STRIPE_API_KEY, STRIPE_WEBHOOK_SECRET, SMTP_PASS, OLLAMA_API_KEY, HUBSPOT_API_KEY, CLOSE_API_KEY, PAGERDUTY_ROUTING_KEY are stored in Secrets Manager or GitHub Secrets.

2. Infrastructure
   - Deploy docker-compose stack (or use Kubernetes): docker compose up -d
   - Required services: backend, redis, chromadb (if used), postgres/sqlite persisted volume

3. Workers
   - Start Celery worker: celery -A backend.celery_app.celery_app worker --loglevel=info
   - Ensure outreach worker runs if not using Celery (backend auto-starts in-process by default)

4. Monitoring
   - Configure OTEL_OTLP_ENDPOINT to your OTLP collector.
   - Configure Prometheus to scrape /metrics on backend host.
   - Configure PagerDuty routing key in PAGERDUTY_ROUTING_KEY.

5. Backups
   - Backup pg_data and output directories regularly.

6. Incident response
   - If outreach failures spike, check SMTP provider health and rotate providers via SMTP_FALLBACKS.
   - For elevated error rates, use PagerDuty helper to create incidents.

7. CI/CD
   - Use GitHub Actions deploy workflow. Populate secrets: DOCKER_REGISTRY_USER, DOCKER_REGISTRY_PASSWORD, SSH_DEPLOY_*.

8. Git history purge
   - Use scripts/purge_secrets_instructions.md to remove leaked .env and rotate keys.
