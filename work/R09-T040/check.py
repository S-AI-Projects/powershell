#!/usr/bin/env python3
"""Run the intergalactic-transmission reference tests and selected probes."""

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
import tomllib


ROOT = Path(__file__).resolve().parents[2]
EXERCISE = ROOT / "exercises/practice/intergalactic-transmission"
SELECTED_CASES = {
    "f99d4046-b429-4582-9324-f0bcac7ab51c": "calculate transmit sequences -> empty message",
    "ee27ea2d-8999-4f23-9275-8f6879545f86": "calculate transmit sequences -> 0x00 is transmitted as 0x0000",
    "9a8084dd-3336-474c-90cb-8a852524604d": "decode received messages -> empty message",
}


def ps_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def configured_file(config: dict, role: str) -> Path:
    paths = config.get("files", {}).get(role)
    if not isinstance(paths, list) or len(paths) != 1 or not isinstance(paths[0], str):
        raise ValueError(f"Expected exactly one configured {role} path")
    candidate = (EXERCISE / paths[0]).resolve()
    if EXERCISE.resolve() not in candidate.parents:
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
$emptyTransmit = @(Invoke-Transmitter -Sequence @())
$emptyReceive = @(Invoke-Receiver -Sequence @())
$zeroTransmit = @(Invoke-Transmitter -Sequence ([byte[]]@(0x00)))
$summary = [ordered]@{{
    totalCount = [int]$result.TotalCount
    passedCount = [int]$result.PassedCount
    failedCount = [int]$result.FailedCount
    skippedCount = [int]$result.SkippedCount
    testNames = @($result.Tests | ForEach-Object {{ $_.Name }})
    probes = @(
        [ordered]@{{ name = "transmit empty message"; input = "@()"; expected = @(); actual = @($emptyTransmit); matchesExpected = (@($emptyTransmit).Count -eq 0) }}
        [ordered]@{{ name = "receive empty message"; input = "@()"; expected = @(); actual = @($emptyReceive); matchesExpected = (@($emptyReceive).Count -eq 0) }}
        [ordered]@{{ name = "transmit zero byte"; input = "@(0x00)"; expected = @(0x00, 0x00); actual = @($zeroTransmit); matchesExpected = ((@($zeroTransmit) -join ",") -ceq "0,0") }}
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
    parser.add_argument("--output", type=Path, default=ROOT / "work/R09-T040/results.json")
    parser.add_argument("--log", type=Path, default=ROOT / "work/R09-T040/runner.log")
    args = parser.parse_args()
    output = args.output.resolve()
    log_path = args.log.resolve()
    evidence: dict[str, object] = {
        "status": "failed",
        "task": "R09-T040",
        "exercise": "intergalactic-transmission",
        "checkedAtUtc": datetime.now(timezone.utc).isoformat(),
        "selectedCanonicalCases": SELECTED_CASES,
        "pester": None,
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
        tests_toml = tomllib.loads((EXERCISE / ".meta/tests.toml").read_text(encoding="utf-8"))
        for case_id, description in SELECTED_CASES.items():
            case = tests_toml.get(case_id)
            if not isinstance(case, dict) or case.get("description") != description:
                raise AssertionError(f"Canonical test metadata does not match selected case {case_id}")
        evidence["learnerSolutionHashBefore"] = hashlib.sha256(solution.read_bytes()).hexdigest()
        declared_tests = len(re.findall(r"(?m)^\s*It\s+\"", test_source.read_text(encoding="utf-8")))

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

        with tempfile.TemporaryDirectory(prefix="intergalactic-transmission-R09-T040-") as temporary:
            temp_root = Path(temporary)
            temp_exercise = temp_root / "intergalactic-transmission"
            shutil.copytree(EXERCISE, temp_exercise)
            temp_solution = temp_exercise / solution.relative_to(EXERCISE)
            temp_test = temp_exercise / test_source.relative_to(EXERCISE)
            temp_solution.write_bytes(example.read_bytes())
            result_path = temp_root / "pester.json"
            invocation = temp_root / "invoke-pester.ps1"
            invocation.write_text(pester_runner(str(temp_solution), str(temp_test), str(result_path)), encoding="utf-8")
            process = subprocess.run(
                [pwsh, "-NoProfile", "-NonInteractive", "-File", str(invocation)],
                cwd=temp_exercise,
                text=True,
                capture_output=True,
                check=False,
                timeout=180,
            )
            log_lines.extend(["$ pwsh -NoProfile -NonInteractive -File invoke-pester.ps1", process.stdout.rstrip(), process.stderr.rstrip()])
            if not result_path.is_file():
                raise RuntimeError(f"PowerShell child did not write a Pester summary (exit {process.returncode})")
            summary = json.loads(result_path.read_text(encoding="utf-8-sig"))
            evidence["pester"] = {**summary, "exitCode": process.returncode, "declaredTestCount": declared_tests}
            if process.returncode != 0:
                raise RuntimeError(f"PowerShell child exited with code {process.returncode}")
            if summary["totalCount"] == 0:
                raise AssertionError("Pester ran zero tests")
            if summary["failedCount"] != 0:
                raise AssertionError(f"Pester reported {summary['failedCount']} failed tests")
            if summary["totalCount"] != declared_tests:
                raise AssertionError(f"Pester ran {summary['totalCount']} tests, expected {declared_tests}")
            if not all(probe["matchesExpected"] for probe in summary["probes"]):
                raise AssertionError("A selected contract probe did not match its expected result")
            if not any("empty message" in name for name in summary["testNames"]):
                raise AssertionError("Pester did not report the empty-message case")
            if not any("0x00 is transmitted as 0x0000" in name for name in summary["testNames"]):
                raise AssertionError("Pester did not report the zero-byte transmission case")

        after_hash = hashlib.sha256(solution.read_bytes()).hexdigest()
        evidence["learnerSolutionHashAfter"] = after_hash
        if evidence["learnerSolutionHashBefore"] != after_hash:
            raise AssertionError("Learner solution changed during the isolated reference check")
        evidence["status"] = "passed"
        print(
            f"PASS: Pester {pester_version.stdout.strip()} on PowerShell {version.stdout.strip()}, "
            f"{summary['passedCount']}/{summary['totalCount']} cases; empty and zero-byte probes matched."
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
        cleaned_log = "\n".join(line for line in log_lines if line)
        log_path.write_text(cleaned_log.rstrip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
