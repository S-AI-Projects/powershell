#!/usr/bin/env python3
"""Validate the "files" object of an exercise's .meta/config.json.

Usage: python3 tools/course_checks/r09-t018.py [EXERCISE_DIR]   (default: connect)
Each declared path must be relative, free of parent traversal, inside the exercise
directory, and an existing file. The declared test, example and solution files must
also agree with how bin/run-tests.ps1 finds them (by file name pattern).
Exit code 0 when valid, 1 otherwise. Each problem prints: ERROR <CODE> <key>: <detail>
"""
import json, sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / "exercises" / "practice" / "connect"
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
    files = json.loads(cfg.read_text()).get("files")
    if not isinstance(files, dict):
        return [("NO_FILES_OBJECT", "files", "")]
    errors = [("MISSING_KEY", k, "") for k in REQUIRED if not files.get(k)]
    for key, paths in files.items():
        if not isinstance(paths, list):
            errors.append(("BAD_TYPE", key, repr(paths)))
            continue
        for p in paths:
            errors.extend(check_path(ex, key, p))
    return errors


def runner_agreement(ex):
    ex = Path(ex).resolve()
    files = json.loads((ex / ".meta" / "config.json").read_text())["files"]
    rel = lambda ps: sorted(p.relative_to(ex).as_posix() for p in ps)
    found = {"test": rel(ex.rglob("*.tests.ps1")),
             "example": rel((ex / ".meta").rglob("*.example.ps1"))}
    errors = []
    for key, want in found.items():
        if sorted(files.get(key, [])) != want:
            errors.append(("RUNNER_MISMATCH", key, f"config {files.get(key)} vs found {want}"))
    if len(found["example"]) == 1:
        derived = Path(found["example"][0]).name.replace("example.", "")
        if files.get("solution") != [derived]:
            errors.append(("RUNNER_MISMATCH", "solution", f"config {files.get('solution')} vs derived {[derived]}"))
    return errors


def main(argv):
    ex = Path(argv[1]) if len(argv) > 1 else DEFAULT
    errors = validate(ex) or runner_agreement(ex)
    for code, key, detail in errors:
        print(f"ERROR {code} {key}: {detail}")
    if not errors:
        print(f"OK {ex}: declared files resolve inside the exercise and match the runner")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
