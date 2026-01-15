#!/usr/bin/env python3
"""Bump version number in project files.

Usage:
    python bump_version.py patch   # 1.2.3 -> 1.2.4
    python bump_version.py minor   # 1.2.3 -> 1.3.0
    python bump_version.py major   # 1.2.3 -> 2.0.0
    python bump_version.py 1.5.0   # Set specific version
"""

import argparse
import re
import sys
from pathlib import Path


def get_current_version(project_path: Path) -> str | None:
    """Get current version from pyproject.toml."""
    pyproject = project_path / "pyproject.toml"
    if not pyproject.exists():
        return None

    content = pyproject.read_text()
    match = re.search(r'version\s*=\s*"([^"]+)"', content)
    return match.group(1) if match else None


def parse_version(version: str) -> tuple[int, int, int]:
    """Parse version string into tuple."""
    parts = version.split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid version format: {version}")
    return int(parts[0]), int(parts[1]), int(parts[2])


def bump_version(current: str, bump_type: str) -> str:
    """Calculate new version based on bump type."""
    major, minor, patch = parse_version(current)

    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    elif bump_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    else:
        # Assume it's a specific version
        try:
            parse_version(bump_type)  # Validate format
            return bump_type
        except ValueError:
            raise ValueError(f"Unknown bump type: {bump_type}")


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

    # __init__.py files
    for init_file in project_path.rglob("src/**/__init__.py"):
        if update_file(
            init_file,
            r'__version__\s*=\s*"[^"]+"',
            f'__version__ = "{new_version}"',
            dry_run,
        ):
            updated_files.append(str(init_file))

    # setup.cfg (if exists)
    setup_cfg = project_path / "setup.cfg"
    if update_file(
        setup_cfg,
        r'version\s*=\s*[\d.]+',
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
    """Update changelog with new version and date."""
    from datetime import date

    changelog = project_path / "CHANGELOG.md"
    if not changelog.exists():
        return False

    content = changelog.read_text()
    today = date.today().isoformat()

    # Replace [Unreleased] with new version
    new_content = re.sub(
        r'\[Unreleased\]',
        f'[Unreleased]\n\n## [{new_version}] - {today}',
        content,
        count=1,
    )

    if content == new_content:
        return False

    if not dry_run:
        changelog.write_text(new_content)

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Bump version in project files"
    )
    parser.add_argument(
        "bump_type",
        choices=["major", "minor", "patch"],
        nargs="?",
        help="Type of version bump (or specific version like 1.2.3)",
    )
    parser.add_argument(
        "--version", "-v",
        help="Set specific version (e.g., 1.2.3)",
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

    args = parser.parse_args()
    project_path = args.project.resolve()

    # Get bump type or version
    if args.version:
        bump_type = args.version
    elif args.bump_type:
        bump_type = args.bump_type
    else:
        parser.print_help()
        sys.exit(1)

    # Get current version
    current = get_current_version(project_path)
    if not current:
        print("Error: Could not find version in pyproject.toml")
        sys.exit(1)

    # Calculate new version
    try:
        new_version = bump_version(current, bump_type)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    print(f"Version: {current} -> {new_version}")

    if args.dry_run:
        print("\n[DRY RUN] Would update:")
    else:
        print("\nUpdating:")

    # Update version files
    updated = update_version(project_path, new_version, args.dry_run)
    for f in updated:
        print(f"  - {f}")

    # Update changelog if requested
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
