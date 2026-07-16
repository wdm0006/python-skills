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

### The client-IP trap this opens up

Trusting `X-Forwarded-For` (XFF) for scheme/host is fine. Trusting it to identify
*who* a request is from is a footgun, and it's the same mistake in three places:
**rate-limit keys, IP allowlists, and the IP you write to audit logs**. A proxy
*appends* the real peer to the XFF chain, so the **left-most** value is whatever the
client sent — attacker-controlled. slowapi's `get_remote_address` returns
`request.client.host`, which under `--forwarded-allow-ips '*'` is *also* derived from
that same untrusted header. So a naive limiter keyed on the left-most XFF (or on
`request.client.host` with a wildcard trust) buckets by a value the attacker picks:

```python
# WRONG — attacker rotates X-Forwarded-For per request, lands in a fresh bucket
# every time. Measured effect: ~0/50 login attempts blocked vs 45/50 on the real IP.
client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
limiter = Limiter(key_func=get_remote_address)  # request.client.host, same problem
```

The trustworthy value is a **fixed position counted from the right** — you trust
exactly as many hops as you actually run. With one managed load balancer in front,
that's the last entry:

```python
# RIGHT — trust N proxies (here 1); take the (N+1)th from the right.
TRUSTED_PROXY_HOPS = 1

def real_client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        chain = [p.strip() for p in xff.split(",") if p.strip()]
        if len(chain) > TRUSTED_PROXY_HOPS:
            return chain[-(TRUSTED_PROXY_HOPS + 1)]
    return request.client.host

limiter = Limiter(key_func=real_client_ip)
```

Define this **once** and reuse it everywhere an IP is consumed — the bug reappears
per-copy when `_get_client_ip` is reimplemented in the limiter, the auth router, and
the audit service independently. Nothing else guards brute force by default
(a `failed_attempts` column with no lockout enforcement does not), so a spoofable
limiter is the whole defense. Note too that an in-memory limiter is **per process**,
so effective limits multiply by instance count — back anything that must hold
app-wide (login, password-reset, registration) with a shared store (Redis), not
process memory.

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
