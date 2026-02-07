"""Utility to generate a simple dependency lockfile from requirements.txt.

Note: This is a lightweight placeholder for CI workflows. In production,
you should use a real pinning tool (e.g. pip-compile) or your preferred
dependency management solution to produce a true, reproducible lockfile.
"""
from __future__ import annotations

import pathlib
import sys


def main():
    root = pathlib.Path(__file__).resolve().parents[1]
    req = root / "config" / "python" / "requirements.txt"
    if not req.exists():
        print("requirements.txt not found; aborting lock generation.")
        return 1
    lock_path = req.with_suffix(".lock")
    with req.open("r", encoding="utf-8") as f_in:
        content = f_in.read()
    with lock_path.open("w", encoding="utf-8") as f_out:
        f_out.write(content)
    print(f"Lockfile generated at: {lock_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
