#!/usr/bin/env python3
"""Verify the robot-simulator reference without touching learner files."""

from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib


ROOT = Path(__file__).resolve().parents[2]
EXERCISE_REL = Path("exercises/practice/robot-simulator")
EVIDENCE_DIR = Path(__file__).resolve().parent
ISSUE = 4
EXPECTED_CASES = {
    "c557c16d-26c1-4e06-827c-f6602cd0785c": {
        "name": "at origin facing north",
        "input": {"constructor": "Robot('NORTH', 0, 0)"},
        "expected": {"direction": "NORTH", "position": [0, 0]},
    },
    "bf0dffce-f11c-4cdb-8a5e-2c89d8a5a67d": {
        "name": "at negative position facing south",
        "input": {"constructor": "Robot('SOUTH', -1, -1)"},
        "expected": {"direction": "SOUTH", "position": [-1, -1]},
    },
    "8cbd0086-6392-4680-b9b9-73cf491e67e5": {
        "name": "clockwise -> changes north to east",
        "input": {"constructor": "Robot('NORTH', 0, 0)", "instruction": "R"},
        "expected": {"direction": "EAST", "position": [0, 0]},
    },
}
DEFAULT_CASE = {
    "name": "at defaults origin without inputs",
    "input": {"constructor": "Robot()"},
    "expected": {"direction": "NORTH", "position": [0, 0]},
}

POWERSHELL_RUNNER = r"""param([Parameter(Mandatory=$true)][string]$TestPath,
      [Parameter(Mandatory=$true)][string]$ResultPath)
$ErrorActionPreference = 'Stop'
try {
    Import-Module Pester -ErrorAction Stop
    Push-Location -LiteralPath (Split-Path -Parent $TestPath)
    try {
        $result = Invoke-Pester -Path $TestPath -PassThru
    }
    finally {
        Pop-Location
    }
    $tests = @($result.Tests | ForEach-Object {
        [ordered]@{
            name = [string]$_.ExpandedName
            result = [string]$_.Result
        }
    })
    $summary = [ordered]@{
        total = [int]$result.TotalCount
        passed = [int]$result.PassedCount
        failed = [int]$result.FailedCount
        skipped = [int]$result.SkippedCount
        pesterVersion = (Get-Module Pester).Version.ToString()
        tests = $tests
    }
    $summary | ConvertTo-Json -Depth 8 -Compress | Set-Content -LiteralPath $ResultPath -Encoding utf8NoBOM
    if ($result.TotalCount -lt 1 -or $result.FailedCount -gt 0) { exit 1 }
    exit 0
}
catch {
    [ordered]@{ error = $_.Exception.Message } | ConvertTo-Json -Compress | Set-Content -LiteralPath $ResultPath -Encoding utf8NoBOM
    [Console]::Error.WriteLine($_.Exception.ToString())
    exit 1
}
"""

CASE_RUNNER = r"""
param([Parameter(Mandatory=$true)][string]$SolutionPath,
      [Parameter(Mandatory=$true)][string]$ResultPath)
$ErrorActionPreference = 'Stop'
. $SolutionPath
$cases = @()
$robot = [Robot]::new()
$cases += [pscustomobject]@{ id = 'defaultConstructor'; name = 'at defaults origin without inputs'; input = @{ constructor = 'Robot()' }; direction = $robot.Direction.ToString(); position = @($robot.GetPosition()) }
$robot = [Robot]::new('NORTH', 0, 0)
$cases += [pscustomobject]@{ id = 'c557c16d-26c1-4e06-827c-f6602cd0785c'; name = 'at origin facing north'; input = @{ constructor = "Robot('NORTH', 0, 0)" }; direction = $robot.Direction.ToString(); position = @($robot.GetPosition()) }
$robot = [Robot]::new('SOUTH', -1, -1)
$cases += [pscustomobject]@{ id = 'bf0dffce-f11c-4cdb-8a5e-2c89d8a5a67d'; name = 'at negative position facing south'; input = @{ constructor = "Robot('SOUTH', -1, -1)" }; direction = $robot.Direction.ToString(); position = @($robot.GetPosition()) }
$robot = [Robot]::new('NORTH', 0, 0)
$robot.Move('R')
$cases += [pscustomobject]@{ id = '8cbd0086-6392-4680-b9b9-73cf491e67e5'; name = 'clockwise -> changes north to east'; input = @{ constructor = "Robot('NORTH', 0, 0)"; instruction = 'R' }; direction = $robot.Direction.ToString(); position = @($robot.GetPosition()) }
$cases | ConvertTo-Json -Depth 6 -Compress | Set-Content -LiteralPath $ResultPath -Encoding utf8NoBOM
"""


def sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def contained_file(base: Path, relative: str) -> Path:
    base_resolved = base.resolve()
    candidate = (base / relative).resolve()
    try:
        candidate.relative_to(base_resolved)
    except ValueError as exc:
        raise ValueError(f"Configured path escapes exercise: {relative}") from exc
    if not candidate.is_file():
        raise FileNotFoundError(f"Configured file does not exist: {candidate}")
    return candidate


def read_config(exercise: Path) -> tuple[dict[str, str], dict[str, Path]]:
    config = json.loads((exercise / ".meta/config.json").read_text(encoding="utf-8"))
    configured: dict[str, Path] = {}
    for role in ("solution", "test", "example"):
        values = config.get("files", {}).get(role)
        if not isinstance(values, list) or len(values) != 1 or not isinstance(values[0], str):
            raise ValueError(f"Expected exactly one configured {role} file")
        configured[role] = contained_file(exercise, values[0])
    relative = {role: str(path.relative_to(exercise)) for role, path in configured.items()}
    return relative, configured


def main() -> int:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    evidence: dict[str, object] = {
        "issue": ISSUE,
        "exercise": str(EXERCISE_REL),
        "status": "failed",
        "canonicalCases": {"countBefore": None, "countAfter": None, "excludedBefore": None, "excludedAfter": None},
        "selectedExpected": {**EXPECTED_CASES, "defaultConstructor": DEFAULT_CASE},
        "pester": None,
        "toolVersions": {"python": sys.version.split()[0], "platform": platform.platform()},
        "learnerSolutionSha256Before": None,
        "learnerSolutionSha256After": None,
    }
    log_parts: list[str] = []
    try:
        exercise = ROOT / EXERCISE_REL
        relative, configured = read_config(exercise)
        solution = exercise / relative["solution"]
        before_hash = sha256(solution)
        evidence["configuredFiles"] = relative
        evidence["learnerSolutionSha256Before"] = before_hash

        toml_path = exercise / ".meta/tests.toml"
        parsed = tomllib.loads(toml_path.read_text(encoding="utf-8"))
        case_count = len(parsed)
        excluded_count = sum(1 for case in parsed.values() if isinstance(case, dict) and case.get("include") is False)
        if case_count != 18 or excluded_count != 0:
            raise AssertionError(f"Expected 18 canonical cases and 0 exclusions; found {case_count} and {excluded_count}")
        evidence["canonicalCases"] = {
            "countBefore": case_count,
            "countAfter": case_count,
            "excludedBefore": excluded_count,
            "excludedAfter": excluded_count,
        }

        pwsh = shutil.which("pwsh")
        if not pwsh:
            raise FileNotFoundError("PowerShell 7 executable 'pwsh' was not found on PATH")
        version = subprocess.run(
            [pwsh, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", "$PSVersionTable.PSVersion.ToString()"],
            text=True,
            capture_output=True,
            check=False,
        )
        evidence["toolVersions"]["pwsh"] = version.stdout.strip()
        if version.returncode != 0:
            raise RuntimeError(f"Could not read PowerShell version: {version.stderr.strip()}")

        with tempfile.TemporaryDirectory(prefix="robot-simulator-R09-T031-") as temporary:
            temporary_root = Path(temporary)
            copied_exercise = temporary_root / "robot-simulator"
            shutil.copytree(exercise, copied_exercise)
            copied_solution = copied_exercise / relative["solution"]
            copied_solution.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(configured["example"], copied_solution)
            copied_test = copied_exercise / relative["test"]
            result_path = temporary_root / "pester-results.json"
            runner_path = temporary_root / "run-pester.ps1"
            runner_path.write_text(POWERSHELL_RUNNER, encoding="utf-8")
            cases_path = temporary_root / "selected-cases.json"
            case_runner_path = temporary_root / "run-selected-cases.ps1"
            case_runner_path.write_text(CASE_RUNNER, encoding="utf-8")
            cases_run = subprocess.run(
                [
                    pwsh,
                    "-NoLogo",
                    "-NoProfile",
                    "-NonInteractive",
                    "-File",
                    str(case_runner_path),
                    "-SolutionPath",
                    str(copied_solution),
                    "-ResultPath",
                    str(cases_path),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            log_parts.extend(["$ selected-case probe", cases_run.stdout, cases_run.stderr])
            if cases_run.returncode != 0 or not cases_path.is_file():
                raise RuntimeError(f"Selected-case probe exited {cases_run.returncode}; see runner.log")
            actual_cases = json.loads(cases_path.read_text(encoding="utf-8-sig"))
            if isinstance(actual_cases, dict):
                actual_cases = [actual_cases]
            expected_by_id = {**EXPECTED_CASES, "defaultConstructor": DEFAULT_CASE}
            actual_by_id = {case["id"]: case for case in actual_cases}
            if set(actual_by_id) != set(expected_by_id):
                raise AssertionError(f"Selected-case probe returned unexpected IDs: {sorted(actual_by_id)}")
            outcomes = {}
            for case_id, specification in expected_by_id.items():
                actual = {
                    "direction": actual_by_id[case_id]["direction"],
                    "position": actual_by_id[case_id]["position"],
                }
                outcomes[case_id] = {
                    "name": specification["name"],
                    "input": specification["input"],
                    "expected": specification["expected"],
                    "actual": actual,
                    "passed": actual == specification["expected"],
                }
                if not outcomes[case_id]["passed"]:
                    raise AssertionError(f"Selected case {case_id} expected {specification['expected']}, got {actual}")
            evidence["selectedOutcomes"] = outcomes
            command = [
                pwsh,
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-File",
                str(runner_path),
                "-TestPath",
                str(copied_test),
                "-ResultPath",
                str(result_path),
            ]
            run = subprocess.run(command, text=True, capture_output=True, check=False)
            log_parts.extend(["$ " + " ".join(command), run.stdout, run.stderr])
            if result_path.is_file():
                pester = json.loads(result_path.read_text(encoding="utf-8-sig"))
            else:
                pester = {"error": "PowerShell runner did not write its result file"}
            evidence["pester"] = {"exitCode": run.returncode, **pester}
            if run.returncode != 0:
                raise RuntimeError(f"Pester runner exited {run.returncode}; see runner.log")
            if "error" in pester:
                raise RuntimeError(pester["error"])
            if pester.get("total", 0) == 0 or pester.get("failed", 0) != 0:
                raise AssertionError(f"Expected nonzero passing Pester run; got {pester}")

            actual_names = {test.get("name", ""): test.get("result") for test in pester.get("tests", [])}
            expected_tests = [spec["name"] for spec in EXPECTED_CASES.values()] + [DEFAULT_CASE["name"]]
            for expected_name in expected_tests:
                matches = [(name, result) for name, result in actual_names.items() if name.endswith(expected_name)]
                if not matches or any(result != "Passed" for _, result in matches):
                    raise AssertionError(f"Expected Pester case to pass: {expected_name}; observed {matches}")
            evidence["selectedPesterResults"] = {
                name: [result for test_name, result in actual_names.items() if test_name.endswith(name)]
                for name in expected_tests
            }

        after_hash = sha256(solution)
        evidence["learnerSolutionSha256After"] = after_hash
        if before_hash != after_hash:
            raise AssertionError("Learner solution changed during the isolated check")
        evidence["status"] = "passed"
        print(f"PASS: {evidence['pester']['passed']}/{evidence['pester']['total']} Pester cases; 18 canonical cases, 0 excluded.")
        return 0
    except Exception as exc:
        evidence["error"] = f"{type(exc).__name__}: {exc}"
        print(evidence["error"], file=sys.stderr)
        return 1
    finally:
        (EVIDENCE_DIR / "results.json").write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (EVIDENCE_DIR / "runner.log").write_text("\n".join(log_parts).rstrip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
