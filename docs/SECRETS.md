# Secrets Management Guide — SwarmEnterprise v2

**Company:** RWV Techsolutions LLC  
**Contact:** robertdemottojr50@gmail.com  
**Address:** 1091 Harrison Ave, Elkins, WV 26241, USA

---

## Overview

This guide explains every secret required to run SwarmEnterprise v2 in production, where to obtain each value, and how to rotate secrets safely.

Never commit real secrets to version control. The `.env.example` file contains only placeholder values and documentation — copy it to `.env` and fill in your real credentials.

```bash
cp .env.example .env
# Then edit .env with your real values
```

---

## Generating Cryptographic Secrets

Use the provided generator script for all high-entropy secrets:

```bash
python scripts/generate_secrets.py
```

This outputs ready-to-paste `.env` lines for:
- `JWT_SECRET_KEY` (256-bit hex)
- `SECRET_KEY` (256-bit hex)
- `POSTGRES_PASSWORD` (URL-safe random)
- `ENCRYPTION_KEY` (URL-safe random)

---

## Secret Reference by Service

### 1. Database (PostgreSQL)

| Variable | Required | Where to Get |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | Constructed from Postgres vars: `postgresql://user:pass@host:5432/dbname` |
| `POSTGRES_USER` | Yes | Choose a username (e.g. `swarmuser`) |
| `POSTGRES_PASSWORD` | Yes | Generate with `scripts/generate_secrets.py` |
| `POSTGRES_DB` | Yes | Choose a database name (e.g. `swarmdb`) |
| `POSTGRES_HOST` | Yes | `localhost` for local, container name for Docker |

**Rotation:** Change `POSTGRES_PASSWORD` in `.env`, update the Postgres user with `ALTER USER swarmuser PASSWORD 'newpass';`, then restart services.

---

### 2. Redis

| Variable | Required | Where to Get |
|----------|----------|-------------|
| `REDIS_URL` | Yes | `redis://localhost:6379/0` for local, `redis://redis:6379/0` for Docker |
| `REDIS_PASSWORD` | No | Set in Redis config and here if using authenticated Redis |

---

### 3. JWT / Authentication

| Variable | Required | Where to Get |
|----------|----------|-------------|
| `JWT_SECRET_KEY` | Yes | Generate: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `SECRET_KEY` | Yes | Same method — use a different value |
| `JWT_ALGORITHM` | No | Default: `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | Default: `15` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | Default: `7` |

**Rotation:** Changing `JWT_SECRET_KEY` immediately invalidates all active sessions. Schedule maintenance window, update the value, restart the backend, notify users to re-login.

---

### 4. Stripe (Payments)

| Variable | Required | Where to Get |
|----------|----------|-------------|
| `STRIPE_API_KEY` | Yes | [Stripe Dashboard](https://dashboard.stripe.com/apikeys) → Secret key |
| `STRIPE_PUBLISHABLE_KEY` | Yes | Stripe Dashboard → Publishable key |
| `STRIPE_WEBHOOK_SECRET` | Yes | Stripe Dashboard → Webhooks → your endpoint → Signing secret |
| `STRIPE_PRICE_STARTER` | Yes | Stripe Dashboard → Products → your plan → Price ID |
| `STRIPE_PRICE_PRO` | Yes | Same |
| `STRIPE_PRICE_ENTERPRISE` | Yes | Same |

**Test vs Production:** Use `sk_test_...` keys for development. Switch to `sk_live_...` for production. Webhook secrets differ between test and live modes.

**Rotation:** Generate new Stripe restricted keys from the dashboard. Update `.env`, restart backend.

---

### 5. SMTP (Email)

| Variable | Required | Where to Get |
|----------|----------|-------------|
| `SMTP_SERVER` | Yes | Your provider's SMTP hostname (e.g. `smtp.gmail.com`) |
| `SMTP_PORT` | Yes | `587` for STARTTLS, `465` for SSL |
| `SMTP_USER` | Yes | Your sender email address |
| `SMTP_PASS` | Yes | App password (not your account password) |
| `SMTP_FROM` | No | Display name + address (defaults to `SMTP_USER`) |

**Gmail setup:**
1. Enable 2FA on your Google account
2. Go to [App Passwords](https://myaccount.google.com/apppasswords)
3. Create an app password for "Mail"
4. Use that 16-character code as `SMTP_PASS`

**SendGrid setup:**
1. Create account at [sendgrid.com](https://sendgrid.com)
2. Settings → API Keys → Create API Key (Full Access or restricted to Mail Send)
3. `SMTP_SERVER=smtp.sendgrid.net`, `SMTP_PORT=587`, `SMTP_USER=apikey`, `SMTP_PASS=<your_api_key>`

---

### 6. LLM Providers

| Variable | Required | Where to Get |
|----------|----------|-------------|
| `OLLAMA_URL` | No | `http://localhost:11434` for local Ollama |
| `OPENAI_API_KEY` | No | [platform.openai.com](https://platform.openai.com/api-keys) |
| `ANTHROPIC_API_KEY` | No | [console.anthropic.com](https://console.anthropic.com) |
| `GROQ_API_KEY` | No | [console.groq.com](https://console.groq.com/keys) |

At least one LLM source should be configured. Ollama (local) is recommended for privacy.

---

### 7. Cloudflare (Optional — DNS & Tunnel)

| Variable | Required | Where to Get |
|----------|----------|-------------|
| `CLOUDFLARE_API_TOKEN` | No | [Cloudflare Dashboard](https://dash.cloudflare.com/profile/api-tokens) → Create Token (Zone:DNS:Edit) |
| `CLOUDFLARE_ZONE_ID` | No | Cloudflare Dashboard → your domain → Overview → Zone ID |
| `CLOUDFLARE_TUNNEL_TOKEN` | No | Cloudflare Zero Trust → Access → Tunnels → create tunnel |

---

### 8. Application Identity

| Variable | Required | Description |
|----------|----------|-------------|
| `ADMIN_EMAIL` | Yes | Initial admin user email (created by `scripts/seed.py`) |
| `ADMIN_PASSWORD` | Yes | Initial admin user password — change immediately after first login |
| `APP_ENV` | No | `production` or `development` (default: `development`) |
| `LOG_LEVEL` | No | `INFO` in production, `DEBUG` in development |

---

## Environment Validation

Run the validator before starting any service:

```bash
python scripts/validate_env.py
```

This checks all required variables and prints `[OK]` / `[!!]` per group with exit code 0 (all present) or 1 (any missing).

---

## Secret Rotation Schedule

| Secret | Rotation Frequency | Impact of Rotation |
|--------|-------------------|-------------------|
| `JWT_SECRET_KEY` | Every 90 days | All sessions invalidated — users must re-login |
| `SECRET_KEY` | Every 90 days | Token signatures invalidated |
| `POSTGRES_PASSWORD` | Every 180 days | Requires DB user update + service restart |
| Stripe API keys | On compromise / annually | No user impact |
| SMTP password | On compromise / on provider prompt | No user impact |
| `ENCRYPTION_KEY` | **With caution** | Encrypted data becomes unreadable — migrate first |

---

## Security Best Practices

1. **Never commit `.env` to git.** The `.gitignore` excludes it. Verify with `git status`.
2. **Use a secrets manager in production.** AWS Secrets Manager, HashiCorp Vault, or Doppler are recommended.
3. **Restrict API key scopes.** Stripe restricted keys, Cloudflare scoped tokens.
4. **Audit secret access.** Review who has access to production `.env` quarterly.
5. **Different secrets per environment.** Never share keys between staging and production.
6. **Monitor for leaks.** Enable GitHub secret scanning. Use `git-secrets` pre-commit hook.

---

## Related Documentation

- [DEPLOYMENT.md](../DEPLOYMENT.md) — full deployment guide
- [docs/guides/SECURITY_HARDENING.md](guides/SECURITY_HARDENING.md) — firewall and SSH hardening
- [scripts/generate_secrets.py](../scripts/generate_secrets.py) — generate cryptographic secrets
- [scripts/validate_env.py](../scripts/validate_env.py) — validate environment on startup

---

*RWV Techsolutions LLC — 1091 Harrison Ave, Elkins, WV 26241 — robertdemottojr50@gmail.com*
