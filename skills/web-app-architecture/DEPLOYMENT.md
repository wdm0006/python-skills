# Deployment

## Contents
- Dockerfile
- One image, three roles
- Migrations run pre-deploy
- Infrastructure as code — Terraform
- Secrets
- Health checks
- CI

**One Docker image, one managed platform, all infrastructure in Terraform.** The web
service, the worker, and migrations are the *same image* run with different commands
— never separate codebases.

## Dockerfile

Build on the `astral-sh/uv` image and use a two-stage `uv sync` so the dependency
layer caches independently of your source.

```dockerfile
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# 1) deps only — cached unless the lockfile changes
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# 2) project source
COPY . .
RUN uv sync --frozen --no-dev

RUN useradd -m appuser
USER appuser

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "myapp.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]
```

`--proxy-headers --forwarded-allow-ips '*'` makes the app trust the platform's
load-balancer headers (correct scheme/host for secure cookies and redirects).

## One image, three roles

| Role    | Command                                            |
|---------|----------------------------------------------------|
| web     | `uvicorn myapp.main:app --proxy-headers ...`       |
| worker  | `python -m myapp.worker` (cron or always-on)       |
| migrate | `alembic upgrade head` (pre-deploy hook)           |

An `entrypoint.sh` that dispatches on `$1` (`web`/`worker`/`migrate`) keeps this in
one place.

## Migrations run pre-deploy

Run `alembic upgrade head` as the platform's **pre-deploy step**, so a new release's
schema is in place before traffic hits it. **Do not** run migrations at app startup
in production — concurrent instances race, and a bad migration takes down boot.

## Infrastructure as code — Terraform

Provision the platform with Terraform; keep a platform Blueprint file (a
`render.yaml`-style manifest) as the documented fallback. Organize by concern:

```
terraform/
  main.tf        # locals: shared env map, CSP, generated secrets
  variables.tf   # inputs (with sensible defaults)
  versions.tf    # provider pins
  render.tf      # project + Postgres + web service + worker/cron (+ static site)
  stripe.tf      # products, prices, webhook endpoint
  posthog.tf     # project + dashboards
  outputs.tf
```

```hcl
# render.tf (shape — applies to any managed platform with a TF provider)
resource "platform_postgres" "db"  { plan = "starter" }

resource "platform_web_service" "web" {
  image                = var.image
  pre_deploy_command   = "alembic upgrade head"
  health_check_path    = "/health"
  env_vars             = local.app_env       # shared map, see below
}

resource "platform_cron_job" "worker" {
  image    = var.image
  schedule = "*/5 * * * *"
  command  = "python -m myapp.worker"
  env_vars = local.app_env
}
```

Typical provider set: the platform provider, the **Stripe** provider, the
**PostHog** provider, and `random` for secret generation. One Terraform tree per
app — the app owns all of its own infrastructure; don't centralize it in a shared
infra repo.

## Secrets

Two clean patterns, no copy-pasting from dashboards:

- **Generate in Terraform** with `random_password` (e.g. `secret_key`) and inject the
  same value into both the web and worker services via the shared `local.app_env`.
- **Mark no-sync** (`sync = false` / equivalent) for values that must come from
  elsewhere, and set them out of band. The provisioned-by-TF Stripe webhook secret
  (covered in the payments reference) flows straight from the resource into the env.

The `secret_key` must be **identical** across web and worker (they verify the same
signed tokens). Never commit real secrets; `.env` is gitignored and `.env.example`
documents the variable names only.

## Health checks

Expose `/health` (and optionally `/readyz`) that runs `SELECT 1` and returns 503 if
the DB is unreachable. Point the platform's health check at it so a database-less
instance is pulled from rotation instead of serving errors.

## CI

GitHub Actions: `uv sync`, `ruff check` + `ruff format --check`, `alembic upgrade
head` against a Postgres service, then `pytest` (coverage-gated). For Approach B
frontends, a parallel job does `npm ci` + lint + build. Build/push the Docker image
on tag or main.
