---
name: building-accessible-interfaces
description: Makes web and app UIs usable by keyboard, screen-reader, low-vision and motion-sensitive users — semantic HTML before ARIA, labelled controls, visible focus, WCAG AA contrast measured rather than eyeballed, touch targets, reduced motion, and automated axe checks plus a manual keyboard pass in CI or before every UI PR. Use when building or restyling a screen, adding a form, modal, menu or custom control, choosing colors, or reviewing a UI change.
---

# Building Accessible Interfaces

Accessibility failures are concentrated in a few places: custom controls built from
`div`s, inputs without labels, invisible focus, low-contrast "subtle" text, and
modals that trap nothing or everything. Check those first; they cover most real
users' problems and most automated findings.

## Contents
- Step 1 — Semantic HTML first
- Step 2 — Every control has a name
- Step 3 — Keyboard and focus
- Step 4 — Contrast, measured
- Step 5 — Motion, zoom and touch
- Step 6 — Automated checks plus a manual pass
- Native apps
- Anti-patterns

## Step 1 — Semantic HTML first

The right element gives keyboard support, focus and screen-reader semantics for free.

| Need | Use | Not |
|------|-----|-----|
| Action | `<button type="button">` | `<div onclick>`, `<a href="#">` |
| Navigation | `<a href="/path">` | `<button onclick="location=…">` |
| Page regions | `<header> <nav> <main> <footer>` | anonymous `div`s |
| Headings | one `<h1>`, then `<h2>`… in order | bold `div`s, skipped levels |
| Lists | `<ul>/<ol>` | stacked `div`s |
| Data | `<table>` with `<th scope>` | grids of `div`s |
| Toggle | `<input type="checkbox">` / `<button aria-pressed>` | a styled `span` |

ARIA is for the gaps HTML cannot fill (tabs, comboboxes, live regions). "No ARIA is
better than bad ARIA": a wrong `role` actively misinforms assistive tech.

## Step 2 — Every control has a name

- Inputs: a visible `<label for>`; placeholder text is not a label (it disappears and
  is usually low contrast).
- Icon-only buttons: `aria-label="Delete contact"` (the action and its object).
- Images: meaningful `alt`; decorative images `alt=""`.
- Errors: tie the message to the field with `aria-describedby` and set
  `aria-invalid="true"`; see the `designing-interaction-states` skill for wording.
- Links: text that makes sense alone — "View invoice #1042", not "click here".

## Step 3 — Keyboard and focus

Unplug the mouse and use Tab, Shift+Tab, Enter, Space, Esc and the arrow keys.

- Every interactive element is reachable, in visual order, with a **visible**
  focus indicator. Never `outline: none` without a replacement; use
  `:focus-visible { outline: 2px solid <focus color>; outline-offset: 2px; }`.
- Modals: move focus into the dialog on open, keep Tab inside it, close on Esc,
  return focus to the trigger on close. The native `<dialog>` element with
  `showModal()` does most of this.
- Menus and popovers close on Esc and on outside click; focus does not get lost.
- Add a "Skip to content" link as the first focusable element on content-heavy pages.
- No keyboard traps; no `tabindex` greater than 0.

## Step 4 — Contrast, measured

WCAG AA: **4.5:1** for normal text, **3:1** for large text (≥ 24px, or ≥ 18.66px
bold) and for UI component boundaries and focus indicators. Measure; do not judge by
eye.

```bash
# axe reports contrast failures with the exact ratio and element
npx --yes @axe-core/cli "http://127.0.0.1:$PORT/" --tags wcag2a,wcag2aa
```

Common failures: grey placeholder text, muted helper text below ~#767676 on white,
white text on light brand colors, disabled-looking "secondary" buttons. Check both
light and dark themes. Never convey meaning by color alone — pair red with an icon
or text ("Overdue").

## Step 5 — Motion, zoom and touch

- Respect `prefers-reduced-motion`: disable parallax, auto-playing animation and
  large transitions.

  ```css
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; scroll-behavior: auto !important; }
  }
  ```
- Text resizes to 200% without loss of content; use `rem` for type, never disable
  zoom (`user-scalable=no`).
- Touch targets at least 44×44px (24×24px absolute minimum with spacing).
- Do not auto-advance carousels or time out forms without a way to extend.

## Step 6 — Automated checks plus a manual pass

Automated tools catch roughly a third of issues; they are a floor, not a verdict.

```python
# tests/test_a11y.py — Playwright + axe; run with: uv run --with playwright --with axe-playwright-python pytest
from axe_playwright_python.sync_playwright import Axe

def test_home_has_no_serious_violations(page, live_server_url):
    page.goto(live_server_url + "/")
    results = Axe().run(page)
    serious = [v for v in results.response["violations"] if v["impact"] in ("serious", "critical")]
    assert not serious, results.generate_report()
```

Then, for every UI PR: a 2-minute keyboard pass of the changed screen, a contrast
check of any new colors, and (for significant flows) a quick pass with VoiceOver
(Cmd+F5 on macOS) to hear that controls announce sensible names.

## Native apps

SwiftUI and UIKit give most of this through system components: use `Button`,
`Toggle`, `Label` and standard lists; support Dynamic Type (text styles, not fixed
point sizes); add `.accessibilityLabel` to icon-only buttons; group related elements
with `.accessibilityElement(children: .combine)`; test with VoiceOver and the
Accessibility Inspector, and at the largest Dynamic Type size.

## Anti-patterns

- `div` and `span` click handlers instead of buttons and links.
- Removing focus outlines for aesthetics.
- Placeholder-as-label forms.
- Light grey text to look "minimal".
- Accessibility deferred to "a later audit" — retrofitting costs far more than
  using the right element now.
