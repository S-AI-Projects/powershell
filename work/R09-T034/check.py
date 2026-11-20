#!/usr/bin/env python3
"""Compare the flatten-array reference before and after its local-name refactor."""

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
EXERCISE = ROOT / "exercises/practice/flatten-array"
BASELINE = ROOT / "work/R09-T034/baseline/FlattenArray.example.ps1"
CASE_COUNT = 11


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


def pester_runner(test_path: str, result_path: str) -> str:
    return f'''$ErrorActionPreference = "Stop"
$testPath = {ps_literal(test_path)}
$resultPath = {ps_literal(result_path)}
$result = Invoke-Pester -Path $testPath -PassThru -Output Detailed
$summary = [ordered]@{{
    totalCount = [int]$result.TotalCount
    passedCount = [int]$result.PassedCount
    failedCount = [int]$result.FailedCount
    skippedCount = [int]$result.SkippedCount
    testNames = @($result.Tests | ForEach-Object {{ $_.Name }})
}}
$summary | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $resultPath -Encoding utf8
if ($result.TotalCount -eq 0) {{ exit 2 }}
if ($result.FailedCount -ne 0) {{ exit 1 }}
exit 0
'''


def probe_runner(solution_path: str, result_path: str) -> str:
    return f'''$ErrorActionPreference = "Stop"
$solutionPath = {ps_literal(solution_path)}
$resultPath = {ps_literal(result_path)}
. $solutionPath
$cases = @(
    @{{ name = "empty"; input = "@()"; run = {{ Invoke-FlattenArray -Array @() }}; expected = @() }}
    @{{ name = "no nesting"; input = "@(1, 2, 3)"; run = {{ Invoke-FlattenArray -Array @(1, 2, 3) }}; expected = @(1, 2, 3) }}
    @{{ name = "flattens a nested array"; input = "@(@(@()))"; run = {{ Invoke-FlattenArray -Array @(@(@())) }}; expected = @() }}
    @{{ name = "flattens array with just integers present"; input = "@(1, @(2, 3, 4, 5, 6, 7), 8)"; run = {{ Invoke-FlattenArray -Array @(1, @(2, 3, 4, 5, 6, 7), 8) }}; expected = @(1, 2, 3, 4, 5, 6, 7, 8) }}
    @{{ name = "5 level nesting"; input = "@(0, 2, @(@(2, 3), 8, 100, 4, @(@(@(50)))), -2)"; run = {{ Invoke-FlattenArray -Array @(0, 2, @(@(2, 3), 8, 100, 4, @(@(@(50)))), -2) }}; expected = @(0, 2, 2, 3, 8, 100, 4, 50, -2) }}
    @{{ name = "6 level nesting"; input = "@(1, @(2, 3, 4, 5, 6, 7), 8)"; run = {{ Invoke-FlattenArray -Array @(1, @(2, 3, 4, 5, 6, 7), 8) }}; expected = @(1, 2, 3, 4, 5, 6, 7, 8) }}
    @{{ name = "null values are omitted from the final result"; input = "@(1, 2, $null)"; run = {{ Invoke-FlattenArray -Array @(1, 2, $null) }}; expected = @(1, 2) }}
    @{{ name = "consecutive null values at the front of the array are omitted from the final result"; input = "@($null, $null, 5)"; run = {{ Invoke-FlattenArray -Array @($null, $null, 5) }}; expected = @(5) }}
    @{{ name = "consecutive null values in the middle of the array are omitted from the final result"; input = "@(1, $null, $null, 4)"; run = {{ Invoke-FlattenArray -Array @(1, $null, $null, 4) }}; expected = @(1, 4) }}
    @{{ name = "6 level nest array with null values"; input = "@(0, 2, @(@(2, 3), 8, @(@(100)), $null, @(@($null))), -2)"; run = {{ Invoke-FlattenArray -Array @(0, 2, @(@(2, 3), 8, @(@(100)), $null, @(@($null))), -2) }}; expected = @(0, 2, 2, 3, 8, 100, -2) }}
    @{{ name = "all values in nested array are null"; input = "@($null, @(@(@($null))), $null, $null, @(@($null, $null), $null), $null)"; run = {{ Invoke-FlattenArray -Array @($null, @(@(@($null))), $null, $null, @(@($null, $null), $null), $null) }}; expected = @() }}
)
$results = foreach ($case in $cases) {{
    $actual = @(& $case.run)
    $actualJson = ConvertTo-Json -InputObject $actual -Compress
    $expectedJson = ConvertTo-Json -InputObject @($case.expected) -Compress
    [ordered]@{{
        name = $case.name
        input = $case.input
        expected = @($case.expected)
        actual = @($actual)
        passed = ($actualJson -ceq $expectedJson)
    }}
}}
$json = ConvertTo-Json -InputObject @($results) -Depth 8
Set-Content -LiteralPath $resultPath -Value $json -Encoding utf8
if (@($results | Where-Object {{ -not $_.passed }}).Count -gt 0) {{ exit 1 }}
'''


def run_child(pwsh: str, script_text: str, script_path: Path, cwd: Path) -> subprocess.CompletedProcess[str]:
    script_path.write_text(script_text, encoding="utf-8")
    return subprocess.run(
        [pwsh, "-NoProfile", "-NonInteractive", "-File", str(script_path)],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        timeout=180,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "work/R09-T034/results.json")
    parser.add_argument("--log", type=Path, default=ROOT / "work/R09-T034/runner.log")
    args = parser.parse_args()
    output = args.output.resolve()
    log_path = args.log.resolve()
    evidence: dict[str, object] = {
        "status": "failed",
        "task": "R09-T034",
        "exercise": "flatten-array",
        "checkedAtUtc": datetime.now(timezone.utc).isoformat(),
        "refactor": "Replace pipeline implicit `$_` with explicit `foreach ($item in $Array)`; recursive output is emitted in input order.",
        "referenceBaseline": "work/R09-T034/baseline/FlattenArray.example.ps1",
        "beforePester": None,
        "afterPester": None,
        "beforeOutputs": None,
        "afterOutputs": None,
        "outputsAgree": False,
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
        if not BASELINE.is_file():
            raise FileNotFoundError(f"Saved baseline reference is missing: {BASELINE}")
        if BASELINE.read_bytes() == example.read_bytes():
            raise AssertionError("The updated reference is identical to the saved baseline")
        evidence["learnerSolutionHashBefore"] = sha256(solution)

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

        with tempfile.TemporaryDirectory(prefix="flatten-array-R09-T034-") as temporary:
            workspace = Path(temporary)
            before = workspace / "before"
            after = workspace / "after"
            shutil.copytree(EXERCISE, before)
            shutil.copytree(EXERCISE, after)
            before_example = before / example.relative_to(EXERCISE)
            after_example = after / example.relative_to(EXERCISE)
            before_example.write_bytes(BASELINE.read_bytes())
            after_example.write_bytes(example.read_bytes())
            before_solution = before / solution.relative_to(EXERCISE)
            after_solution = after / solution.relative_to(EXERCISE)
            before_solution.write_bytes(before_example.read_bytes())
            after_solution.write_bytes(after_example.read_bytes())
            before_test = before / test_source.relative_to(EXERCISE)
            after_test = after / test_source.relative_to(EXERCISE)

            before_pester_json = workspace / "before-pester.json"
            after_pester_json = workspace / "after-pester.json"
            before_pester = run_child(
                pwsh,
                pester_runner(str(before_test), str(before_pester_json)),
                workspace / "before-pester.ps1",
                before,
            )
            after_pester = run_child(
                pwsh,
                pester_runner(str(after_test), str(after_pester_json)),
                workspace / "after-pester.ps1",
                after,
            )
            if not before_pester_json.is_file() or not after_pester_json.is_file():
                raise RuntimeError("A Pester child exited without writing its test summary")
            before_summary = json.loads(before_pester_json.read_text(encoding="utf-8-sig"))
            after_summary = json.loads(after_pester_json.read_text(encoding="utf-8-sig"))
            evidence["beforePester"] = {**before_summary, "exitCode": before_pester.returncode}
            evidence["afterPester"] = {**after_summary, "exitCode": after_pester.returncode}
            for label, result, summary in [
                ("before", before_pester, before_summary),
                ("after", after_pester, after_summary),
            ]:
                if result.returncode != 0:
                    raise RuntimeError(f"{label} Pester child returned exit code {result.returncode}")
                if summary["totalCount"] == 0:
                    raise AssertionError(f"{label} Pester run executed zero tests")
                if summary["failedCount"] != 0:
                    raise AssertionError(f"{label} Pester run had {summary['failedCount']} failures")
                if summary["totalCount"] != CASE_COUNT:
                    raise AssertionError(f"{label} Pester ran {summary['totalCount']} cases, expected {CASE_COUNT}")
            if before_summary["testNames"] != after_summary["testNames"]:
                raise AssertionError("Before and after Pester runs discovered different test names")

            before_probe_json = workspace / "before-probes.json"
            after_probe_json = workspace / "after-probes.json"
            before_probe_run = run_child(
                pwsh,
                probe_runner(str(before_solution), str(before_probe_json)),
                workspace / "before-probes.ps1",
                before,
            )
            after_probe_run = run_child(
                pwsh,
                probe_runner(str(after_solution), str(after_probe_json)),
                workspace / "after-probes.ps1",
                after,
            )
            if before_probe_run.returncode != 0 or after_probe_run.returncode != 0:
                raise RuntimeError("A before/after output comparison child returned a non-zero exit code")
            if not before_probe_json.is_file() or not after_probe_json.is_file():
                raise RuntimeError("A before/after output comparison did not write its evidence")
            before_outputs = json.loads(before_probe_json.read_text(encoding="utf-8-sig"))
            after_outputs = json.loads(after_probe_json.read_text(encoding="utf-8-sig"))
            evidence["beforeOutputs"] = before_outputs
            evidence["afterOutputs"] = after_outputs
            if len(before_outputs) != CASE_COUNT or len(after_outputs) != CASE_COUNT:
                raise AssertionError("The direct output comparison did not cover every enabled Pester case")
            if not all(case["passed"] for case in before_outputs + after_outputs):
                raise AssertionError("At least one direct case output differed from its expected result")
            if [case["actual"] for case in before_outputs] != [case["actual"] for case in after_outputs]:
                raise AssertionError("Before and after reference outputs differ")
            evidence["outputsAgree"] = True
            log_lines.extend([
                "$ pwsh -NoProfile -NonInteractive -File before-pester.ps1",
                before_pester.stdout.rstrip(),
                before_pester.stderr.rstrip(),
                "$ pwsh -NoProfile -NonInteractive -File after-pester.ps1",
                after_pester.stdout.rstrip(),
                after_pester.stderr.rstrip(),
                "Before/after case outputs: " + json.dumps(
                    [{"name": case["name"], "expected": case["expected"], "actual": case["actual"], "agree": True} for case in before_outputs],
                    sort_keys=True,
                ),
            ])

        evidence["learnerSolutionHashAfter"] = sha256(solution)
        if evidence["learnerSolutionHashBefore"] != evidence["learnerSolutionHashAfter"]:
            raise AssertionError("Learner solution changed during the isolated reference check")
        evidence["status"] = "passed"
        print(
            f"PASS: before and after each passed {CASE_COUNT}/{CASE_COUNT} Pester cases; "
            "all expected outputs match across both references and the learner file is unchanged."
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
