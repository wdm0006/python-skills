---
name: wiring-application-config
description: Load, merge, and validate layered application configuration (defaults plus a user YAML/TOML/JSON file or a stored settings object) so a mis-wired or misspelled key fails loudly instead of silently reverting to the default — sections the code reads that exist nowhere, sections that exist but nothing reads, unvalidated recursive merges, `bool`-passes-as-`int`, defaults aliased by a shallow merge, falsy-but-valid values killed by `or`/`||`, partial write-backs that are stickier than a missing file, and bootstrap ordering that swallows the loader's own warnings. Use when adding a config key, writing or reviewing a config loader/merge/schema, reading a setting in a new module, persisting user settings, wiring logging from config, or debugging a setting that "has no effect".
---

# Wiring Application Configuration

Configuration bugs are quiet because every layer on the path has a fallback. A
value travels defaults → user file → merge → consumer, and each hop can drop it
without raising anything. The result is an application that starts cleanly,
reports success, and runs on values the user did not choose.

**Use a typed settings model when you can.** `pydantic-settings`, a tagged
struct, or any schema-first loader collapses most of this page into one class:
unknown keys and wrong types fail at construction, and every consumer gets
attribute access instead of `config["a"]["b"]`. Reach for the hand-rolled merge
below only when you genuinely need a layered file surface the typed model
doesn't cover — and then port the guarantees, don't skip them.

## A config key is a contract between two files. Check both ends.

The reader indexes one section; the defaults declare another:

```python
# consumer
cache_cfg = config["cache"]         # section name that exists nowhere
store = ResultStore(cache_cfg)

# defaults.py
DEFAULT_CONFIG = {"storage": {"backend": "...", "max_entries": 512, ...}}
```

Nothing fails at load. Nothing fails at startup. Every request through that path
returns `{"error": "Request failed: 'max_entries'"}` — a `KeyError` caught by a
broad `except` several frames away and folded into a normal-shaped result. That
can ship for months, because tests that assert on the result's *shape* pass.

So make this the first check on any config lookup you write or review: **does
the section this code reads actually exist in the defaults?** It is a grep, not
an inspection:

```bash
# every section name the code reads
grep -rhoE 'config(\.get\(|\[)"[a-z_]+"' src/ | grep -oE '"[a-z_]+"' | sort -u
# each one must appear in the defaults module
```

Run it in the other direction too. A section that appears **only** in the
defaults and the schema is inert: the user sets it, validation accepts it, and
nothing reads it. Separate the two causes before "fixing" it —

- **Unwired**: something is supposed to consume it and doesn't. That is a bug;
  wire it up.
- **Unimplemented**: the key describes a capability nobody built (a
  config-driven directory when the directory is a module constant). That is a
  feature request. Don't implement it under cover of a wiring fix — and don't
  leave a documented key that silently does nothing either. Say which it is.

## Be strict at the boundary, permissive after it

The same config dict is routinely consumed at two strictness levels: the loader
or manager uses `cfg.get("backend", DEFAULT)`, and a deeper function
hard-indexes `cfg["max_entries"]`. A partial config then loads fine, constructs
objects fine, and explodes deep inside a request — where the broad `except`
turns it into an error-shaped response.

Pick one place to be strict — the load boundary — and validate there. After
that, missing keys shouldn't be possible, so `[...]` indexing downstream is
correct and self-documenting. `.get(key, default)` scattered through consumers
is what makes a typo survive to production: it silently supplies a plausible
value for a key that was never spelled correctly anywhere.

## Validate the file surface at load; drop unknown keys with a warning

A recursive merge that accepts whatever the YAML contained has two failure
modes, both silent:

- `storage.max_entires: 1024` is retained under the misspelled name while the
  real `max_entries` keeps its default. The user sees their key in the file and
  concludes it works.
- `storage: redis` — a scalar where a mapping belongs — survives the load and
  fails only when something treats it as a mapping.

Declare the surface, validate before merging, and warn with the **full dotted
path** so the message is actionable:

```python
CONFIG_SCHEMA = {
    "storage": {"backend": STRING, "max_entries": INTEGER, "batch_size": INTEGER},
    "logging": {"level": STRING, "format": STRING},
}

def _validate(node, schema, path=""):
    clean = {}
    for key, value in node.items():
        dotted = f"{path}.{key}" if path else key
        expected = schema.get(key)
        if expected is None:
            logger.warning("Unknown config key %r — ignored", dotted)
        elif isinstance(expected, dict):
            if isinstance(value, dict):
                clean[key] = _validate(value, expected, dotted)
            else:
                logger.warning("Config key %r must be a mapping — ignored", dotted)
        elif _matches_kind(value, expected):
            clean[key] = value
        else:
            logger.warning("Config key %r has wrong type — ignored", dotted)
    return clean
```

**Exclude `bool` explicitly in any numeric type check.** `isinstance(True, int)`
is `True` in Python, and the same widening bites in most dynamic languages, so
`batch_size: true` sails through a naive integer check and becomes `1` deep in an
arithmetic path. `_matches_kind` must short-circuit on `isinstance(value, bool)`
*before* the integer branch.

## Validation makes config a closed surface — add a coverage test

Once unknown keys are dropped, the schema is load-bearing in a new direction:
**anything you add to the defaults, or to the config file you ship, must also be
added to the schema or it is silently discarded at load.** The warning goes to a
log nobody is reading during development.

Two cheap guards, both worth having:

```python
def test_defaults_are_declared():
    assert leaf_paths(DEFAULT_CONFIG) <= leaf_paths(CONFIG_SCHEMA)

def test_shipped_config_validates_without_warnings(caplog):
    load_config("config.example.yaml")
    assert [r for r in caplog.records if r.levelno >= logging.WARNING] == []
```

Declare the **documented** surface, not just the consumed subset. Keys that ship
in your own example config belong in the schema even if nothing reads them yet —
otherwise every load of your own file emits warnings. Tightening the schema down
to the consumed subset is fine, but it has to edit the shipped file in the same
change.

## A merge that recurses on dicts only aliases your defaults

Deep-merge helpers usually recurse into dicts and copy everything else by
reference. Every list, set, or nested object in the defaults is then **shared**
with the loaded config, and a later mutation of the loaded config reaches back
into a module-level global that the rest of the process — and every other test
in the run — reads from.

The same bug wears a different hat in JS: `{...DEFAULTS, lastIndex: i}` copies
the top level and aliases every nested object. Merge nested keys explicitly, or
deep-copy the defaults before merging:

```python
merged = copy.deepcopy(DEFAULT_CONFIG)   # not {**DEFAULT_CONFIG}
```

It costs nothing at startup and removes a whole class of cross-test bleed.

## Falsy is not missing

```python
timeout = cfg.get("timeout") or 30        # a configured 0 becomes 30
start_hour = settings.get("start") or 9   # midnight becomes 9am
```

`0`, `""`, `False`, and `[]` are all legitimate configured values. Use
`cfg.get(key, default)` in Python and `??` in JavaScript, never `or`/`||`, for
any setting whose valid range includes a falsy value — hours, counts,
thresholds, retry limits, feature flags.

## Never persist a partial settings object

Writing back a spread of whatever you just read is fine until the read returns
nothing:

```javascript
// Bad — if `settings` was absent, this persists an object missing every other key
await storage.set({ settings: { ...settings, lastIndex: i } });
```

A *missing* config self-heals: `settings ?? DEFAULTS` catches it. A *partial*
one does not — it is truthy, so the reader keeps it and throws on the first
nested key, and the corruption is sticky across restarts. Read-modify-write
rules:

1. **Re-read** immediately before writing, so a concurrent writer's change isn't
   lost.
2. **Merge over the full defaults**, spelling out nested keys, so the persisted
   object is always complete.
3. **Await the write** — a worker or page that is torn down mid-write loses it.

Validate user-entered values before they reach storage, too. A field parsed with
a bare `int()`/`parseInt()` yields `None`/`NaN`, serializes to `null`, and is
silently replaced by the default on the next read — while the UI says "saved".
Declarative constraints that nothing evaluates (an HTML `min`/`max` on a form
that is never submitted) are inert; enforce the range in code.

## Bootstrap ordering: don't swallow the loader's own warnings

When config configures logging, the order is fixed:

1. `basicConfig` with hardcoded defaults, **before** `load_config()` — the
   loader emits the "unknown key / wrong type" warnings, and they must land
   somewhere.
2. Re-apply level and format from the loaded config afterwards.

Two details that bite:

- **Keep the output stream pinned in both calls.** A process that speaks a
  protocol over stdout (stdio JSON-RPC, a CLI whose stdout is piped into another
  tool) corrupts that stream the moment a log record goes to it. Log to stderr,
  explicitly, in the bootstrap call and the reconfigure call.
- **Resolve the level before applying it.** `basicConfig(level="LOUD",
  force=True)` removes the existing handlers *before* raising on the bad level,
  so an invalid value can leave the process with no logging at all. Look the
  level up first, fall back to the default with a warning, and never let a bad
  config value raise out of the logging setup.

## Testing

- **Give the loader a `config_path` parameter** and write a real file into a
  temp directory. That is far cheaper and truer than stacking patches on `open`,
  `Path.exists`, and `yaml.safe_load`, and it lets you assert on the returned
  values *and* the warning text in one test.
- **Always pass an explicit path.** A default path resolved relative to the
  current working directory means a bare `load_config()` in a test reads the
  repo's own shipped file — so editing that file changes the outcome of
  unrelated tests. The single exception is the test that deliberately validates
  the shipped file.
- **Assert `"error" not in result`** in tests that exercise a config-consuming
  code path. Where a broad `except` wraps the consumer, that assertion is the
  only thing separating a mis-wired key from a working one.
- **Mutation-test the wiring.** Rename the section back to the wrong name; some
  test must go red. If the suite stays green, your coverage is shape assertions,
  not behavior. Separately, drop the `bool` short-circuit from the type check —
  exactly one test should fail.
- **Test the typo, not just the happy path.** A config with a misspelled key
  must produce a warning naming the dotted path *and* leave the real key at its
  default.

## Checklist

- [ ] Every section the code reads exists in the defaults (grep both directions)
- [ ] Every section in the defaults/shipped file is read by something, or is
      explicitly labelled unimplemented rather than left silently inert
- [ ] Strict validation at the load boundary; consumers index instead of
      `.get(key, default)`-ing a required key
- [ ] Unknown keys and wrong types dropped with a warning naming the dotted path
- [ ] `bool` excluded before any integer/number type check
- [ ] Defaults ⊆ schema asserted by a test; shipped config validates warning-free
- [ ] Schema covers the documented surface, not just the consumed subset
- [ ] Defaults deep-copied before merge — no list/nested object shared by reference
- [ ] `get(key, default)` / `??` rather than `or` / `||` for any falsy-valid value
- [ ] Write-backs re-read, merge over full defaults, and are awaited
- [ ] User input range-checked in code, not by inert declarative constraints
- [ ] Bootstrap logging configured before `load_config()`; stream pinned in both;
      an unknown level falls back with a warning instead of raising
- [ ] Loader takes an explicit path; tests never rely on the cwd-relative default

Related: **reporting-derived-metrics** for how a broad `except` disguises a
mis-wired key as a normal-shaped result, **verifying-external-behavior** for
confirming what a permissive client does with an argument it doesn't recognise,
and **shipping-across-surfaces** for keeping a documented config key in step with
the code that reads it.
