#!/usr/bin/env python3
"""Run the Minesweeper reference Pester suite in an isolated exercise copy."""

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
EXERCISE = ROOT / "exercises/practice/minesweeper"
GENERATION_CHECK = ROOT / "tools/course_checks/r09-t032.py"
SELECTED = {
    "no rows": {
        "input": "@()",
        "expected": "null or empty result",
    },
    "no columns": {
        "input": '@("")',
        "expected": '[""] (one row containing an empty string)',
    },
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def powershell_script(solution_path: str, test_path: str, result_path: str) -> str:
    return f'''$ErrorActionPreference = "Stop"
$solutionPath = {ps_literal(solution_path)}
$testPath = {ps_literal(test_path)}
$resultPath = {ps_literal(result_path)}
. $solutionPath
$noRows = @(Get-Annotate -Minefield @())
$noColumns = @(Get-Annotate -Minefield @(""))
$probes = [ordered]@{{
    noRows = [ordered]@{{ input = "@()"; expected = "empty result"; actual = @($noRows); actualCount = $noRows.Count; passed = ($noRows.Count -eq 0) }}
    noColumns = [ordered]@{{ input = '@("")'; expected = '[""]'; actual = @($noColumns); actualCount = $noColumns.Count; passed = ($noColumns.Count -eq 1 -and $noColumns[0] -ceq "") }}
}}
$result = Invoke-Pester -Path $testPath -PassThru -Output Detailed
$summary = [ordered]@{{
    totalCount = [int]$result.TotalCount
    passedCount = [int]$result.PassedCount
    failedCount = [int]$result.FailedCount
    skippedCount = [int]$result.SkippedCount
    testNames = @($result.Tests | ForEach-Object {{ $_.Name }})
    selectedCaseProbes = $probes
}}
$summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $resultPath -Encoding utf8
if (-not $probes.noRows.passed -or -not $probes.noColumns.passed) {{ exit 3 }}
if ($result.TotalCount -eq 0) {{ exit 2 }}
if ($result.FailedCount -ne 0) {{ exit 1 }}
exit 0
'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "work/R09-T032/results.json")
    parser.add_argument("--log", type=Path, default=ROOT / "work/R09-T032/runner.log")
    parser.add_argument("--skip-generation", action="store_true", help="Run only the isolated Pester check")
    args = parser.parse_args()
    output = args.output.resolve()
    log_path = args.log.resolve()
    evidence: dict[str, object] = {
        "status": "failed",
        "task": "R09-T032",
        "exercise": "minesweeper",
        "checkedAtUtc": datetime.now(timezone.utc).isoformat(),
        "selectedCases": SELECTED,
        "learnerSolutionHashBefore": None,
        "learnerSolutionHashAfter": None,
        "generationEvidence": None,
        "pester": None,
        "powerShellVersion": None,
        "pesterVersion": None,
    }
    log_lines: list[str] = []

    try:
        config = json.loads((EXERCISE / ".meta/config.json").read_text(encoding="utf-8"))
        solution = configured_file(config, "solution")
        test_source = configured_file(config, "test")
        example = configured_file(config, "example")
        evidence["learnerSolutionHashBefore"] = sha256(solution)

        if not args.skip_generation:
            generated = subprocess.run(
                [sys.executable, str(GENERATION_CHECK), "--output", str(ROOT / "work/R09-T032/generation.json")],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
                timeout=600,
            )
            log_lines.append("$ python3 tools/course_checks/r09-t032.py")
            log_lines.extend([generated.stdout.rstrip(), generated.stderr.rstrip()])
            if generated.returncode != 0:
                raise RuntimeError(f"generation check failed with exit code {generated.returncode}")
            evidence["generationEvidence"] = "work/R09-T032/generation.json"

        pwsh = shutil.which("pwsh")
        if not pwsh:
            raise FileNotFoundError("PowerShell 7 (pwsh) is required")

        with tempfile.TemporaryDirectory(prefix="minesweeper-R09-T032-tests-") as temporary:
            temp_root = Path(temporary)
            temp_exercise = temp_root / "minesweeper"
            shutil.copytree(EXERCISE, temp_exercise)
            temp_solution = temp_exercise / solution.relative_to(EXERCISE)
            temp_test = temp_exercise / test_source.relative_to(EXERCISE)
            temp_solution.write_bytes(example.read_bytes())
            pester_result = temp_root / "pester-result.json"
            invocation = temp_root / "invoke-pester.ps1"
            invocation.write_text(
                powershell_script(str(temp_solution), str(temp_test), str(pester_result)), encoding="utf-8"
            )
            version_result = subprocess.run(
                [pwsh, "-NoProfile", "-NonInteractive", "-Command", "$PSVersionTable.PSVersion.ToString()"],
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            if version_result.returncode != 0:
                raise RuntimeError(f"Could not read PowerShell version: {version_result.stderr.strip()}")
            evidence["powerShellVersion"] = version_result.stdout.strip()
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

            run = subprocess.run(
                [pwsh, "-NoProfile", "-NonInteractive", "-File", str(invocation)],
                cwd=temp_exercise,
                text=True,
                capture_output=True,
                check=False,
                timeout=180,
            )
            log_lines.extend(["$ pwsh -NoProfile -NonInteractive -File invoke-pester.ps1", run.stdout.rstrip(), run.stderr.rstrip()])
            if not pester_result.is_file():
                raise RuntimeError(f"Pester did not write a summary (exit {run.returncode})")
            summary = json.loads(pester_result.read_text(encoding="utf-8-sig"))
            evidence["pester"] = summary
            if run.returncode != 0:
                raise RuntimeError(f"Pester exited with code {run.returncode}")
            if summary["totalCount"] <= 0:
                raise RuntimeError("Pester ran zero tests")
            if summary["failedCount"] != 0:
                raise RuntimeError(f"Pester reported {summary['failedCount']} failed tests")
            missing_names = {f"{name}" for name in SELECTED} - set(summary.get("testNames", []))
            if missing_names:
                raise RuntimeError(f"Selected tests were not reported by Pester: {sorted(missing_names)}")

        evidence["learnerSolutionHashAfter"] = sha256(solution)
        if evidence["learnerSolutionHashBefore"] != evidence["learnerSolutionHashAfter"]:
            raise AssertionError("Learner solution changed during the isolated check")
        evidence["status"] = "passed"
        print(
            f"PASS: Pester {evidence['pesterVersion']} on PowerShell {evidence['powerShellVersion']}; "
            f"{evidence['pester']['passedCount']}/{evidence['pester']['totalCount']} passed, learner file unchanged."
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
