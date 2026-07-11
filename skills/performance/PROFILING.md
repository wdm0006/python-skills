# Profiling

Deep dive on finding where time and memory actually go. Always profile before optimizing; the bottleneck is rarely where you guess.

## Contents

- [cProfile + pstats](#cprofile--pstats)
- [PyInstrument](#pyinstrument)
- [Memory: memray](#memory-memray)
- [Memory: tracemalloc](#memory-tracemalloc)
- [line_profiler](#line_profiler)
- [Choosing a tool](#choosing-a-tool)

## cProfile + pstats

Deterministic profiler built into the stdlib. Counts every call, so it inflates overhead on call-heavy code but gives exact call counts.

```bash
# Sort by cumulative time (time in a function + everything it calls)
uv run python -m cProfile -s cumulative script.py

# Sort by total time (time in the function body itself, excluding callees)
uv run python -m cProfile -s tottime script.py

# Save raw stats for later analysis
uv run python -m cProfile -o profile.stats script.py
```

Read a saved `.stats` file with `pstats`:

```python
import pstats
from pstats import SortKey

stats = pstats.Stats("profile.stats")
stats.strip_dirs().sort_stats(SortKey.CUMULATIVE).print_stats(20)

# Who calls the hot function, and who it calls
stats.print_callers("encode")
stats.print_callees("encode")
```

Profile a region in code instead of the whole script:

```python
import cProfile, pstats

with cProfile.Profile() as pr:
    result = my_function()

pstats.Stats(pr).sort_stats("tottime").print_stats(10)
```

Reading the columns:

| Column | Meaning |
|--------|---------|
| `ncalls` | Call count (`20/4` = 20 calls, 4 primitive after recursion) |
| `tottime` | Time in the function body only — high here means the function itself is slow |
| `cumtime` | Time including callees — high here means it drives a slow subtree |
| `percall` | tottime or cumtime divided by ncalls |

Rule of thumb: high `tottime` means optimize this function; high `cumtime` with low `tottime` means the cost is downstream — follow the call tree.

## PyInstrument

Statistical, wall-clock profiler. Samples the stack on an interval, so it captures I/O and sleep (which cProfile misses) with negligible overhead, and collapses uninteresting frames into a readable call tree. Times reflect real elapsed time, not just CPU.

```bash
uv run pyinstrument script.py

# Interactive HTML flame view in the browser
uv run pyinstrument -r html -o profile.html script.py

# Speedscope format for the speedscope.app viewer
uv run pyinstrument -r speedscope -o profile.json script.py
```

Programmatic use for a specific region:

```python
from pyinstrument import Profiler

profiler = Profiler()
profiler.start()
result = my_function()
profiler.stop()

print(profiler.output_text(unicode=True, color=True))
```

Or as a context manager:

```python
from pyinstrument import Profiler

with Profiler() as profiler:
    result = my_function()
profiler.print()
```

Reading the tree: indentation is the call stack, and each line shows wall-clock seconds and the percentage of total runtime. Follow the largest percentages down until the number stops dropping — that frame is where the time is spent. Because it is statistical, sub-millisecond functions may not appear; that is intentional noise reduction, not a bug.

Use PyInstrument first for a fast, honest picture of wall-clock cost; drop to cProfile when you need exact call counts.

## Memory: memray

Tracks every allocation (including in C extensions) and produces flame graphs and leak reports. Best tool for "why does this use so much RAM" and native-allocation questions.

```bash
uv add --dev memray

# Record allocations to a binary file
uv run memray run -o output.bin script.py

# Render an allocation flame graph
uv run memray flamegraph output.bin

# Only allocations still live at exit — the leak view
uv run memray flamegraph --leaks output.bin

# Terminal summary and a live table of the biggest allocators
uv run memray summary output.bin
uv run memray table output.bin

# Watch memory live while the program runs
uv run memray run --live script.py
```

Reading it: the flame graph width is bytes allocated, and stacks show the allocation path. The default view counts total allocations over the run (churn/peak); `--leaks` restricts to memory never freed, which is what you want when hunting an actual leak. A growing `--leaks` graph across a longer run points straight at the retaining call site.

## Memory: tracemalloc

Stdlib allocation tracker. No dependency, pure-Python allocations only, and its snapshot/diff API makes it the right tool for pinpointing growth between two moments — e.g. across one iteration of a loop that leaks.

```python
import tracemalloc

tracemalloc.start()

# ... run the code under test ...

snapshot = tracemalloc.take_snapshot()
for stat in snapshot.statistics("lineno")[:10]:
    print(stat)
```

Diff two snapshots to isolate what grew between them:

```python
import tracemalloc

tracemalloc.start()
snapshot1 = tracemalloc.take_snapshot()

run_one_cycle()

snapshot2 = tracemalloc.take_snapshot()
for stat in snapshot2.compare_to(snapshot1, "lineno")[:10]:
    print(stat)  # shows +size / +count deltas per line
```

Capture stack traces (not just the final line) to see how an allocation was reached:

```python
import tracemalloc

tracemalloc.start(25)  # keep up to 25 frames per allocation
snapshot = tracemalloc.take_snapshot()
top = snapshot.statistics("traceback")[0]
print("\n".join(top.traceback.format()))
```

If the diff line grows every cycle, that line is retaining memory. Prefer tracemalloc for reproducible in-process leak hunts; reach for memray when the allocations are in C code or you want a flame graph.

## line_profiler

Line-by-line timing for a single hot function once profiling has already told you which function to look at. Overhead is high, so scope it tightly with `@profile`.

```bash
uv add --dev line_profiler
```

Decorate the target function with `@profile` (injected by the tool — no import needed) and run under `kernprof`:

```python
@profile
def encode(lat, lon):
    ...
```

```bash
uv run kernprof -l -v script.py
```

Or profile explicitly without editing source:

```python
from line_profiler import LineProfiler

lp = LineProfiler()
wrapped = lp(encode)
wrapped(37.7749, -122.4194)
lp.print_stats()
```

Reading the output: `% Time` is the share of the function's runtime spent on each line — scan that column for the one or two lines that dominate. `Hits` reveals unexpected loop counts; `Per Hit` reveals a line that is cheap once but called constantly.

## Choosing a tool

| Question | Tool |
|----------|------|
| Where does wall-clock time go? | PyInstrument |
| Exact call counts / call graph | cProfile + pstats |
| Which line in this function is slow? | line_profiler |
| Peak memory / native allocations / flame graph | memray |
| What grew between two points (in-process leak) | tracemalloc snapshots |

Workflow: PyInstrument or cProfile to find the hot function, then line_profiler to find the hot line; memray for peak-memory questions, tracemalloc to diff a leaking cycle.
