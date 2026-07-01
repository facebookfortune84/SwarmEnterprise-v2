# Contributing to SwarmEnterprise v2

Thank you for your interest in contributing. This document explains how to set
up your development environment, the branching strategy, commit conventions,
pull request process, and code-review requirements.

---

## Table of Contents

1. [Development Environment Setup](#development-environment-setup)
2. [Branching Strategy](#branching-strategy)
3. [Commit Message Conventions](#commit-message-conventions)
4. [Pull Request Process](#pull-request-process)
5. [Code Review Requirements](#code-review-requirements)
6. [Code Style and Quality Gates](#code-style-and-quality-gates)

---

## Development Environment Setup

### Prerequisites

| Tool | Minimum Version |
|------|----------------|
| Python | 3.11 |
| Docker + Docker Compose | 24.x / 2.x |
| Git | 2.40+ |
| Make | any |

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/rwv-techsolutions/swarmenterprise-v2.git
cd swarmenterprise-v2

# 2. Create and activate a virtual environment
python -m venv .venv
# Linux / macOS
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# 3. Install all runtime and development dependencies
pip install -r requirements.txt -r requirements-dev.txt

# 4. Install pre-commit hooks
pre-commit install

# 5. Copy and configure environment variables
cp .env.example .env
python scripts/generate_secrets.py   # generates JWT_SECRET_KEY, SECRET_KEY, etc.
# Open .env and fill in DATABASE_URL / POSTGRES_PASSWORD / STRIPE_* etc.

# 6. Run database migrations
alembic upgrade head

# 7. Confirm everything works
pytest tests/ -q
```

### Useful Make Targets

| Target | Purpose |
|--------|---------|
| `make lint` | ruff check + ruff format |
| `make test` | pytest with coverage |
| `make migrate` | alembic upgrade head |
| `make health` | poll /health endpoint |
| `make smoke` | API smoke tests |
| `make clean` | remove containers, volumes, caches |

---

## Branching Strategy

This project uses a **trunk-based development** model with short-lived feature
branches.

```
main                  ← production-ready, always deployable
  └── feature/<slug>  ← new features (merged via PR)
  └── fix/<slug>      ← bug fixes (merged via PR)
  └── chore/<slug>    ← tooling, deps, docs (merged via PR)
  └── hotfix/<slug>   ← urgent production patches
```

### Rules

- `main` is **protected** — no direct pushes; all changes go through PRs.
- Branch names use **kebab-case**: `feature/add-webhook-retry`,
  `fix/jwt-expiry-edge-case`.
- Feature branches are deleted after merge.
- Keep branches short-lived (≤ 3 working days). If longer is needed, open a
  draft PR to signal work-in-progress.

---

## Commit Message Conventions

This project follows [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).

```
<type>(<scope>): <short summary>

[optional body]

[optional footer(s)]
```

### Types

| Type | When to use |
|------|------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting, whitespace (no logic change) |
| `refactor` | Code restructure without feature/fix |
| `perf` | Performance improvement |
| `test` | Adding or fixing tests |
| `chore` | Build tooling, deps, CI |
| `ci` | CI/CD pipeline changes |
| `revert` | Revert a previous commit |

### Scope (optional)

Use the affected module: `auth`, `tickets`, `workflows`, `notifications`,
`celery`, `alembic`, `docker`, `docs`, `ci`.

### Examples

```
feat(tickets): add SLA breach escalation endpoint
fix(auth): handle expired refresh token gracefully
chore(deps): pin starlette to <0.42.0
test(workflows): add cancel and resume coverage
docs(api): document /api/v1/tickets endpoints
```

### Rules

- Summary line ≤ 72 characters, **imperative mood** ("add" not "added").
- No period at the end of the summary.
- Reference issues/PRs in the footer: `Closes #42`, `Refs #17`.

---

## Pull Request Process

1. **Open a PR early** — as a draft if the work is in progress.
2. **Fill out the PR template** completely (description, motivation, test plan).
3. **Ensure all CI checks pass** before requesting review:
   - `lint` — ruff check + ruff format
   - `typecheck` — mypy
   - `unit-tests` — pytest with ≥ 90 % coverage
   - `security` — bandit + pip-audit
   - `migration-check` — alembic up/down round-trip
4. **Request at least one reviewer** from the `@rwv-techsolutions/core` team.
5. **Address all review comments** before merging — resolve threads, don't just
   close them.
6. **Squash-merge** into `main` — the merge commit title must match
   Conventional Commits format.
7. **Delete the branch** after merge.

### PR Size Guidelines

| Lines changed | Guidance |
|--------------|---------|
| < 200 | Ideal — review same day |
| 200–500 | Acceptable — break up if possible |
| > 500 | Split into smaller PRs unless truly atomic |

---

## Code Review Requirements

### Reviewer Responsibilities

- Read every line changed, not just the diff summary.
- Verify tests cover the new code paths.
- Check for security implications (SQL injection, auth bypass, secret exposure).
- Confirm Pydantic v2 patterns (`model_dump`, `model_validate`, `ConfigDict`).
- Ensure all FastAPI route handlers use `Depends(get_db)` — never
  `SessionLocal()` directly.
- Verify no hardcoded secrets, hostnames, or ports.

### Author Responsibilities

- Self-review your own diff before requesting review.
- Respond to all comments within 1 business day.
- Explain non-obvious code decisions in comments or PR description; use a
  linked issue instead of an inline annotation marker.

### Merge Criteria

All of the following must be true before merging:

- [ ] All CI checks green
- [ ] At least 1 approved review
- [ ] No unresolved review threads
- [ ] Coverage is ≥ 90 % (or a documented exception has been approved)
- [ ] `CHANGELOG.md` updated if this is a user-facing change
- [ ] Migration reviewed if schema changes are included

---

## Code Style and Quality Gates

- **Formatter**: `ruff format` (line length 100, target Python 3.11)
- **Linter**: `ruff check` — zero violations required
- **Type checker**: `mypy backend/` — no new unignored errors
- **Security**: `bandit -r backend/` — no HIGH/CRITICAL issues
- **Pre-commit**: all hooks must pass (`pre-commit run --all-files`)

Run the full local quality gate before pushing:

```bash
ruff format .
ruff check . --fix
mypy backend/ --ignore-missing-imports
pytest tests/ -q --cov=backend --cov-fail-under=90
```

---

*Made with IBM Bob*
