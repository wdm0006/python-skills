---
name: building-browser-extensions
description: Builds and tests Manifest V3 browser extensions — service-worker message channels and chrome.* side effects that survive teardown, chrome.storage read-modify-write safety, settings validation in the popup, and a Jest chrome mock that can actually fail. Use when writing or reviewing a background service worker, a popup that reads/writes chrome.storage, an extension's Jest suite, or debugging an extension whose UI silently stops responding.
---

# Manifest V3 Extensions

An MV3 background script is not a long-lived page — it is a service worker the
browser tears down whenever it looks idle. Almost every bug below is the same
bug in different clothes: **work that was started but never awaited, or state
that was written from a stale snapshot.** Both fail silently. There is no crash,
no console error in front of the user — just a setting that reverts, a button
that does nothing, or a suite that stays green over a broken handler.

## Await every side effect before the handler resolves

A fire-and-forget `chrome.storage.local.set` can be killed with the worker. If a
message handler's caller depends on that write, the write must complete *before*
the response is sent.

MV3's `onMessage` closes the reply channel as soon as the listener returns unless
it returns literal `true`:

```js
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.action === 'triggerAction') {
    doWork()                                  // resolves only after its writes land
      .then(() => sendResponse({ success: true }))
      .catch((error) => sendResponse({ success: false, error: String(error) }));
    return true;                              // REQUIRED: keeps the channel open
  }
});
```

Then let the caller **await the response** instead of guessing at a delay:

```js
// BAD — a race dressed up as a fix. Slow worker: stale read. Fast worker: wasted 500ms.
chrome.runtime.sendMessage({ action: 'triggerAction' });
setTimeout(loadFromStorage, 500);

// GOOD — the response is the signal that the write is durable.
const res = await chrome.runtime.sendMessage({ action: 'triggerAction' });
if (!res?.success) return showRetryState(res?.error);
await loadFromStorage();
```

Treat a missing or falsy response as failure, not success — a torn-down worker
resolves `sendMessage` with `undefined`. The same rule covers every side effect
behind an acknowledgement. If the handler reschedules an alarm, both operations
must be awaited:

```js
async function setupAlarm(intervalMinutes) {
  await chrome.alarms.clear('scheduled-work');
  await chrome.alarms.create('scheduled-work', {
    periodInMinutes: intervalMinutes,
  });
}
```

Awaiting only `clear` is a subtle false success: the handler can acknowledge the
request while alarm creation is still pending, and a rejected `create` becomes
an unhandled promise instead of a `{ success: false }` response. Apply the same
rule to notifications and other `chrome.*` promises — returning from an outer
`async` function does not wait for a promise that function started but did not
return or await.

## `??`, never `||`, for numeric settings

`0` is a legitimate value for an hour, a count, or an offset, and `||` throws it
away. A user who sets a start hour of midnight gets the default instead.

```js
const startHour = stored.startHour ?? DEFAULTS.startHour;   // 0 survives
```

## chrome.storage read-modify-write is a lost update

`get` → mutate → `set` on the whole settings object races every other context
(popup, worker, options page) writing the same key. Worse, if the object is
absent from storage, code that spreads a local variable persists a **partial**
settings record — and the next reader's `stored || DEFAULTS` keeps the truthy
partial, so a missing nested key throws.

Re-read inside the write path, and rebuild over the defaults rather than over
whatever snapshot you happen to be holding:

```js
async function persistLastIndex(category, index) {
  const { settings } = await chrome.storage.local.get('settings');   // fresh read
  await chrome.storage.local.set({
    settings: {
      ...DEFAULTS,
      ...settings,
      enabledCategories: { ...DEFAULTS.enabledCategories, ...settings?.enabledCategories },
      lastIndices: { ...DEFAULTS.lastIndices, ...settings?.lastIndices, [category]: index },
    },
  });
}
```

Two things that snippet is doing deliberately:

- **Defaults-based, never partial.** Every key a consumer indexes into exists,
  even on a first write after storage was cleared.
- **Nested objects merged explicitly.** A shallow `{...DEFAULTS}` *aliases*
  `DEFAULTS.enabledCategories` — it is the same object, typically a module
  global shared by worker and popup. Mutating the stored copy later reaches back
  and rewrites your defaults for the rest of the process.

The cleanest version of this rule: **make selection pure and persistence
explicit.** A function that picks a random item should return
`{ item, category, index }` and write nothing; the caller awaits the persist.
Pure selection is trivially testable, and the write can no longer be silently
skipped.

## One code path, two entry points — pass a flag

A "show something now" routine usually serves both a scheduled alarm (which must
respect quiet hours / weekends) and a manual button (which must not). Do not fork
into a second near-copy; take an explicit opt-out and default it to the safe
value:

```js
async function showReminder(skipTimeCheck = false) {
  if (!skipTimeCheck && !isWithinActiveHours(settings)) return;
  // ...
}

// alarm handler: showReminder();        → gated
// user action:   showReminder(true);    → always fires
```

Every new user-initiated entry point has to pass `true` — audit them when you add
one, because the failure ("my button does nothing at 9pm") only reproduces
off-hours.

## HTML input constraints are inert; validate in JS

`min="0" max="23"` on a number input is enforced only by form submission or an
explicit `checkValidity()`. A popup that reads `.value` on a click handler gets
none of it, and `parseInt('')` is `NaN`:

```js
// BAD — NaN >= NaN is false, so this "range check" passes for a blank field.
const start = parseInt(startInput.value);
if (start >= end) return showError();
```

`NaN` then serializes through `chrome.storage` to `null`, gets replaced by the
default on read (so the app looks fine), and renders as an **empty field** next
time the popup opens — sticky corruption behind a "Settings saved ✓" toast.
Out-of-range values are stored verbatim and can make an active-hours predicate
true for every hour of the day.

```js
function readHour(input, name) {
  const n = Number.parseInt(input.value, 10);
  if (!Number.isInteger(n) || n < 0 || n > 23) throw new ValidationError(name);
  return n;
}
```

Validate in the shared save path, not per-field in the markup — and report the
failure instead of showing success.

## A throw during `DOMContentLoaded` kills the whole popup

Popup init typically loads state *and* binds listeners in one handler. If the
state load throws — say a partial settings object missing a nested key — the
handler unwinds before `addEventListener` runs, and every button in the popup is
dead with no visible error. Bind listeners first, then load state inside
`try/catch` and degrade to defaults.

## Notifications: stable ids replace, and `openPopup` can reject

Reusing one notification id means a new notification replaces the pending one —
usually what you want, so state it deliberately rather than discovering it. In a
click handler, clear the clicked id *before* awaiting `chrome.action.openPopup()`,
and catch that call: it rejects when there is no active window to attach to.

## Your chrome mock is part of the system under test

A hand-rolled `chrome` mock decides which bugs are reachable. Four failure modes,
all of which produce a green suite over broken code:

**Stubs leak across tests.** `jest.clearAllMocks()` clears recorded calls but
**keeps** implementations, so one test's `sendMessage.mockResolvedValue(...)`
answers for every later test in the file — silently unhooking the real listener.
Have the reset helper reinstall default implementations:

```js
function resetAll() {
  jest.clearAllMocks();
  installDefaultImplementations(chrome);   // not just clearAllMocks()
}
```

**A mock that drops async responses.** If the fake `sendMessage` invokes
listeners in a `forEach` and resolves `responses[0]`, then any listener that
returns `true` and responds later resolves to `undefined` — so every handler
using the async pattern above appears to fail. Honor `return true` by resolving
the promise the listener eventually fulfills. Until it does, a test needing a
real round trip must invoke the listener directly
(`chrome.runtime.onMessage.addListener.mock.calls[0][0]`).

**Synchronous mock storage cannot detect a missing `await`.** If the fake `set`
mutates its backing object and returns an already-resolved promise, the write
wins the microtask race whether or not the handler awaited it. To test *ordering*
you must gate the write, then prove the handler is still pending:

```js
let release;
const gate = new Promise((r) => { release = r; });
const realSet = chrome.storage.local.set.getMockImplementation();
chrome.storage.local.set.mockImplementation((items) =>
  items.settings ? gate.then(() => realSet(items)) : realSet(items));

const pending = handler({ action: 'save' }, {}, sendResponse);
for (let i = 0; i < 50; i++) await Promise.resolve();   // drain microtasks
expect(sendResponse).not.toHaveBeenCalled();            // fails if the await is missing
release();
await pending;
expect(sendResponse).toHaveBeenCalledWith({ success: true });
```

`getMockImplementation()` returns the default the reset helper installed, so this
*composes* with the mock instead of replacing storage behavior. For alarm
rescheduling, gate `alarms.create`, not only `alarms.clear`: a clear-gated test
still passes when creation is fire-and-forget. Assert that both the response and
any UI refresh remain pending until the create gate is released, then make the
gate reject and assert that the handler sends its failure response.

**Fake timers are dropped the moment you go real.** `jest.useRealTimers()`
mid-test discards `setSystemTime`, so any `new Date()` afterward sees wall-clock
time and a time-of-day branch follows whatever hour CI runs at — green by day,
red at night. Stay on fake timers and drain microtasks in a loop instead of
awaiting a real `setTimeout`.

Two smaller traps: throwing from `chrome.notifications.create` is the cheapest way
to drive a handler's rejection path, but if the handler ever stops awaiting or
catching it, Jest dies with an unhandled rejection and worker crashes rather than
a named assertion failure — still red, just unreadable. And a `tests/setup.js`
that replaces `global.console` swallows probe output even under `--verbose`; write
to a temp file when you need to see inside a run.

## PR-comment CI steps need two permissions

A workflow step that comments on a pull request via the issues API needs **both**
`issues: write` and `pull-requests: write`; with only the first it fails 403 after
every build/lint/test step has passed. Confirm it against the 403's
`x-accepted-github-permissions` header rather than guessing.

```yaml
permissions:
  contents: read
  issues: write
  pull-requests: write
```

Watch for the masking: such a step is often gated
`if: github.event.action == 'opened'`, so pushing another commit re-runs the
workflow as `synchronize`, skips the step, and turns the job green without
fixing anything.

## Checklist

```
MV3 extension health:
- [ ] every onMessage handler that responds asynchronously returns true and replies on both paths
- [ ] callers await the response; no setTimeout used to "wait for" a write
- [ ] every chrome.* side effect behind success is awaited, including the final alarms.create
- [ ] a missing/falsy sendMessage response is treated as failure
- [ ] numeric settings read with ?? (0 is valid), never ||
- [ ] storage writes re-read first and rebuild over DEFAULTS; nested objects merged explicitly
- [ ] selection/computation is pure; persistence is a separate awaited call
- [ ] manual entry points pass the explicit gate-bypass flag; alarms keep the default
- [ ] settings validated in JS (Number.isInteger + range), not by inert HTML min/max
- [ ] popup binds listeners before loading state; state load degrades to defaults
- [ ] chrome mock: reset reinstalls default implementations; async responses honored
- [ ] tests gate the final side effect (for rescheduling, alarms.create) to prove it is awaited
- [ ] fake timers never swapped for real timers mid-test
- [ ] PR-comment workflow step has issues: write AND pull-requests: write
```
