---
name: building-apple-platform-apps
description: Builds and ships native Swift/SwiftUI apps for Apple platforms (iOS/macOS) — Xcode & SwiftPM build/test in CI (code signing, @testable module traps, missing test targets), secure OAuth and token storage (Keychain, PKCE, state), SwiftData/CloudKit modeling, deterministic date/RNG handling, and repo hygiene. Use when building or reviewing a Swift app, fixing xcodebuild/`swift test` failures, wiring OAuth sign-in, or preparing an App Store release.
---

# Building Apple-Platform Apps

Native Swift apps fail in ways a Python library never does: the build depends on
signing identities and provisioning profiles, the IDE lies about compile errors,
tokens land in the wrong store, and "run" behaves differently under CI than on a
developer's Mac. This skill encodes the traps that recur when shipping SwiftUI
apps to the App Store or a CI runner.

## Building & testing in CI

**Code signing is the #1 reason `xcodebuild test` fails on a runner.** An app
target with **Automatic** signing (`DEVELOPMENT_TEAM = …`) and entitlements
(CloudKit, App Groups, keychain sharing) fails with *"requires a provisioning
profile"* on a machine without that team's credentials — and the test bundle is
usually *hosted by the app* (`TEST_HOST`), so the app must build to run tests.

Passing ad-hoc signing flags does **not** fix it — the profile-bound entitlement
check still fires:

```bash
# DOES NOT WORK — entitlement check still runs:
xcodebuild test ... CODE_SIGN_IDENTITY=- CODE_SIGNING_REQUIRED=NO

# WORKS — skips signing AND the entitlement check; the arm64 linker still
# applies an implicit ad-hoc signature, so the host app launches:
xcodebuild test -scheme MyApp -destination 'platform=iOS Simulator,name=iPhone 15' \
  CODE_SIGNING_ALLOWED=NO
```

**`swift test` breaks when tests reach into the app target.** In a mixed repo
with a SwiftPM module *and* an Xcode app target, `@testable import MyModule`
tests that reference types living in the **app** target (not the SPM module)
fail to compile — `swift build` succeeds, only the test target fails, so the
documented `swift test` path is broken. The SPM module can only test symbols it
actually contains. Test app-target types via an Xcode test target; test the SPM
module's own types (e.g. a `TemplateEngine`) in the SPM test target. Keep each
side's tests where their symbols live.

**A `make test` / DEVELOPMENT.md that advertises tests but has no test target.**
If `project.pbxproj` contains only a `product-type.application` and no
`.unit-test`/`.ui-test` target, there is nothing testable — `make test` fails
even though pure logic in `Services/`/`Models/` is trivially unit-testable. Add
the target before claiming coverage.

**Trust the build, not the editor.** In a single-target Xcode project (not
SwiftPM), out-of-band SourceKit lacks the module graph and reports false
positives like *"Cannot find type 'HTTPServer' in scope"* for symbols defined in
sibling files. These are not real errors — `xcodebuild`/`make build` is the
source of truth.

**A gitignored `Config.xcconfig` breaks a clean checkout.** If the `.xcodeproj`
references `Config.xcconfig` as a base configuration but only
`Config.xcconfig.example` is tracked (the real file gitignored for secrets), a
fresh clone fails immediately: *"Unable to open base configuration reference
file."* Document the `cp Config.xcconfig.example Config.xcconfig` bootstrap step
(placeholder creds compile fine) — or the first build always fails.

## Secrets & OAuth

**Store tokens in the Keychain, never `UserDefaults`.** `UserDefaults` is
plaintext in the app's prefs plist. OAuth **refresh** tokens are long-lived
credentials — persisting them (or access tokens) there is a credential leak.
Use the Keychain.

**An OAuth flow needs `state` and PKCE.** A localhost/redirect callback that
accepts any `code` with no `state` parameter is a login-CSRF / code-injection
risk. Generate a per-attempt `state` from cryptographic randomness, append it to
the auth URL, and validate it (single-use) in the callback *before* exchanging
the code:

```swift
var bytes = [UInt8](repeating: 0, count: 32)
_ = SecRandomCopyBytes(kSecRandomDefault, bytes.count, &bytes)
let state = Data(bytes).base64URLEncodedString()   // +→-, /→_, strip =
// ...append &state=\(state); on callback: guard returnedState == state else { reject }
```

Add PKCE (`code_challenge`/`code_verifier`) on top for public clients — a native
app cannot keep a client secret.

> URL-safe base64: standard base64 corrupts in a URL query because `+`/`/`/`=`
> aren't escaped and `+` decodes back to a space. Emit **base64url** for any
> value you put in a query string (share links, `state`), and reverse the map on
> read.

## SwiftData & CloudKit

**CloudKit forces optional stored properties.** SwiftData models synced via
CloudKit must keep stored props **optional** (CloudKit has no non-null
guarantee), typically with `resolvedX` computed fallbacks. Do not "tidy" these
into non-optional — it breaks CloudKit sync. The optionality is a constraint,
not sloppiness.

**Codable-embedded value types need save migration.** If a persisted model
embeds whole `struct`s via `Codable` (e.g. a saved game snapshotting a
`PlantType`/`Location`), changing those static definitions later leaves **stale
copies** frozen in existing saves. Version your save format and migrate, or reference
stable IDs instead of embedding the whole value.

## Determinism: dates, formatters, and RNG

**Fixed-format `DateFormatter` needs a POSIX locale and a time zone.** Parsing
`yyyyMMdd` without `locale = Locale(identifier: "en_US_POSIX")` misbehaves under
non-Gregorian device calendars/locales (Apple's documented footgun). Set
`locale` and `timeZone` on every fixed-format formatter.

**Don't mix a seeded RNG with system randomness.** If reproducibility matters
(game seeds, deterministic simulations), route *all* draws through the seeded
generator. Mixing in `Array.randomElement()` or `Date()` mid-computation makes
outcomes non-reproducible from the seed. Also beware home-rolled LCGs that derive
values via `next() % N` — low-order bits have short periods and poor
distribution; prefer a vetted generator.

## Don't fabricate data on failure

A fetch path that, on any network error, **silently substitutes randomized
sample data** makes the UI show fabricated numbers indistinguishable from real
ones (only an `errorMessage` betrays it). Surface the failure to the user;
never let a fallback masquerade as live data.

## Repo hygiene

Swift repos accumulate cruft the default `.gitignore` misses:

- Editor/build leftovers: `*.backup` (e.g. a stale `ContentView.swift.backup`),
  `*.log`, `.DS_Store` — none covered by a stock Swift `.gitignore`.
- Personal scratch databases (`*.db`, `todo.db` from a local MCP/tool) — a
  privacy leak in a public repo. `git rm --cached` and add the pattern.
- Never track the real `Config.xcconfig`; track only `Config.xcconfig.example`.

## Checklist

```
Build & CI:
- [ ] CI uses CODE_SIGNING_ALLOWED=NO (not just CODE_SIGNING_REQUIRED=NO)
- [ ] A test target actually exists in project.pbxproj
- [ ] Tests live where their symbols do (SPM module vs app target)
- [ ] Config.xcconfig bootstrap (cp from .example) documented

Security:
- [ ] Access & refresh tokens in Keychain, not UserDefaults
- [ ] OAuth uses per-attempt state (validated) + PKCE
- [ ] base64url for anything placed in a URL query

Correctness:
- [ ] CloudKit-synced SwiftData props stay optional
- [ ] Save format versioned if it Codable-embeds value types
- [ ] Fixed-format DateFormatters set en_US_POSIX locale + timeZone
- [ ] Seeded RNG not mixed with randomElement()/Date()
- [ ] No silent sample-data fallback on fetch failure

Hygiene:
- [ ] .gitignore covers *.backup, *.log, .DS_Store, *.db
```
