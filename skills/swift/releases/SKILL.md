---
name: shipping-swift-apps
description: Ships native Swift/SwiftUI apps to TestFlight and the App Store with fastlane and xcodebuild — one App Store Connect API key for both, fastlane lanes scoped to metadata/pricing/subscriptions, headless `xcodebuild archive` + `-exportArchive destination=upload`, build numbers read from App Store Connect instead of guessed, closed pre-release trains, `SKIP_INSTALL` for bundled helper apps, and per-destination archives for multiplatform targets. Use when setting up fastlane for an Xcode project, uploading a build to TestFlight from a script or CI, or debugging "Invalid Pre-Release Train", "expected one {} but found app-store-connect", "Unknown Distribution Error", or a duplicate-build-number rejection.
---

# Shipping Swift Apps to TestFlight

Distribution fails differently from building. The compiler is happy, the archive
succeeds, and then App Store Connect rejects the upload for a reason that has
nothing to do with your code — a version train that closed when the last release
was approved, a build number someone already used, a helper target that made the
archive undistributable. Every trap below comes from an upload that was rejected
after a clean build.

For build- and CI-side problems (unsigned builds, the hand-maintained pbxproj,
test-target boundaries), see the `building-swift-apps` skill. This skill starts
at the archive.

## fastlane owns metadata; xcodebuild owns the binary

The reflex is to hand fastlane the whole release with `gym` + `pilot`. You don't
have to, and there's a good reason not to: `xcodebuild` already uploads, so
fastlane's build wrapper is one more layer between you and the signing error.

A useful split:

- **fastlane** — App Store Connect state: listing copy, screenshots, pricing,
  subscription products. This is the tedious, API-shaped work fastlane is
  genuinely better at.
- **xcodebuild** — archive, sign, and upload the binary.

Lanes that only touch metadata are also safer to run: they can't accidentally
ship a build. Say so in the Fastfile header, because "fastlane" reads as "this
submits things" to everyone who didn't write it:

```ruby
# Lanes:
#   fastlane mac metadata   # upload copy + screenshots to the editable version
#   fastlane subscriptions  # dry-run by default; APPLY=1 to write
#
# Nothing here submits for review. Lanes populate the editable version, which
# stays a draft until you submit in App Store Connect.
```

## One API key authenticates both tools

Generate one App Store Connect API key (Users and Access → Integrations, role
App Manager or Admin) and point both tools at it. No Apple ID, no interactive
session, no signed-in Xcode required — which is what makes the whole thing work
headlessly and in CI.

fastlane:

```ruby
def asc_api_key
  app_store_connect_api_key(
    key_id: ENV.fetch("ASC_KEY_ID"),
    issuer_id: ENV.fetch("ASC_ISSUER_ID"),
    key_filepath: ENV.fetch("ASC_KEY_PATH"),
    in_house: false
  )
end
```

`ENV.fetch`, not `ENV[]` — a missing key should stop the lane, not authenticate
as nobody and fail somewhere less obvious.

xcodebuild takes the same key:

```
xcodebuild archive \
  -project MyApp.xcodeproj -scheme MyApp -configuration Release \
  -archivePath build/MyApp.xcarchive \
  -destination 'generic/platform=iOS' \
  -allowProvisioningUpdates \
  -authenticationKeyPath   "$ASC_KEY_PATH" \
  -authenticationKeyID     "$ASC_KEY_ID" \
  -authenticationKeyIssuerID "$ASC_ISSUER_ID"
```

`-allowProvisioningUpdates` fetches the distribution profile. The archive's
Info.plist may still name an "Apple Development" identity — the export re-signs
for distribution, so that isn't the bug you're looking for.

## Ignore the credentials before you write them

The `.p8` is a private key and the env file names your key and issuer IDs. Add
the ignore rules **in the same commit that introduces the automation** — ideally
before the files exist on disk:

```gitignore
*.p8
.env.asc
.fastlane_screens/
```

The near-miss worth internalizing: an env file sat untracked in a worktree for
weeks while the `.gitignore` rules that would have covered it lived in an
uncommitted stash. Nothing was leaked, but the repo was one `git add -A` away
from publishing credentials, and `git status` showed the file as ordinary
untracked noise the whole time. Untracked is not ignored. Check the rule exists
rather than assuming:

```
git check-ignore -v .env.asc || echo "NOT IGNORED"
```

Keep the `.p8` outside the repo entirely, and somewhere that isn't auto-cleaned
— `~/Downloads` loses files.

## Never guess the next build number — ask

The build number in your project file drifts from what's actually uploaded. It
drifts whenever a release is cut from another checkout, whenever a bot bumps it,
whenever an archive script increments it in place. Reusing a number gets the
upload rejected after you've already paid for the archive.

Read the truth from the API instead. Build numbers must be unique within a
marketing-version train, so query the trains and take the max:

```
GET /v1/apps?limit=200                                  -> app id per bundleId
GET /v1/apps/{id}/preReleaseVersions?limit=200          -> version + platform
GET /v1/preReleaseVersions/{id}/builds?limit=200        -> build numbers
```

Auth is a short-lived ES256 JWT signed with the `.p8`, `kid` = key ID, `aud` =
`appstoreconnect-v1`, expiry under 20 minutes:

```
uv run --with 'pyjwt[crypto]' --with requests python asc_builds.py
```

```python
now = int(time.time())
token = jwt.encode(
    {"iss": ISSUER_ID, "iat": now, "exp": now + 900, "aud": "appstoreconnect-v1"},
    open(KEY_PATH).read(), algorithm="ES256",
    headers={"kid": KEY_ID, "typ": "JWT"},
)
```

Note the API returns builds unsorted and paginated — follow `links.next` and
sort numerically, or you'll read a "max" that isn't one.

## A shipped version closes its train

The rejection that surprises people most:

```
Invalid Pre-Release Train. The train version '1.6' is closed for new build
submissions.
This bundle is invalid. The value for key CFBundleShortVersionString [1.6]
must contain a higher version than that of the previously approved version [1.6].
```

Once a marketing version is **approved**, you cannot add TestFlight builds to it,
no matter how you bump the build number. Bumping `CURRENT_PROJECT_VERSION` is not
enough — `MARKETING_VERSION` has to move too, and a fresh train starts empty so
any build number is free.

So there are two different bumps, and which one you need depends on state you
can't see from the repo:

| Last release state | Bump |
|---|---|
| Version still in TestFlight / not yet approved | `CURRENT_PROJECT_VERSION` only |
| Version approved and released | `MARKETING_VERSION` **and** keep a valid build number |

Check before you archive rather than after the upload fails.

## Helper `.app` targets must set `SKIP_INSTALL`

An app that bundles a second executable as an `.app` (an MCP server, an XPC-ish
helper, a login item) will produce two bundles in `Products/Applications` unless
the helper opts out. Xcode then can't tell which one is the product, and the
export dies with two errors that name nothing useful:

```
IDEDistributionMethodManager ... Error = "Unknown Distribution Error"
error: exportArchive exportOptionsPlist error for key "method"
       expected one {} but found app-store-connect
```

That `expected one {}` is the tell: the set of valid distribution methods is
**empty**, because no primary app was identified. It is not a problem with your
`method` value.

Diagnose it straight from the archive — a healthy one has `ApplicationProperties`,
a broken one doesn't:

```
plutil -p build/MyApp.xcarchive/Info.plist | head -20
ls        build/MyApp.xcarchive/Products/Applications/
```

Fix it on the helper target, in every configuration:

```
SKIP_INSTALL = YES;
```

The helper still ships — it's copied *inside* the main app by a build phase.
`SKIP_INSTALL` only stops the redundant standalone copy from being installed
into the archive root.

## Multiplatform targets need one archive per destination

A target whose `SUPPORTED_PLATFORMS` covers both `macosx` and `iphoneos` does not
produce a universal upload. Archive and upload once per destination:

```
-destination 'generic/platform=macOS'
-destination 'generic/platform=iOS'
```

Both go to the same App Store Connect app record, land on separate per-platform
trains, and share a build number. Same for a project with distinct macOS and iOS
schemes — two archives, two uploads, one version.

## Pin the version Xcode uploads

In `ExportOptions.plist`, keep Xcode from rewriting the numbers you just
carefully derived:

```xml
<key>method</key><string>app-store-connect</string>
<key>destination</key><string>upload</string>
<key>signingStyle</key><string>automatic</string>
<key>manageAppVersionAndBuildNumber</key><false/>
```

Without `manageAppVersionAndBuildNumber = false`, Xcode may silently bump the
build number during export, and the number you verified against the API is not
the number that gets uploaded.

## A release build failing on correct code means a stale checkout

If a release build fails on a type error that makes no sense — the API you're
calling matches the version in `Package.resolved`, and the code reads correctly —
compare what's resolved against what's actually checked out. SwiftPM keeps
package sources in DerivedData, and they can lag a dependency bump, so the
compiler is type-checking against a version the manifest no longer pins:

```
find ~/Library/Developer/Xcode/DerivedData/MyApp-*/SourcePackages/checkouts \
     -name "*.swift" -path "*TheDependency*"
```

Clearing DerivedData for the project resolves it. Worth ruling out early: this
looks exactly like a real breaking-change bug, and you can burn a long time
"fixing" source that was never wrong.

## Uploaded is not processed, and processed is not released

`exportArchive` exiting 0 means Apple accepted the bytes. Verify the build
actually arrived and finished processing before telling anyone to test:

```
GET /v1/preReleaseVersions/{id}/builds   ->  processingState == "VALID"
```

`PROCESSING` becomes `VALID` in minutes; it can also become `INVALID` after a
successful upload, which is why "the upload succeeded" is not a release report.
A `VALID` build may still need export-compliance answered before testers see it.

## Commit the version bump, and fetch first

The archive is built from your working tree, so a bump that stays uncommitted
means the shipped build corresponds to no commit anyone can check out. Commit
the bump as part of the release.

Fetch before you do. Release automation and bots bump versions too, and the
conflict is not textual but factual — a bot may set a marketing version that is
*behind* what is already uploaded to TestFlight. Resolve toward what App Store
Connect actually has, and say so in the commit message rather than silently
reverting someone's bump:

```
Release 1.4 (build 27)

Supersedes the 1.3.1 bump: 1.4 build 26 is already on the pre-release
train, so the next build has to continue that train.
```
