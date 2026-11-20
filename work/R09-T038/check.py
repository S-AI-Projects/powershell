#!/usr/bin/env python3
"""Validate ISBN exercise paths and run the reference Pester suite in a temp copy."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[2]
EXERCISE = ROOT / "exercises/practice/isbn-verifier"
PATH_CHECKER = ROOT / "tools/course_checks/r09-t038.py"


def ps_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def pester_runner(solution_path: str, test_path: str, output_path: str) -> str:
    return f'''$ErrorActionPreference = "Stop"
$solutionPath = {ps_literal(solution_path)}
$testPath = {ps_literal(test_path)}
$outputPath = {ps_literal(output_path)}
. $solutionPath
$result = Invoke-Pester -Path $testPath -PassThru -Output Detailed
$valid = Test-Isbn -Isbn "3-598-21508-8"
$invalidCheckDigit = Test-Isbn -Isbn "3-598-21508-9"
$summary = [ordered]@{{
    totalCount = [int]$result.TotalCount
    passedCount = [int]$result.PassedCount
    failedCount = [int]$result.FailedCount
    skippedCount = [int]$result.SkippedCount
    testNames = @($result.Tests | ForEach-Object {{ $_.Name }})
    probes = @(
        [ordered]@{{ input = "3-598-21508-8"; expected = $true; actual = [bool]$valid }}
        [ordered]@{{ input = "3-598-21508-9"; expected = $false; actual = [bool]$invalidCheckDigit }}
    )
}}
$summary | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $outputPath -Encoding utf8
if ($result.TotalCount -eq 0) {{ exit 2 }}
if ($result.FailedCount -ne 0) {{ exit 1 }}
if (-not $valid -or $invalidCheckDigit) {{ exit 3 }}
exit 0
'''


def run_child(command: list[str], cwd: Path, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False, timeout=timeout)


def create_fixture(base: Path, name: str, original_config: dict, mutate_role: str, new_path: str) -> tuple[Path, Path]:
    exercise = base / name
    config_path = exercise / ".meta/config.json"
    config = json.loads(json.dumps(original_config))
    for role_paths in config["files"].values():
        for relative_path in role_paths:
            target = exercise / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("fixture\n", encoding="utf-8")
    config["files"][mutate_role] = [new_path]
    if name == "outside-exercise-path":
        (base / "outside.ps1").write_text("outside fixture\n", encoding="utf-8")
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return exercise, config_path


def validate_fixture(
    python: str,
    exercise: Path,
    config: Path,
    name: str,
    expected_error: str,
) -> dict[str, object]:
    result = run_child(
        [python, str(PATH_CHECKER), "--exercise-root", str(exercise), "--config", str(config)],
        cwd=ROOT,
        timeout=30,
    )
    if result.returncode == 0:
        raise AssertionError(f"Invalid metadata fixture {name} unexpectedly passed")
    if expected_error not in result.stderr:
        raise AssertionError(f"Fixture {name} failed for the wrong reason: {result.stderr.strip()}")
    return {"name": name, "exitCode": result.returncode, "expectedFailure": expected_error, "rejected": True}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "work/R09-T038/results.json")
    parser.add_argument("--log", type=Path, default=ROOT / "work/R09-T038/runner.log")
    args = parser.parse_args()
    output = args.output.resolve()
    log_path = args.log.resolve()
    evidence: dict[str, object] = {
        "status": "failed",
        "task": "R09-T038",
        "exercise": "isbn-verifier",
        "checkedAtUtc": datetime.now(timezone.utc).isoformat(),
        "metadataValidation": None,
        "invalidFixtures": [],
        "pester": None,
        "learnerSolutionHashBefore": None,
        "learnerSolutionHashAfter": None,
        "powerShellVersion": None,
        "pesterVersion": None,
    }
    log_lines: list[str] = []

    try:
        config_path = EXERCISE / ".meta/config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        evidence["learnerSolutionHashBefore"] = hashlib.sha256((EXERCISE / config["files"]["solution"][0]).read_bytes()).hexdigest()

        real_validation = run_child(
            [sys.executable, str(PATH_CHECKER), "--exercise-root", str(EXERCISE), "--config", str(config_path)],
            cwd=ROOT,
            timeout=30,
        )
        if real_validation.returncode != 0:
            raise RuntimeError(f"real metadata validation failed: {real_validation.stderr.strip()}")
        validator_data = json.loads(real_validation.stdout)
        roles = validator_data["files"]
        evidence["metadataValidation"] = {
            "passed": True,
            "files": {role: [entry["relativePath"] for entry in entries] for role, entries in roles.items()},
            "editorFilesDeclared": validator_data["editorFilesDeclared"],
        }
        solution = EXERCISE / roles["solution"][0]["relativePath"]
        test_source = EXERCISE / roles["test"][0]["relativePath"]
        example = EXERCISE / roles["example"][0]["relativePath"]

        fixtures: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory(prefix="isbn-verifier-R09-T038-fixtures-") as temporary:
            fixture_root = Path(temporary)
            missing_reference = create_fixture(fixture_root, "missing-reference", config, "example", ".meta/Missing.example.ps1")
            fixtures.append(validate_fixture(sys.executable, *missing_reference, "missing-reference", "does not exist"))
            missing_test = create_fixture(fixture_root, "missing-test", config, "test", "Missing.tests.ps1")
            fixtures.append(validate_fixture(sys.executable, *missing_test, "missing-test", "does not exist"))
            outside_path = create_fixture(fixture_root, "outside-exercise-path", config, "example", "../outside.ps1")
            fixtures.append(validate_fixture(sys.executable, *outside_path, "outside-exercise-path", "escapes exercise root"))
        evidence["invalidFixtures"] = fixtures

        pwsh = shutil.which("pwsh")
        if not pwsh:
            raise FileNotFoundError("PowerShell 7 (pwsh) is required")
        version = run_child(
            [pwsh, "-NoProfile", "-NonInteractive", "-Command", "$PSVersionTable.PSVersion.ToString()"],
            cwd=ROOT,
            timeout=30,
        )
        if version.returncode != 0:
            raise RuntimeError(f"Could not read PowerShell version: {version.stderr.strip()}")
        evidence["powerShellVersion"] = version.stdout.strip()
        pester_version = run_child(
            [pwsh, "-NoProfile", "-NonInteractive", "-Command", "(Get-Module Pester -ListAvailable | Sort-Object Version -Descending | Select-Object -First 1 -ExpandProperty Version).ToString()"],
            cwd=ROOT,
            timeout=30,
        )
        if pester_version.returncode != 0 or not pester_version.stdout.strip():
            raise RuntimeError("Pester is not installed for this PowerShell environment")
        evidence["pesterVersion"] = pester_version.stdout.strip()

        declared_tests = len(re.findall(r"(?m)^\s*It\s+\"", test_source.read_text(encoding="utf-8")))
        with tempfile.TemporaryDirectory(prefix="isbn-verifier-R09-T038-tests-") as temporary:
            temp_root = Path(temporary)
            temp_exercise = temp_root / "isbn-verifier"
            shutil.copytree(EXERCISE, temp_exercise)
            temp_solution = temp_exercise / solution.relative_to(EXERCISE)
            temp_test = temp_exercise / test_source.relative_to(EXERCISE)
            temp_solution.write_bytes(example.read_bytes())
            pester_json = temp_root / "pester.json"
            script_path = temp_root / "pester.ps1"
            script_path.write_text(pester_runner(str(temp_solution), str(temp_test), str(pester_json)), encoding="utf-8")
            pester = run_child([pwsh, "-NoProfile", "-NonInteractive", "-File", str(script_path)], temp_exercise)
            log_lines.extend(["$ pwsh -NoProfile -NonInteractive -File pester.ps1", pester.stdout.rstrip(), pester.stderr.rstrip()])
            if not pester_json.is_file():
                raise RuntimeError(f"Pester did not write a summary (exit {pester.returncode})")
            pester_summary = json.loads(pester_json.read_text(encoding="utf-8-sig"))
            evidence["pester"] = {**pester_summary, "exitCode": pester.returncode}
            if pester.returncode != 0:
                raise RuntimeError(f"Pester exited with code {pester.returncode}")
            if pester_summary["totalCount"] == 0:
                raise AssertionError("Pester ran zero tests")
            if pester_summary["failedCount"] != 0:
                raise AssertionError(f"Pester reported {pester_summary['failedCount']} failed tests")
            if pester_summary["totalCount"] != declared_tests:
                raise AssertionError(f"Pester ran {pester_summary['totalCount']} cases, expected {declared_tests}")
            if not any(probe["actual"] is True for probe in pester_summary["probes"]):
                raise AssertionError("Valid ISBN probe did not return true")
            if not any(probe["actual"] is False for probe in pester_summary["probes"]):
                raise AssertionError("Invalid-check-digit probe did not return false")

        after_hash = hashlib.sha256(solution.read_bytes()).hexdigest()
        evidence["learnerSolutionHashAfter"] = after_hash
        if evidence["learnerSolutionHashBefore"] != after_hash:
            raise AssertionError("Learner solution changed during the isolated check")
        evidence["status"] = "passed"
        print(
            f"PASS: config paths validated; three bad fixtures rejected; Pester "
            f"{pester_version.stdout.strip()} on PowerShell {version.stdout.strip()}, "
            f"{pester_summary['passedCount']}/{pester_summary['totalCount']} cases."
        )
        return 0
    except Exception as exc:
        evidence["error"] = f"{type(exc).__name__}: {exc}"
        log_lines.append(evidence["error"])
        print(evidence["error"], file=sys.stderr)
        return 1
    finally:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("\n".join(line for line in log_lines if line) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
