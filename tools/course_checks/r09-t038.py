#!/usr/bin/env python3
"""Validate exercise file paths declared in .meta/config.json."""

from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import sys


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EXERCISE = ROOT / "exercises/practice/isbn-verifier"
REQUIRED_ROLES = ("solution", "test", "example")


def validate(exercise_root: Path, config_path: Path) -> dict[str, object]:
    root = exercise_root.resolve()
    config_file = config_path.resolve()
    try:
        config_file.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"config path escapes exercise root: {config_file}") from exc
    if not config_file.is_file():
        raise FileNotFoundError(f"config file does not exist: {config_file}")

    try:
        config = json.loads(config_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"cannot parse config JSON: {exc}") from exc
    files = config.get("files")
    if not isinstance(files, dict):
        raise ValueError("config must contain a files object")
    missing_roles = [role for role in REQUIRED_ROLES if role not in files]
    if missing_roles:
        raise ValueError(f"missing required file roles: {', '.join(missing_roles)}")

    resolved: dict[str, list[dict[str, str]]] = {}
    for role, paths in files.items():
        if not isinstance(paths, list) or not paths:
            raise ValueError(f"file role {role!r} must be a non-empty list of paths")
        resolved[role] = []
        for index, value in enumerate(paths):
            if not isinstance(value, str) or not value:
                raise ValueError(f"file role {role!r} entry {index} must be a non-empty string")
            relative = Path(value)
            windows_path = PureWindowsPath(value)
            if relative.is_absolute() or windows_path.is_absolute() or windows_path.drive:
                raise ValueError(f"file role {role!r} path must be relative: {value}")
            candidate = (root / relative).resolve()
            try:
                relpath = candidate.relative_to(root)
            except ValueError as exc:
                raise ValueError(f"file role {role!r} path escapes exercise root: {value}") from exc
            portable_parts = PurePosixPath(value.replace("\\", "/")).parts
            if ".." in portable_parts:
                raise ValueError(f"file role {role!r} path must not traverse parents: {value}")
            if not candidate.is_file():
                raise FileNotFoundError(f"file role {role!r} file does not exist: {value}")
            resolved[role].append({"declaredPath": value, "relativePath": relpath.as_posix()})

    return {
        "exerciseRoot": str(root),
        "config": config_file.relative_to(root).as_posix(),
        "files": resolved,
        "editorFilesDeclared": "editor" in files,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exercise-root", type=Path, default=DEFAULT_EXERCISE)
    parser.add_argument("--config", type=Path, help="Defaults to <exercise-root>/.meta/config.json")
    args = parser.parse_args()
    config_path = args.config or args.exercise_root / ".meta/config.json"
    try:
        print(json.dumps(validate(args.exercise_root, config_path), indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
