---
name: building-llm-backed-features
description: Builds application features on top of an LLM API in Python — prompt surfaces that drift apart, structured outputs, context budgeting, model/config wiring, keeping live-model calls out of default CI, evaluating stochastic output, and presenting model output truthfully. Use when adding an LLM call to an app, designing structured outputs or prompt templates, wiring model config, or testing/evaluating LLM-backed analysis.
---

# Building LLM-Backed Features

Calling a model is easy; shipping a feature around one is where the bugs live.
The model is a non-deterministic dependency whose *inputs are spread across your
codebase* and whose *outputs get presented to users as facts*. This skill covers
the failure modes that recur in that gap. (Building a server that exposes tools
**to** a model is the other direction — see
**[../mcp-servers/SKILL.md](../mcp-servers/SKILL.md)**.)

## Every string the model reads is prompt surface

Wording that shapes model behavior does not live only in the prompt template. It
typically lives in four places that drift apart independently:

| Layer | Looks like | Actually is |
|-------|-----------|-------------|
| System/user prompt template | prompt | prompt |
| Structured-output field descriptions | docstrings | **prompt** — the model reads them |
| Strings you interpolate into rendered results | formatting | user-facing claims |
| Template/API disclaimers | copy | the user's only caveat |

The second row is the trap. A `Field(description=...)` is part of the schema sent
to the model, so softening the prompt while leaving a categorical field
description in place changes nothing about the output.

```python
class Finding(BaseModel):
    # This description is prompt surface. "violation" here will produce
    # verdict-shaped output no matter how the system prompt is worded.
    concern: str = Field(description="Potential concern; may implicate the cited rule")
    citation: str = Field(description="Rule or policy the text may implicate")
```

Two habits keep the layers together:

- **Put the load-bearing phrases in one module of constants** that the prompt
  template, the field descriptions, and the result formatter all import. A
  wording change then lands everywhere or fails to compile.
- **Grep for dead prompt modules before declaring the change done.** Superseded
  rule sets and legacy analyzers usually stay in the tree with the original
  wording, and they are what the next feature gets copy-pasted from.

## Bound the context once, in a shared helper

The common shape is one call path that truncates and a sibling path that does
not, because they were written months apart. The unbounded one is the one that
blows the context window or the bill in production.

```python
def fit_context(text: str, *, max_tokens: int) -> str:
    """Single limiter every prompt path calls."""
    ...
```

- **Budget in tokens, not characters.** `body[:500]` is a character count that
  has no fixed relationship to context cost, and it silently changes meaning
  across languages.
- **If a limit is expressed in bytes, truncate on a character boundary**, never
  by slicing an encoded buffer — the same rule as any other bounded text
  (**[../../go/projects/SKILL.md](../../go/projects/SKILL.md)** has the
  UTF-8-safe version).
- **Apply the limiter at the boundary**, so a new call site inherits it instead
  of re-deciding. A per-call-site `[:N]` is how the two paths diverge again.

## Wire config to a section that exists — and validate it at boot

Reading `config["gpt2"]` when the defaults define `config["perplexity"]` is a
one-word bug with an expensive symptom: the section is missing, the lookup raises
a `KeyError`, and a broad `except Exception` around the analysis converts it into
the module's normal error-shaped result. Every call returns
`{"error": "Analysis failed: 'max_length'", ...}` and any test that asserts only
on result *shape* stays green.

Two rules:

- **First check on any config lookup: does this section actually exist in the
  defaults?** A section name that appears nowhere else is the bug.
- **Don't mix strictness across a config's consumers.** A manager that reads with
  `.get(key, default)` while the analysis path hard-indexes `config["max_length"]`
  will load a model fine from an empty config and only explode deep inside the
  work, where the broad `except` hides it.

Parse config into a typed model at startup so a missing key fails at boot:

```python
class PerplexityConfig(BaseModel):
    model_name: str
    max_length: int = 512
    overlap: int = 128
    thresholds: dict[str, float]

cfg = PerplexityConfig(**settings.get("perplexity", {}))   # fails now, not mid-request
```

## Keep live-model calls out of the default test path

Mark modules that make real API calls and make sure the default run deselects
them:

```python
pytestmark = pytest.mark.integration     # module-level: whole file is live
```

- **Reproduce CI with the full marker expression**, not a shortened one. A local
  `-m "not browser"` runs an integration module that CI's longer filter
  deselects, and the failure looks like a regression when it is a config
  difference.
- **A placeholder API key does not fail harmlessly.** It produces `401`s, and a
  client with a circuit breaker will open it — later tests then fail for a reason
  unrelated to what they test.

To exercise the real analysis path with no network and no model download,
populate the lazy cache directly so the loader never runs, then stub the scoring
call:

```python
manager = initialize_models(cfg)["scorer"]
manager._model, manager._tokenizer = Mock(), Mock()      # loader is now short-circuited
manager._tokenizer.encode.return_value = [0] * 10        # short enough to skip chunking
monkeypatch.setattr(Analyzer, "_score", Mock(side_effect=[12.0, 30.5]))
```

That runs in milliseconds and covers the wiring, chunking, and thresholding —
which is where the bugs actually are.

## Evaluate accuracy as its own job, and record raw outcomes

Model output is stochastic, so a single-run assertion is a coin flip and belongs
nowhere near a CI gate. Run evaluation as an explicit, credentialed job:

- A **versioned fixture** with **positive *and* negative** cases for every
  dimension you claim to detect. Positive-only fixtures cannot distinguish a
  working detector from one that flags everything.
- **Several runs per case** (five is a reasonable default), because one pass
  measures nothing about a stochastic system.
- **Persist raw per-run outcomes alongside the aggregate metrics.** A score that
  drops from 0.9 to 0.7 with no per-run record is undiagnosable.

CI still tests the *scorer and report logic* — with canned outcomes, no API calls
— so that half stays deterministic and fast.

## Don't present output as more than it is

Two shapes cause most of the damage:

**A field whose name promises something the value isn't.** Populating a
per-finding `confidence` with the response's overall quality score gives every
finding from one response the same number. Either compute the value the name
claims, or drop the field — a plausible-looking number is worse than none.

```python
# BAD — one response-level score copied onto each finding, labelled "confidence"
issues = [Issue(text=t, confidence=result.overall_score) for t in result.findings]
```

**Categorical verdicts in domains that need professional judgment.** Legal,
medical, and compliance features are the usual ones. Hedge the output, and hedge
it in all four layers from the first section:

| Categorical | Qualified |
|-------------|-----------|
| `Violates <LAW>` | `Potential concern — may implicate <LAW>` |
| `Missing required statement` | `Not found; may be required depending on jurisdiction and context` |
| `compliant: bool` | `concerns: list[Concern]` |

The public API field is the hardest layer to walk back — a boolean named
`compliant` is a legal conclusion in your response schema forever. Pick the
hedged name up front.

## Checklist

```
Prompt surface:
- [ ] Load-bearing wording lives in shared constants, not duplicated per layer
- [ ] Structured-output field descriptions reviewed as prompt, not as docs
- [ ] Superseded/legacy prompt modules updated or deleted, not left to be copied

Inputs:
- [ ] One shared context limiter; every prompt path calls it
- [ ] Budget in tokens; byte limits truncate on character boundaries

Config:
- [ ] Every section a lookup reads exists in the defaults
- [ ] Config validated into a typed model at boot (no hard-indexing deep in the work)
- [ ] Broad `except` around analysis can't disguise a wiring error as a normal result

Tests & evaluation:
- [ ] Live-model modules marked; default/CI run deselects them
- [ ] CI reproduced with the full marker expression
- [ ] Real analysis path covered with a pre-populated model cache (no network)
- [ ] Accuracy fixture is versioned, has negative cases, runs each case N times,
      and persists raw outcomes

Output:
- [ ] No field whose name over-claims what the value measures
- [ ] Professional-judgment domains hedged in prompt, schema, strings, and UI
```

## Learn More

This skill is based on the [Guide to Developing High-Quality Python Libraries](https://mcginniscommawill.com/guides/python-library-development/) by [Will McGinnis](https://mcginniscommawill.com/).
