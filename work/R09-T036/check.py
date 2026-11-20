#!/usr/bin/env python3
"""Compare the Hello World literal reference with a StringBuilder alternative."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[2]
EXERCISE = ROOT / "exercises/practice/hello-world"
ALTERNATIVE = ROOT / "work/R09-T036/alternative.ps1"
EXPECTED_OUTPUT = "Hello, World!"
PESTER_CASE_COUNT = 1


def ps_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def configured_file(config: dict, key: str) -> Path:
    paths = config.get("files", {}).get(key)
    if not isinstance(paths, list) or len(paths) != 1 or not isinstance(paths[0], str):
        raise ValueError(f"Expected exactly one configured {key} path")
    candidate = (EXERCISE / paths[0]).resolve()
    if EXERCISE.resolve() not in candidate.parents:
        raise ValueError(f"Configured {key} path escapes the exercise: {paths[0]}")
    if not candidate.is_file():
        raise FileNotFoundError(f"Configured {key} file is missing: {candidate}")
    return candidate


def runner(solution_path: str, test_path: str, result_path: str) -> str:
    return f'''$ErrorActionPreference = "Stop"
$solutionPath = {ps_literal(solution_path)}
$testPath = {ps_literal(test_path)}
$resultPath = {ps_literal(result_path)}
. $solutionPath
$result = Invoke-Pester -Path $testPath -PassThru -Output Detailed
$actual = Get-HelloWorld
$summary = [ordered]@{{
    totalCount = [int]$result.TotalCount
    passedCount = [int]$result.PassedCount
    failedCount = [int]$result.FailedCount
    skippedCount = [int]$result.SkippedCount
    testNames = @($result.Tests | ForEach-Object {{ $_.Name }})
    input = "no arguments"
    expected = "Hello, World!"
    actual = [string]$actual
    matchesExpected = ([string]$actual -ceq "Hello, World!")
}}
$summary | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $resultPath -Encoding utf8
if ($result.TotalCount -eq 0) {{ exit 2 }}
if ($result.FailedCount -ne 0) {{ exit 1 }}
if (-not $summary.matchesExpected) {{ exit 3 }}
exit 0
'''


def run_approach(pwsh: str, exercise: Path, solution: Path, test: Path, label: str, temporary: Path) -> dict[str, object]:
    result_path = temporary / f"{label}-result.json"
    script_path = temporary / f"{label}-runner.ps1"
    script_path.write_text(runner(str(solution), str(test), str(result_path)), encoding="utf-8")
    process = subprocess.run(
        [pwsh, "-NoProfile", "-NonInteractive", "-File", str(script_path)],
        cwd=exercise,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    if not result_path.is_file():
        raise RuntimeError(f"{label} run produced no result summary (exit {process.returncode})")
    result = json.loads(result_path.read_text(encoding="utf-8-sig"))
    return {"exitCode": process.returncode, "summary": result, "stdout": process.stdout, "stderr": process.stderr}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "work/R09-T036/results.json")
    parser.add_argument("--log", type=Path, default=ROOT / "work/R09-T036/runner.log")
    args = parser.parse_args()
    output = args.output.resolve()
    log_path = args.log.resolve()
    evidence: dict[str, object] = {
        "status": "failed",
        "task": "R09-T036",
        "exercise": "hello-world",
        "checkedAtUtc": datetime.now(timezone.utc).isoformat(),
        "referenceApproach": "Return the constant greeting string directly.",
        "alternativeApproach": "Append the two greeting parts to a StringBuilder, then return its final string.",
        "reference": None,
        "alternative": None,
        "sameOutput": False,
        "learnerSolutionHashBefore": None,
        "learnerSolutionHashAfter": None,
        "powerShellVersion": None,
        "pesterVersion": None,
    }
    log_lines: list[str] = []

    try:
        config = json.loads((EXERCISE / ".meta/config.json").read_text(encoding="utf-8"))
        solution = configured_file(config, "solution")
        test_source = configured_file(config, "test")
        example = configured_file(config, "example")
        if not ALTERNATIVE.is_file():
            raise FileNotFoundError(f"Alternative implementation is missing: {ALTERNATIVE}")
        evidence["learnerSolutionHashBefore"] = hashlib.sha256(solution.read_bytes()).hexdigest()

        pwsh = shutil.which("pwsh")
        if not pwsh:
            raise FileNotFoundError("PowerShell 7 (pwsh) is required")
        version = subprocess.run(
            [pwsh, "-NoProfile", "-NonInteractive", "-Command", "$PSVersionTable.PSVersion.ToString()"],
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
        if version.returncode != 0:
            raise RuntimeError(f"Could not read PowerShell version: {version.stderr.strip()}")
        evidence["powerShellVersion"] = version.stdout.strip()
        pester_version = subprocess.run(
            [pwsh, "-NoProfile", "-NonInteractive", "-Command", "(Get-Module Pester -ListAvailable | Sort-Object Version -Descending | Select-Object -First 1 -ExpandProperty Version).ToString()"],
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
        if pester_version.returncode != 0 or not pester_version.stdout.strip():
            raise RuntimeError("Pester is not installed for this PowerShell environment")
        evidence["pesterVersion"] = pester_version.stdout.strip()

        with tempfile.TemporaryDirectory(prefix="hello-world-R09-T036-") as temporary:
            root = Path(temporary)
            reference_exercise = root / "reference"
            alternative_exercise = root / "alternative"
            shutil.copytree(EXERCISE, reference_exercise)
            shutil.copytree(EXERCISE, alternative_exercise)
            reference_solution = reference_exercise / solution.relative_to(EXERCISE)
            alternative_solution = alternative_exercise / solution.relative_to(EXERCISE)
            reference_test = reference_exercise / test_source.relative_to(EXERCISE)
            alternative_test = alternative_exercise / test_source.relative_to(EXERCISE)
            reference_solution.write_bytes(example.read_bytes())
            alternative_solution.write_bytes(ALTERNATIVE.read_bytes())

            reference_run = run_approach(pwsh, reference_exercise, reference_solution, reference_test, "reference", root)
            alternative_run = run_approach(pwsh, alternative_exercise, alternative_solution, alternative_test, "alternative", root)
            for label, run in [("reference", reference_run), ("alternative", alternative_run)]:
                summary = run["summary"]
                evidence[label] = {**summary, "exitCode": run["exitCode"]}
                if run["exitCode"] != 0:
                    raise RuntimeError(f"{label} child returned non-zero exit code {run['exitCode']}")
                if summary["totalCount"] == 0:
                    raise AssertionError(f"{label} Pester run executed zero tests")
                if summary["totalCount"] != PESTER_CASE_COUNT:
                    raise AssertionError(f"{label} Pester ran {summary['totalCount']} cases, expected {PESTER_CASE_COUNT}")
                if summary["failedCount"] != 0:
                    raise AssertionError(f"{label} Pester reported {summary['failedCount']} failures")
                if not summary["matchesExpected"] or summary["actual"] != EXPECTED_OUTPUT:
                    raise AssertionError(f"{label} output differed from {EXPECTED_OUTPUT!r}")
            if reference_run["summary"]["testNames"] != alternative_run["summary"]["testNames"]:
                raise AssertionError("The two approaches did not run the same Pester cases")
            evidence["sameOutput"] = reference_run["summary"]["actual"] == alternative_run["summary"]["actual"]
            if not evidence["sameOutput"]:
                raise AssertionError("Reference and alternative returned different output")
            log_lines.extend([
                "$ pwsh -NoProfile -NonInteractive -File reference-runner.ps1",
                reference_run["stdout"].rstrip(),
                reference_run["stderr"].rstrip(),
                "$ pwsh -NoProfile -NonInteractive -File alternative-runner.ps1",
                alternative_run["stdout"].rstrip(),
                alternative_run["stderr"].rstrip(),
                f"Expected: {EXPECTED_OUTPUT!r}; reference actual: {reference_run['summary']['actual']!r}; alternative actual: {alternative_run['summary']['actual']!r}",
            ])

        after_hash = hashlib.sha256(solution.read_bytes()).hexdigest()
        evidence["learnerSolutionHashAfter"] = after_hash
        if evidence["learnerSolutionHashBefore"] != after_hash:
            raise AssertionError("Learner solution changed during the isolated comparison")
        evidence["status"] = "passed"
        print(
            f"PASS: reference and StringBuilder alternative each passed "
            f"{PESTER_CASE_COUNT}/{PESTER_CASE_COUNT} Pester cases; both returned {EXPECTED_OUTPUT!r}."
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
