# Starter design tokens

## Contents
- Principles
- Starter token set (CSS)
- Using the tokens
- Mapping to Tailwind
- Auditing an existing stylesheet

## Principles

- **Role names, not value names.** `--color-text-muted` survives a palette change;
  `--grey-500` does not.
- **Scales, not one-offs.** Every value a component uses comes from a scale. A value
  that is not on the scale is either a new scale step (rare) or a mistake.
- **Dark mode overrides roles only.** Components never mention dark mode.
- **Few steps.** Seven font sizes and ten spacing steps cover almost every product.

## Starter token set (CSS)

Drop into the global stylesheet and adjust the brand hue. Values are a sound default,
not a brand.

```css
:root {
  /* Type */
  --font-sans: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  --text-xs: 0.75rem;   /* 12 */
  --text-sm: 0.875rem;  /* 14 */
  --text-base: 1rem;    /* 16 */
  --text-lg: 1.25rem;   /* 20 */
  --text-xl: 1.5rem;    /* 24 */
  --text-2xl: 2rem;     /* 32 */
  --text-3xl: 2.5rem;   /* 40 */
  --leading-tight: 1.25;
  --leading-normal: 1.5;
  --weight-regular: 400;
  --weight-medium: 500;
  --weight-semibold: 600;

  /* Space (4px base) */
  --space-1: 0.25rem;  /* 4 */
  --space-2: 0.5rem;   /* 8 */
  --space-3: 0.75rem;  /* 12 */
  --space-4: 1rem;     /* 16 */
  --space-6: 1.5rem;   /* 24 */
  --space-8: 2rem;     /* 32 */
  --space-12: 3rem;    /* 48 */
  --space-16: 4rem;    /* 64 */

  /* Shape */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-full: 999px;
  --shadow-sm: 0 1px 2px rgb(0 0 0 / 0.06);
  --shadow-md: 0 4px 12px rgb(0 0 0 / 0.08);

  /* Layout */
  --width-content: 72rem;  /* app pages */
  --width-prose: 42rem;    /* reading */

  /* Color — roles (light) */
  --color-bg: #ffffff;
  --color-surface: #f7f7f8;
  --color-surface-raised: #ffffff;
  --color-border: #e4e4e7;
  --color-border-strong: #d4d4d8;
  --color-text: #18181b;
  --color-text-muted: #52525b;    /* 7.7:1 on white */
  --color-text-subtle: #71717a;   /* 4.8:1 on white — the floor for body-size text */
  --color-accent: #2563eb;
  --color-accent-hover: #1d4ed8;
  --color-on-accent: #ffffff;
  --color-success: #15803d;
  --color-warning: #b45309;
  --color-danger: #b91c1c;
  --color-info: #0369a1;
  --color-focus: #2563eb;
}

@media (prefers-color-scheme: dark) {
  :root {
    --color-bg: #0f0f11;
    --color-surface: #18181b;
    --color-surface-raised: #1f1f23;
    --color-border: #2e2e33;
    --color-border-strong: #3f3f46;
    --color-text: #f4f4f5;
    --color-text-muted: #a1a1aa;
    --color-text-subtle: #8b8b94;
    --color-accent: #60a5fa;
    --color-accent-hover: #93c5fd;
    --color-on-accent: #0b1220;
    --color-success: #4ade80;
    --color-warning: #fbbf24;
    --color-danger: #f87171;
    --color-info: #38bdf8;
    --color-focus: #93c5fd;
    --shadow-sm: none;
    --shadow-md: 0 4px 16px rgb(0 0 0 / 0.5);
  }
}

body {
  font-family: var(--font-sans);
  font-size: var(--text-base);
  line-height: var(--leading-normal);
  color: var(--color-text);
  background: var(--color-bg);
}
:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 2px; }
```

## Using the tokens

```css
.btn {
  display: inline-flex; align-items: center; gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  font: var(--weight-medium) var(--text-sm)/1 var(--font-sans);
  border-radius: var(--radius-md);
  border: 1px solid transparent;
}
.btn-primary { background: var(--color-accent); color: var(--color-on-accent); }
.btn-primary:hover { background: var(--color-accent-hover); }
.btn-secondary { background: var(--color-surface-raised); color: var(--color-text); border-color: var(--color-border-strong); }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }

.card {
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
}
.page { max-width: var(--width-content); margin: 0 auto; padding: var(--space-8) var(--space-4); }
```

## Mapping to Tailwind

If the app already uses Tailwind, do not add a second system. Put the same scales in
`theme.extend` (or the v4 `@theme` block) and use role names for colors:

```css
@theme {
  --color-text: #18181b;
  --color-text-muted: #52525b;
  --color-accent: #2563eb;
  --radius-md: 8px;
}
```

Then `text-text-muted`, `bg-accent` and `rounded-md` replace arbitrary values like
`text-[#666]` and `p-[13px]`. Searching for `\[#` and `-\[\d` in templates finds the
one-offs to migrate.

## Auditing an existing stylesheet

Count the drift before proposing a fix; the numbers make the issue concrete.

```bash
# distinct colors
grep -rhoE '#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)' static/ templates/ src/ | sort | uniq -c | sort -rn | head -40
# distinct font sizes
grep -rhoE 'font-size:\s*[^;]+' static/ templates/ src/ | sort | uniq -c | sort -rn
# distinct spacing values
grep -rhoE '(margin|padding|gap)[a-z-]*:\s*[^;]+' static/ src/ | sort | uniq -c | sort -rn | head -40
```

Thirty greys and fifteen font sizes is the typical finding in an old app, and the
justification for a tokens-first issue.
