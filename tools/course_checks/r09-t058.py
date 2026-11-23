#!/usr/bin/env python3
"""Validate the "files" object of an exercise's .meta/config.json.

Usage: python3 tools/course_checks/r09-t058.py [EXERCISE_DIR]   (default: series)
Each declared path must be relative, free of parent traversal, inside the exercise
directory, and an existing file. The declared test, example and solution files must
also agree with how bin/run-tests.ps1 finds them (by file name pattern).
Exit code 0 when valid, 1 otherwise. Each problem prints: ERROR <CODE> <key>: <detail>
"""
import json
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / "exercises" / "practice" / "series"
REQUIRED = ("solution", "test", "example")


def check_path(ex, key, p):
    if not isinstance(p, str) or not p:
        return [("BAD_PATH", key, repr(p))]
    pp = PurePosixPath(p)
    if pp.is_absolute() or ".." in pp.parts:
        return [("OUTSIDE_EXERCISE", key, p)]
    target = (ex / p).resolve()
    try:
        target.relative_to(ex)
    except ValueError:
        return [("OUTSIDE_EXERCISE", key, p)]
    if not target.is_file():
        return [("MISSING_FILE", key, p)]
    return []


def validate(ex):
    ex = Path(ex).resolve()
    cfg = ex / ".meta" / "config.json"
    if not cfg.is_file():
        return [("NO_CONFIG", "config", ".meta/config.json")]
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
    except Exception as e:
        return [("INVALID_JSON", "config", str(e))]
    files = data.get("files")
    if not isinstance(files, dict):
        return [("NO_FILES_OBJECT", "files", "files key missing or not a dict")]

    errors = []
    for req in REQUIRED:
        val = files.get(req)
        if not isinstance(val, list) or len(val) == 0:
            errors.append(("MISSING_KEY", req, f"required key '{req}' missing or empty"))
        else:
            for p in val:
                errors.extend(check_path(ex, req, p))

    for k, val in files.items():
        if k in REQUIRED or not isinstance(val, list):
            continue
        for p in val:
            errors.extend(check_path(ex, k, p))

    if not errors:
        name = ex.name.replace("-", "")
        # Check runner agreement
        tests = files.get("test", [])
        if not any(PurePosixPath(p).name.lower() == f"{name}.tests.ps1".lower() for p in tests):
            errors.append(("RUNNER_MISMATCH", "test", f"expected {name}.tests.ps1 in declared test files"))
        examples = files.get("example", [])
        if not any(PurePosixPath(p).name.lower() == f"{name}.example.ps1".lower() for p in examples):
            errors.append(("RUNNER_MISMATCH", "example", f"expected {name}.example.ps1 in declared example files"))
        solutions = files.get("solution", [])
        if not any(PurePosixPath(p).name.lower() == f"{name}.ps1".lower() for p in solutions):
            errors.append(("RUNNER_MISMATCH", "solution", f"expected {name}.ps1 in declared solution files"))

    return errors


def main():
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    errors = validate(target)
    for code, key, detail in errors:
        print(f"ERROR {code} {key}: {detail}")
    if errors:
        sys.exit(1)
    print(f"OK: metadata valid for {target}")
    sys.exit(0)


if __name__ == "__main__":
    main()
