---
name: building-swift-apps
description: Builds, tests, and ships Swift/Xcode apps (macOS/iOS) reliably in CI and locally — unsigned CI builds, the hand-maintained pbxproj, SwiftPM-module vs app-target test boundaries, SourceKit false positives, gitignored base xcconfig, Keychain vs UserDefaults for secrets, and CloudKit/SwiftData constraints. Use when wiring CI for an Xcode project, debugging "requires a provisioning profile" / "no testable scheme" / "cannot find type in scope", adding a Swift file to a target, or reviewing a Swift app.
---

# Building Swift/Xcode Apps

Xcode projects fail in ways a package-manager-driven language never does: the
build graph lives in a hand-edited `project.pbxproj`, CI can't sign, and the IDE
lints against a module graph it doesn't actually have. The traps below each come
from a build that was green locally and broken in CI (or vice versa). The rule
throughout: trust `xcodebuild`, not the IDE, not `swift build`, not a green
`make test` that runs nothing.

## CI can't sign — build unsigned

CI runners don't have the developer team's provisioning profiles, so a normal
build dies with *"requires a provisioning profile"*. The half-fix everyone tries
first — ad-hoc signing — does **not** work when the app declares entitlements
(CloudKit, App Groups, Keychain sharing): the profile-bound entitlement check
still fires.

```
# DOES NOT fix it — the entitlement check still requires a profile:
CODE_SIGN_IDENTITY=- CODE_SIGNING_REQUIRED=NO

# The working recipe — skip signing AND the entitlement check entirely:
xcodebuild build CODE_SIGNING_ALLOWED=NO
xcodebuild test  CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO CODE_SIGN_IDENTITY=
```

`CODE_SIGNING_ALLOWED=NO` skips both signing and the entitlement gate. On arm64
the linker still applies an implicit ad-hoc signature, so the host app is
launchable and `xcodebuild test` can host and run the test bundle. Pass these
flags through your Makefile (`XCODE_FLAGS`) so local and CI builds match.

**Pin the runner and Xcode version to your local toolchain.** Swift 6.2
concurrency semantics are rejected by older toolchains, so a project that builds
locally fails on a default runner. Pin both explicitly:

```yaml
runs-on: macos-26            # not macos-latest
- run: sudo xcode-select -s /Applications/Xcode_26.2.app
```

## The pbxproj is hand-maintained — new files aren't in the build

Adding a `.swift` file to the folder on disk does **not** add it to the build.
The file must be wired into `project.pbxproj` in three places: a
`PBXFileReference`, the target's `PBXSourcesBuildPhase`, and a group. Until then
the target fails to compile with `Cannot find 'NewType' in scope` at the *use*
site — even though the file plainly exists. This often stays latent until CI
builds the app target as a test host and surfaces it.

Rule: after adding any Swift file, build the app target (`xcodebuild build`),
not just the file's own preview. Let Xcode add files (it edits the pbxproj) or
verify the three entries by hand.

## `swift test` vs `xcodebuild test` — mind the module boundary

A `Package.swift` target and an app target are different modules. Test code that
does `@testable import AppModule` only sees symbols compiled *into that SwiftPM
target*. If it references types that live in the app target (`Library/…` sources
not in the package), `swift build` succeeds but `swift test` fails to compile
with *"cannot find X in scope"*.

- Put logic you want to unit-test in the SwiftPM **library** target, and test it
  there — that's what `swift test` can reach.
- App-target-only types (SwiftData `@Model`s, SwiftUI views, managers wired to
  the app) are testable only via `xcodebuild test` against a hosted XCTest
  target. Don't document `swift test` as the test command if the tests need the
  app module.

## "no testable scheme" — the test gate that runs nothing

A `make test` that advertises tests but has no XCTest target (or no *shared*
scheme) either fails with *"no testable scheme"* or silently no-ops. A hosted
test target needs: the XCTest target itself, `TEST_HOST` pointing at the app,
and a **shared** scheme (checked into `xcshareddata`, or CI can't see it).
Confirm the gate actually runs by asserting the test count in the log, not just
exit 0.

## SourceKit false positives — trust the build, not the squiggles

In a single-target Xcode project (not SPM), out-of-band SourceKit / IDE
diagnostics lack the full module graph and report phantom errors like *"Cannot
find type 'HTTPServer' in scope"* for symbols defined in a sibling file. These
are not real — `xcodebuild build` is the source of truth. Don't chase them or
"fix" them by moving code around; verify against a real build first.

## Clean-checkout footgun: gitignored base xcconfig

If the project references a `Config.xcconfig` as a base configuration but that
file is gitignored (only `Config.xcconfig.example` is tracked), a fresh clone
fails immediately: *"Unable to open base configuration reference file"*. Keep an
`.example` with placeholder values and make the first build step copy it:

```
cp -n Config.xcconfig.example Config.xcconfig   # placeholders compile fine
```

Document this in the README/Makefile — it blocks the very first build, before
any code runs.

## Secrets: Keychain, not UserDefaults

OAuth access/refresh tokens, API keys, and passwords do **not** belong in
`UserDefaults` — that's a plaintext plist in the app container. Refresh tokens
are long-lived credentials; store them in the Keychain. Same discipline as any
repo: a credential that reaches a user's disk (or git history) is compromised.
And an OAuth flow needs a `state` parameter (and ideally PKCE) — a localhost
callback that accepts any `code` is a login-CSRF / code-injection surface.

## CloudKit + SwiftData: optional is deliberate, don't "tidy" it

CloudKit-synced SwiftData `@Model` types must have every stored property either
optional or defaulted, and relationships optional — it's a hard CloudKit
constraint, not sloppiness. Projects express this by keeping stored props
optional and exposing non-optional `resolvedX` computed fallbacks:

```swift
@Model final class Idea {
    var title: String?                    // optional for CloudKit — required
    var resolvedTitle: String { title ?? "Untitled" }   // callers use this
}
```

Do **not** refactor these to non-optional to "clean them up" — it breaks CloudKit
sync. When reviewing, recognize the pattern and leave it.

## Nondeterministic output makes brittle tests

`.shuffled()`, `Array.randomElement()`, and `Date()` inside logic make output
nondeterministic, so tests get written loosely ("contains any of these words")
and can't assert precise behavior. If you want tight assertions, inject a seeded
RNG / a clock and test that seam; otherwise keep the loose assertion and don't
pretend it verifies exact output. Note LCG-style `next() % N` generators have
poor low-bit distribution — don't rely on them for anything statistical.

## Checklist

- [ ] CI builds/tests unsigned with `CODE_SIGNING_ALLOWED=NO` (not ad-hoc)
- [ ] Runner OS + Xcode version pinned to the local toolchain (not `-latest`)
- [ ] Every new `.swift` file wired into the pbxproj; app target compiles
- [ ] Test command matches reality: `swift test` only if tests stay in the SPM module
- [ ] Test gate actually runs (hosted target + shared scheme; assert test count)
- [ ] Clean checkout builds (base xcconfig copied from `.example`)
- [ ] Tokens/keys in Keychain, not UserDefaults; OAuth uses `state`/PKCE
- [ ] CloudKit SwiftData props stay optional with `resolved*` fallbacks
