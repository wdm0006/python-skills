#!/usr/bin/env python3
"""Copy a versioned evaluation fixture into a new directory.

Only copies files; nothing from the fixture is executed or installed.
Usage: materialize.py FIXTURE_ID DESTINATION
"""
import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent
EVALS = FIXTURES.parent
ID_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MANIFEST_VERSION = 1


class FixtureError(Exception):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_tree(files_dir: Path) -> dict[str, str]:
    """Map relative POSIX path -> sha256 for every file; reject symlinks."""
    hashes = {}
    for path in sorted(files_dir.rglob("*")):
        if path.is_symlink():
            raise FixtureError(f"symlink in fixture: {path.relative_to(files_dir)}")
        if path.is_file():
            hashes[path.relative_to(files_dir).as_posix()] = sha256_bytes(path.read_bytes())
    return hashes


def tree_digest(hashes: dict[str, str]) -> str:
    text = "".join(f"{name}\0{digest}\n" for name, digest in sorted(hashes.items()))
    return sha256_bytes(text.encode())


def load_manifest(fixture_id: str, root: Path = FIXTURES) -> dict:
    if not isinstance(fixture_id, str) or not ID_PATTERN.fullmatch(fixture_id):
        raise FixtureError(f"unsafe fixture id: {fixture_id!r}")
    manifest_path = root / fixture_id / "fixture.json"
    if not manifest_path.is_file():
        raise FixtureError(f"unknown fixture: {fixture_id}")
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("fixture_version") != MANIFEST_VERSION or manifest.get("id") != fixture_id:
        raise FixtureError(f"bad manifest header for {fixture_id}")
    return manifest


def input_errors(manifest: dict, root: Path = FIXTURES) -> list[str]:
    """Compare the starting files on disk with the recorded hashes."""
    files_dir = root / manifest["id"] / "files"
    try:
        actual = hash_tree(files_dir)
    except FixtureError as exc:
        return [str(exc)]
    recorded = manifest["files"]
    errors = [f"unexpected file: {n}" for n in sorted(set(actual) - set(recorded))]
    errors += [f"missing file: {n}" for n in sorted(set(recorded) - set(actual))]
    errors += [f"hash changed: {n}" for n in sorted(set(actual) & set(recorded)) if actual[n] != recorded[n]]
    if not errors and tree_digest(actual) != manifest["tree_sha256"]:
        errors.append("tree_sha256 does not match files")
    return errors


def prompt_errors(manifest: dict, evals_dir: Path = EVALS) -> list[str]:
    """Check the exact prompt and rubric text still exist in the scenario file."""
    scenario_path = evals_dir / manifest["scenario"]
    if not scenario_path.is_file():
        return [f"scenario file missing: {manifest['scenario']}"]
    scenario = json.loads(scenario_path.read_text())
    errors = []
    if scenario.get("schema_version") != manifest["scenario_schema_version"]:
        errors.append("scenario schema_version differs from the fixture's")
    if scenario.get("skill") != manifest["skill"]:
        errors.append("scenario skill differs from the fixture's")
    if manifest["prompt"] not in scenario.get("positive_prompts", []):
        errors.append(f"prompt not found in positive_prompts: {manifest['prompt']!r}")
    rubric = scenario.get("rubric", [])
    errors += [f"rubric item not found: {item!r}" for item in manifest["rubric_items"] if item not in rubric]
    return errors


def materialize(fixture_id: str, destination: Path, root: Path = FIXTURES) -> dict:
    """Validate everything first, then create destination and copy files."""
    manifest = load_manifest(fixture_id, root)
    errors = input_errors(manifest, root)
    if errors:
        raise FixtureError("fixture inputs invalid: " + "; ".join(errors))
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise FixtureError(f"destination already exists: {destination}")
    if not destination.parent.is_dir():
        raise FixtureError(f"destination parent is not a directory: {destination.parent}")
    source = root / fixture_id / "files"
    destination.mkdir()
    for name in manifest["files"]:
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / name, target)
    return manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Copy an evaluation fixture into a new directory.")
    parser.add_argument("fixture_id")
    parser.add_argument("destination", type=Path)
    args = parser.parse_args(argv)
    try:
        manifest = materialize(args.fixture_id, args.destination)
    except FixtureError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"fixture: {manifest['id']}")
    print(f"tree_sha256: {manifest['tree_sha256']}")
    print(f"destination: {args.destination}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
