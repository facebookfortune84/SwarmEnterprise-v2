# Security Policy

## Supported Versions

Only the latest release on the `main` branch receives security fixes.
Older versions are not backported.

| Version | Supported |
|---------|-----------|
| `main` (latest) | ✅ Yes |
| Any tagged release ≥ 2.0.0 | ✅ Patch releases issued |
| < 2.0.0 | ❌ No — upgrade required |

---

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub Issues.**

### Preferred Channel

Send an email to **ops@realms2riches.com** with:

- Subject line: `[SECURITY] SwarmEnterprise v2 — <brief description>`
- A description of the vulnerability and its potential impact
- Steps to reproduce (proof-of-concept code if applicable)
- The version or commit hash where the issue was observed
- Your preferred contact method for follow-up

All reports are acknowledged within **48 hours** on business days.

### Alternative Channel

If email is not suitable, you may use GitHub's private
[Security Advisories](https://github.com/rwv-techsolutions/swarmenterprise-v2/security/advisories/new)
feature to submit a report confidentially.

---

## Disclosure Policy

This project follows a **coordinated disclosure** model:

| Timeline | Action |
|----------|--------|
| Day 0 | Vulnerability report received; acknowledgement sent within 48 h |
| Day 1–7 | Report triaged; severity assessed (CVSS score assigned) |
| Day 7–30 | Fix developed, tested, and reviewed in a private branch |
| Day 30 | Fix released; advisory published on GitHub Security Advisories |
| Day 30 | Reporter credited in the advisory (unless anonymity requested) |

For **critical severity** (CVSS ≥ 9.0) vulnerabilities we target a **7-day**
patch timeline.

We ask reporters to:

- Give us reasonable time to investigate and release a fix before public
  disclosure.
- Not exploit the vulnerability beyond what is necessary to demonstrate it.
- Not share details of the vulnerability with others until the coordinated
  disclosure date.

---

## Scope

The following are **in scope** for security reports:

- Authentication and authorisation bypass (JWT, API keys, session tokens)
- SQL injection or ORM-level data access violations
- Server-side request forgery (SSRF)
- Remote code execution (RCE)
- Sensitive data exposure (PII, secrets, credentials)
- Broken access control (tenant isolation, admin privilege escalation)
- Insecure direct object references (IDOR) on tickets, users, workflows
- Webhook signature verification bypass
- Rate-limit bypass on authentication endpoints
- Dependency vulnerabilities with a known exploit path

The following are **out of scope**:

- Denial-of-service attacks requiring sustained high traffic
- Social engineering or phishing of project contributors
- Vulnerabilities in third-party services we integrate with (Stripe, SendGrid)
- Self-XSS or issues that require physical access to a user's machine
- Reports generated solely by automated scanners with no proof of exploitability

---

## Security Design Notes

The following controls are implemented in the codebase. Reports claiming a
control is absent when it is present will be closed as invalid.

| Control | Implementation |
|---------|---------------|
| Password hashing | `bcrypt` with minimum cost factor 12 (`bcrypt.gensalt()`) |
| JWT signing | HS256 with secret ≥ 32 bytes, enforced at startup |
| Token revocation | Redis blacklist; TTL matches token expiry |
| SQL access | SQLAlchemy ORM only — no raw string interpolation |
| CORS | Origin whitelist via `CORS_ORIGINS` env var; wildcard blocked in production |
| Rate limiting | Per-IP in-process limiter (120 req/min default); upgrade to slowapi for production |
| Secrets | All via environment variables; `generate_secrets.py` creates cryptographically strong values |
| Dependency scanning | `pip-audit` and `bandit` run in CI on every push |
| Container | Non-root user; multi-stage Dockerfile; pinned base image |

---

## Security Contact

**RWV Techsolutions LLC**  
Email: ops@realms2riches.com  
GitHub: [@rwv-techsolutions](https://github.com/rwv-techsolutions)  
Response SLA: 48 hours (business days)

*Made with IBM Bob*
