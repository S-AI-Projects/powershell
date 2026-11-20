#!/usr/bin/env python3
"""Check the Minesweeper canonical metadata and maintained Pester source."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib


ROOT = Path(__file__).resolve().parents[2]
EXERCISE_REL = Path("exercises/practice/minesweeper")
EXPECTED_CASES = {
    "0c5ec4bd-dea7-4138-8651-1203e1cb9f44": {
        "description": "no rows",
        "input": "@()",
        "expected": "null or empty result",
    },
    "650ac4c0-ad6b-4b41-acde-e4ea5852c3b8": {
        "description": "no columns",
        "input": '@("")',
        "expected": '[""] (one row containing an empty string)',
    },
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def track_ignore(_directory: str, names: list[str]) -> set[str]:
    ignored = {".git", "work", "__pycache__", ".pytest_cache", ".venv"}
    return {name for name in names if name in ignored}


def read_catalog(exercise: Path) -> tuple[dict[str, dict[str, object]], bytes]:
    path = exercise / ".meta/tests.toml"
    raw = path.read_bytes()
    return tomllib.loads(raw.decode("utf-8")), raw


def get_configlet(root: Path) -> Path:
    candidates = [root / "bin/configlet"]
    found = shutil.which("configlet")
    if found:
        candidates.append(Path(found))
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError("configlet is missing; run `bash bin/fetch-configlet` from the track root first")


def run_sync(configlet: Path, track: Path, cache: Path, offline: bool) -> dict[str, object]:
    cache.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["XDG_CACHE_HOME"] = str(cache)
    command = [str(configlet), "--track-dir", str(track), "sync", "--tests", "include", "--update", "--yes"]
    if offline:
        command.append("--offline")
    result = subprocess.run(command, cwd=track, env=env, text=True, capture_output=True, check=False, timeout=240)
    recorded_command = ["configlet", "--track-dir", "<temporary-track-copy>", *command[3:]]
    return {
        "command": " ".join(recorded_command),
        "exitCode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "work/R09-T032/generation.json")
    args = parser.parse_args()
    output = args.output.resolve()
    evidence: dict[str, object] = {
        "status": "failed",
        "exercise": str(EXERCISE_REL),
        "configletVersion": None,
        "caseCountBefore": None,
        "caseCountAfter": None,
        "selectedCases": EXPECTED_CASES,
        "pesterSuite": "Minesweeper test cases",
        "pesterCaseCount": None,
        "exerciseTemplates": [],
        "runs": [],
        "testFileUnchanged": False,
        "testFileHashes": [],
        "caseCatalogUnchanged": False,
        "timestampNormalization": "none; the maintained Pester source has no generated timestamp",
    }

    try:
        exercise = ROOT / EXERCISE_REL
        catalog_before, catalog_bytes = read_catalog(exercise)
        evidence["caseCountBefore"] = len(catalog_before)
        for case_id, expected in EXPECTED_CASES.items():
            case = catalog_before.get(case_id)
            if not isinstance(case, dict) or case.get("description") != expected["description"]:
                raise AssertionError(f"Canonical case {case_id} does not match {expected['description']!r}")

        pester_path = exercise / "Minesweeper.tests.ps1"
        pester_source = pester_path.read_bytes()
        pester_text = pester_source.decode("utf-8")
        if 'Describe "Minesweeper test cases"' not in pester_text:
            raise AssertionError("Expected the maintained Pester suite title")
        required_snippets = [
            'It "no rows"',
            'Get-Annotate -Minefield @()',
            'Should -BeNullOrEmpty',
            'It "no columns"',
            'Get-Annotate -Minefield @("")',
            '$want = @("")',
            'Should -BeExactly $want',
        ]
        missing = [snippet for snippet in required_snippets if snippet not in pester_text]
        if missing:
            raise AssertionError(f"Pester source is missing required case evidence: {missing}")
        evidence["pesterCaseCount"] = len(re.findall(r"(?m)^\s*It\s+\"", pester_text))

        template_files = []
        for path in exercise.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".j2", ".jinja", ".jinja2", ".tpl"}:
                template_files.append(str(path.relative_to(ROOT)))
        evidence["exerciseTemplates"] = template_files
        if template_files:
            raise AssertionError(f"Unexpected per-exercise test templates found: {template_files}")

        configlet = get_configlet(ROOT)
        version = subprocess.run([str(configlet), "--version"], text=True, capture_output=True, check=False)
        if version.returncode != 0:
            raise RuntimeError(f"Could not read configlet version: {version.stderr.strip()}")
        evidence["configletVersion"] = version.stdout.strip()

        with tempfile.TemporaryDirectory(prefix="minesweeper-R09-T032-") as temporary:
            base = Path(temporary)
            cache = base / "cache"
            runs: list[dict[str, object]] = []
            test_hashes: list[str] = []
            catalog_hashes: list[str] = []
            for index in range(2):
                track_copy = base / f"track-{index + 1}"
                shutil.copytree(ROOT, track_copy, ignore=track_ignore)
                copied_exercise = track_copy / EXERCISE_REL
                copied_tests = copied_exercise / "Minesweeper.tests.ps1"
                before_tests = copied_tests.read_bytes()
                result = run_sync(configlet, track_copy, cache, offline=index == 1)
                runs.append(result)
                if result["exitCode"] != 0:
                    raise RuntimeError(f"configlet sync run {index + 1} exited {result['exitCode']}")
                after_tests = copied_tests.read_bytes()
                test_hashes.append(sha256(after_tests))
                if after_tests != before_tests or after_tests != pester_source:
                    raise AssertionError(f"configlet sync run {index + 1} changed Minesweeper.tests.ps1")
                copied_catalog, copied_catalog_bytes = read_catalog(copied_exercise)
                catalog_hashes.append(sha256(copied_catalog_bytes))
                if copied_catalog_bytes != catalog_bytes:
                    raise AssertionError(f"configlet sync run {index + 1} changed Minesweeper tests.toml")
                if set(copied_catalog) != set(catalog_before):
                    raise AssertionError(f"configlet sync run {index + 1} dropped or added Minesweeper cases")
                for case_id, expected in EXPECTED_CASES.items():
                    case = copied_catalog.get(case_id)
                    if not isinstance(case, dict) or case.get("description") != expected["description"]:
                        raise AssertionError(f"configlet sync run {index + 1} changed case {case_id}")

            if len(set(test_hashes)) != 1:
                raise AssertionError("Two fresh configlet sync runs produced different Pester test files")
            evidence["runs"] = runs
            evidence["testFileHashes"] = test_hashes
            evidence["testsTomlHashesAfter"] = catalog_hashes
            evidence["testFileUnchanged"] = True
            evidence["caseCatalogUnchanged"] = True
            evidence["caseCountAfter"] = len(catalog_before)

        evidence["status"] = "passed"
        print(f"PASS: configlet {evidence['configletVersion']}; two fresh syncs preserved {evidence['pesterCaseCount']} Pester cases and all {evidence['caseCountAfter']} metadata cases.")
        return 0
    except Exception as exc:
        evidence["error"] = f"{type(exc).__name__}: {exc}"
        print(evidence["error"], file=sys.stderr)
        return 1
    finally:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
