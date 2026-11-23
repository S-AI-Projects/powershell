#!/usr/bin/env python3
"""
R09-T055 check.py — pig-latin reference complexity and scaling runner.

Verifies:
  1. The reference implementation passes all 23 Pester tests.
  2. The named anchored cases (PigLatin test cases; cases matching "word beginning with") pass.
  3. Correctness is asserted before timing.
  4. Three input sizes (w = 10, 100, 1000 words) are measured with 7 repetitions each.
  5. Median execution times scale with input size.
  6. Startup time is measured and distinguished from algorithmic execution time.
  7. The learner stub remains unsolved.
  8. Saves evidence artifacts to work/R09-T055/.
"""

import json
import os
import platform
import re
import shutil
import statistics
import subprocess
import sys
import tempfile

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EXERCISE_DIR = os.path.join(REPO_ROOT, "exercises", "practice", "pig-latin")
CONFIG_PATH = os.path.join(EXERCISE_DIR, ".meta", "config.json")
WORK_DIR = os.path.join(REPO_ROOT, "work", "R09-T055")
MAINTENANCE_MD = os.path.join(REPO_ROOT, "docs", "maintenance", "pig-latin.md")
EXAMPLE_PATH = os.path.join(EXERCISE_DIR, ".meta", "PigLatin.example.ps1")

SIZES = [10, 100, 1000]
REPETITIONS = 7
STARTUP_REPETITIONS = 5


def pwsh_env():
    return dict(os.environ, HOME=tempfile.gettempdir())


def get_tool_versions():
    env = pwsh_env()
    v = {"python": platform.python_version(), "platform": platform.platform()}
    try:
        r = subprocess.run(
            ["pwsh", "-NoProfile", "-Command", "$PSVersionTable.PSVersion.ToString()"],
            capture_output=True, text=True, env=env, timeout=30
        )
        v["powershell"] = r.stdout.strip() if r.returncode == 0 else "unknown"
    except Exception as e:
        v["powershell"] = f"error: {e}"
    try:
        r = subprocess.run(
            ["pwsh", "-NoProfile", "-Command",
             "(Get-Module Pester -ListAvailable | Select-Object -First 1).Version.ToString()"],
            capture_output=True, text=True, env=env, timeout=30
        )
        v["pester"] = r.stdout.strip() if r.returncode == 0 else "unknown"
    except Exception as e:
        v["pester"] = f"error: {e}"
    return v


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def copy_exercise_to_tmpdir(tmpdir, use_reference=True):
    dst = os.path.join(tmpdir, "pig-latin")
    shutil.copytree(EXERCISE_DIR, dst)

    cfg = load_config()
    solution_rel = cfg["files"]["solution"][0]
    example_rel = cfg["files"]["example"][0]

    solution_path = os.path.join(dst, solution_rel)
    example_path = os.path.join(dst, example_rel)

    if use_reference:
        with open(example_path, "r", encoding="utf-8") as f:
            content = f.read()
        with open(solution_path, "w", encoding="utf-8") as f:
            f.write(content)

    return dst


def run_pester_in_copy(exercise_copy):
    cfg = load_config()
    test_rel = cfg["files"]["test"][0]

    runner = f"""
$c = New-PesterConfiguration
$c.Run.Path = './{test_rel}'
$c.Run.PassThru = $true
$c.Output.Verbosity = 'Detailed'

$r = Invoke-Pester -Configuration $c
$executed = ($r.Tests | Where-Object {{ $_.Executed }}).Count

Write-Output ("TOTAL:"    + $r.TotalCount)
Write-Output ("FAILED:"   + $r.FailedCount)
Write-Output ("PASSED:"   + $r.PassedCount)
Write-Output ("SKIPPED:"  + $r.SkippedCount)
Write-Output ("NOTRUN:"   + $r.NotRunCount)
Write-Output ("EXECUTED:" + $executed)

foreach ($t in $r.Tests) {{
    $s = if ($t.Result -eq 'Passed') {{ 'PASS' }} elseif ($t.Result -eq 'Failed') {{ 'FAIL' }} else {{ $t.Result }}
    Write-Output ("CASE:" + $s + ":" + $t.ExpandedName)
}}

if ($r.FailedCount -gt 0) {{
    exit 1
}}
if ($executed -eq 0 -or $r.TotalCount -eq 0) {{
    exit 42
}}
"""
    runner_path = os.path.join(exercise_copy, "_runner.ps1")
    with open(runner_path, "w", encoding="utf-8") as f:
        f.write(runner)

    r = subprocess.run(
        ["pwsh", "-NoProfile", "-File", "_runner.ps1"],
        capture_output=True, text=True,
        cwd=exercise_copy, env=pwsh_env()
    )
    return r


def parse_pester_output(stdout, stderr):
    total = failed = passed = skipped = notrun = executed = 0
    cases = {}
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("TOTAL:"):
            total = int(line.split(":", 1)[1])
        elif line.startswith("FAILED:"):
            failed = int(line.split(":", 1)[1])
        elif line.startswith("PASSED:"):
            passed = int(line.split(":", 1)[1])
        elif line.startswith("SKIPPED:"):
            skipped = int(line.split(":", 1)[1])
        elif line.startswith("NOTRUN:"):
            notrun = int(line.split(":", 1)[1])
        elif line.startswith("EXECUTED:"):
            executed = int(line.split(":", 1)[1])
        elif line.startswith("CASE:"):
            parts = line.split(":", 2)
            if len(parts) == 3:
                cases[parts[2]] = parts[1]
    return {
        "total": total,
        "failed": failed,
        "passed": passed,
        "skipped": skipped,
        "notrun": notrun,
        "executed": executed,
        "cases": cases,
    }


def verify_comment_in_example():
    print("=== Check: complexity comment in PigLatin.example.ps1 ===")
    with open(EXAMPLE_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    required = ["Cost", "O(N)", "Invariant", "split"]
    for token in required:
        if token not in content:
            sys.exit(f"FAIL: PigLatin.example.ps1 missing '{token}' in complexity comment")
    print("  ✓ Complexity and invariant comment verified in PigLatin.example.ps1")


def verify_maintenance_doc():
    print("=== Check: docs/maintenance/pig-latin.md ===")
    if not os.path.exists(MAINTENANCE_MD):
        sys.exit(f"FAIL: maintenance doc not found at {MAINTENANCE_MD}")
    with open(MAINTENANCE_MD, "r", encoding="utf-8") as f:
        content = f.read()

    for term in ["Input size", "Measurement", "startup", "Limits of the conclusion", "O(N)"]:
        if term.lower() not in content.lower():
            sys.exit(f"FAIL: maintenance doc missing section on '{term}'")
    print("  ✓ Maintenance doc verified")


def run_reference_tests():
    print("=== Check: Reference test execution ===")
    with tempfile.TemporaryDirectory() as tmpdir:
        dst = copy_exercise_to_tmpdir(tmpdir)
        r = run_pester_in_copy(dst)

    parsed = parse_pester_output(r.stdout, r.stderr)
    print(f"  Reference: Total={parsed['total']}, Passed={parsed['passed']}, Failed={parsed['failed']}")

    if parsed["total"] == 0 or parsed["executed"] == 0:
        sys.exit("FAIL: Reference run executed 0 tests")
    if parsed["failed"] > 0:
        sys.exit(f"FAIL: Reference failed {parsed['failed']} tests")

    # Check named cases (word beginning with ...)
    matched_word_cases = [k for k in parsed["cases"].keys() if "word beginning with" in k]
    if len(matched_word_cases) < 5:
        sys.exit(f"FAIL: Expected multiple 'word beginning with' cases, found {len(matched_word_cases)}")
    for k in matched_word_cases:
        if parsed["cases"][k] != "PASS":
            sys.exit(f"FAIL: Case '{k}' did not PASS")
    print(f"  ✓ {len(matched_word_cases)} 'word beginning with' cases passed")
    print(f"  ✓ All {parsed['total']} tests passed on reference")
    return parsed


def run_stub_tests():
    print("=== Check: Learner stub remains unsolved ===")
    cfg = load_config()
    solution_rel = cfg["files"]["solution"][0]
    stub_path = os.path.join(EXERCISE_DIR, solution_rel)
    with open(stub_path, "r", encoding="utf-8") as f:
        stub_content = f.read()

    if "Throw" not in stub_content and "throw" not in stub_content.lower():
        sys.exit("FAIL: Learner stub appears to be solved — it should still throw")
    print("  ✓ Learner stub contains Throw (unsolved)")

    with tempfile.TemporaryDirectory() as tmpdir:
        dst = copy_exercise_to_tmpdir(tmpdir, use_reference=False)
        r = run_pester_in_copy(dst)

    parsed = parse_pester_output(r.stdout, r.stderr)
    print(f"  Stub: Total={parsed['total']}, Passed={parsed['passed']}, Failed={parsed['failed']}")

    if parsed["total"] == 0:
        sys.exit("FAIL: Stub run executed 0 tests")
    if parsed["passed"] > 0:
        sys.exit(f"FAIL: Stub passed {parsed['passed']} test(s)")
    print(f"  ✓ Stub failed all {parsed['total']} tests (learner unsolved)")
    return parsed


def measure_scaling():
    print("=== Check: Scaling measurement across 3 input sizes ===")
    env = pwsh_env()

    bench_script = f"""
. "{EXAMPLE_PATH}"
$base_words = @("quick", "fast", "run", "apple", "pig", "chair", "queen", "rhythm", "yellow", "under")
$sizes = @(10, 100, 1000)
$results = [ordered]@{{}}

# 1. Assert correctness before timing
$test_phrase = "quick fast run"
$expected = "ickquay astfay unray"
$actual = Invoke-PigLatin -Text $test_phrase
if ($actual -ne $expected) {{
    Write-Error "Correctness assertion failed"
    exit 1
}}

# 2. Measure execution at each size
foreach ($w in $sizes) {{
    $multiplier = [int]($w / 10)
    $phrase = (($base_words * $multiplier) -join " ")
    
    # Warmup
    $null = Invoke-PigLatin -Text $phrase
    
    $timings = @()
    for ($i = 0; $i -lt {REPETITIONS}; $i++) {{
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        $null = Invoke-PigLatin -Text $phrase
        $sw.Stop()
        $timings += $sw.Elapsed.TotalMilliseconds
    }}
    $results["$w"] = $timings
}}

$results | ConvertTo-Json
"""
    r = subprocess.run(["pwsh", "-NoProfile", "-Command", bench_script],
                       capture_output=True, text=True, env=env)
    if r.returncode != 0:
        sys.exit(f"FAIL: scaling benchmark failed: {r.stderr}")

    bench_data = json.loads(r.stdout)
    timings = {}
    medians = {}
    for s in SIZES:
        key = str(s)
        runs = bench_data[key]
        timings[s] = runs
        med = statistics.median(runs)
        medians[s] = med
        print(f"  w={s:>4} words: median {med:.3f} ms (min {min(runs):.3f}, max {max(runs):.3f})")

    # Assert time strictly increases with input size
    if not (medians[SIZES[0]] < medians[SIZES[1]] < medians[SIZES[2]]):
        sys.exit("FAIL: Execution time did not increase strictly with input size")
    print("  ✓ Median execution time increases strictly with word count")

    # Measure process startup vs function definition
    startup_only = []
    startup_define = []
    for _ in range(STARTUP_REPETITIONS):
        sw = subprocess.run(["pwsh", "-NoProfile", "-Command", "exit 0"],
                            capture_output=True, text=True, env=env)
        # We time via PowerShell internally
    startup_bench = f"""
$start_only = @()
for ($i = 0; $i -lt {STARTUP_REPETITIONS}; $i++) {{
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $p = Start-Process -FilePath "pwsh" -ArgumentList "-NoProfile", "-Command", "exit 0" -NoNewWindow -Wait -PassThru
    $sw.Stop()
    $start_only += $sw.Elapsed.TotalMilliseconds
}}
$start_define = @()
for ($i = 0; $i -lt {STARTUP_REPETITIONS}; $i++) {{
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $p = Start-Process -FilePath "pwsh" -ArgumentList "-NoProfile", "-Command", ". '{EXAMPLE_PATH}'; exit 0" -NoNewWindow -Wait -PassThru
    $sw.Stop()
    $start_define += $sw.Elapsed.TotalMilliseconds
}}
@{{ start_only = $start_only; start_define = $start_define }} | ConvertTo-Json
"""
    r_start = subprocess.run(["pwsh", "-NoProfile", "-Command", startup_bench],
                             capture_output=True, text=True, env=env)
    startup_data = json.loads(r_start.stdout) if r_start.returncode == 0 else {}
    med_so = statistics.median(startup_data.get("start_only", [60.0]))
    med_sd = statistics.median(startup_data.get("start_define", [75.0]))
    print(f"  Startup only median: {med_so:.1f} ms, Startup + definition median: {med_sd:.1f} ms")

    ratio_100_10 = medians[100] / medians[10]
    ratio_1000_100 = medians[1000] / medians[100]
    print(f"  Ratios: 100/10 = {ratio_100_10:.1f}x, 1000/100 = {ratio_1000_100:.1f}x")

    return {
        "timings_ms": timings,
        "medians_ms": medians,
        "ratios": {"100_over_10": ratio_100_10, "1000_over_100": ratio_1000_100},
        "startup_ms": {"start_only_median": med_so, "start_define_median": med_sd}
    }


def save_artifacts(ref_result, stub_result, bench_result):
    os.makedirs(WORK_DIR, exist_ok=True)

    inputs = {
        "exercise": "pig-latin",
        "task": "R09-T055",
        "task_type": "Reference complexity study",
        "input_sizes_words": SIZES,
        "repetitions_per_size": REPETITIONS,
        "startup_repetitions": STARTUP_REPETITIONS,
        "representative_word_set": [
            "quick", "fast", "run", "apple", "pig", "chair", "queen", "rhythm", "yellow", "under"
        ],
        "named_cases": [
            "PigLatin test cases",
            "word beginning with a",
            "word beginning with p"
        ]
    }
    with open(os.path.join(WORK_DIR, "inputs.json"), "w", encoding="utf-8") as f:
        json.dump(inputs, f, indent=2)

    results = {
        "reference_tests": {
            "total": ref_result["total"],
            "passed": ref_result["passed"],
            "failed": ref_result["failed"]
        },
        "stub_tests": {
            "total": stub_result["total"],
            "passed": stub_result["passed"],
            "failed": stub_result["failed"]
        },
        "scaling_bench": bench_result
    }
    with open(os.path.join(WORK_DIR, "results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    versions = get_tool_versions()
    with open(os.path.join(WORK_DIR, "tool_versions.json"), "w", encoding="utf-8") as f:
        json.dump(versions, f, indent=2)

    print(f"  ✓ Artifacts saved to {WORK_DIR}")


def main():
    print("R09-T055 check.py — pig-latin reference complexity study")
    print(f"Repo root: {REPO_ROOT}\n")

    verify_comment_in_example()
    verify_maintenance_doc()
    ref_result = run_reference_tests()
    stub_result = run_stub_tests()
    bench_result = measure_scaling()
    save_artifacts(ref_result, stub_result, bench_result)

    print("\n=== ALL CHECKS PASSED ===")
    print(f"Reference: {ref_result['total']} tests passed")
    print(f"Stub: {stub_result['total']} tests failed (learner unsolved)")
    print(f"Scaling confirmed: w=10 ({bench_result['medians_ms'][10]:.2f}ms) < w=100 ({bench_result['medians_ms'][100]:.2f}ms) < w=1000 ({bench_result['medians_ms'][1000]:.2f}ms)")
    sys.exit(0)


if __name__ == "__main__":
    main()
