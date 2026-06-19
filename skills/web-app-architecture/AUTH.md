# Authentication

What stays constant across every app, and the one real choice: **which token**.

## Constant: hashing + dependency guards

- **bcrypt** for passwords (`bcrypt>=4.2`). Never store or log plaintext.
- Auth is expressed as **FastAPI dependencies**, not middleware, so each route
  declares its own requirement and you get it for free in the OpenAPI schema.

```python
# security.py
import bcrypt

def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

def verify_password(pw: str, hashed: str) -> bool:
    return bcrypt.checkpw(pw.encode(), hashed.encode())
```

```python
# api/deps.py
async def current_user(...) -> User | None: ...        # may be anonymous
async def require_user(user=Depends(current_user)) -> User:
    if user is None:
        raise HTTPException(401)
    return user
async def require_admin(user=Depends(require_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403)
    return user

UserDep  = Annotated[User, Depends(require_user)]
AdminDep = Annotated[User, Depends(require_admin)]
```

### Timing-safe lookups

On login, if the email doesn't exist, still run a dummy bcrypt verify before
returning failure. Otherwise response time reveals which emails are registered.
Use `hmac.compare_digest` for comparing tokens/CSRF values.

## The choice: which token

Pick **one** scheme per app based on who calls the API. The guards above don't
change — only how `current_user` resolves a request to a user.

### 1. Cookie-JWT — browser apps (server-rendered)

JWT (HS256, `pyjwt`) stored in an **httponly, `samesite=lax`, `secure`-in-prod**
cookie. Best default for a Jinja-rendered app: no token handling in JS, and the
cookie can't be read by scripts. Add CSRF protection for state-changing POSTs.

### 2. Bearer-JWT / API key — programmatic or SPA clients

`HTTPBearer`; the SPA stores the access token and sends `Authorization: Bearer`.
Issue short-lived access + longer refresh tokens with a `type` claim. For
machine clients, issue API keys (`sk_live_...`): show once, store only a **SHA-256
hash**, look up by hash.

### 3. Magic link — passwordless

Email a single-use, signed, expiring link; clicking it mints a session token. No
passwords to store or leak. Good for low-friction consumer signups.

### 4. OAuth — delegated identity

Authorization-code flow against a provider (Google, GitHub, a domain-specific
provider). **Always validate the `state` parameter** to block login-CSRF. Encrypt
any third-party access/refresh tokens at rest (e.g. a SQLAlchemy `TypeDecorator`
that encrypts on the way in and decrypts on the way out).

## CSRF (cookie-based auth only)

If auth rides in a cookie, the browser attaches it automatically, so you need CSRF
protection on state-changing requests: a per-session token rendered into forms and
checked on POST with `hmac.compare_digest`. Token-in-header schemes (bearer) are not
CSRF-exposed and don't need this.

## Quick guide

| App type                         | Scheme            |
|----------------------------------|-------------------|
| Server-rendered Jinja dashboard  | Cookie-JWT (+CSRF) |
| Decoupled SPA / mobile           | Bearer-JWT (+refresh) |
| Public/programmatic API          | API key (hashed)  |
| Low-friction consumer signup     | Magic link        |
| "Sign in with <provider>"        | OAuth             |
