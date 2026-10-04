---
name: designing-marketing-pages
description: Designs landing, pricing, comparison and product pages that explain the product fast and convert honestly — one-sentence value proposition above the fold, a single primary call to action, real product screenshots instead of stock art, proof, a clear pricing table, fast responsive pages, and no dark patterns. Use when building or redesigning a landing page, marketing site, pricing or comparison page, app store–style product page, or reviewing why a product's public pages feel dated or don't convert.
---

# Designing Marketing Pages

A visitor decides in a few seconds whether a page is for them. Everything on a
marketing page either answers "what is this, is it for me, what do I do next?" or
gets in the way. Most dated landing pages fail on clarity, not style.

## Contents
- The page skeleton
- Above the fold
- Show the product
- Proof and objections
- Pricing pages
- Comparison pages
- Visual design
- Performance and responsiveness
- Honesty rules
- Review checklist

## The page skeleton

A dependable order for a product landing page:

1. **Hero** — headline, one supporting sentence, primary CTA, product visual.
2. **The problem / who it's for** — in the visitor's words.
3. **How it works** — 3 steps or 3 key features, each with a real screenshot.
4. **Proof** — numbers, logos, quotes, ratings (only real ones).
5. **Details for evaluators** — integrations, privacy/security, platforms, FAQ.
6. **Pricing** (or a link to it).
7. **Final CTA** — repeat the primary action.

## Above the fold

- **Headline:** what the product does for whom, in plain words — "Book and track
  equipment rentals from your phone", not "Reimagine the rental experience".
- **Subhead:** one sentence on the key differentiator or how it works.
- **One primary CTA** with an outcome label ("Download for Mac", "Start free"); at
  most one secondary ("See how it works"). Three equal buttons means no choice.
- **A real product visual** — a screenshot or short clip of the actual UI.
- Price or "free" signal near the CTA when it removes a question.

## Show the product

Real screenshots beat illustrations and stock photos: they prove the product exists
and answer "what does it look like?". Use crisp, current captures with realistic
(fake) data, cropped to the feature being described, framed consistently (same
device frame or same shadow and radius). Retake them when the UI changes — stale
screenshots are the most common accuracy bug on product sites.

## Proof and objections

- Specific beats general: "Used by 1,200 teams" beats "Loved by teams".
- Quotes with a name and role; ratings with their source.
- An FAQ that answers the real objections: price, privacy, data export, platform
  support, what happens when you cancel.
- Never fabricate testimonials, user counts, logos or ratings.

## Pricing pages

- 2–4 plans in columns; recommended plan visually marked; monthly/annual toggle that
  shows the real per-month price and the saving.
- Each plan lists what is included in the same order, with the differences first.
- The price shown is the price paid — taxes and limits stated plainly near it.
- A free tier or trial says exactly what is free and what happens at the limit.
- FAQ under the table for billing questions.

## Comparison pages

"X vs Y" and "alternatives to Y" pages are high-intent and worth building: a fair
feature table, honest about where the alternative is better, with a clear "choose us
if…" / "choose them if…" section. Keep competitor facts dated and sourced; inaccurate
comparisons damage trust and can create legal exposure.

## Visual design

The `designing-interfaces` skill's fundamentals apply, tuned for reading:

- Larger type than the app: 18–20px body, 40–64px hero headline on desktop, scaling
  down with `clamp()` on phones.
- Generous vertical rhythm between sections (64–128px); one idea per section.
- Prose blocks at ~65 characters wide even inside wide layouts.
- One accent color reserved for CTAs so the action is always the most visible thing.
- Consistent section structure (heading, one sentence, visual) so the page scans.

## Performance and responsiveness

Marketing pages are judged on first load, often on a phone:

- Largest Contentful Paint under ~2.5s: compress and size images (`srcset`, WebP/AVIF,
  explicit `width`/`height` to avoid layout shift), lazy-load below the fold, avoid
  render-blocking scripts and heavy font stacks (one family, two weights, `font-display: swap`).
- Check with `npx --yes lighthouse "$URL" --only-categories=performance,accessibility,seo --view`.
- Design the phone layout first; stack sections, keep the CTA reachable, and make
  sure screenshots remain legible when scaled down (crop tighter for mobile).
- Meta title, description and an Open Graph image so shared links look intentional.

## Honesty rules

No dark patterns: no fake countdown timers or scarcity, no pre-checked upsells, no
hidden costs revealed at checkout, no confirmshaming ("No thanks, I don't like saving
money"), cancellation as easy as signup. Every claim on the page must be true of the
shipped product today — check copy against the live app before publishing.

## Review checklist

- [ ] A stranger can say what it is and who it's for after 5 seconds above the fold
- [ ] One primary CTA, repeated at the end, labelled with the outcome
- [ ] Real, current product screenshots
- [ ] Proof is real and specific; FAQ covers price, privacy, export, cancellation
- [ ] Pricing shows the real price and limits
- [ ] Phone layout checked; Lighthouse performance and accessibility reviewed
- [ ] Every claim verified against the shipped product
