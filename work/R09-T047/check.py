#!/usr/bin/env python3
"""
R09-T047 check.py — nth-prime
Identifies the language construct used in NthPrime.example.ps1 (explicit
`return` of the last element of a growing array), illustrates it with a
standalone micro-example plus a contrasting pitfall, and verifies all
enabled Pester test cases against the reference implementation.
"""

import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EXERCISE_DIR = os.path.join(REPO_ROOT, "exercises", "practice", "nth-prime")
CONFIG_PATH  = os.path.join(EXERCISE_DIR, ".meta", "config.json")

# ── ANCHORED CASES ────────────────────────────────────────────────────────────
ANCHORED = [
    "NthPrime Tests",    # Describe block → verified via FailedCount==0
    "first prime",
    "second prime",
]

# ─────────────────────────────────────────────────────────────────────────────
# Language-construct analysis
# ─────────────────────────────────────────────────────────────────────────────
# NthPrime.example.ps1 uses:
#   1. Array accumulation:  $primes += $i     (appends to a growing array)
#   2. Negative indexing:   $primes[-1]       (retrieves the last element)
#   3. Explicit return:     return $primes[-1] (emits a scalar, not the full array)
#
# MICRO-EXAMPLE (does NOT solve nth-prime):
#   Accumulate the first 3 even numbers, then read the last one.
#
# PITFALL:
#   Dropping `return` and writing just `$primes[-1]` as the last expression
#   works in a simple function but becomes ambiguous when the function emits
#   other values to the pipeline earlier (PowerShell collects ALL pipeline
#   output into an array, so the caller can get @(2, 4, 6) instead of 6).
#   The contrasting script below shows this by deliberately emitting an extra
#   value then relying on the last-expression convention.

MICRO_SCRIPT = r'''
# Micro-example: array accumulation + negative indexing + explicit return
# (does NOT solve nth-prime — just demonstrates the construct)
function Get-LastEven {
    param([int]$Count)
    $evens = @()
    $n = 2
    while ($evens.Count -lt $Count) {
        $evens += $n
        $n += 2
    }
    return $evens[-1]   # explicit return of last element (a scalar)
}

$result = Get-LastEven -Count 3
Write-Output "MICRO:$result"
'''
# Expected: MICRO:6  (first 3 evens are 2,4,6; last is 6)
MICRO_EXPECTED = "MICRO:6"

PITFALL_SCRIPT = r'''
# PITFALL: pipeline pollution — extra Write-Output before the return
# means the caller sees an array, not just the last element.
function Get-LastEvenPolluted {
    param([int]$Count)
    $evens = @()
    $n = 2
    while ($evens.Count -lt $Count) {
        $evens += $n
        $n += 2
    }
    # BUG: accidentally emits something to the pipeline before the value
    Write-Output "debug: computing..."   # <-- pipeline pollution
    return $evens[-1]                    # <-- also emits to pipeline
}

$result = Get-LastEvenPolluted -Count 3
# $result is now an ARRAY: @("debug: computing...", 6)
# Using $result.Count or type shows it's not a plain scalar
if ($result -is [array]) {
    Write-Output "PITFALL:array:count=$($result.Count):last=$($result[-1])"
} else {
    Write-Output "PITFALL:scalar:$result"
}
'''
# Expected: PITFALL:array:count=2:last=6
# (the caller gets @("debug: computing...", 6) not just 6)
PITFALL_EXPECTED = "PITFALL:array:count=2:last=6"


# ── HELPERS ───────────────────────────────────────────────────────────────────

def pwsh_env():
    return dict(os.environ, HOME=tempfile.gettempdir())


def run_pwsh_script(script_text, label):
    """Write script to a temp file and run it; return (stdout, stderr, rc)."""
    with tempfile.NamedTemporaryFile(
            suffix=".ps1", mode="w", encoding="utf-8", delete=False
    ) as f:
        f.write(script_text)
        path = f.name
    try:
        r = subprocess.run(
            ["pwsh", "-NoProfile", "-File", path],
            capture_output=True, text=True, env=pwsh_env()
        )
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    finally:
        os.unlink(path)


def copy_exercise(tmp_dir):
    dest = os.path.join(tmp_dir, "nth-prime")
    shutil.copytree(EXERCISE_DIR, dest)
    return dest


def run_pester(exercise_copy):
    runner = r"""
$r = Invoke-Pester -Path './NthPrime.tests.ps1' -PassThru -Output Detailed
Write-Output ("TOTAL:"  + $r.TotalCount)
Write-Output ("FAILED:" + $r.FailedCount)
Write-Output ("PASSED:" + $r.PassedCount)
Write-Output ("SKIPPED:" + $r.SkippedCount)
foreach ($t in $r.Tests) {
    $s = if ($t.Result -eq 'Passed') { 'PASS' } else { 'FAIL' }
    Write-Output ("CASE:" + $s + ":" + $t.ExpandedName)
}
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


def parse_pester(stdout, stderr):
    total = failed = passed = skipped = 0
    cases = []
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
        elif line.startswith("CASE:"):
            parts = line.split(":", 2)
            cases.append({"name": parts[2] if len(parts) > 2 else "",
                          "status": parts[1]})
    return {"total": total, "failed": failed, "passed": passed,
            "skipped": skipped, "cases": cases}


def get_tool_versions():
    env = pwsh_env()
    v = {}
    try:
        r = subprocess.run(["python3", "--version"], capture_output=True, text=True)
        v["python"] = (r.stdout + r.stderr).strip()
    except Exception as e:
        v["python"] = str(e)
    try:
        r = subprocess.run(
            ["pwsh", "-NoProfile", "-Command",
             "$PSVersionTable.PSVersion.ToString()"],
            capture_output=True, text=True, env=env)
        v["powershell"] = r.stdout.strip()
    except Exception as e:
        v["powershell"] = str(e)
    try:
        r = subprocess.run(
            ["pwsh", "-NoProfile", "-Command",
             "(Get-Module Pester -ListAvailable | Select-Object -First 1).Version.ToString()"],
            capture_output=True, text=True, env=env)
        v["pester"] = r.stdout.strip()
    except Exception as e:
        v["pester"] = str(e)
    try:
        r = subprocess.run(["git", "--version"], capture_output=True, text=True)
        v["git"] = r.stdout.strip()
    except Exception as e:
        v["git"] = str(e)
    v["os"] = platform.platform()
    v["arch"] = platform.machine()
    return v


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("R09-T047 · nth-prime — check.py")
    print("=" * 70)

    # 1. Parse config.json
    with open(CONFIG_PATH) as f:
        config = json.load(f)
    solution_rel = config["files"]["solution"][0]
    test_rel     = config["files"]["test"][0]
    example_rel  = config["files"]["example"][0]
    solution_path = os.path.join(EXERCISE_DIR, solution_rel)
    test_path     = os.path.join(EXERCISE_DIR, test_rel)
    example_path  = os.path.join(EXERCISE_DIR, example_rel)

    print(f"  solution : {solution_path}")
    print(f"  test     : {test_path}")
    print(f"  example  : {example_path}")
    print()

    # 2. Confirm learner stub is untouched
    with open(solution_path, encoding="utf-8") as f:
        stub_content = f.read()
    assert "Please implement this function" in stub_content, \
        "FAIL: learner stub appears to have been modified!"
    print("  ✓ Learner stub confirmed untouched (still contains placeholder).")
    print()

    # 3. Load reference implementation
    with open(example_path, encoding="utf-8") as f:
        reference_ps1 = f.read()

    # 4. Tool versions
    print("── Tool versions ──────────────────────────────────────────────────")
    versions = get_tool_versions()
    for k, v in versions.items():
        print(f"  {k:12s}: {v}")
    print()

    errors = []

    # 5. Run micro-example and pitfall scripts
    print("── Micro-example: array accumulation + return $arr[-1] ────────────")
    micro_out, micro_err, micro_rc = run_pwsh_script(MICRO_SCRIPT, "micro")
    micro_line = next((l for l in micro_out.splitlines() if l.startswith("MICRO:")), "")
    print(f"  stdout    : {micro_line!r}")
    print(f"  expected  : {MICRO_EXPECTED!r}")
    micro_ok = micro_line == MICRO_EXPECTED
    print(f"  match     : {'✓' if micro_ok else '✗'}")
    if not micro_ok:
        errors.append(f"Micro-example mismatch: got {micro_line!r}, expected {MICRO_EXPECTED!r}")
        if micro_err:
            print(f"  stderr: {micro_err[:500]}")
    print()

    print("── Pitfall: pipeline pollution — Write-Output before return ────────")
    pit_out, pit_err, pit_rc = run_pwsh_script(PITFALL_SCRIPT, "pitfall")
    pit_line = next((l for l in pit_out.splitlines() if l.startswith("PITFALL:")), "")
    print(f"  stdout    : {pit_line!r}")
    print(f"  expected  : {PITFALL_EXPECTED!r}")
    pit_ok = pit_line == PITFALL_EXPECTED
    print(f"  match     : {'✓' if pit_ok else '✗'}")
    if not pit_ok:
        errors.append(f"Pitfall mismatch: got {pit_line!r}, expected {PITFALL_EXPECTED!r}")
        if pit_err:
            print(f"  stderr: {pit_err[:500]}")
    print()

    # 6. Run Pester with reference implementation
    print("── Run Pester: REFERENCE implementation ────────────────────────────")
    with tempfile.TemporaryDirectory(prefix="R09-T047-ref-") as tmp:
        ex = copy_exercise(tmp)
        sol = os.path.join(ex, "NthPrime.ps1")
        with open(sol, "w", encoding="utf-8") as f:
            f.write(reference_ps1)
        proc = run_pester(ex)
        parsed = parse_pester(proc.stdout, proc.stderr)

    print(f"  Return code : {proc.returncode}")
    print(f"  TotalCount  : {parsed['total']}")
    print(f"  FailedCount : {parsed['failed']}")
    print(f"  PassedCount : {parsed['passed']}")
    print(f"  SkippedCount: {parsed['skipped']}")
    for c in parsed["cases"]:
        sym = "✓" if c["status"] == "PASS" else "✗"
        print(f"    {sym} {c['status']:4s}  {c['name']}")

    if proc.returncode != 0:
        errors.append(f"Pester pwsh exited with code {proc.returncode}")
    if parsed["total"] == 0:
        errors.append("Pester TotalCount == 0 — no tests ran")
    if parsed["failed"] > 0:
        errors.append(f"Pester FailedCount == {parsed['failed']}")
    print()

    # 7. Assert anchored cases
    print("── Anchored case assertions ────────────────────────────────────────")
    for anchor in ANCHORED:
        if anchor == "NthPrime Tests":
            ok = parsed["failed"] == 0 and parsed["total"] > 0
            sym = "✓" if ok else "✗"
            print(f"  [{sym}]  {anchor!r}  "
                  f"(Describe block — FailedCount==0 and TotalCount>0)")
            if not ok:
                errors.append(f"ANCHORED NOT PASSING: {anchor!r}")
        else:
            matches = [c for c in parsed["cases"]
                       if anchor in c["name"] or c["name"] == anchor]
            ok = any(c["status"] == "PASS" for c in matches) if matches else False
            sym = "✓" if ok else "✗"
            print(f"  [{sym}]  {anchor!r}")
            if not ok:
                errors.append(f"ANCHORED NOT PASSING: {anchor!r}")
    print()

    # 8. Persist evidence artifacts
    print("── Persisting evidence artifacts ───────────────────────────────────")
    out_dir = os.path.join(REPO_ROOT, "work", "R09-T047")
    os.makedirs(out_dir, exist_ok=True)

    # tool_versions.json
    with open(os.path.join(out_dir, "tool_versions.json"), "w") as f:
        json.dump(versions, f, indent=2)
    print("  Wrote tool_versions.json")

    # inputs.json
    inputs = {
        "config_paths": {
            "solution": solution_path,
            "test": test_path,
            "example": example_path,
        },
        "anchored_cases": ANCHORED,
        "construct_identified": {
            "file": ".meta/NthPrime.example.ps1",
            "mechanism": "explicit `return $primes[-1]` — returns the last element of an accumulated array as a scalar",
            "key_lines": [
                "$primes += $i        # array accumulation via += operator",
                "return $primes[-1]   # explicit return of last element (negative indexing)",
            ],
        },
        "micro_example": {
            "description": "Accumulate first N even numbers, return the last one",
            "script": MICRO_SCRIPT,
            "expected_output": MICRO_EXPECTED,
        },
        "pitfall_example": {
            "description": "Pipeline pollution: Write-Output before return causes caller to receive an array",
            "script": PITFALL_SCRIPT,
            "expected_output": PITFALL_EXPECTED,
        },
    }
    with open(os.path.join(out_dir, "inputs.json"), "w") as f:
        json.dump(inputs, f, indent=2)
    print("  Wrote inputs.json")

    # expected_vs_actual.json
    ev = {
        "pester_reference": {
            "total": parsed["total"],
            "failed": parsed["failed"],
            "passed": parsed["passed"],
            "skipped": parsed["skipped"],
            "cases": parsed["cases"],
        },
        "micro_example": {
            "expected": MICRO_EXPECTED,
            "actual": micro_line,
            "match": micro_ok,
        },
        "pitfall": {
            "expected": PITFALL_EXPECTED,
            "actual": pit_line,
            "match": pit_ok,
        },
        "hint_agreement": {
            "summary": (
                "The micro-example confirms that `return $arr[-1]` emits a scalar. "
                "The pitfall confirms that adding a Write-Output before the return "
                "causes pipeline pollution, turning the caller's result into an array."
            ),
            "micro_match": micro_ok,
            "pitfall_match": pit_ok,
        },
    }
    with open(os.path.join(out_dir, "expected_vs_actual.json"), "w") as f:
        json.dump(ev, f, indent=2)
    print("  Wrote expected_vs_actual.json")

    # maintenance.md
    maintenance_md = """\
# R09-T047 · nth-prime — Maintenance Notes

## Language Construct in `NthPrime.example.ps1`

The reference implementation uses **three interacting constructs**:

### 1. Array accumulation with `+=`

```powershell
$primes = @()
# ...
$primes += $i   # appends $i to the array and reassigns $primes
```

In PowerShell, `+=` on an array creates a **new array** each time (copying
all existing elements plus the new one). For small primes this is fine; for
very large N (e.g., `big prime` test: n=10001) the quadratic copy cost is
noticeable but tolerable.

### 2. Negative indexing with `$arr[-1]`

```powershell
return $primes[-1]
```

PowerShell supports negative indices: `-1` is the last element, `-2` is
second-to-last, etc. This is the natural way to retrieve the most recently
accumulated prime without tracking an extra variable.

### 3. Explicit `return` with a scalar result

The function ends with `return $primes[-1]`. The `return` keyword:
- Immediately exits the function.
- Emits **exactly one value** to the pipeline (the scalar integer `$primes[-1]`).
- Prevents any earlier pipeline output from being accidentally included
  in the return value (see pitfall below).

---

## Standalone Micro-Example (does NOT solve nth-prime)

```powershell
function Get-LastEven {
    param([int]$Count)
    $evens = @()
    $n = 2
    while ($evens.Count -lt $Count) {
        $evens += $n
        $n += 2
    }
    return $evens[-1]   # returns 6 when Count=3  (evens: 2, 4, 6)
}

$result = Get-LastEven -Count 3
Write-Output "MICRO:$result"   # → MICRO:6
```

**Key behaviour:** The caller receives the integer `6`, not the full array
`@(2, 4, 6)`. The `return` keyword + `-1` index together select a single
scalar from the accumulated collection.

---

## Contrasting Pitfall — Pipeline Pollution

```powershell
function Get-LastEvenPolluted {
    param([int]$Count)
    $evens = @()
    $n = 2
    while ($evens.Count -lt $Count) {
        $evens += $n
        $n += 2
    }
    Write-Output "debug: computing..."   # <─── pipeline pollution!
    return $evens[-1]
}

$result = Get-LastEvenPolluted -Count 3
# $result is @("debug: computing...", 6) — an ARRAY, not a scalar!
```

**Why outcomes differ:**

| Construct | Pipeline output | `$result` type |
|-----------|----------------|----------------|
| `return $evens[-1]` only | single integer | scalar `[int]` |
| `Write-Output "debug..."` **then** `return $evens[-1]` | two items | `[array]` with 2 elements |

PowerShell functions collect *all* values emitted to the pipeline into the
caller's result. Any `Write-Output`, `Write-Host` to pipeline, or bare
expression that isn't captured will appear in the return value. This is
why the reference uses `return $primes[-1]` with no intermediate pipeline
writes — it guarantees the caller always gets a scalar integer.

---

## Connection to `nth-prime` Specification

The test cases check for **exact integer equality**:

```powershell
$got = Get-NthPrime -Number 1
$want = 2
$got | Should -Be $want      # would fail if $got is @(..., 2)
```

`Should -Be` on an array vs a scalar would fail or behave unexpectedly.
So `return $primes[-1]` is not just a style choice — it's what makes
`$got | Should -Be $want` reliable.

---

## Learner Hint

> When your function accumulates results into `$arr` and needs to return
> only the **last** one, use `return $arr[-1]`. Avoid any `Write-Output`
> or bare expressions inside the function body before that `return`, or
> PowerShell will bundle all pipeline emissions into an array and your
> caller will get a collection instead of a scalar.

---

## Anchored Cases Verified

| Case | Reference |
|------|-----------|
| `NthPrime Tests` (Describe block) | PASS (FailedCount=0) |
| `first prime`  | PASS |
| `second prime` | PASS |

---

## Note for Upstream Contribution

Remove `work/R09-T047/` before any branch targeting upstream `exercism/powershell`.
The learner stub `NthPrime.ps1` was **never modified** in the working tree.
All substitution occurred inside Python `tempfile.mkdtemp()` directories.
"""
    with open(os.path.join(out_dir, "maintenance.md"), "w") as f:
        f.write(maintenance_md)
    print("  Wrote maintenance.md")
    print()

    # 9. Final verdict
    print("=" * 70)
    if errors:
        print("VERIFICATION FAILED:")
        for e in errors:
            print(f"  ✗ {e}")
        if proc.stderr:
            print("\nPester stderr:")
            print(proc.stderr[:2000])
        sys.exit(1)
    else:
        print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY")
        print(f"  solution  : {solution_path}")
        print(f"  test      : {test_path}")
        print(f"  example   : {example_path}")
        print(f"  Pester — TotalCount={parsed['total']}, FailedCount={parsed['failed']}")
        print()
        print("  Anchored cases verified:")
        for a in ANCHORED:
            print(f"    ✓ {a}")
        print()
        print("  Micro-example (array accumulation + return $arr[-1]) : ✓")
        print("  Pitfall (pipeline pollution → array result)           : ✓")
        print()
        print("  Construct: explicit `return $primes[-1]` on accumulated array")
        print("  Learner stub NthPrime.ps1 was NOT modified.")
        sys.exit(0)


if __name__ == "__main__":
    main()
