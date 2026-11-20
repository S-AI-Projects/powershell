#!/usr/bin/env python3
"""Check the Dot DSL reference and measure warmed graph construction."""

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
EXERCISE = ROOT / "exercises/practice/dot-dsl"
SIZES = [10, 50, 100]
REPETITIONS = 5
PESTER_CASE_COUNT = 8


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


def pester_runner(test_path: str, output_path: str) -> str:
    return f'''$ErrorActionPreference = "Stop"
$testPath = {ps_literal(test_path)}
$outputPath = {ps_literal(output_path)}
$result = Invoke-Pester -Path $testPath -PassThru -Output Detailed
$summary = [ordered]@{{
    totalCount = [int]$result.TotalCount
    passedCount = [int]$result.PassedCount
    failedCount = [int]$result.FailedCount
    skippedCount = [int]$result.SkippedCount
    testNames = @($result.Tests | ForEach-Object {{ $_.Name }})
}}
$summary | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $outputPath -Encoding utf8
if ($result.TotalCount -eq 0) {{ exit 2 }}
if ($result.FailedCount -ne 0) {{ exit 1 }}
exit 0
'''


def benchmark_runner(solution_path: str, output_path: str) -> str:
    return f'''$ErrorActionPreference = "Stop"
$solutionPath = {ps_literal(solution_path)}
$outputPath = {ps_literal(output_path)}
. $solutionPath
$sizes = @({", ".join(str(size) for size in SIZES)})
$repetitions = {REPETITIONS}
$results = foreach ($size in $sizes) {{
    $nodes = @(
        for ($index = 0; $index -lt $size; $index++) {{
            [Node]::new("node-$index")
        }}
    )

    # Validate the constructed graph before timing it.
    $check = [Graph]::new($nodes)
    if ($check.Nodes.Count -ne $size -or $check.Edges.Count -ne 0 -or $check.Attrs.Count -ne 0) {{
        throw "Incorrect graph contents for size $size"
    }}

    # Warm the constructor and exclude input creation and class loading from each sample.
    [void][Graph]::new($nodes)
    $times = @(
        for ($repeat = 0; $repeat -lt $repetitions; $repeat++) {{
            $watch = [System.Diagnostics.Stopwatch]::StartNew()
            $graph = [Graph]::new($nodes)
            $watch.Stop()
            if ($graph.Nodes.Count -ne $size -or $graph.Edges.Count -ne 0 -or $graph.Attrs.Count -ne 0) {{
                throw "Incorrect timed graph contents for size $size"
            }}
            [Math]::Round($watch.Elapsed.TotalMilliseconds, 6)
        }}
    )
    $sortedTimes = @($times | Sort-Object)
    $copies = [long]($size * ($size - 1) / 2)
    [ordered]@{{
        inputSize = [int]$size
        expected = [ordered]@{{ nodes = [int]$size; edges = 0; attrs = 0 }}
        actual = [ordered]@{{ nodes = [int]$check.Nodes.Count; edges = [int]$check.Edges.Count; attrs = [int]$check.Attrs.Count }}
        recordVisits = [int]$size
        nodeAppends = [int]$size
        existingSlotsCopied = $copies
        repetitions = [int]$repetitions
        timesMilliseconds = @($times)
        medianMilliseconds = [double]$sortedTimes[[int][Math]::Floor($repetitions / 2)]
    }}
}}
$result = [ordered]@{{
    timingScope = "Graph constructor only; class load, process startup, input creation, preflight and warm-up excluded"
    sizes = @($results)
}}
$result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $outputPath -Encoding utf8
'''


def run_child(pwsh: str, script: str, path: Path, cwd: Path, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    path.write_text(script, encoding="utf-8")
    return subprocess.run(
        [pwsh, "-NoProfile", "-NonInteractive", "-File", str(path)],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "work/R09-T035/results.json")
    parser.add_argument("--log", type=Path, default=ROOT / "work/R09-T035/runner.log")
    args = parser.parse_args()
    output = args.output.resolve()
    log_path = args.log.resolve()
    evidence: dict[str, object] = {
        "status": "failed",
        "task": "R09-T035",
        "exercise": "dot-dsl",
        "checkedAtUtc": datetime.now(timezone.utc).isoformat(),
        "inputDefinition": "Number of Node records passed to Graph([object[]] $Data)",
        "sizes": SIZES,
        "repetitionsPerSize": REPETITIONS,
        "timingScope": "Graph constructor only; excludes process startup, class loading, input creation, preflight and warm-up",
        "algorithmCounts": {"recordVisits": "n", "nodeAppends": "n", "existingNodeSlotsCopied": "n(n-1)/2"},
        "pester": None,
        "benchmark": None,
        "powerShellVersion": None,
        "pesterVersion": None,
        "learnerSolutionHashBefore": None,
        "learnerSolutionHashAfter": None,
    }
    log_lines: list[str] = []

    try:
        config = json.loads((EXERCISE / ".meta/config.json").read_text(encoding="utf-8"))
        solution = configured_file(config, "solution")
        test_source = configured_file(config, "test")
        example = configured_file(config, "example")
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

        with tempfile.TemporaryDirectory(prefix="dot-dsl-R09-T035-") as temporary:
            temporary_root = Path(temporary)
            temp_exercise = temporary_root / "dot-dsl"
            shutil.copytree(EXERCISE, temp_exercise)
            temp_solution = temp_exercise / solution.relative_to(EXERCISE)
            temp_test = temp_exercise / test_source.relative_to(EXERCISE)
            temp_solution.write_bytes(example.read_bytes())

            pester_json = temporary_root / "pester.json"
            pester = run_child(
                pwsh,
                pester_runner(str(temp_test), str(pester_json)),
                temporary_root / "pester.ps1",
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
            if pester_summary["totalCount"] != PESTER_CASE_COUNT:
                raise AssertionError(f"Pester ran {pester_summary['totalCount']} cases, expected {PESTER_CASE_COUNT}")

            benchmark_json = temporary_root / "benchmark.json"
            benchmark = run_child(
                pwsh,
                benchmark_runner(str(temp_solution), str(benchmark_json)),
                temporary_root / "benchmark.ps1",
                temp_exercise,
                timeout=300,
            )
            log_lines.extend(["$ pwsh -NoProfile -NonInteractive -File benchmark.ps1", benchmark.stdout.rstrip(), benchmark.stderr.rstrip()])
            if benchmark.returncode != 0 or not benchmark_json.is_file():
                raise RuntimeError(f"Benchmark child failed with exit code {benchmark.returncode}: {benchmark.stderr.strip()}")
            benchmark_result = json.loads(benchmark_json.read_text(encoding="utf-8-sig"))
            evidence["benchmark"] = benchmark_result
            observed = benchmark_result["sizes"]
            if [item["inputSize"] for item in observed] != SIZES:
                raise AssertionError("Benchmark input sizes did not match the declared sizes")
            for item in observed:
                size = item["inputSize"]
                if item["expected"] != item["actual"]:
                    raise AssertionError(f"Graph contents differed from expected values at size {size}")
                if item["repetitions"] != REPETITIONS or len(item["timesMilliseconds"]) != REPETITIONS:
                    raise AssertionError(f"Expected {REPETITIONS} timings at size {size}")
                expected_copies = size * (size - 1) // 2
                if item["existingSlotsCopied"] != expected_copies:
                    raise AssertionError(f"Unexpected append-copy count at size {size}")

        after_hash = hashlib.sha256(solution.read_bytes()).hexdigest()
        evidence["learnerSolutionHashAfter"] = after_hash
        if evidence["learnerSolutionHashBefore"] != after_hash:
            raise AssertionError("Learner solution changed during the isolated check")
        evidence["status"] = "passed"
        print(
            f"PASS: Pester {pester_version.stdout.strip()} on PowerShell {version.stdout.strip()}, "
            f"{pester_summary['passedCount']}/{pester_summary['totalCount']} cases; "
            f"five benchmark runs at each of {', '.join(map(str, SIZES))} node sizes."
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
