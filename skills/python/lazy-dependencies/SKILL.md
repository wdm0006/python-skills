---
name: deferring-heavy-dependencies
description: Keep expensive resources — ML models, spellcheck dictionaries, embedded databases, large third-party imports — off code paths that never use them. Covers constructor work paid by every caller, one-size factories that load the heaviest member for the cheapest request, load-and-unload-per-call masquerading as a cache, measuring per-call cost in a fresh process, telling a one-time import from a repeated model load, and the test fallout (patches that only now take effect, autouse fixtures that hide the dependency). Use when a trivially cheap operation takes hundreds of milliseconds, when adding a heavy dependency to a shared constructor or factory, or when reviewing a class whose `__init__` builds something most callers never touch.
---

# Deferring Heavy Dependencies

A word count should not load a language model. When it does, the cause is almost
never the algorithm — it is that the cheap function shares a constructor, a
factory, or an import with an expensive one. Profiling the function body finds
nothing, because the time is spent before the body runs.

## The cost is in construction, not in the call

```python
# Bad — every instance builds a dictionary, whatever the caller asked for.
class TextAnalyzer:
    def __init__(self) -> None:
        self.spell_checker = SpellChecker()      # ~12 MB retained, ~80 ms

    def character_count(self, text: str) -> int:
        return len(text)                         # never touches spell_checker
```

`character_count` profiles as free and still takes 80 ms. Defer the field:

```python
# Good — built on first real use, then cached on the instance.
class TextAnalyzer:
    def __init__(self) -> None:
        self._spell_checker: SpellChecker | None = None

    @property
    def spell_checker(self) -> SpellChecker:
        if self._spell_checker is None:
            self._spell_checker = SpellChecker()
        return self._spell_checker
```

`functools.cached_property` is the same thing with less code; use the explicit
form when you also need to reset or pre-populate the slot (see below).

Deferring is only safe when construction has no side effect the caller depends
on ordering-wise — opening a file, binding a port, registering a signal handler.
If it does, it isn't initialization, it's an operation: give it a method name.

## One factory for everything makes cheap paths pay for the expensive one

The pattern that produces the worst numbers is a single accessor that builds the
whole family:

```python
# Bad — loads the NLP model, then constructs all four analyzers.
def get_analyzers() -> dict[str, Any]:
    nlp = load_language_model()          # seconds
    return {
        "basic": BasicStatsAnalyzer(),   # pure len()/split()
        "readability": ReadabilityAnalyzer(),
        "keywords": KeywordAnalyzer(nlp),
        "detection": DetectionAnalyzer(nlp),
    }
```

Every entry point calls `get_analyzers()`, so character counts, word counts, and
reading-time estimates each pay a full model load and unload. Measured in a
fresh process, that is on the order of half a second per call for work that is
otherwise microseconds.

Split by what the path actually needs. Either give each analyzer its own
accessor, or make the model itself a lazy handle the analyzers that need it pull
from. Then state the boundary explicitly — which helpers are pure (regex,
string, third-party parsers) and which genuinely require the initialized model —
because that boundary is what the next change will violate.

## Load-and-unload per call is not a cache

A factory that loads a model, uses it, and unloads it at the end of the request
has the worst of both: the cost of loading, and none of the benefit of keeping
it. Cache the handle for the process lifetime.

That choice has a consequence worth stating in the code: **a cache that is never
cleared makes every constructor cost permanent**, so anything expensive inside
the cached objects must be lazy too. The two techniques are a pair — process-long
caching is what makes eager `__init__` work unrecoverable, and laziness is what
makes process-long caching affordable.

## Measure per call, in a fresh process

In-process timing after the first call measures nothing; the model is already
resident. Time the first call of a cold process, one entry point at a time:

```bash
python -c "
import time
from mypkg.api import character_count, readability_score
for fn, name in ((character_count, 'character_count'), (readability_score, 'readability_score')):
    t = time.perf_counter(); fn('hello world'); print(name, round(time.perf_counter() - t, 4))
"
```

**Distinguish a one-time import from a repeated load.** After the fix, one entry
point often still shows a few hundred milliseconds on its first call — that is
the third-party package importing, paid once per process, not a model load
returning. Confirm which you are looking at before reading it as the fix
failing:

```bash
python -X importtime -c "import mypkg.api" 2>&1 | sort -k2 -n -r | head
```

Then re-time the same call a second time in the same process: a one-time import
drops to near zero, a per-call load does not.

For the memory half, `tracemalloc` around a single construction gives the
retained size that argues for laziness far better than a wall-clock number does.

## An ambient fixture hides the dependency you are trying to remove

The test that should catch a re-introduced model load usually cannot, because a
session-scoped `autouse` fixture already loaded the real model for the whole
run. Everything passes whether or not the cheap path touched it.

Assert on the loader, not on the outcome:

```python
def test_character_count_does_not_load_the_model(monkeypatch):
    loader = Mock(side_effect=AssertionError("model loaded on a model-free path"))
    monkeypatch.setattr("mypkg.api.load_language_model", loader)

    assert character_count("hello world")["characters"] == 11
    loader.assert_not_called()
```

Failing loudly from the mock is deliberate: a bare `assert_not_called()` at the
end still passes if the production code catches the exception it provoked.

## Making a field lazy changes when patches bind

This is the surprise that follows the refactor. A test like:

```python
@patch("mypkg.analyzers.SpellChecker")
def test_spelling(self, mock_checker): ...
```

did **nothing** while the field was eager and the instance was built in
`setup_method` — the real object was already bound before the patch applied, so
the test exercised the real dictionary. Once the field is lazy, the patch is
consulted at first use and finally takes effect. The tests keep passing, but
they now assert against a mock. Re-read every test that patches the deferred
constructor and decide, per test, whether the mock is what you wanted.

The same shift is useful on purpose: to exercise code behind a lazy handle
without loading anything, populate the private slot directly.

```python
manager = build_manager(config)
manager._model = Mock()          # fills the lazy cache …
manager._tokenizer = Mock()      # … so the loader is never called
```

That runs in milliseconds and needs no fixtures — but it reaches past the public
API, so keep it to tests whose subject is the surrounding logic, not the loading.

## Checklist

```
- [ ] No `__init__` builds a resource most callers never read
- [ ] Deferred construction is side-effect-free (else it's a method, not a field)
- [ ] Cheap entry points don't route through a factory that builds heavy ones
- [ ] Heavy handles are cached for the process, not loaded and unloaded per call
- [ ] Timings taken in a fresh process, first call, one entry point at a time
- [ ] One-time import cost told apart from a per-call load (`-X importtime`, second call)
- [ ] Retained size measured (`tracemalloc`) where memory is the argument
- [ ] A test asserts the loader is NOT called on model-free paths
- [ ] Tests that patch the now-lazy constructor re-read — some only now take effect
```
