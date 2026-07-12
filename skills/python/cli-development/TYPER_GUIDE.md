# Typer Guide

Typer builds CLIs from type hints, on top of Click. Run everything through `uv` (`uv add typer`, `uv run mycli ...`). `typer` pulls in `rich` for formatted output.

## Contents

- Type-Hint-Driven Commands
- Options and Arguments
- Subcommand Apps
- Progress and Rich Output
- Testing
- Click vs Typer — Which to Choose

## Type-Hint-Driven Commands

Function parameters become CLI parameters; their type hints drive parsing, validation, and `--help`. A parameter with a default is an option; without one it is an argument.

```python
import typer

app = typer.Typer()

@app.command()
def greet(name: str, count: int = 1, formal: bool = False):
    """Greet someone."""
    greeting = "Good day" if formal else "Hi"
    for _ in range(count):
        typer.echo(f"{greeting}, {name}")

if __name__ == "__main__":
    app()
```

`name` is a required argument, `--count` an int option, `--formal/--no-formal` a boolean flag — all inferred. Entry point:

```toml
[project.scripts]
mycli = "my_package.cli:app"
```

A single-command app still needs `typer.Typer()`; call `app()` as the entry point. Typer exposes the command directly (no subcommand name) when only one is registered.

## Options and Arguments

Attach metadata with `typer.Option` / `typer.Argument` as the default value, using `Annotated` so the type hint stays clean.

```python
from typing import Annotated
from pathlib import Path
import typer

@app.command()
def process(
    src: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    out: Annotated[Path, typer.Option("--out", "-o")] = Path("-"),
    count: Annotated[int, typer.Option(min=1, max=100)] = 1,
    tags: Annotated[list[str], typer.Option()] = [],          # repeatable
    mode: Annotated[str, typer.Option()] = "safe",
    token: Annotated[str, typer.Option(envvar="MYCLI_TOKEN")] = "",
    password: Annotated[str, typer.Option(prompt=True, hide_input=True)] = "",
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
):
    ...
```

`Path` with `exists=True` validates like Click's `click.Path`. Use an `Enum` for a fixed choice set:

```python
from enum import Enum

class Mode(str, Enum):
    fast = "fast"
    safe = "safe"

@app.command()
def run(mode: Annotated[Mode, typer.Option()] = Mode.safe):
    typer.echo(mode.value)
```

Raise `typer.BadParameter("message")` for invalid input and `raise typer.Exit(code=1)` to exit with a status. `typer.confirm(...)` and `typer.prompt(...)` mirror Click's prompts.

## Subcommand Apps

Compose CLIs by mounting sub-apps with `add_typer`. Each sub-app is its own `Typer()` with its own commands.

```python
app = typer.Typer()
db = typer.Typer()
app.add_typer(db, name="db", help="Database commands.")

@db.command()
def create(name: str):
    """Create a database."""
    typer.echo(f"Creating {name}")

# Invoked as: uv run mycli db create mydb
```

Share state across subcommands with a callback that stores an object on the context:

```python
@app.callback()
def main(ctx: typer.Context, verbose: bool = False):
    ctx.obj = {"verbose": verbose}

@db.command()
def status(ctx: typer.Context):
    if ctx.obj["verbose"]:
        typer.echo("verbose on")
```

The `@app.callback()` runs before any subcommand — use it for group-level options and setup. `typer.Context` is Click's context (`ctx.obj`, `ctx.invoke`, `ctx.exit`).

## Progress and Rich Output

`typer.echo` and `typer.secho` wrap Click's equivalents:

```python
typer.echo("plain")
typer.secho("Success", fg=typer.colors.GREEN, bold=True)
typer.secho("Error", fg=typer.colors.RED, err=True)
```

Typer bundles `rich` for progress and formatting. Use `rich.progress` for progress bars:

```python
from rich.progress import track

for item in track(items, description="Processing..."):
    handle(item)
```

For full control (columns, multiple bars, unknown length):

```python
from rich.progress import Progress

with Progress() as progress:
    task = progress.add_task("Downloading", total=len(chunks))
    for chunk in chunks:
        write(chunk)
        progress.advance(task)
```

`rich` also gives `rich.print`, tables, and syntax highlighting; Typer renders `--help` through it automatically.

## Testing

Typer ships a `CliRunner` (re-exported from Click) via `typer.testing`.

```python
from typer.testing import CliRunner
from my_package.cli import app

runner = CliRunner()

def test_greet():
    result = runner.invoke(app, ["Alice", "--count", "2"])
    assert result.exit_code == 0
    assert result.output.count("Alice") == 2

def test_subcommand():
    result = runner.invoke(app, ["db", "create", "mydb"])
    assert result.exit_code == 0
    assert "Creating mydb" in result.output

def test_prompt():
    result = runner.invoke(app, ["login"], input="secret\n")
    assert result.exit_code == 0

def test_error():
    result = runner.invoke(app, ["process", "missing.txt"])
    assert result.exit_code != 0
```

`result` carries the same `exit_code`, `output`, and `exception` fields as Click's runner. Pass `mix_stderr=False` to `CliRunner()` to read `result.stderr` separately.

## Click vs Typer — Which to Choose

Both are solid; Typer is a thin layer over Click, so they share runtime, context, and testing.

**Typer** when the CLI mirrors typed Python functions and you want minimal boilerplate, inferred `--help`, and `rich` output for free. Best for new tools and teams already using type hints.

**Click** when you need maximum control or mature third-party plugins, are targeting an older/established codebase, or want zero magic between the decorator and the parser. Every Click pattern is reachable from Typer via `typer.Context` and Click objects, so choosing Typer does not close the door on Click's internals.

Do not mix both frameworks for one CLI's top-level app. Pick one entry point; drop to Click APIs from within Typer only when a specific feature requires it.
