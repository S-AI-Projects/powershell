#!/usr/bin/env python3
"""Run the sum-of-multiples reference and a duplicate-counting mutant."""

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
EXERCISE = ROOT / "exercises/practice/sum-of-multiples"
MUTATION_MARKER = "break   # Break out of the foreach look because we've found a factor"
TEST_COUNT = 13
PROBES = [
    {"name": "existing canonical case", "multiples": [4, 6], "limit": 15, "expected": 30},
    {"name": "reduced diagnostic", "multiples": [1, 2], "limit": 3, "expected": 3},
]
REJECTING_CASE = {
    "id": "2d0d5faa-f177-4ad6-bde9-ebb865083751",
    "description": "factors not relatively prime",
    "testName": "Given the factors 4 6 and to a limit of 15 the sum of multiples should be 30",
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


def make_pester_runner(test_path: str, result_path: str) -> str:
    return f'''$ErrorActionPreference = "Stop"
$testPath = {ps_literal(test_path)}
$resultPath = {ps_literal(result_path)}
$result = Invoke-Pester -Path $testPath -PassThru -Output Detailed
$summary = [ordered]@{{
    totalCount = [int]$result.TotalCount
    passedCount = [int]$result.PassedCount
    failedCount = [int]$result.FailedCount
    skippedCount = [int]$result.SkippedCount
}}
$summary | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $resultPath -Encoding utf8
if ($result.TotalCount -eq 0) {{ exit 2 }}
if ($result.FailedCount -ne 0) {{ exit 1 }}
exit 0
'''


def make_probe_runner(solution_path: str, result_path: str) -> str:
    return f'''$ErrorActionPreference = "Stop"
$solutionPath = {ps_literal(solution_path)}
$resultPath = {ps_literal(result_path)}
. $solutionPath
$probes = @(
    @{{ name = "existing canonical case"; multiples = @(4, 6); limit = 15; expected = 30 }}
    @{{ name = "reduced diagnostic"; multiples = @(1, 2); limit = 3; expected = 3 }}
)
$results = foreach ($probe in $probes) {{
    $actual = Get-SumOfMultiples -Multiples $probe.multiples -Limit $probe.limit
    [ordered]@{{
        name = $probe.name
        multiples = @($probe.multiples)
        limit = [int]$probe.limit
        expected = [int]$probe.expected
        actual = [int]$actual
        matchesExpected = ([int]$actual -eq [int]$probe.expected)
    }}
}}
$json = ConvertTo-Json -InputObject @($results) -Depth 6
Set-Content -LiteralPath $resultPath -Value $json -Encoding utf8
'''


def create_copy(source: Path, destination: Path, solution_rel: Path, example: Path, mutate: bool) -> None:
    shutil.copytree(source, destination)
    copied_solution = destination / solution_rel
    copied_solution.write_bytes(example.read_bytes())
    if mutate:
        source_text = copied_solution.read_text(encoding="utf-8")
        if source_text.count(MUTATION_MARKER) != 1:
            raise AssertionError("Could not find exactly one target break statement for the scratch mutation")
        copied_solution.write_text(
            source_text.replace(MUTATION_MARKER, "# mutation: keep checking after a matching factor"),
            encoding="utf-8",
        )


def run_pester(pwsh: str, test_path: Path, workspace: Path, label: str) -> dict[str, object]:
    result_path = workspace / f"{label}-pester.json"
    runner_path = workspace / f"{label}-pester.ps1"
    runner_path.write_text(make_pester_runner(str(test_path), str(result_path)), encoding="utf-8")
    run = subprocess.run(
        [pwsh, "-NoProfile", "-NonInteractive", "-File", str(runner_path)],
        cwd=test_path.parent,
        text=True,
        capture_output=True,
        check=False,
        timeout=180,
    )
    if not result_path.is_file():
        raise RuntimeError(f"{label} Pester run produced no summary (exit {run.returncode})")
    summary = json.loads(result_path.read_text(encoding="utf-8-sig"))
    return {"exitCode": run.returncode, "summary": summary, "stdout": run.stdout, "stderr": run.stderr}


def run_probes(pwsh: str, solution: Path, workspace: Path, label: str) -> list[dict[str, object]]:
    result_path = workspace / f"{label}-probes.json"
    runner_path = workspace / f"{label}-probes.ps1"
    runner_path.write_text(make_probe_runner(str(solution), str(result_path)), encoding="utf-8")
    run = subprocess.run(
        [pwsh, "-NoProfile", "-NonInteractive", "-File", str(runner_path)],
        cwd=solution.parent,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    if run.returncode != 0 or not result_path.is_file():
        raise RuntimeError(f"{label} diagnostic probes failed to execute: {run.stderr.strip()}")
    parsed = json.loads(result_path.read_text(encoding="utf-8-sig"))
    return parsed if isinstance(parsed, list) else [parsed]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "work/R09-T033/results.json")
    parser.add_argument("--log", type=Path, default=ROOT / "work/R09-T033/runner.log")
    args = parser.parse_args()
    output = args.output.resolve()
    log_path = args.log.resolve()
    evidence: dict[str, object] = {
        "status": "failed",
        "task": "R09-T033",
        "exercise": "sum-of-multiples",
        "checkedAtUtc": datetime.now(timezone.utc).isoformat(),
        "mutation": "Remove the inner-loop break so a value shared by factors is added for every matching factor.",
        "rejectingCase": REJECTING_CASE,
        "probes": PROBES,
        "referencePester": None,
        "mutantPester": None,
        "referenceProbeResults": None,
        "mutantProbeResults": None,
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

        with tempfile.TemporaryDirectory(prefix="sum-of-multiples-R09-T033-") as temporary:
            workspace = Path(temporary)
            reference = workspace / "reference"
            mutant = workspace / "mutant"
            solution_rel = solution.relative_to(EXERCISE)
            create_copy(EXERCISE, reference, solution_rel, example, mutate=False)
            create_copy(EXERCISE, mutant, solution_rel, example, mutate=True)
            reference_solution = reference / solution_rel
            mutant_solution = mutant / solution_rel
            reference_test = reference / test_source.relative_to(EXERCISE)
            mutant_test = mutant / test_source.relative_to(EXERCISE)

            reference_run = run_pester(pwsh, reference_test, workspace, "reference")
            mutant_run = run_pester(pwsh, mutant_test, workspace, "mutant")
            reference_summary = reference_run["summary"]
            mutant_summary = mutant_run["summary"]
            evidence["referencePester"] = {
                "exitCode": reference_run["exitCode"],
                "totalCount": reference_summary["totalCount"],
                "passedCount": reference_summary["passedCount"],
                "failedCount": reference_summary["failedCount"],
                "skippedCount": reference_summary["skippedCount"],
            }
            evidence["mutantPester"] = {
                "exitCode": mutant_run["exitCode"],
                "totalCount": mutant_summary["totalCount"],
                "passedCount": mutant_summary["passedCount"],
                "failedCount": mutant_summary["failedCount"],
                "skippedCount": mutant_summary["skippedCount"],
            }

            if reference_run["exitCode"] != 0:
                raise RuntimeError("Original reference Pester run returned a non-zero exit code")
            if reference_summary["totalCount"] != TEST_COUNT or reference_summary["failedCount"] != 0:
                raise AssertionError(f"Original reference did not pass all {TEST_COUNT} Pester cases")
            if mutant_summary["totalCount"] != TEST_COUNT or mutant_summary["failedCount"] == 0:
                raise AssertionError("Mutant did not produce a failing assertion across the complete test suite")
            if mutant_run["exitCode"] != 1:
                raise RuntimeError(f"Expected mutant Pester failure exit code 1, got {mutant_run['exitCode']}")

            mutant_stdout = mutant_run["stdout"]
            case_line = f"[-] {REJECTING_CASE['testName']}"
            expected_line = "Expected exactly 30, but got 42."
            if case_line not in mutant_stdout or expected_line not in mutant_stdout:
                raise AssertionError("The mutant output did not show the named case rejecting 42 instead of 30")
            if f"[+] {REJECTING_CASE['testName']}" not in reference_run["stdout"]:
                raise AssertionError("The original output did not pass the named rejecting case")

            reference_probes = run_probes(pwsh, reference_solution, workspace, "reference")
            mutant_probes = run_probes(pwsh, mutant_solution, workspace, "mutant")
            evidence["referenceProbeResults"] = reference_probes
            evidence["mutantProbeResults"] = mutant_probes
            if len(reference_probes) != len(PROBES) or len(mutant_probes) != len(PROBES):
                raise AssertionError("Diagnostic probe count did not match the documented inputs")
            for reference_probe, mutant_probe, probe in zip(reference_probes, mutant_probes, PROBES, strict=True):
                if reference_probe["name"] != probe["name"] or reference_probe["actual"] != probe["expected"]:
                    raise AssertionError(f"Original reference failed diagnostic probe: {probe['name']}")
                if mutant_probe["name"] != probe["name"]:
                    raise AssertionError(f"Mutant probe order changed: {probe['name']}")
            if mutant_probes[0]["actual"] != 42 or mutant_probes[1]["actual"] != 5:
                raise AssertionError("Mutant probe actual values differ from documented evidence")

            log_lines.extend([
                "$ pwsh -NoProfile -NonInteractive -File reference-pester.ps1",
                reference_run["stdout"].rstrip(),
                reference_run["stderr"].rstrip(),
                "$ pwsh -NoProfile -NonInteractive -File mutant-pester.ps1 (expected assertion failures)",
                mutant_run["stdout"].rstrip(),
                mutant_run["stderr"].rstrip(),
                "Reference diagnostic probes: " + json.dumps(reference_probes, sort_keys=True),
                "Mutant diagnostic probes: " + json.dumps(mutant_probes, sort_keys=True),
            ])

        evidence["learnerSolutionHashAfter"] = sha256(solution)
        if evidence["learnerSolutionHashBefore"] != evidence["learnerSolutionHashAfter"]:
            raise AssertionError("Learner solution changed during the isolated mutation check")
        evidence["status"] = "passed"
        print(
            f"PASS: reference {reference_summary['passedCount']}/{reference_summary['totalCount']}; "
            f"mutant rejected by {mutant_summary['failedCount']}/{mutant_summary['totalCount']} cases; "
            "named assertion and both diagnostic probes confirmed."
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
