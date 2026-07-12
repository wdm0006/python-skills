# Click Patterns

Advanced Click usage. Run everything through `uv` (`uv add click`, `uv run mycli ...`).

## Contents

- Command Groups and Subcommands
- Arguments vs Options
- Shared State with Context
- Prompts
- Progress Bars
- Colored Output
- Shell Completion
- Testing with CliRunner

## Command Groups and Subcommands

A `group` dispatches to `command`s. Nest groups for multi-level CLIs.

```python
import click

@click.group()
def cli():
    """Top-level tool."""

@cli.group()
def db():
    """Database commands."""

@db.command()
@click.argument('name')
def create(name):
    """Create a database."""
    click.echo(f"Creating {name}")

# Invoked as: uv run mycli db create mydb
```

Register a command onto multiple groups, or add one built elsewhere:

```python
cli.add_command(create, name='new')          # alias
cli.add_command(other_module.build)           # command from another file
```

Options on the group apply to every subcommand and run before it:

```python
@click.group()
@click.option('--config', type=click.Path(), help='Config file path')
def cli(config):
    ...
```

## Arguments vs Options

**Arguments** are positional and required by default; **options** are named flags. Prefer options for anything not obviously positional.

```python
@cli.command()
@click.argument('src')                                  # required positional
@click.argument('dst', required=False)                  # optional positional
@click.argument('files', nargs=-1)                      # variadic -> tuple
@click.option('--count', '-c', default=1, type=int, show_default=True)
@click.option('--name', '-n', multiple=True)            # repeatable -> tuple
@click.option('--force/--no-force', default=False)      # boolean flag pair
@click.option('--verbose', '-v', count=True)            # -vvv -> 3
@click.option('--mode', type=click.Choice(['fast', 'safe']), default='safe')
@click.option('--password', prompt=True, hide_input=True)
@click.option('--token', envvar='MYCLI_TOKEN')          # falls back to env var
def run(src, dst, files, count, name, force, verbose, mode, password, token):
    ...
```

Useful types: `click.Path(exists=True, dir_okay=False)`, `click.File('r')`, `click.INT`, `click.FLOAT`, `click.DateTime()`, `click.IntRange(0, 100)`.

Reject bad input with the framework's errors so exit codes and stderr are handled:

```python
if count < 1:
    raise click.BadParameter('must be >= 1', param_hint='--count')
raise click.UsageError('src and dst must differ')
```

## Shared State with Context

`click.Context` carries state between a group and its subcommands. Use `ctx.obj` for a shared object; `ensure_object` initializes it lazily.

```python
class State:
    def __init__(self):
        self.verbose = False

@click.group()
@click.option('--verbose', '-v', is_flag=True)
@click.pass_context
def cli(ctx, verbose):
    ctx.ensure_object(State)
    ctx.obj.verbose = verbose

@cli.command()
@click.pass_context
def status(ctx):
    if ctx.obj.verbose:
        click.echo('verbose on')
```

`pass_obj` skips straight to `ctx.obj`; `make_pass_decorator` gives a typed decorator:

```python
pass_state = click.make_pass_decorator(State, ensure=True)

@cli.command()
@pass_state
def status(state):
    click.echo(state.verbose)
```

Other context uses: `ctx.invoke(other_cmd, arg=1)` to call another command, `ctx.exit(2)` to exit with a code, and `ctx.get_help()` / `ctx.abort()`.

## Prompts

```python
name = click.prompt('Name')
count = click.prompt('Count', default=1, type=int)
secret = click.prompt('Password', hide_input=True, confirmation_prompt=True)

if click.confirm('Continue?', abort=True):   # abort=True exits on "no"
    ...

# Open the editor / pager for large input
message = click.edit('# initial text')
click.echo_via_pager(long_text)
```

Prefer the `prompt=` option kwarg over calling `click.prompt` inside the body — it integrates with `--help` and lets non-interactive callers pass the value directly.

## Progress Bars

```python
with click.progressbar(items, label='Processing') as bar:
    for item in bar:
        handle(item)

# Unknown-length / manual updates
with click.progressbar(length=total, label='Downloading') as bar:
    for chunk in stream:
        write(chunk)
        bar.update(len(chunk))

# Show per-item detail
with click.progressbar(items, item_show_func=lambda i: i.name if i else '') as bar:
    for item in bar:
        handle(item)
```

Progress bars render to stderr and auto-hide when output is not a TTY, so piped output stays clean.

## Colored Output

`click.echo` is the portable print (handles encoding, stderr, and strips color when redirected). `click.secho` adds styling.

```python
click.echo('plain')
click.echo('to stderr', err=True)
click.secho('Success', fg='green', bold=True)
click.secho('Error', fg='red', err=True)
click.echo(click.style('mixed ', fg='cyan') + 'normal')
```

Colors: `black red green yellow blue magenta cyan white` plus `bright_*`. Styling auto-disables on non-TTYs; force with `color=True`. On Windows, call `click.echo` (not `print`) so ANSI codes are translated.

## Shell Completion

Completion is built in. Generate and source the script for the user's shell (name the env var `_<UPPERCASED_PROG>_COMPLETE`):

```bash
# bash -> ~/.bashrc
_MYCLI_COMPLETE=bash_source uv run mycli > ~/.mycli-complete.bash
echo '. ~/.mycli-complete.bash' >> ~/.bashrc

# zsh, fish
_MYCLI_COMPLETE=zsh_source uv run mycli > ~/.mycli-complete.zsh
_MYCLI_COMPLETE=fish_source uv run mycli > ~/.config/fish/completions/mycli.fish
```

Provide dynamic completions with `shell_complete`:

```python
def complete_env(ctx, param, incomplete):
    return [e for e in ('dev', 'staging', 'prod') if e.startswith(incomplete)]

@cli.command()
@click.option('--env', shell_complete=complete_env)
def deploy(env):
    ...
```

Return `click.shell_completion.CompletionItem(value, help='...')` objects for richer entries.

## Testing with CliRunner

`CliRunner` invokes commands in-process and captures output and exit code.

```python
from click.testing import CliRunner
from mypackage.cli import cli

def test_create():
    runner = CliRunner()
    result = runner.invoke(cli, ['db', 'create', 'mydb'])
    assert result.exit_code == 0
    assert 'Creating mydb' in result.output

def test_stdin():
    runner = CliRunner()
    result = runner.invoke(cli, ['run', '-'], input='data\n')
    assert result.exit_code == 0

def test_prompt():
    runner = CliRunner()
    result = runner.invoke(cli, ['login'], input='alice\nsecret\n')
    assert result.exit_code == 0

def test_error():
    runner = CliRunner()
    result = runner.invoke(cli, ['run', '--count', '0'])
    assert result.exit_code != 0
    assert isinstance(result.exception, SystemExit)
```

Isolate filesystem side effects and inject `ctx.obj` when needed:

```python
def test_writes_file():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ['build', 'out.txt'])
        assert result.exit_code == 0
        with open('out.txt') as f:
            assert f.read()

# Pass a pre-built context object
runner.invoke(cli, ['status'], obj=State())
```

By default stderr is merged into `result.output`. Pass `mix_stderr=False` to `CliRunner()` and read `result.stderr` separately when a test must distinguish the streams.
