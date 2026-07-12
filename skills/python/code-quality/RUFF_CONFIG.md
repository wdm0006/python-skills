# Ruff Configuration Reference

## Comprehensive Configuration

```toml
[tool.ruff]
line-length = 88
target-version = "py310"

[tool.ruff.lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # Pyflakes
    "I",      # isort
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "UP",     # pyupgrade
    "ARG",    # flake8-unused-arguments
    "SIM",    # flake8-simplify
    "TCH",    # flake8-type-checking
    "PTH",    # flake8-use-pathlib
    "ERA",    # eradicate (commented code)
    "PL",     # pylint
    "RUF",    # ruff-specific
]
ignore = [
    "E501",    # line too long (formatter handles)
    "PLR0913", # too many arguments
    "PLR2004", # magic value comparison
]

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["S101", "ARG001", "PLR2004"]
"__init__.py" = ["F401"]  # unused imports OK in __init__

[tool.ruff.lint.isort]
known-first-party = ["my_library"]
force-single-line = true

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

## Rule Categories

| Code | Category | Description |
|------|----------|-------------|
| E, W | pycodestyle | PEP 8 style |
| F | Pyflakes | Logical errors |
| I | isort | Import sorting |
| B | flake8-bugbear | Bug patterns |
| C4 | comprehensions | Simplify comprehensions |
| UP | pyupgrade | Modern syntax |
| S | bandit | Security |
| ARG | unused-arguments | Unused params |
| SIM | simplify | Code simplification |

## Commands

```bash
ruff check src tests           # Lint
ruff check --fix src tests     # Lint + autofix
ruff format src tests          # Format
ruff check --select=I --fix .  # Fix imports only
```
