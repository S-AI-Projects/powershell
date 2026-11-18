#!/usr/bin/env python3
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXERCISE_DIR = REPO_ROOT / "exercises" / "practice" / "rectangles"
CONFIG_PATH = EXERCISE_DIR / ".meta" / "config.json"
EVIDENCE_DIR = REPO_ROOT / "work" / "R09-T005"

def run_pester(exercise_dir):
    env = os.environ.copy()
    env["HOME"] = "/tmp"
    ps_module_dir = str(REPO_ROOT / ".modules")
    sys_module_dir = "/opt/homebrew/Cellar/powershell/7.7.0/libexec/Modules"
    env["PSModulePath"] = f"{ps_module_dir}:{sys_module_dir}"

    ps_cmd = (
        f"Push-Location '{exercise_dir}'; "
        "$res = Invoke-Pester -PassThru; "
        "Pop-Location; "
        "$summary = @{ TotalCount = $res.TotalCount; PassedCount = $res.PassedCount; FailedCount = $res.FailedCount }; "
        "ConvertTo-Json $summary -Compress"
    )

    proc = subprocess.run(
        ["pwsh", "-NoProfile", "-Command", ps_cmd],
        capture_output=True,
        text=True,
        env=env,
    )
    lines = [line.strip() for line in proc.stdout.splitlines() if line.strip().startswith("{")]
    if not lines:
        sys.exit(f"Failed to parse Pester JSON output:\n{proc.stdout}\n{proc.stderr}")
    return json.loads(lines[-1]), proc.stdout

def benchmark_sizes(example_file):
    env = os.environ.copy()
    env["HOME"] = "/tmp"

    bench_script = f"""
    . '{example_file}'
    $small = @("++", "++")
    $medium = @("  +-+", "  | |", "+-+-+", "| | |", "+-+-+")
    $large = @(
        "+---+--+----+",
        "|   +--+----+",
        "+---+--+    |",
        "|   +--+----+",
        "+---+--+--+-+",
        "+---+--+--+-+",
        "+------+  | |",
        "          +-+"
    )

    Function Measure-Case($inputDiagram, $reps) {{
        $times = @()
        for ($i=0; $i -lt $reps; $i++) {{
            $sw = [System.Diagnostics.Stopwatch]::StartNew()
            $ans = Get-Rectangles -Strings $inputDiagram
            $sw.Stop()
            $times += $sw.Elapsed.TotalMilliseconds
        }}
        return @{{ Ans = $ans; Times = $times }}
    }}

    $resSmall = Measure-Case $small 7
    $resMed = Measure-Case $medium 7
    $resLarge = Measure-Case $large 7

    $output = @{{
        Small = $resSmall
        Medium = $resMed
        Large = $resLarge
    }}
    ConvertTo-Json $output -Depth 4 -Compress
    """

    proc = subprocess.run(
        ["pwsh", "-NoProfile", "-Command", bench_script],
        capture_output=True,
        text=True,
        env=env,
    )
    lines = [line.strip() for line in proc.stdout.splitlines() if line.strip().startswith("{")]
    if not lines:
        sys.exit(f"Failed to parse benchmark JSON output:\n{proc.stdout}\n{proc.stderr}")
    return json.loads(lines[-1])

def main():
    print("=== Running R09-T005 check.py ===")
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    solution_rel = config["files"]["solution"][0]
    test_rel = config["files"]["test"][0]
    example_rel = config["files"]["example"][0]

    # Verify learner stub is unsolved
    stub_path = EXERCISE_DIR / solution_rel
    stub_content = stub_path.read_text(encoding="utf-8")
    assert "Throw \"Please implement this function\"" in stub_content, "Learner stub must remain unsolved!"

    # 1. Pester test run in temporary directory
    print("Running Pester tests against reference solution...")
    with tempfile.TemporaryDirectory() as tmp:
        copy_dir = Path(tmp) / "rectangles"
        shutil.copytree(EXERCISE_DIR, copy_dir)
        shutil.copy2(copy_dir / example_rel, copy_dir / solution_rel)

        summary, stdout = run_pester(copy_dir)
        print(f"Pester results: Total={summary['TotalCount']}, Passed={summary['PassedCount']}, Failed={summary['FailedCount']}")
        assert summary["TotalCount"] > 0, "No tests executed!"
        assert summary["FailedCount"] == 0, f"{summary['FailedCount']} tests failed!"

    # 2. Benchmark scaling across 3 valid domain sizes
    print("Measuring scaling over small, medium, and large inputs (median over repetitions)...")
    bench_data = benchmark_sizes(EXERCISE_DIR / example_rel)

    small_ans = bench_data["Small"]["Ans"]
    small_median = statistics.median(bench_data["Small"]["Times"])
    assert small_ans == 1, f"Small input returned {small_ans}, expected 1"

    med_ans = bench_data["Medium"]["Ans"]
    med_median = statistics.median(bench_data["Medium"]["Times"])
    assert med_ans == 5, f"Medium input returned {med_ans}, expected 5"

    large_ans = bench_data["Large"]["Ans"]
    large_median = statistics.median(bench_data["Large"]["Times"])
    assert large_ans == 60, f"Large input returned {large_ans}, expected 60"

    print(f"Small (2x2): answer={small_ans}, median={small_median:.3f} ms")
    print(f"Medium (5x5): answer={med_ans}, median={med_median:.3f} ms")
    print(f"Large (8x13): answer={large_ans}, median={large_median:.3f} ms")

    # 3. Save evidence
    results = {
        "task_id": "R09-T005",
        "exercise": "rectangles",
        "pester_results": summary,
        "benchmark_results": {
            "small": {"grid": "2x2", "rectangles": small_ans, "median_ms": round(small_median, 3)},
            "medium": {"grid": "5x5", "rectangles": med_ans, "median_ms": round(med_median, 3)},
            "large": {"grid": "8x13", "rectangles": large_ans, "median_ms": round(large_median, 3)}
        },
        "complexity": "O(R * C * (R + C) + E_H^2) where E_H is number of horizontal segments",
        "tools": {
            "python": sys.version,
            "powershell": "7.7.0",
            "pester": "6.2.0"
        },
        "success": True
    }

    with open(EVIDENCE_DIR / "results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    with open(EVIDENCE_DIR / "run.log", "w", encoding="utf-8") as f:
        f.write("R09-T005 Automated Check Log\n")
        f.write(f"Pester Output:\n{stdout}\n")
        f.write(f"Benchmark Results:\n{json.dumps(results['benchmark_results'], indent=2)}\n")

    print(f"R09-T005 check completed successfully! Evidence saved to {EVIDENCE_DIR}")

if __name__ == "__main__":
    main()
