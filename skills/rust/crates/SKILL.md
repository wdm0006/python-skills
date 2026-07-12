---
name: building-rust-crates
description: Sets up, tests, and publishes Rust crates — Cargo project layout, a fmt/clippy/test CI gate that actually gates, MSRV pinning, feature-flag hygiene, and crates.io publishing with cargo-release. Use when creating a Rust crate, wiring GitHub Actions for Rust, debugging a clippy or MSRV CI failure, or preparing a crates.io release.
---

# Building Rust Crates

> Starting point. This skill captures the load-bearing Rust project conventions;
> extend it with reference files (a full `Cargo.toml`, a CI workflow, a clippy
> config) as the patterns firm up, following the same one-owner discipline as the
> Python skills.

Rust's tooling is unusually good, which makes it easy to ship a crate that
compiles but fails other people: a lint gate that only runs locally, an MSRV you
advertise but never test, or a feature flag that breaks when a downstream unifies
it. The rules below make the gate mean what it says.

## Project layout & Cargo.toml essentials

```toml
[package]
name = "my-crate"
version = "0.1.0"
edition = "2021"          # pin the edition explicitly
rust-version = "1.74"     # your MSRV — CI must actually test this
license = "MIT OR Apache-2.0"
description = "One line; required by crates.io"
repository = "https://github.com/owner/my-crate"

[dependencies]
# minimum compatible versions, not exact pins — let downstreams unify
serde = { version = "1", features = ["derive"], optional = true }

[features]
default = []
serde = ["dep:serde"]     # gate optional deps behind features
```

Library code lives in `src/lib.rs`; a binary in `src/main.rs` or `src/bin/`.
Keep `Cargo.lock` **out** of git for a library, **in** git for a binary/app.

## The CI gate: fmt + clippy-as-error + test

A green `cargo build` proves nothing about style or lints. Run all four, and make
clippy warnings **fail** — otherwise the lint job is decorative:

```yaml
- uses: dtolnay/rust-toolchain@stable      # pin the toolchain, not "latest"
  with: { components: rustfmt, clippy }
- run: cargo fmt --all --check              # formatting is a gate, not a suggestion
- run: cargo clippy --all-targets --all-features -- -D warnings
- run: cargo test --all-features
```

`-D warnings` is the load-bearing flag: without it clippy prints warnings and
exits 0, so a "clippy" job stays green while lints pile up. Use `--all-features`
so feature-gated code is actually compiled and linted.

## Test the MSRV you advertise

`rust-version` in `Cargo.toml` is a promise. If CI only runs `stable`, a
dependency bump or a newer-than-MSRV language feature can silently raise your real
minimum while the manifest still claims the old one. Add an MSRV cell that pins
the exact version:

```yaml
strategy:
  matrix:
    rust: [stable, "1.74"]   # 1.74 == the rust-version in Cargo.toml
```

If you don't want to maintain an MSRV, delete `rust-version` rather than let it
lie.

## Feature-flag hygiene

Cargo **unifies** features across a dependency graph: if any crate in the build
enables your `serde` feature, it's on for everyone. So every feature combination
must compile on its own *and* together.

- Test the extremes: `cargo test --no-default-features` and
  `cargo test --all-features`. A `--no-default-features` build that fails means a
  downstream who opts out of your defaults can't use the crate.
- Never make one feature silently depend on another's items without declaring it
  in `[features]`; a downstream enabling only the first gets a compile error.

## Don't `.unwrap()` in library code

`.unwrap()`/`.expect()` on a `Result`/`Option` in a library turns a recoverable
error into a panic that aborts the *caller's* process. Return `Result` with a real
error type (`thiserror` for libraries, `anyhow` for binaries) and let the caller
decide. Reserve `unwrap` for tests and for invariants you've just locally proven.

## Publishing to crates.io

```bash
cargo publish --dry-run     # validates metadata + that it packages cleanly
cargo publish               # irreversible: a version can be yanked, never reused
```

Prefer `cargo-release` to automate the version bump + tag + publish in one
tag-triggered step, mirroring the Python release-automation pattern. crates.io
enforces semver on the version number but not on your API — bump the major
yourself on a breaking change, and never re-publish a yanked version's number.

## Checklist

```
Rust crate health:
- [ ] edition and rust-version (MSRV) pinned in Cargo.toml
- [ ] license + description + repository set (crates.io requires them)
- [ ] CI runs cargo fmt --check, clippy -D warnings, and test
- [ ] clippy job actually fails on warnings (-D warnings present)
- [ ] MSRV tested as its own matrix cell (or rust-version removed, not left lying)
- [ ] builds with --no-default-features AND --all-features
- [ ] no .unwrap()/.expect() on fallible paths in library code
- [ ] cargo publish --dry-run passes before a real release
- [ ] Cargo.lock committed for a binary, ignored for a library
```
