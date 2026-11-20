#!/usr/bin/env python3
"""Check linked-list reference behavior and the return/enumeration hint examples."""

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
EXERCISE = ROOT / "exercises/practice/linked-list"
SCALAR_EXPECTED = "7|Int32|1"
PIPELINE_EXPECTED = [7, 8]


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


def micro_example_runner(solution_path: str, result_path: str) -> str:
    return f'''$ErrorActionPreference = "Stop"
$solutionPath = {ps_literal(solution_path)}
$resultPath = {ps_literal(result_path)}
. $solutionPath
$route = [LinkedList]::new()
$route.Push(7)
$station = $route.Pop()
$scalarOutput = "{{0}}|{{1}}|{{2}}" -f $station, $station.GetType().Name, @($station).Count
$route.Push([object[]]@(7, 8))
$removed = $route.Pop()
$pipelineRecords = @($removed | ForEach-Object {{ $_ }})
$evidence = [ordered]@{{
    scalarExample = [ordered]@{{
        input = "Push(7), then Pop()"
        expected = "7|Int32|1"
        actual = $scalarOutput
        value = $station
        typeName = $station.GetType().Name
        arrayCaptureCount = @($station).Count
        passed = ($scalarOutput -ceq "7|Int32|1")
    }}
    pipelineContrast = [ordered]@{{
        input = "Push([object[]]@(7, 8)), then Pop() | ForEach-Object {{ $_ }}"
        expectedPipelineRecords = @(7, 8)
        actualPipelineRecords = @($pipelineRecords)
        poppedArrayCount = $removed.Count
        passed = ((@($pipelineRecords) -join ",") -ceq "7,8")
    }}
}}
$evidence | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $resultPath -Encoding utf8
if (-not $evidence.scalarExample.passed -or -not $evidence.pipelineContrast.passed) {{ exit 1 }}
'''


def run_child(pwsh: str, script: str, script_path: Path, cwd: Path, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    script_path.write_text(script, encoding="utf-8")
    return subprocess.run(
        [pwsh, "-NoProfile", "-NonInteractive", "-File", str(script_path)],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "work/R09-T037/results.json")
    parser.add_argument("--log", type=Path, default=ROOT / "work/R09-T037/runner.log")
    args = parser.parse_args()
    output = args.output.resolve()
    log_path = args.log.resolve()
    evidence: dict[str, object] = {
        "status": "failed",
        "task": "R09-T037",
        "exercise": "linked-list",
        "checkedAtUtc": datetime.now(timezone.utc).isoformat(),
        "selectedConstruct": "Explicit return of the removed value in LinkedList.Pop() and LinkedList.Shift().",
        "scalarExample": None,
        "pipelineContrast": None,
        "pester": None,
        "testCountDeclared": None,
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
        evidence["learnerSolutionHashBefore"] = hashlib.sha256(solution.read_bytes()).hexdigest()
        test_count = len(re.findall(r"(?m)^\s*It\s+\"", test_source.read_text(encoding="utf-8")))
        evidence["testCountDeclared"] = test_count

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

        with tempfile.TemporaryDirectory(prefix="linked-list-R09-T037-") as temporary:
            root = Path(temporary)
            temp_exercise = root / "linked-list"
            shutil.copytree(EXERCISE, temp_exercise)
            temp_solution = temp_exercise / solution.relative_to(EXERCISE)
            temp_test = temp_exercise / test_source.relative_to(EXERCISE)
            temp_solution.write_bytes(example.read_bytes())

            pester_json = root / "pester.json"
            pester = run_child(
                pwsh,
                pester_runner(str(temp_test), str(pester_json)),
                root / "pester.ps1",
                temp_exercise,
            )
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
            if pester_summary["totalCount"] != test_count:
                raise AssertionError(f"Pester ran {pester_summary['totalCount']} cases; test source declares {test_count}")

            micro_json = root / "micro-examples.json"
            micro = run_child(
                pwsh,
                micro_example_runner(str(temp_solution), str(micro_json)),
                root / "micro-examples.ps1",
                temp_exercise,
            )
            log_lines.extend(["$ pwsh -NoProfile -NonInteractive -File micro-examples.ps1", micro.stdout.rstrip(), micro.stderr.rstrip()])
            if micro.returncode != 0 or not micro_json.is_file():
                raise RuntimeError(f"Micro-example child failed with exit code {micro.returncode}: {micro.stderr.strip()}")
            micro_result = json.loads(micro_json.read_text(encoding="utf-8-sig"))
            evidence["scalarExample"] = micro_result["scalarExample"]
            evidence["pipelineContrast"] = micro_result["pipelineContrast"]
            if not micro_result["scalarExample"]["passed"] or micro_result["scalarExample"]["actual"] != SCALAR_EXPECTED:
                raise AssertionError("Scalar Pop() micro-example differed from the documented output")
            if not micro_result["pipelineContrast"]["passed"] or micro_result["pipelineContrast"]["actualPipelineRecords"] != PIPELINE_EXPECTED:
                raise AssertionError("Array pipeline contrast differed from the documented output")

        after_hash = hashlib.sha256(solution.read_bytes()).hexdigest()
        evidence["learnerSolutionHashAfter"] = after_hash
        if evidence["learnerSolutionHashBefore"] != after_hash:
            raise AssertionError("Learner solution changed during the isolated check")
        evidence["status"] = "passed"
        print(
            f"PASS: Pester {pester_version.stdout.strip()} on PowerShell {version.stdout.strip()}, "
            f"{pester_summary['passedCount']}/{pester_summary['totalCount']} cases; both micro-examples matched."
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
