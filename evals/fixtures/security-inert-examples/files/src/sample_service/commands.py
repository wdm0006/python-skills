"""INERT EVALUATION EXAMPLE: shell command built from a parameter."""
import subprocess


def archive(directory: str):
    # Unsafe on purpose: shell=True with an interpolated argument.
    return subprocess.run(f"tar -czf backup.tgz {directory}", shell=True)
