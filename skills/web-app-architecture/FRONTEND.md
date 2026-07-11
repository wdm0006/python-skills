# Frontend

Two supported approaches. Pick one per app; don't mix paradigms within a single UI.

## Approach A — Server-rendered Jinja (default, ship-fast)

Render HTML on the server with Jinja2, style with **Tailwind via CDN**, add
interactivity with **Alpine.js via CDN**. **No JS build step, no bundler, no
node_modules in the critical path.** This is the right default for dashboards,
marketing, and CRUD-heavy apps — you stay in one language and one deploy artifact.

```python
# templating.py
from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory="app/templates")
templates.env.globals["posthog_key"] = settings.posthog_key   # inject brand/analytics
templates.env.filters["markdown"] = render_markdown            # custom filters
```

```
app/templates/
  base.html              # <head>, Tailwind CDN, Alpine CDN, analytics snippet
  _chrome/{nav,footer}.html
  dashboard/index.html   # {% extends "base.html" %}
```

- **Design tokens in one CSS file.** Even with Tailwind-CDN for layout, keep a
  hand-authored `static/css/tokens.css` of CSS custom properties (colors, fonts,
  spacing) so the look is consistent and themeable. This is the only CSS you write.
- **Alpine for sprinkles**, not for an app. Dropdowns, modals, tabs, optimistic
  toggles — `x-data`/`x-show`/`@click`. If a page starts needing real client state,
  that page wants Approach B, not more Alpine.
- **Hand-written CSS** (no Tailwind at all) is also fine for small apps; the point
  is *no build step*.

Trade-off: cheapest to build and operate; weakest for highly interactive,
stateful UIs.

## Approach B — Decoupled SPA (rich, interactive)

A separate **React + TypeScript + Vite** app in `web/`, built (`tsc -b && vite
build`) and deployed as static files on **its own origin**. The FastAPI app becomes
a pure JSON API (`/api/v1/...`) with **CORS** allowing the SPA origin. Tailwind (the
real PostCSS build, not CDN), `react-router`, an `axios`/`fetch` client, `posthog-js`.

```
web/
  src/{pages,components,context,lib}/
  package.json   vite.config.ts   tailwind.config.js
```

- The API serves no HTML; `docs` stays gated to admins.
- Auth is bearer-token (Approach B pairs with the Bearer-JWT scheme in the auth reference).
- The static site gets the same security headers and an SPA rewrite (all routes →
  `index.html`).

Trade-off: best UX for app-like products; two build pipelines, two deploys, and
CORS to manage.

## Choosing

| Want…                                        | Use |
|----------------------------------------------|-----|
| Fastest path to a working product, one deploy | A — Jinja + Tailwind/Alpine |
| Marketing + dashboard CRUD                    | A   |
| Highly interactive, stateful, app-like UI     | B — React/Vite SPA |
| A public API that *also* has a web UI         | B (the UI is just another API client) |

## Marketing & blog

Keep marketing pages as plain templates (Approach A) or a static-site generator
(e.g. Hugo) built into the same Docker image and served under `/blog` via
`StaticFiles`. No need for a separate hosting story.

## LLM features

When the app calls an LLM, use **`pydantic-ai`** with **structured Pydantic
outputs** so model responses are validated, typed objects rather than free text:

```python
from pydantic_ai import Agent

agent = Agent(f"openai-chat:{settings.openai_model}", output_type=Analysis, retries=2)
result = await agent.run(prompt)        # result.output is a validated `Analysis`
```

- **Require the key at boot** (`Field(min_length=1)`) when the feature is core — fail
  fast rather than discovering a missing key mid-request. Gate the feature behind a
  config flag if it's optional.
- **Make the model configurable** via env (`MYAPP_OPENAI_MODEL`) so you can swap
  models without a deploy.
- Keep all LLM calls inside a service module, like any other external SDK.
