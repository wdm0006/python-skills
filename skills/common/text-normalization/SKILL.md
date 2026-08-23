---
name: normalizing-text-for-measurement
description: Strip, parse, and segment a document before something else measures it — normalizers that fuse two blocks into one word because a close-token emits no separator, character-based metrics (reading time, token budgets, size limits) that bill markup syntax as content while word-based metrics stay clean, sibling consumers that skip the normalizer entirely, parser presets whose rule set silently reclassifies a construct, sections grouped by a non-unique heading key that collapse and double-count into an ancestor, and deliberate lossiness that the next reader mistakes for a bug. Use when writing or reviewing a markdown/HTML stripper, a plain-text extractor, a section or paragraph splitter, a reading-time/word-count/readability/token-count function, a dedup key or checksum built from prose, or a search-index preprocessing step.
---

# Normalizing Text for Measurement

Any pipeline that reduces a document to a number — word count, reading time,
readability, a token budget, a dedup key, a checksum, a search index — has two
halves: a **normalizer** that turns markup into something comparable, and a
**measurer** that consumes it. Reviews concentrate on the measurer. Almost every
bug in this shape lives in the normalizer, and none of them raise.

The failure mode is uniform: the output is still a plausible string, the metric
is still a plausible number, and nothing anywhere reports a problem. See
[reporting-derived-metrics](../derived-metrics/SKILL.md) for the other end of the
same pipeline — what the measurer does when the sample is too small.

## A missing separator fuses two blocks into one token

A token-walking stripper emits text for content tokens and separators for close
tokens. Miss one close token and two blocks become one word.

```python
# Bad — paragraphs are separated, headings are not
for token in tokens:
    if token.type == "inline":
        out.append(token.content)
    elif token.type == "paragraph_close":
        out.append("\n\n")
```

`"# Title\n\nBody text here."` normalizes to `"TitleBody text here."`. One word
instead of four, and a word that appears in no dictionary. Every consumer
inherits it:

- word count drops by one per heading
- average word length rises, so readability scores report plain prose as far
  harder than it is — **and the error scales with heading density**, so the most
  structured documents are the most wrong
- a dedup key or checksum diverges from the same prose written without a heading

The general rule: **every block-level construct the parser opens must close with
a separator.** Enumerate the close-token types your parser emits (`heading_close`,
`list_item_close`, `blockquote_close`, `table_row_close`, …) and account for each
one explicitly. A stripper that handles two of six is not "mostly right"; it is
wrong on every document containing the other four.

## Character-based metrics bill markup as content; word-based metrics don't

This asymmetry decides which of your metrics need auditing.

- **Word- and syllable-based** metrics (word count, readability grade levels,
  syllable ratios) tokenize on whitespace and punctuation, so stray `|` and `---`
  delimiters mostly disappear on their own. Table pipes leave readability scores
  essentially unchanged.
- **Character-based** metrics (reading time computed as `chars × ms_per_char`,
  byte-size limits, character quotas, rough token estimates) count every
  character of syntax as something a human reads.

So a link's target URL, an image's path, fence delimiters, and table pipes are
all billed. On link- and image-heavy prose a character-based reading time can run
*roughly double* the true figure; a single small table adds a noticeable
double-digit percentage. The overshoot grows with markup density, which means it
is worst on exactly the documents (docs pages, READMEs, changelogs) the estimate
matters most for.

Audit rule: for each metric, ask whether it is character-based. If it is, it
**must** consume normalized text, and its tests must compare against a plain-text
equivalent rather than assert a shape.

## Enumerate every consumer of the normalizer

The most common version of this bug is not a broken normalizer — it is a sibling
function that never calls it.

```python
def readability(text: str) -> dict:
    return score(strip_markup(text))     # normalized

def reading_time(text: str) -> float:
    return textstat.reading_time(text)   # not normalized — same module, same input
```

Nothing fails. The two functions take the same argument, live in the same file,
are described the same way in the docs, and disagree by a factor of two on any
markdown input. Whenever you add or fix a normalizer:

1. Grep for every call site of the *measurer*, not the normalizer, and check each
   one goes through normalization.
2. Grep for every call site of the *normalizer* and note them — the count matters
   in both directions. Once a stripper has two production consumers, a one-line
   change to it moves two public outputs, and the PR description has to say so.
3. Check the segmented paths too. If the API exposes `level="full" | "section" |
   "paragraph"`, a fix applied to the full-document path may leave the segmented
   ones on the old behaviour.

## A parser preset is a rule set you did not choose

Constructing a parser with no arguments selects a default profile, and that
profile decides which constructs are *recognized at all*.

```python
md = MarkdownIt()          # CommonMark preset — no `table` rule
```

A GFM table under this preset is not a table. It is an ordinary paragraph whose
text happens to contain `|` and `---`, so every delimiter survives normalization
into what you are calling "plain text". Nothing errors, because a paragraph is a
perfectly valid parse.

Before trusting a parse tree, print the enabled rule set (`md.get_active_rules()`
or the library's equivalent) and confirm the constructs you actually receive are
in it. When you enable a rule, the stripper needs matching close-token handling
in the same change — enabling `table` without emitting a space at cell close and
a newline at row close just moves the problem.

Treat this as one case of a general habit: verify what a dependency actually does
on your input rather than what its README implies. See
[verifying-external-behavior](../verifying-external-behavior/SKILL.md).

## Grouping by a natural key that is not unique

Segmenting a document into sections and returning them as a `dict` keyed by
heading text assumes headings are unique. They are not — `### Example`,
`## Notes`, and `## Usage` repeat all through real documents.

```python
# Bad — the second "## Notes" overwrites or is discarded
sections = {heading_text: body for heading_text, body in walk(doc)}
```

Two consequences, and the second is the one people miss:

- **Collapse.** The first occurrence keeps the key; later ones are never reported
  under any key of their own. A document with four sections returns three.
- **Double counting.** The lost content usually is not dropped. A hierarchy stack
  extends it into the nearest *ancestor* section, so the ancestor's word count and
  reading time silently include a body that is also reported elsewhere. With no
  ancestor, it appears only in the full-document text. So the per-section numbers
  neither sum to the whole nor stay disjoint.

Key sections by something structurally unique — an index, a `(level, index)` pair,
or a slug with a disambiguating suffix — and carry the display heading as a field.
Then audit downstream: any dict comprehension over the sections and any
`processed_keys`-style dedup guard was written assuming uniqueness too.

## Write down which lossiness is deliberate

Normalizers are intentionally lossy in places. A stripper may drop list markers
so `- a\n- b` measures as two bare items, or ignore raw HTML block content
entirely. Those are design decisions, and they are indistinguishable at a glance
from the missing-separator bug above.

Both directions of the mistake happen: a deliberate drop gets "fixed" by someone
who read it as a defect, and an accidental fusion gets pinned by a test and
survives for years as apparent intent. Put a one-line comment stating the intent
next to the branch, and make the test name say it (`test_list_markers_are_dropped`,
not `test_list_output`). A future reader should be able to tell which branches are
decisions without reconstructing the argument.

## Testing a normalizer without depending on a third-party constant

Two rules specific to this pipeline; for mutation-testing technique generally see
[testing-python-libraries](../../python/testing-strategy/SKILL.md).

**Assert equivalence, not magic numbers.** The strongest assertion needs no
constant from the analysis library at all: *the markdown input must measure
identically to its hand-written plain-text equivalent.*

```python
def test_markdown_measures_as_its_plain_equivalent():
    markdown = "# Title\n\nSome [linked](https://example.com/a/long/path) text.\n"
    plain = "Title\n\nSome linked text.\n"
    assert reading_time(markdown) == reading_time(plain)
    assert strip_markup(markdown).strip() == "Title\n\nSome linked text."
    assert len(strip_markup(markdown).split()) == 3
```

This fails hard when the stripper regresses, and keeps passing when the scoring
library is upgraded. If the analysis dependency is unpinned, an exact-float
assertion on its output is version-brittle: the same document can score several
points differently across releases. Where you want a number for documentation,
use a tolerance sized against the bug's own gap (if the defect moved a score by
~30 points, `abs=1.0` is both a real value assertion and version-tolerant), and
**measure the expected value by running the code** — never estimate it by hand.
These constants are not intuitive and a plausible guess fails CI.

**A test that pins buggy output is worse than no test.** When you find a
normalizer defect, read its test file before assuming it is uncovered — often the
wrong output is already asserted verbatim, which is why nobody noticed. Fixing the
bug means updating those assertions, and there is usually more than one: the
obvious unit test named after the construct, and a longer "mixed content" or
"end to end" fixture whose expected string contains the same fused or dropped text
mid-way. Scope the change by grepping the fixture bodies for the affected text,
not by the test names.

**A whitespace-only or empty input test guards nothing here.** Most measurers
already return `0` for `"   \n\n  "` before any fix, so such a test passes on the
broken code and reads as coverage it is not.

## Review checklist

- [ ] Every block-level close token the parser emits has an explicit separator
      branch; the list was enumerated from the parser, not from memory
- [ ] Each metric classified as character-based or word-based; every
      character-based one consumes normalized text
- [ ] Every call site of the measurer goes through the normalizer — including
      segmented (`section`/`paragraph`) paths, not just the full-document path
- [ ] Number of production consumers of the normalizer is known, and a change to
      it names every output it moves
- [ ] Parser rule set confirmed to include the constructs the input actually uses;
      newly enabled rules have matching close-token handling
- [ ] Section/segment maps keyed by something structurally unique, not by heading
      text; downstream comprehensions and dedup guards audited for the same
      assumption
- [ ] Deliberate lossiness commented at the branch and named in the test
- [ ] Regression tests assert markdown-equals-plain-equivalent plus the exact
      stripped string and word count, rather than a float from an unpinned library
- [ ] Existing tests checked for pinned buggy output before declaring the defect
      untested
