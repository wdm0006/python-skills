---
name: building-python-web-apps
description: Provides an opinionated reference architecture for production Python web apps — FastAPI + async SQLAlchemy + Postgres, pydantic-settings config, Stripe billing, server-rendered Jinja or a decoupled SPA, deployed as a single Docker image on a managed platform via Terraform. Use when starting a new SaaS/web app, choosing a stack, structuring routers/services/models, wiring Stripe webhooks, protecting FastAPI docs or OpenAPI routes, setting up config/secrets, or deciding how to deploy.
---

# Building Python Web Apps

An opinionated, batteries-included blueprint for shipping a small-to-mid SaaS app
solo or with a small team. It favors **boring, well-understood pieces wired the same
way every time** so a new app reaches "auth + billing + deploy" in hours, not weeks.

## The Default Stack

| Concern        | Default                                                        |
|----------------|---------------------------------------------------------------|
| Framework      | **FastAPI** (async), `uvicorn[standard]`                      |
| Packaging      | **uv** + `pyproject.toml` + `uv.lock`, hatchling, `src/` layout |
| Database       | **Postgres 16** + `asyncpg`, **SQLAlchemy 2.0** async, **Alembic** |
| Config         | **pydantic-settings** `BaseSettings`, env-prefixed, `@lru_cache` |
| Payments       | **Stripe ≥15**, one signed webhook, idempotency table         |
| Auth           | dependency guards + **bcrypt**; token scheme per app (see AUTH.md) |
| Frontend       | **Jinja2 + Tailwind (CDN) + Alpine.js**, *or* a decoupled SPA |
| Background work | **cron-as-worker** (same image, different command) — no Celery |
| Observability  | **Sentry + PostHog**, both no-op until keyed                  |
| Deploy         | **Docker** → managed platform (Render-style) via **Terraform** |
| Lint/test      | **ruff** + **pytest** + `pytest-asyncio`, Makefile entrypoint |

If you have no reason to deviate, use every row. The rest of this skill is the
"how", and the reference files hold copy-pasteable templates.

## Package Layout

One layered package, routers split by domain. Business logic never lives in a route.

```
src/myapp/
  main.py            # app + middleware + include_router() in a loop
  config.py          # pydantic-settings Settings + get_settings()
  db.py              # lazy async engine/sessionmaker + get_session() dep
  models.py          # SQLAlchemy 2.0 DeclarativeBase, Mapped[]
  schemas.py         # Pydantic request/response models
  security.py        # hashing, tokens, auth dependencies
  observability.py   # Sentry/PostHog init (guarded)
  api/               # one APIRouter module per domain (+ deps.py, webhooks.py)
  services/          # business logic; external SDKs isolated here
migrations/versions/ # Alembic
tests/               # pytest, mirrors api/ + services/
terraform/           # render.tf, stripe.tf, posthog.tf, variables.tf
Dockerfile  docker-compose.yml  pyproject.toml  uv.lock  alembic.ini  Makefile
```

**Routes → Services → Models.** Routes parse/validate and call services. Services
hold the logic and own all external SDK calls (Stripe, email, LLM) so they're
mockable. Models are persistence only.

## App Wiring

A module-level `app` (a factory is fine but unnecessary), routers registered in a
loop, cross-cutting concerns as middleware, and a health check that proves the DB
is reachable. Full template in **[STACK.md](STACK.md)**.

```python
# main.py (shape)
app = FastAPI(docs_url=None if settings.is_prod else "/docs")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, ...)
# request-id + security-headers middleware, slowapi rate limiter
for router in (auth.router, billing.router, webhooks.router, ...):
    app.include_router(router)

@app.get("/health")
async def health(db: SessionDep):
    await db.execute(text("SELECT 1"))   # 503 if the DB is down
    return {"status": "ok"}
```

Share dependencies as `Annotated` type aliases — they read cleanly in signatures:

```python
# api/deps.py
SessionDep = Annotated[AsyncSession, Depends(get_session)]
UserDep    = Annotated[User, Depends(require_user)]
```

## Database

Lazy singleton async engine, `pool_pre_ping=True`, `expire_on_commit=False`, a
`get_session()` async-generator dependency, and a URL normalizer so platform-issued
`postgres://` URLs become `postgresql+asyncpg://`. **Postgres in prod, SQLite
(`aiosqlite`) for fast local/CI tests.** Migrations via Alembic, applied in the
deploy's pre-deploy step. See **[STACK.md](STACK.md)**.

## Config & Secrets

One `Settings(BaseSettings)` with an env prefix, `@lru_cache get_settings()`, and
**validators that refuse to boot in production with a default/missing secret**.
Commit a `.env.example`; never commit `.env`. Computed `@property` helpers
(`is_prod`, `cors_origins`, `billing_enabled`) keep routes clean.

## Payments

Stripe with **exactly one signature-verified webhook endpoint**, idempotency backed
by a persisted events table, and dispatch by event type that never 500s on an
unknown event. Isolate every SDK call in a `services/stripe/` module. Full patterns
(checkout, subscriptions, webhook handler, Terraform-provisioned signing secret) in
**[PAYMENTS.md](PAYMENTS.md)**.

## The Decisions You Actually Make

Everything above is fixed. These are the real per-app choices:

- **Frontend** — server-rendered Jinja + Tailwind/Alpine (zero JS build, ship fast)
  *or* a decoupled React/Vite SPA on its own origin (richer UI, more moving parts).
  → **[FRONTEND.md](FRONTEND.md)**
- **Auth scheme** — cookie-JWT (browser app), bearer-JWT/API-key (programmatic),
  magic-link (passwordless), or OAuth (delegated). bcrypt + dependency guards are
  constant; only the token differs. → **[AUTH.md](AUTH.md)**
- **Background work** — inline in the request (simplest), cron-as-worker (the
  default for periodic/queued work), or a Redis-backed job queue (long-poll jobs).
  Reach for Celery only when you've outgrown all three. → **[BACKGROUND_JOBS.md](BACKGROUND_JOBS.md)**
- **LLM features** — `pydantic-ai` with structured Pydantic outputs, key required
  at boot, model configurable via env. → **[FRONTEND.md](FRONTEND.md)** has the note.

## Deployment

Single Docker image (the `astral-sh/uv` base, two-stage `uv sync` for layer
caching, non-root, `uvicorn --proxy-headers`). The **same image** runs web, worker,
and migrations via different commands. Target a managed platform; provision it with
**Terraform** (app + Postgres + Stripe + PostHog as code), with a platform Blueprint
file as the documented fallback. Migrations run in the pre-deploy step. Secrets are
generated in Terraform or marked no-sync and set out of band. → **[DEPLOYMENT.md](DEPLOYMENT.md)**

## Review Checklist

```
Structure:
- [ ] Logic in services/, not in route handlers
- [ ] External SDKs (Stripe/email/LLM) isolated behind a service module
- [ ] /health (or /readyz) actually pings the database

Data:
- [ ] Async engine is a lazy singleton with pool_pre_ping
- [ ] postgres:// URLs normalized to postgresql+asyncpg://
- [ ] Every schema change has an Alembic migration

Config:
- [ ] Production refuses to boot on a default/missing secret
- [ ] CORS not "*" and HTTPS enforced in production
- [ ] .env.example committed; .env gitignored

Billing & security:
- [ ] Exactly one Stripe webhook, signature-verified, idempotent
- [ ] Passwords bcrypt-hashed; auth via reusable dependencies
- [ ] CSRF enforced globally for cookie auth (not per-form opt-in); no
      state-changing GET requests — mutations use POST/DELETE
- [ ] Client IP for rate-limit keys/allowlists/audit logs taken from a fixed
      position in the X-Forwarded-For chain (not the spoofable left-most value)
- [ ] Private OpenAPI schema served only by a custom guarded route (`openapi_url=None`)
- [ ] Sentry + PostHog init guarded (no-op when unkeyed, never break a request)

Ship:
- [ ] One Docker image; web/worker/migrate are just different commands
- [ ] Migrations run pre-deploy, not at app startup in prod
- [ ] Infra is in Terraform; secrets are not committed
```

## Reference Files

- **[STACK.md](STACK.md)** — pyproject, `main.py`, `db.py`, `config.py`, Makefile templates
- **[PAYMENTS.md](PAYMENTS.md)** — Stripe checkout + idempotent webhook patterns
- **[AUTH.md](AUTH.md)** — the four token schemes and shared dependency guards
- **[BACKGROUND_JOBS.md](BACKGROUND_JOBS.md)** — inline vs cron-worker vs Redis queue
- **[FRONTEND.md](FRONTEND.md)** — Jinja/Tailwind/Alpine vs decoupled SPA (+ LLM note)
- **[DEPLOYMENT.md](DEPLOYMENT.md)** — Dockerfile, Terraform, migrations, secrets
