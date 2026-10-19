# Modernizing an old UI

## Contents
- What "old" usually means
- The order of operations
- Trace the cascade before restyling
- Slicing it into PRs
- Server-rendered apps
- What not to do
- Done criteria

## What "old" usually means

An app reads as dated for a short list of reasons, nearly all fixable without a
rewrite:

- Default browser or early-Bootstrap styling: serif body text, blue underlined links
  everywhere, gradients and bevels, heavy borders with no consistent role.
  Consistent outlines and solid offset shadows can be intentional in a game or
  playful consumer interface; preserve that character when fixing drift.
- Dense, small text with tight line height and no whitespace.
- Too many colors and font sizes, chosen per page over the years.
- Fixed-width desktop layout that does not reflow on a phone.
- Tables used for layout; forms with labels beside fields in a grid.
- No visual states: no hover, no focus, no loading, no empty states.
- Icons from three different sets, or none at all.

## The order of operations

Each step makes the next one cheaper. Skipping ahead (redesigning a page before the
tokens exist) produces one pretty page and a new inconsistency.

1. **Screenshot the key screens** at desktop and phone width. These are the "before"
   images for every later PR.
2. **Add tokens with no visual change.** Introduce the token set and replace existing
   hard-coded values with the nearest token. The screenshots should look nearly
   identical; that is the point — this PR is pure plumbing and easy to review.
3. **Base styles.** Body font, size and line height; heading scale; link style; a
   max content width; page padding. This single PR changes the feel of every page.
4. **Primitives.** Buttons, inputs, cards, tables, alerts, nav — rebuilt on tokens
   with all interactive states and a visible focus ring.
5. **Layout and responsiveness.** Replace fixed widths with fluid containers and a
   simple grid; stack columns at phone width; make tables scroll horizontally or
   collapse to cards.
6. **Screen by screen.** Now redesign individual screens, highest-traffic first
   (landing/home, the core journey, settings), adding empty/loading/error states.
7. **Polish.** Icons from one set, dark mode via token overrides, subtle motion
   (respecting `prefers-reduced-motion`).

## Trace the cascade before restyling

Repeated design passes can leave the same selector defined several times. Editing
an earlier block may do nothing because a later declaration wins. Before changing
a component, search for every definition and inspect the browser's matched rules
and computed value on the actual element:

```bash
rg -n '\.result-card|\.settings-input' web/ --glob '*.css'
```

```css
/* Earlier block: changing this border alone has no visible effect. */
.result-card { border: 1px solid var(--color-border); }
/* Later block with equal specificity wins in the same cascade layer. */
.result-card { border: 1px solid var(--color-accent); }
```

Consolidate overlapping declarations for the component you are touching into one
base rule plus explicit state and responsive overrides. Repeated selectors are
not automatically redundant: media queries, theme scopes, cascade layers and
pseudo-classes can give them different jobs. Preserve those conditions and check
which declaration wins before moving or deleting a block. Avoid appending another
override or adding `!important` just to defeat an earlier design pass.

Verify the consolidation with before/after screenshots at desktop and phone
widths, including affected focus, hover, checked and theme states. A cleanup
should preserve the computed appearance; then apply the intended restyle to the
rule that actually owns the property.

Screenshots miss states and sub-pixel differences, so back a pure deduplication with
a computed-style diff. Drive the page in a headless browser at one fixed width, in
each theme, with animations and transitions disabled. For every element (and its
`::before`/`::after` when they have `content`), dump `getComputedStyle` into JSON,
once on the base commit and once on the branch, and diff the files. Repeat across
each screen state (first-run, populated, running, error) and with hover, focus,
disabled and invalid forced on representative elements. An empty diff means the
cleanup changed nothing; any entry is a block that was not redundant. Also run a
structural scan of the stylesheet (for example with a CSS parser) and confirm that
no selector is still defined twice within the same at-rule context.

Do not pixel-diff regions that show live data such as clocks or countdowns; they
differ even between two runs of the same commit.

## Slicing it into PRs

One step above is usually one PR; step 6 is one PR per screen. Each PR:

- names the screens it touches,
- includes before and after screenshots at both widths,
- avoids behavior changes (a redesign PR that also changes logic is hard to review),
- leaves the app shippable — no half-migrated page left in a broken state.

A step-2 "tokens, no visual change" PR is the safest first move on any old app and a
good first issue.

## Server-rendered apps

Most old apps are server-rendered (Django/Flask/Jinja templates, ERB, plain HTML).
They modernize well in place:

- Keep the templates; add one global stylesheet with tokens and primitives, and
  replace inline styles and per-page CSS as each screen is touched.
- Add a base layout template if pages duplicate their chrome; it is where the nav,
  max width and footer get fixed once.
- Progressive enhancement (a small amount of JavaScript or htmx) is enough for
  interactive states; a SPA rewrite is not a design improvement.

## What not to do

- A framework migration presented as a redesign.
- A "v2" redesign branch that diverges for weeks — ship incrementally on main.
- Copying a trendy look (glassmorphism, heavy gradients) without fixing hierarchy.
- Changing information architecture and visual design in the same PR.
- Introducing a component library and leaving the old styles alongside it forever;
  migrate a screen fully when you touch it.

## Done criteria

- One token source; no hard-coded colors, font sizes or spacing in new code.
- Body text 16px, line height ~1.5, readable line length.
- Every page usable at 390px width without horizontal scrolling (data tables
  excepted, which scroll in their own container).
- Every interactive element has hover and visible focus states.
- Key screens have designed empty, loading and error states.
- Contrast passes the checks in the `building-accessible-interfaces` skill.
