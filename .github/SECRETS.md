# GitHub Actions Secrets Reference

All secrets listed here must be configured in **Settings → Secrets and variables → Actions**
(or at the environment level for `staging` / `production` environments).

Generate cryptographic secrets with:
```bash
python scripts/generate_secrets.py
```

---

## Repository Secrets (all environments)

| Secret | Description | How to obtain |
|--------|-------------|---------------|
| `DOCKER_REGISTRY_USER` | GitHub username for GHCR login | Your GitHub username |
| `DOCKER_REGISTRY_PASSWORD` | GHCR token with `write:packages` scope | GitHub → Settings → Developer Settings → Personal Access Tokens |
| `PRIMARY_DOMAIN` | Primary production domain (e.g. `realms2riches.com`) | Your DNS provider |

---

## Environment: `staging`

Configure under **Settings → Environments → staging**.

| Secret | Description |
|--------|-------------|
| `SSH_DEPLOY_HOST` | IP or hostname of the staging server |
| `SSH_DEPLOY_USER` | SSH username on the staging server (e.g. `deploy`) |
| `SSH_DEPLOY_PRIVATE_KEY` | PEM-encoded RSA/ECDSA private key (base64 if needed) |
| `JWT_SECRET_KEY` | 64-char hex — staging value (different from production) |
| `SECRET_KEY` | 64-char hex — staging value |
| `ENCRYPTION_KEY` | 32-byte URL-safe base64 — staging value |
| `POSTGRES_PASSWORD` | Strong random password for staging Postgres |
| `STRIPE_API_KEY` | `sk_test_…` — Stripe test mode key |
| `STRIPE_WEBHOOK_SECRET` | `whsec_…` — staging webhook signing secret |
| `SMTP_USER` | SMTP username for staging email delivery |
| `SMTP_PASS` | SMTP password for staging |
| `SMTP_SERVER` | SMTP hostname for staging |
| `FLOWER_USER` | Celery Flower basic-auth username (default: `admin`) |
| `FLOWER_PASSWORD` | Celery Flower basic-auth password |

---

## Environment: `production`

Configure under **Settings → Environments → production**.
Enable **Required reviewers** to create a manual approval gate before production deployments.

| Secret | Description |
|--------|-------------|
| `SSH_DEPLOY_HOST` | IP or hostname of the production server |
| `SSH_DEPLOY_USER` | SSH username on the production server |
| `SSH_DEPLOY_PRIVATE_KEY` | PEM-encoded private key for production SSH |
| `JWT_SECRET_KEY` | 64-char hex — **unique production value** |
| `SECRET_KEY` | 64-char hex — **unique production value** |
| `ENCRYPTION_KEY` | 32-byte URL-safe base64 — **unique production value** |
| `POSTGRES_PASSWORD` | Strong production Postgres password |
| `STRIPE_API_KEY` | `sk_live_…` — Stripe live key |
| `STRIPE_WEBHOOK_SECRET` | `whsec_…` — production webhook signing secret |
| `SMTP_USER` | Production SMTP username |
| `SMTP_PASS` | Production SMTP password |
| `SMTP_SERVER` | Production SMTP hostname |
| `FLOWER_USER` | Celery Flower username |
| `FLOWER_PASSWORD` | Celery Flower password |
| `SENTRY_DSN` | Sentry project DSN for error tracking |
| `OTEL_OTLP_ENDPOINT` | OpenTelemetry collector endpoint (optional) |

---

## Automatic Secrets (no configuration required)

| Secret | Description |
|--------|-------------|
| `GITHUB_TOKEN` | Automatically provided by GitHub Actions with scoped permissions |

---

## Security Notes

- **Never commit** `.env` or any file containing actual secret values.
- **Rotate** all secrets at least every 90 days. After rotation, update both
  the server `.env` files and the GitHub secrets.
- Use `python scripts/generate_secrets.py` to create cryptographically strong values.
- The `ENCRYPTION_KEY` is used for encrypting stored PII. If rotated, existing
  encrypted data must be re-encrypted before deploying. See `docs/guides/SECRETS_MANAGEMENT.md`.
- Staging and production must have **different** values for all `*_KEY` secrets.
- The `SSH_DEPLOY_PRIVATE_KEY` should belong to a dedicated `deploy` user with
  minimal permissions (no `sudo`, restricted to the deploy directory).
