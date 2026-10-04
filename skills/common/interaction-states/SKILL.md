---
name: designing-interaction-states
description: Designs the states screens actually spend their time in — first-run and empty states, loading and skeletons, inline validation and error messages, success feedback, destructive confirmations, and the microcopy for each — so a product feels finished instead of only working on the happy path. Use when building a form, list, dashboard, upload, checkout or settings screen, adding an async action, writing error or empty-state copy, or reviewing a UI that shows blank pages, raw errors or spinners forever.
---

# Designing Interaction States

Most screens are designed in one state: full of realistic data, with every request
succeeding. Users mostly see the others — empty on day one, loading on a slow
network, an error on a typo. Those states are where an app feels either finished or
neglected.

## Contents
- The state inventory
- Empty and first-run states
- Loading
- Forms and validation
- Errors
- Success and feedback
- Destructive actions
- Microcopy rules
- Checklist

## The state inventory

For every screen, list and design each of these before calling it done:

| State | Question it answers |
|-------|---------------------|
| First run / empty | "What is this and what do I do first?" |
| Loading | "Is it working?" |
| Partial / some data | "Does it still look intentional with one item?" |
| Full / overflow | "What happens with 500 items or a very long name?" |
| Error | "What went wrong, and what do I do now?" |
| Success | "Did it work?" |
| Offline / permission denied | "Why can't I do this?" |

Seed local data for each and screenshot them; reviewers should see every state.

## Empty and first-run states

An empty state is the product's best onboarding surface. Replace "No items." with:

- a one-line explanation of what will appear here,
- the single primary action that fills it ("Import contacts", "Create your first
  project"), as a real button,
- optionally a secondary path (sample data, docs link).

Distinguish *empty because new* from *empty because filtered* ("No results for
'acme' — clear filters") from *empty because of an error* (that is an error state,
not an empty one).

## Loading

- Under ~300ms: show nothing (a flashing spinner reads as jank).
- Content areas: skeletons shaped like the content, so the layout does not jump.
- Actions: disable the button and show progress *in* it ("Saving…"), preventing
  double submits.
- Over ~10s or multi-step: real progress (steps or percent) and the option to leave.
- Never an indefinite spinner: every request has a timeout that becomes an error
  state with a retry.

## Forms and validation

- Labels above fields, visible always; help text below the label, not in the
  placeholder.
- Mark optional fields ("(optional)") rather than starring required ones, when most
  are required.
- Validate on blur or on submit, not on every keystroke; never show an error before
  the user has had a chance to type.
- On submit with errors: keep everything the user typed, show a summary at the top
  linking to each field, move focus to the first invalid field.
- Error text sits next to its field, says what is wrong *and* how to fix it, and is
  linked with `aria-describedby` (see the `building-accessible-interfaces` skill).
- Use the right input types (`email`, `tel`, `number`, `date`, `autocomplete`
  attributes) so phones show the right keyboard and browsers can autofill.
- One primary button per form, at the end, labelled with the outcome ("Create
  account", not "Submit").

## Errors

A good error message has three parts: **what happened, why (if known), what to do
next**.

| Bad | Good |
|-----|------|
| "Error 500" | "We couldn't save your changes. Your edits are still here — try again in a moment." |
| "Invalid input" | "Enter a date in the future." |
| "Failed to fetch" | "You're offline. We'll retry when you reconnect." |

- Never show stack traces, raw exception text or status codes to end users; log them
  with a reference ID and show the ID.
- Errors are recoverable where possible: a retry button, preserved input, a link to
  the place to fix the cause (e.g. billing settings).
- Page-level failures get a designed page (404, 500, expired link) with navigation
  back into the app, not the framework default.

## Success and feedback

- Confirm every action that changes data: inline ("Saved ✓" next to the button) for
  small edits, a toast for background actions, a full success screen for
  milestones (account created, payment complete) that says what happens next.
- Toasts auto-dismiss (~5s) except for errors and anything with an action ("Undo").
- Optimistic UI is fine for low-risk actions if failures roll back visibly.

## Destructive actions

- Prefer **undo** over confirmation for reversible actions ("Contact archived.
  Undo").
- For irreversible ones, confirm with a dialog that names the object and the
  consequence ("Delete 'Q3 report'? This removes it for everyone and can't be
  undone.") and a button labelled with the action ("Delete report"), styled as
  danger — never a generic "OK".
- For high-stakes deletes (an account, a workspace), require typing the name.

## Microcopy rules

- Plain words, sentence case, second person ("Your invoices"), active voice.
- Buttons are verbs naming the outcome; links say where they go.
- Be specific with numbers and names ("3 contacts imported, 2 skipped — see why").
- Same term for the same thing everywhere (pick "workspace" or "team", not both).
- No blame ("You entered an invalid…" → "Enter a valid…"), no jokes in errors.

## Checklist

- [ ] Every screen has designed empty, loading, error and success states
- [ ] No spinner without a timeout and an error path
- [ ] Forms keep input on error, focus the first invalid field, and use real labels
- [ ] Error messages say what happened and what to do; no raw exceptions shown
- [ ] Destructive actions use undo or a specific, danger-styled confirmation
- [ ] Screenshots of each state attached to the PR
