# Core Stack Templates

Copy-pasteable starting points for the framework, packaging, database, and config
layers. Names use `myapp`; the env prefix is `MYAPP_`.

## pyproject.toml

```toml
[project]
name = "myapp"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "sqlalchemy[asyncio]>=2.0.36",
    "asyncpg>=0.30",
    "alembic>=1.14",
    "pydantic-settings>=2.6",
    "stripe>=15.2",
    "sentry-sdk[fastapi]>=2.18",
    "posthog>=7.18",
    "slowapi>=0.1.9",
    "bcrypt>=4.2",
    "pyjwt>=2.10",
    "jinja2>=3.1",            # if server-rendering
    "httpx>=0.27",
]

[project.scripts]
myapp-api    = "myapp.main:run"
myapp-worker = "myapp.worker:main"
myapp-seed   = "myapp.seed:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv]
package = true

[dependency-groups]
dev = ["pytest>=8.3", "pytest-asyncio>=0.24", "pytest-cov", "ruff", "playwright"]

[tool.ruff]
line-length = 100
[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "C4", "SIM"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
pythonpath = ["src"]
```

Manage with **uv** only: `uv sync`, `uv run pytest`, `uv add <pkg>`. Commit `uv.lock`.
`requires-python >=3.11`; the Docker image and CI can pin 3.12.

## config.py — pydantic-settings with prod guards

```python
from functools import lru_cache
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MYAPP_", env_file=".env", extra="ignore")

    environment: str = "development"
    secret_key: str = "dev-insecure-change-me"
    database_url: str = "sqlite+aiosqlite:///./local.db"
    cors_origins_raw: str = ""
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    sentry_dsn: str = ""
    posthog_key: str = ""

    @property
    def is_prod(self) -> bool:
        return self.environment == "production"

    @property
    def db_url(self) -> str:
        # Platforms hand out postgres://; SQLAlchemy async needs the driver.
        url = self.database_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins_raw.split(",") if o.strip()]

    @property
    def billing_enabled(self) -> bool:
        return bool(self.stripe_secret_key and self.stripe_webhook_secret)

    @model_validator(mode="after")
    def _guard_prod(self):
        if self.is_prod:
            if self.secret_key == "dev-insecure-change-me":
                raise ValueError("MYAPP_SECRET_KEY must be set in production")
            if "*" in self.cors_origins:
                raise ValueError("wildcard CORS not allowed in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

Commit `.env.example` documenting every variable; gitignore `.env`.

## db.py — lazy async engine + session dependency

```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from myapp.config import get_settings

_engine = None
_sessionmaker = None


def _init():
    global _engine, _sessionmaker
    if _engine is None:
        _engine = create_async_engine(
            get_settings().db_url,
            pool_pre_ping=True,
            pool_recycle=300,
            future=True,
        )
        _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    _init()
    async with _sessionmaker() as session:
        yield session
```

Why each knob: `pool_pre_ping` survives platform connection drops;
`expire_on_commit=False` keeps ORM objects usable after commit (essential in async);
the lazy singleton avoids opening a pool at import time (breaks tests and CLI tools).

## models.py — SQLAlchemy 2.0 declarative

```python
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    password_hash: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(default=None)  # soft delete
```

Use typed `Mapped[]`/`mapped_column`. Prefer soft-delete (`deleted_at`) over hard
deletes. For capacity/race-prone rows, lock explicitly with `SELECT ... FOR UPDATE`.

## Alembic

`alembic init migrations`, point `sqlalchemy.url` at the runtime config, set
`target_metadata = Base.metadata`. Autogenerate then **read the diff** before
committing. Apply with `alembic upgrade head` in the deploy's pre-deploy step — never
auto-migrate at app startup in production. Use `render_as_batch=True` if you also run
SQLite locally.

## Makefile — the developer entrypoint

```makefile
run:        ; uv run uvicorn myapp.main:app --reload
test:       ; uv run pytest
lint:       ; uv run ruff check . && uv run ruff format --check .
fmt:        ; uv run ruff format . && uv run ruff check --fix .
migrate:    ; uv run alembic upgrade head
revision:   ; uv run alembic revision --autogenerate -m "$(m)"
```

## Testing shape

`pytest` + `pytest-asyncio` (`asyncio_mode=auto`). `conftest.py` sets env vars
*before* importing the app, builds the schema from `Base.metadata` on a fresh
SQLite engine per test, and drives the app through `httpx.ASGITransport` (no live
server). Run against SQLite locally for speed; run a Postgres service in CI. Add
Playwright for browser/e2e and a thin prod smoke suite.
