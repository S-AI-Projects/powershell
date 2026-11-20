#!/usr/bin/env python3
"""Run the list-ops reference suite in a temporary exercise copy."""

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
EXERCISE = ROOT / "exercises/practice/list-ops"


def ps_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def captured_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def configured_file(exercise: Path, config: dict, role: str) -> Path:
    paths = config.get("files", {}).get(role)
    if not isinstance(paths, list) or len(paths) != 1 or not isinstance(paths[0], str):
        raise ValueError(f"Expected exactly one configured {role} path")
    candidate = (exercise / paths[0]).resolve()
    if exercise.resolve() not in candidate.parents:
        raise ValueError(f"Configured {role} path escapes the exercise: {paths[0]}")
    if not candidate.is_file():
        raise FileNotFoundError(f"Configured {role} file is missing: {candidate}")
    return candidate


def pester_runner(solution_path: str, test_path: str, result_path: str) -> str:
    return f'''$ErrorActionPreference = "Stop"
$solutionPath = {ps_literal(solution_path)}
$testPath = {ps_literal(test_path)}
$resultPath = {ps_literal(result_path)}
. $solutionPath
$result = Invoke-Pester -Path $testPath -PassThru -Output Detailed
$emptyAppend = @(Invoke-Append -List1 @() -List2 @())
$listToEmpty = @(Invoke-Append -List1 @() -List2 @(1, 2, 3, 4))
$summary = [ordered]@{{
    totalCount = [int]$result.TotalCount
    passedCount = [int]$result.PassedCount
    failedCount = [int]$result.FailedCount
    skippedCount = [int]$result.SkippedCount
    testNames = @($result.Tests | ForEach-Object {{ $_.Name }})
    probes = @(
        [ordered]@{{ name = "empty lists"; input = "List1=@(), List2=@()"; expected = @(); actual = @($emptyAppend); matchesExpected = (@($emptyAppend).Count -eq 0) }}
        [ordered]@{{ name = "list to empty list"; input = "List1=@(), List2=@(1, 2, 3, 4)"; expected = @(1, 2, 3, 4); actual = @($listToEmpty); matchesExpected = ((@($listToEmpty) -join ",") -ceq "1,2,3,4") }}
    )
}}
$summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $resultPath -Encoding utf8
if ($result.TotalCount -eq 0) {{ exit 2 }}
if ($result.FailedCount -ne 0) {{ exit 1 }}
if (@($summary.probes | Where-Object {{ -not $_.matchesExpected }}).Count -gt 0) {{ exit 3 }}
exit 0
'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("reference", "failing-reference", "empty-selection"), default="reference")
    parser.add_argument("--output", type=Path, help="Optional JSON result file")
    parser.add_argument("--log", type=Path, help="Optional captured Pester log")
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    evidence: dict[str, object] = {
        "status": "failed",
        "mode": args.mode,
        "exercise": "list-ops",
        "checkedAtUtc": datetime.now(timezone.utc).isoformat(),
        "learnerSolutionHashBefore": None,
        "learnerSolutionHashAfter": None,
        "temporaryDirectoryCleaned": False,
        "pester": None,
        "powerShellVersion": None,
        "pesterVersion": None,
    }
    log = ""
    solution: Path | None = None
    temporary_name: str | None = None
    error: str | None = None

    try:
        config_path = EXERCISE / ".meta/config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        solution = configured_file(EXERCISE, config, "solution")
        test_source = configured_file(EXERCISE, config, "test")
        example = configured_file(EXERCISE, config, "example")
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

        with tempfile.TemporaryDirectory(prefix="list-ops-course-check-") as temporary:
            temporary_root = Path(temporary)
            temporary_name = str(temporary_root)
            temp_exercise = temporary_root / "list-ops"
            shutil.copytree(EXERCISE, temp_exercise)
            temp_solution = temp_exercise / solution.relative_to(EXERCISE)
            temp_test = temp_exercise / test_source.relative_to(EXERCISE)
            temp_solution.write_bytes(example.read_bytes())
            if args.mode == "failing-reference":
                source_text = temp_solution.read_text(encoding="utf-8")
                if source_text.count("$List1 + $List2") != 1:
                    raise AssertionError("Could not identify the append expression for the deliberate failing reference")
                temp_solution.write_text(source_text.replace("$List1 + $List2", "@()", 1), encoding="utf-8")
            elif args.mode == "empty-selection":
                temp_test.write_text("# Deliberately empty Pester selection for runner validation.\n", encoding="utf-8")

            result_path = temporary_root / "result.json"
            script_path = temporary_root / "run-pester.ps1"
            script_path.write_text(pester_runner(str(temp_solution), str(temp_test), str(result_path)), encoding="utf-8")
            try:
                process = subprocess.run(
                    [pwsh, "-NoProfile", "-NonInteractive", "-File", str(script_path)],
                    cwd=temp_exercise,
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=args.timeout,
                )
                log = process.stdout + process.stderr
                evidence["pesterChildExitCode"] = process.returncode
            except subprocess.TimeoutExpired as exc:
                log = captured_text(exc.stdout) + captured_text(exc.stderr)
                raise TimeoutError(f"Pester child exceeded {args.timeout} seconds") from exc

            if not result_path.is_file():
                raise RuntimeError("Pester child did not write a result summary")
            summary = json.loads(result_path.read_text(encoding="utf-8-sig"))
            evidence["pester"] = summary
            if process.returncode != 0:
                error = f"Pester child exited with code {process.returncode}"
            elif summary["totalCount"] == 0:
                error = "Pester ran zero tests"
            elif summary["failedCount"] != 0:
                error = f"Pester reported {summary['failedCount']} assertion failures"
            elif args.mode != "reference":
                raise AssertionError(f"{args.mode} scenario unexpectedly passed")
            else:
                evidence["status"] = "passed"

    except KeyboardInterrupt:
        error = "Pester run interrupted"
        raise
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    finally:
        if solution is not None and solution.is_file():
            evidence["learnerSolutionHashAfter"] = hashlib.sha256(solution.read_bytes()).hexdigest()
            if evidence["learnerSolutionHashBefore"] != evidence["learnerSolutionHashAfter"]:
                error = "Learner solution hash changed during isolated run"
        if temporary_name:
            evidence["temporaryDirectoryCleaned"] = not Path(temporary_name).exists()
            if not evidence["temporaryDirectoryCleaned"]:
                error = "Temporary run directory was not cleaned up"
        if error:
            evidence["status"] = "failed"
            evidence["error"] = error

        result_text = json.dumps(evidence, indent=2, sort_keys=True) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(result_text, encoding="utf-8")
        else:
            print(result_text, end="")
        if args.log:
            args.log.parent.mkdir(parents=True, exist_ok=True)
            args.log.write_text(log, encoding="utf-8")

    return 0 if evidence["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
