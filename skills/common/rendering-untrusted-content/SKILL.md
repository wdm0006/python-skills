---
name: rendering-untrusted-content
description: Renders stored, authored, or imported content into HTML without shipping XSS — auditing every autoescape bypass (|safe, Markup, innerHTML), sanitizing Markdown output with an allowlist, escaping on both the server and the DOM, and writing sanitization tests that assert on the right copy of the string. Use when adding a Markdown or rich-text filter, rendering user/admin-authored content, reviewing a template that marks HTML trusted, building a client that injects values into innerHTML, or fixing an XSS report.
---

# Rendering Untrusted Content

Template engines autoescape by default, so the vulnerable surface is small and
enumerable: it is exactly the places where something says *this value is already
safe HTML*. Find those first; everything else is already handled.

## Step 1 — Enumerate the trust bypasses

```bash
# Server-side (Jinja/Django templates + the Python that feeds them)
grep -rnE '\|\s*safe|Markup\(|autoescape false|mark_safe' templates/ src/

# Client-side
grep -rnE 'innerHTML|outerHTML|insertAdjacentHTML|document\.write' web/ static/
```

Every hit is a claim that needs justification. A `|safe` on a value that came from
a database column is a claim about *everything that has ever been written to that
column*, including via an import path nobody remembers.

## Step 2 — Markdown output is not sanitized HTML

Markdown renderers pass raw HTML through **by design** — that is a documented
feature, not a bug. So a shared template filter shaped like this is an XSS sink:

```python
# BAD — the filter marks arbitrary stored markup trusted.
def _markdown(text: str) -> Markup:
    return Markup(markdown.markdown(text, extensions=["extra", "tables"]))
```

"Only admins author content" is not a boundary. As soon as there is an import
path, a seed script, or a second author, the content store is untrusted input.

Render, then sanitize with an **allowlist**, and only then mark trusted:

```python
import markdown, nh3
from markupsafe import Markup

ALLOWED_TAGS = {
    "p", "br", "hr", "em", "strong", "code", "pre", "blockquote",
    "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li",
    "a", "img", "table", "thead", "tbody", "tr", "th", "td",
}
ALLOWED_ATTRS = {
    "a": {"href", "title", "rel"},
    "img": {"src", "alt", "title"},
    "th": {"style", "align"},
    "td": {"style", "align"},
}

def _markdown(text: str) -> Markup:
    html = markdown.markdown(text, extensions=["extra", "tables"])
    return Markup(nh3.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        filter_style_properties={"text-align"},   # see below
    ))
```

**Do not hand-roll the allowlist logic.** Use a maintained HTML sanitizer
(`nh3`, the Rust/ammonia-backed successor to `bleach`). Regex-stripping `<script>`
is not sanitization.

### The table-alignment trap

Markdown's `tables` extension encodes column alignment as an inline style —
`<th style="text-align: left;">`. An allowlist that drops `style` is "secure" and
silently removes alignment from **every table in the corpus**. Allow `style` on
table cells and constrain which properties survive (`filter_style_properties`).

Then note that the sanitizer *normalizes* what it keeps: `text-align: left;`
comes back as `text-align:left` — no space, no trailing semicolon. An
exact-output test must expect the normalized form, not the string Markdown
emitted, or it fails on a correct fix.

## Step 3 — A shared filter has the whole corpus as its blast radius

One filter feeds every post body, every FAQ answer, every description. Changing
it re-renders all of them at once, and the failure mode is not a crash — it is
content quietly losing a construct.

Render every piece of authored content before and after the change and diff it
**character by character**, then keep that as a regression test:

```python
@pytest.mark.parametrize("path", sorted(CONTENT_DIR.glob("*.md")))
def test_authored_content_is_unchanged_by_sanitization(path):
    raw = markdown.markdown(path.read_text(), extensions=EXTENSIONS)
    assert _markdown(path.read_text()) == raw
```

If no authored file contains raw HTML, that equality holds and any future diff is
a genuine regression. If some file *does* need raw HTML, you have found the one
case worth an explicit decision instead of discovering it in production.

## Step 4 — Test the copy of the string that actually matters

The same value is often rendered several times on one page: in prose, in
`<meta>` tags, and inside a JSON-LD `<script>` block. A whole-document assertion
therefore reports a vulnerability that isn't one:

```python
# BAD — fails even when the prose is correctly sanitized.
assert "<script>alert(1)</script>" not in html
```

Template `tojson` filters emit HTML-safe JSON — angle brackets become
`\u003c` / `\u003e`, so the JSON-LD copy cannot break out of its
`<script>` element and is *not* a vulnerability. But the payload's text still
appears there, so a document-wide assertion goes red while the prose is
perfectly sanitized. Scope the assertion to the rendered prose:

```python
article = extract_article_html(html)
assert "<script>" not in article
assert "&lt;script&gt;" in article        # proves it was escaped, not dropped
```

Assert the escaped form is *present*, not just that the dangerous form is absent —
otherwise a filter that silently deletes the whole field passes.

Also scope the audit: a feed or export built from separately-escaped
title/description fields that never includes the body is not part of this
surface. Don't "fix" it.

## Step 5 — Escape at both ends

Server-side escaping does nothing for a client that re-injects the same value
through `innerHTML`. A card grid rendered safely by the server and a detail modal
built with a template literal are two independent sinks, and the second one is
usually the one that got missed.

```js
// Prefer the API that cannot execute markup.
el.textContent = item.description;

// When you must build markup, escape into a local first.
const description = escapeHtml(item.description);
const tags = item.tags.map(escapeHtml).join(", ");
modal.innerHTML = `<p>${description}</p><footer>${tags}</footer>`;
```

Escaping into a `const` before the template literal is not just style: wrapping
the expression inline pushes the line past the linter's length limit, and
reflowing the HTML string to fit introduces leading whitespace that is *visible*
inside `white-space: pre-wrap` blocks. Escape first, interpolate second.

## Step 6 — "No event handlers" is a test that fails on clean code

Asserting that no `on*` attribute appears in rendered output looks like a strong
XSS regression test, and it goes red immediately: application templates
legitimately emit handlers (`onclick="showDetail(3)"`). A test that fails on
correct code gets deleted within a week.

Allowlist the handlers your own templates emit and assert on the remainder:

```python
handlers = re.findall(r'\son(\w+)="([^"]*)"', card_html)
assert handlers == [("click", "showDetail(3)")]
```

Pinning the full list (rather than `not any(...)`) also catches a *second*,
injected handler alongside the legitimate one — presence assertions can't.

## Checklist

```
- [ ] Every |safe / Markup() / mark_safe / innerHTML site enumerated and justified
- [ ] Markdown (and any rich-text) output passes through an allowlist sanitizer
      before being marked trusted — a maintained library, not a regex
- [ ] Allowlist keeps constructs the renderer depends on (table-cell style),
      and tests expect the sanitizer's normalized output
- [ ] Authored content diffed before/after the filter change, pinned by a test
- [ ] Sanitization tests assert on the rendered prose, and assert the escaped
      form is present — not just that the raw payload is absent
- [ ] Client-side injection points escape too (or use textContent)
- [ ] Handler/attribute assertions allowlist what the app's own templates emit
```
