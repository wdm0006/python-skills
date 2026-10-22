---
name: designing-interfaces
description: Makes a product's UI look deliberate and current instead of dated or improvised — auditing a screen against hierarchy, type scale, spacing scale, color tokens, layout and component consistency; introducing design tokens before restyling anything; and verifying every change visually with before/after screenshots. Use when building or restyling any web or app screen, reviewing a UI that looks old, cluttered or inconsistent, starting a design system for an existing app, or planning a design-improvement issue.
---

# Designing Interfaces

Most "ugly" apps are not missing talent, they are missing **constraints**: twelve
font sizes, spacing picked per element, a dozen near-identical greys, and buttons
that each grew their own style. Good design here is mostly removing choices. Fix
the system first (tokens, scales), then the screens fall into line.

## Contents
- Step 1 — Look before you touch anything
- Step 2 — Audit against the six fundamentals
- Match the visual language to the product
- Step 3 — Tokens first, restyle second
- Step 4 — Components and states
- Step 5 — Verify visually
- Native apps
- Scoping design work into issues
- Anti-patterns

## Step 1 — Look before you touch anything

Run the app with local data and screenshot the screens that matter at desktop and
phone widths. Design judged from source code is guesswork.

```bash
uvx --from playwright playwright screenshot --viewport-size "1280,800" "http://127.0.0.1:$PORT/" before-home-desktop.png
uvx --from playwright playwright screenshot --viewport-size "390,844"  "http://127.0.0.1:$PORT/" before-home-phone.png
```

Keep these "before" images; every design change is reviewed as a before/after pair.

## Step 2 — Audit against the six fundamentals

Score each screen; the lowest scores are where the work is.

1. **Hierarchy** — squint at the screenshot. Is there exactly one obvious primary
   thing (heading, primary action), then a clear second level, then the rest? If
   everything is bold, large, or colored, nothing is. Demote before you promote:
   most fixes make secondary text smaller and lighter, not the primary bigger.
2. **Typography** — one or two families, a modular scale of 5–7 sizes (e.g. 12, 14,
   16, 20, 24, 32, 40), body at 16px with ~1.5 line height, line length 50–75
   characters, weights limited to regular/medium/semibold. Count the distinct font
   sizes in the CSS; more than eight is a finding.
3. **Spacing** — every margin, padding and gap comes from one scale on a 4px base
   (4, 8, 12, 16, 24, 32, 48, 64). Related things sit closer together than
   unrelated things (proximity *is* grouping). Generous whitespace reads as quality;
   cramped reads as old.
4. **Color** — for a utility interface, start with a neutral ramp (8–10 greys,
   one slightly tinted family), one brand accent, and semantic colors (success,
   warning, danger, info). Games and playful consumer/social apps can use several
   saturated accents with stable roles; see "Match the visual language to the
   product" below. Text meets contrast (4.5:1 body, 3:1 large text and UI borders)
   — see the `building-accessible-interfaces` skill.
5. **Layout** — a max content width (≈ 1100–1280px for apps, ≈ 680–720px for
   reading), a consistent grid or column structure, alignment to shared edges, and
   a layout that reflows at phone width rather than shrinking.
6. **Consistency** — the same thing looks the same everywhere: one button style per
   role, one card style, one input style, one icon set at one stroke weight, one
   corner radius scale (e.g. 4/8/12/999). Inconsistency is the main thing that
   makes an app look assembled rather than designed.

## Match the visual language to the product

Choose the intended feel before choosing tokens. A restrained utility palette is
one starting point, not a universal definition of quality. Games should feel
playable; consumer/social apps built around fun should carry that energy in their
visual language.

- Use saturated accents for distinct roles (primary action, play surface, reward),
  rather than adding unrelated colors per component. Keep warning/danger meanings
  distinct from decorative or reward colors.
- Pair a playful display face for short headings with a readable body face; keep
  dense controls and data in the body face.
- Make game controls feel pressable with chunky shapes, consistent outlines and
  solid offset shadows. Show a pressed state by reducing the shadow and moving the
  control toward it; preserve the visible keyboard focus ring.
- Use drawn vector icons from one coherent set instead of emoji for game controls;
  emoji rendering varies by platform and weakens the shared visual language.

For example, a game can give its board a saturated background, its main action a
contrasting fill and offset shadow, and its score a reward accent while keeping
instructions on a quiet, readable surface. Hierarchy still needs one obvious
primary action. Expressiveness changes styling, not features or product scope.

Other audiences need their own register, not a default framework theme:

- **Professional B2B tools** should stay calm but carry a real identity: a
  distinctive palette with one signature accent, a display face for headings and
  key numerals, and a custom mark. A stock component-library theme with a
  swapped primary color reads as unfinished.
- **Developer-facing products** should look developer-made: a dark theme with
  monospaced type for code, identifiers and most chrome, instead of a light
  clean-SaaS look. Check contrast on the dark surfaces, not just the light ones.
- **Financial and quantitative workbenches** should be dark and very dense:
  compact rows, small type, many figures per screen, because the job is scanning
  numbers. Use tabular (fixed-width) numerals and right-align numeric columns so
  digits line up, keep decimals consistent per column, and reserve color for
  sign and state (gain/loss, alert) rather than decoration. Never rely on red
  versus green alone: add a sign, arrow or label. Whitespace-heavy "clean"
  layouts waste the screen the user came to read.
- **Consumer products with a theme** should lean into it: illustrated scenes,
  dividers and textures drawn from the subject, with bold display type, rather
  than a generic dashboard that happens to have the subject's name on it.
- **Ornament** (blobs, squiggles, shapes) is fine when it is designed: one
  consistent shape language and outline weight, cropped by its container,
  asymmetric but balanced, and never placed over text or controls.
- **Cleanup removes noise, not color.** When tidying a playful screen, fix
  alignment, spacing and clutter but keep the large saturated surfaces and
  display type; flattening it to white and cream turns a character into a
  template.
- **Keep an existing logo as shipped** in mockups and redesign targets. A
  restyle changes the surrounding system; replacing the mark is a separate,
  explicit brand decision.

## Step 3 — Tokens first, restyle second

Before changing how any screen looks, introduce **design tokens** — named values
for color, type, spacing, radius, shadow — in one place, and point existing styles
at them. Then restyling becomes editing tokens, not hunting hex codes.

- Web: CSS custom properties on `:root` (works with any framework, including none).
  If the app already uses Tailwind, put the scales in the Tailwind theme instead of
  adding a parallel system.
- Name by role, not by value: `--color-text-muted`, not `--grey-500`; `--space-4`,
  not `--sixteen`.
- Define dark mode by overriding the role tokens under
  `@media (prefers-color-scheme: dark)`, never by restyling components.

A starter token set (CSS custom properties with scales, semantic colors, and a dark
override) is in [TOKENS.md](TOKENS.md). The order of operations for retrofitting an
old app — and how to split it into reviewable PRs — is in
[MODERNIZING.md](MODERNIZING.md).

## Step 4 — Components and states

Build or fix the handful of primitives everything else uses: button (primary,
secondary, ghost, danger), input/select/textarea with label and help text, card,
table, badge, alert, modal, nav. Each needs every state, not just the resting one:
default, hover, focus-visible, active, disabled, loading — plus the screen-level
states (empty, loading, error, success) covered in the
`designing-interaction-states` skill.

A component library (shadcn/ui, Radix, Headless UI, a design-system package) is a
good choice for a new app. For an old server-rendered app, a small set of
hand-written classes on top of tokens is usually lighter than migrating frameworks.

## Step 5 — Verify visually

Re-take the same screenshots after the change, at both widths, and compare side by
side. Check: the hierarchy squint test, nothing overflowing at 390px, focus rings
visible when tabbing, dark mode if supported. Attach the before/after pair to the
PR — reviewers approve design changes by looking, not by reading CSS diffs.

### Consolidating CSS without changing the design

Stacked restyles often leave the same selector defined several times. Editing
the first block can have no visible effect because a later block wins. Before
retinting or consolidating a component, inspect every definition and the winning
declarations in browser DevTools.

- Scan with a CSS parser (such as PostCSS), grouping repeated selectors by their
  enclosing at-rule context. A selector in a dark-mode or narrow-screen media
  query is not a duplicate of its base rule. Repeated rules can also be deliberate;
  preserve cascade order when consolidating declarations.
- For a cleanup intended to preserve appearance, compare base and branch at the
  same viewport, theme, data and UI state. Dump `getComputedStyle(element)` for
  matching elements, plus `::before` and `::after` when their `content` is present.
  This catches a changed winning declaration even when a screenshot looks close.
- Cover light/dark themes and the relevant empty, active, paused and settings
  screens, including hover, focus, disabled and invalid controls. Disable
  animations for the comparison; settling one default screenshot is insufficient.
- Keep screenshots as a layout check, but mask or freeze live clocks and
  countdowns before pixel comparison. A base-versus-base capture reveals which
  differences are nondeterministic rather than caused by the cleanup.

An empty duplicate-selector report proves only structural cleanup. Matching
computed styles across the exercised states and matching layouts provide the
evidence that the cleanup preserved the design.

## App chrome and dense views

The frame around the content is judged as hard as the content itself.

- **Sidebar:** in an app shell, make it a full-bleed rail attached to the left, top and bottom viewport edges, with one background step against the page. A rounded box floating inside a margin wastes width and reads as a widget, not a frame.
- **Footer:** one slim row (about 48px) of minimal text and a few links. Tall multi-column footers belong on marketing pages, not in a product, and even there they should be earned.
- **Dense lists and boards:** single-line titles that truncate with a tooltip, compact rows, small buttons, and horizontal scroll inside a board rather than wrapping cards into tall stacks. Density is a hierarchy choice: keep the one primary action per row visible and demote the rest to a menu.
- **Chrome follows the product's character:** a playful product's header and footer should carry the same outlines, accents and shadows as its content (an outlined floating pill header, a colored or ink footer), not a flat neutral bar that makes the page look like two designs stitched together.
- **Brand marks are inputs, not design targets:** a restyle uses the shipped logo as-is. Rework the layout, color and type around it; never redraw or "refresh" it as a side effect.

## Native apps

On iOS and macOS, follow the platform (Apple's Human Interface Guidelines) rather
than porting web conventions: system fonts and Dynamic Type text styles, semantic
system colors (`.primary`, `.secondary`, `Color(.systemBackground)`), SF Symbols,
standard navigation and list patterns, 44pt minimum touch targets. "Looks like a
good Apple app" beats "looks like our website". The fundamentals above still apply
— hierarchy, spacing rhythm, consistency — expressed through platform styles.

## Scoping design work into issues

Design improvements are legitimate, valuable issues — an app that looks abandoned
loses users before they try a feature. Keep each one a single reviewable PR:

- "Introduce design tokens and route existing colors through them" (no visual change)
- "Adopt a type scale; remove the N ad-hoc font sizes"
- "Rebuild the primary/secondary button styles on tokens across all pages"
- "Redesign the dashboard empty state and first-run screen"
- "Make the settings page responsive at phone width"

Each issue names the screens it touches and includes before screenshots; each PR
includes after screenshots. Avoid "redesign the whole app" issues — they never
finish and can't be reviewed.

## Anti-patterns

- Restyling screen by screen without tokens, which recreates the inconsistency.
- Swapping CSS frameworks as a "design fix" — it changes the plumbing, not the design.
- Gradients, shadows and animation added to compensate for weak hierarchy.
- A thick colored stripe down one edge of every card, alert or panel to signal category or state. It is the most recognizable generic-template tell. Keep one uniform border (or none) on every card and carry state with a dot, chip, icon or text label — which also survives for color-blind users.
- Light grey text on white to look "clean" (it fails contrast and reads as disabled).
- Centering everything; long centered paragraphs are hard to read.
- Designing only the happy path at desktop width.
