#!/usr/bin/env python3
"""Bump version number in project files.

Usage:
    uv run python scripts/bump_version.py patch      # 1.2.3 -> 1.2.4
    uv run python scripts/bump_version.py minor      # 1.2.3 -> 1.3.0
    uv run python scripts/bump_version.py major      # 1.2.3 -> 2.0.0
    uv run python scripts/bump_version.py 1.5.0      # Set a specific version
"""

import argparse
import re
import sys
from datetime import date
from pathlib import Path

BUMP_TYPES = ("major", "minor", "patch")


def get_current_version(project_path: Path) -> str | None:
    """Get current version from pyproject.toml."""
    pyproject = project_path / "pyproject.toml"
    if not pyproject.exists():
        return None

    content = pyproject.read_text()
    match = re.search(r'version\s*=\s*"([^"]+)"', content)
    return match.group(1) if match else None


def parse_version(version: str) -> tuple[int, int, int]:
    """Parse a semantic version string into a (major, minor, patch) tuple."""
    parts = version.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise ValueError(f"Invalid version format: {version!r} (expected MAJOR.MINOR.PATCH)")
    return int(parts[0]), int(parts[1]), int(parts[2])


def bump_version(current: str, spec: str) -> str:
    """Calculate the new version from a bump type (major/minor/patch) or explicit version."""
    if spec in BUMP_TYPES:
        major, minor, patch = parse_version(current)
        if spec == "major":
            return f"{major + 1}.0.0"
        if spec == "minor":
            return f"{major}.{minor + 1}.0"
        return f"{major}.{minor}.{patch + 1}"

    # Otherwise treat spec as an explicit version; validate its format.
    parse_version(spec)
    return spec


def update_file(
    file_path: Path,
    pattern: str,
    replacement: str,
    dry_run: bool = False,
) -> bool:
    """Update version in a file using regex."""
    if not file_path.exists():
        return False

    content = file_path.read_text()
    new_content = re.sub(pattern, replacement, content)

    if content == new_content:
        return False

    if not dry_run:
        file_path.write_text(new_content)

    return True


def update_version(
    project_path: Path,
    new_version: str,
    dry_run: bool = False,
) -> list[str]:
    """Update version in all relevant files."""
    updated_files = []

    # pyproject.toml
    pyproject = project_path / "pyproject.toml"
    if update_file(
        pyproject,
        r'version\s*=\s*"[^"]+"',
        f'version = "{new_version}"',
        dry_run,
    ):
        updated_files.append(str(pyproject))

    # Top-level package __init__.py (src/<package>/__init__.py), not every subpackage.
    src = project_path / "src"
    if src.is_dir():
        for init_file in src.glob("*/__init__.py"):
            if update_file(
                init_file,
                r'__version__\s*=\s*"[^"]+"',
                f'__version__ = "{new_version}"',
                dry_run,
            ):
                updated_files.append(str(init_file))

    # setup.cfg (legacy; match only the metadata version line)
    setup_cfg = project_path / "setup.cfg"
    if update_file(
        setup_cfg,
        r'(?m)^version\s*=\s*[\d.]+\s*$',
        f'version = {new_version}',
        dry_run,
    ):
        updated_files.append(str(setup_cfg))

    return updated_files


def update_changelog(
    project_path: Path,
    new_version: str,
    dry_run: bool = False,
) -> bool:
    """Insert a new release heading under the [Unreleased] section of the changelog."""
    changelog = project_path / "CHANGELOG.md"
    if not changelog.exists():
        return False

    content = changelog.read_text()
    today = date.today().isoformat()

    # Match the [Unreleased] heading only (not the [Unreleased]: link reference
    # at the bottom of the file), and insert the new version heading after it.
    new_content = re.sub(
        r'(?m)^(##\s*\[Unreleased\].*)$',
        rf'\1\n\n## [{new_version}] - {today}',
        content,
        count=1,
    )

    if content == new_content:
        return False

    if not dry_run:
        changelog.write_text(new_content)

    return True


def main():
    parser = argparse.ArgumentParser(description="Bump version in project files")
    parser.add_argument(
        "bump_type",
        nargs="?",
        metavar="major|minor|patch|X.Y.Z",
        help="major, minor, patch, or an explicit version like 1.2.3",
    )
    parser.add_argument(
        "--version", "-v",
        help="Set a specific version (e.g., 1.2.3)",
    )
    parser.add_argument(
        "--project", "-p",
        type=Path,
        default=Path("."),
        help="Project path (default: current directory)",
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Show what would be changed without making changes",
    )
    parser.add_argument(
        "--changelog",
        action="store_true",
        help="Also update CHANGELOG.md",
    )
    parser.add_argument(
        "--allow-downgrade",
        action="store_true",
        help="Permit setting a version lower than the current one",
    )

    args = parser.parse_args()
    project_path = args.project.resolve()

    spec = args.version or args.bump_type
    if not spec:
        parser.print_help()
        sys.exit(1)

    current = get_current_version(project_path)
    if not current:
        print("Error: Could not find version in pyproject.toml")
        sys.exit(1)

    try:
        new_version = bump_version(current, spec)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    if parse_version(new_version) < parse_version(current) and not args.allow_downgrade:
        print(
            f"Error: {new_version} is lower than the current {current}. "
            "Pass --allow-downgrade to override."
        )
        sys.exit(1)

    print(f"Version: {current} -> {new_version}")

    if args.dry_run:
        print("\n[DRY RUN] Would update:")
    else:
        print("\nUpdating:")

    updated = update_version(project_path, new_version, args.dry_run)
    for f in updated:
        print(f"  - {f}")

    if args.changelog:
        if update_changelog(project_path, new_version, args.dry_run):
            print(f"  - {project_path / 'CHANGELOG.md'}")

    if not updated:
        print("  No files updated")

    if args.dry_run:
        print("\n[DRY RUN] No changes made")
    else:
        print(f"\nVersion bumped to {new_version}")
        print("\nNext steps:")
        print("  git add -A")
        print(f'  git commit -m "Bump version to {new_version}"')
        print(f'  git tag -a v{new_version} -m "Release v{new_version}"')
        print("  git push origin main --tags")


if __name__ == "__main__":
    main()
