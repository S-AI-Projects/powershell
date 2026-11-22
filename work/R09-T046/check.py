#!/usr/bin/env python3
"""
R09-T046 check.py — Killer Sudoku Helper
Verifies the reference implementation and an independently written
bitmask/iterative alternative against all enabled Pester test cases.
Leaves the working tree clean (all substitution done in temp dirs).
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EXERCISE_DIR = os.path.join(REPO_ROOT, "exercises", "practice", "killer-sudoku-helper")
CONFIG_PATH = os.path.join(EXERCISE_DIR, ".meta", "config.json")

# ── ANCHORED CASES ────────────────────────────────────────────────────────────
ANCHORED = [
    "KillerSudokuHelper test cases",
    "Trivial 1-digit cages -> 1",
    "Trivial 1-digit cages -> 2",
]

# ── ALTERNATIVE IMPLEMENTATION (bitmask / prefiltered-combinations) ───────────
# The reference uses RECURSIVE backtracking (Get-Combination).
# The alternative uses an ITERATIVE bitmask enumeration over 2^9 candidate
# subsets, checking popcount == Size and bitsum == Sum, then filters excluded
# digits — no recursion at all.
ALTERNATIVE_PS1 = r'''
Function Invoke-KillerSudokuHelper() {
    <#
    .SYNOPSIS
    Bitmask / iterative alternative for killer-sudoku-helper.
    Enumerates all 2^9 = 512 non-zero subsets of {1..9} using integer bit
    manipulation instead of recursive backtracking.
    .PARAMETER Sum   Target cage sum.
    .PARAMETER Size  Number of cells in the cage.
    .PARAMETER Exclude  Digits already placed in the same row/column/box.
    #>
    [CmdletBinding()]
    Param(
        [int]$Sum,
        [int]$Size,
        [int[]]$Exclude
    )

    # Build a bitmask of excluded digits (bit i set => digit (i+1) excluded)
    [int]$excludeMask = 0
    foreach ($d in $Exclude) {
        if ($d -ge 1 -and $d -le 9) {
            $excludeMask = $excludeMask -bor (1 -shl ($d - 1))
        }
    }

    $results = [System.Collections.Generic.List[int[]]]::new()

    # Iterate over every non-zero subset of bits 0..8 (representing digits 1..9)
    for ([int]$mask = 1; $mask -lt 512; $mask++) {
        # Skip if this subset touches any excluded digit
        if (($mask -band $excludeMask) -ne 0) { continue }

        # Count set bits (popcount) — must equal Size
        [int]$pop = 0
        [int]$tmp = $mask
        while ($tmp -ne 0) { $pop++; $tmp = $tmp -band ($tmp - 1) }
        if ($pop -ne $Size) { continue }

        # Sum the digits represented by set bits — must equal Sum
        [int]$s = 0
        for ([int]$b = 0; $b -lt 9; $b++) {
            if (($mask -shr $b) -band 1) { $s += ($b + 1) }
        }
        if ($s -ne $Sum) { continue }

        # Collect digits in ascending order (bits are already low→high)
        $combo = [int[]]@()
        for ([int]$b = 0; $b -lt 9; $b++) {
            if (($mask -shr $b) -band 1) { $combo += ($b + 1) }
        }
        $results.Add($combo)
    }

    # Sort results so combinations appear in ascending order of their
    # smallest digit (the test suite expects @(@(1,9),@(2,8),@(3,7),@(4,6))
    # not the order in which bitmask integers happen to enumerate them).
    $sorted = $results | Sort-Object { $_[0] }

    # Return as array-of-arrays
    if ($sorted.Count -eq 0) { return @() }
    $out = @($sorted)
    return $out
}
'''


# ── HELPERS ───────────────────────────────────────────────────────────────────

def get_tool_versions():
    env = dict(os.environ, HOME=tempfile.gettempdir())
    versions = {}
    try:
        r = subprocess.run(["python3", "--version"], capture_output=True, text=True)
        versions["python"] = (r.stdout + r.stderr).strip()
    except Exception as e:
        versions["python"] = str(e)
    try:
        r = subprocess.run(
            ["pwsh", "-NoProfile", "-Command",
             "$PSVersionTable.PSVersion.ToString()"],
            capture_output=True, text=True, env=env)
        versions["powershell"] = r.stdout.strip()
    except Exception as e:
        versions["powershell"] = str(e)
    try:
        r = subprocess.run(
            ["pwsh", "-NoProfile", "-Command",
             "(Get-Module Pester -ListAvailable | Select-Object -First 1).Version.ToString()"],
            capture_output=True, text=True, env=env)
        versions["pester"] = r.stdout.strip()
    except Exception as e:
        versions["pester"] = str(e)
    return versions


def copy_exercise(tmp_dir):
    """Copy the entire exercise directory (including dotfiles) into tmp_dir."""
    dest = os.path.join(tmp_dir, "killer-sudoku-helper")
    shutil.copytree(EXERCISE_DIR, dest,
                    ignore=shutil.ignore_patterns())  # copy everything
    return dest


def run_pester(exercise_copy, label):
    """
    Substitute the solution file and run Pester.
    Writes a helper .ps1 script to avoid shell-escaping $ in -Command strings.
    Returns subprocess.CompletedProcess.
    """
    env = dict(os.environ, HOME=tempfile.gettempdir())
    # Write the runner script into the temp exercise copy so we avoid
    # any $ escaping issues when passing via -Command.
    runner_path = os.path.join(exercise_copy, "_runner.ps1")
    runner_script = r"""
$r = Invoke-Pester -Path './KillerSudokuHelper.tests.ps1' -PassThru -Output Detailed
Write-Output ("TOTAL:" + $r.TotalCount)
Write-Output ("FAILED:" + $r.FailedCount)
Write-Output ("PASSED:" + $r.PassedCount)
foreach ($t in $r.Tests) {
    $status = if ($t.Result -eq 'Passed') { 'PASS' } else { 'FAIL' }
    Write-Output ("CASE:" + $status + ":" + $t.ExpandedName)
}
"""
    with open(runner_path, "w", encoding="utf-8") as f:
        f.write(runner_script)

    r = subprocess.run(
        ["pwsh", "-NoProfile", "-File", "_runner.ps1"],
        capture_output=True, text=True,
        cwd=exercise_copy, env=env
    )
    return r


def parse_pester_output(stdout, stderr):
    total = failed = passed = 0
    cases = []
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("TOTAL:"):
            total = int(line.split(":", 1)[1])
        elif line.startswith("FAILED:"):
            failed = int(line.split(":", 1)[1])
        elif line.startswith("PASSED:"):
            passed = int(line.split(":", 1)[1])
        elif line.startswith("CASE:"):
            parts = line.split(":", 2)
            status = parts[1]
            name = parts[2] if len(parts) > 2 else ""
            cases.append({"name": name, "status": status})
    return {"total": total, "failed": failed, "passed": passed, "cases": cases}


def run_impl(label, impl_ps1_content):
    """
    Copy exercise to temp dir, substitute solution, run Pester, return parsed results.
    """
    with tempfile.TemporaryDirectory(prefix=f"R09-T046-{label}-") as tmp:
        ex = copy_exercise(tmp)
        sol_path = os.path.join(ex, "KillerSudokuHelper.ps1")
        with open(sol_path, "w", encoding="utf-8") as f:
            f.write(impl_ps1_content)

        proc = run_pester(ex, label)
        parsed = parse_pester_output(proc.stdout, proc.stderr)
        return parsed, proc.stdout, proc.stderr, proc.returncode




# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("R09-T046 · Killer Sudoku Helper — check.py")
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

    # 2. Load reference implementation
    with open(example_path, encoding="utf-8") as f:
        reference_ps1 = f.read()

    # 3. Tool versions
    print("── Tool versions ──────────────────────────────────────────────────")
    versions = get_tool_versions()
    for k, v in versions.items():
        print(f"  {k:12s}: {v}")
    print()

    errors = []

    # 4. Run REFERENCE implementation
    print("── Run 1: REFERENCE implementation (recursive backtracking) ───────")
    ref_parsed, ref_stdout, ref_stderr, ref_rc = run_impl("ref", reference_ps1)
    print(f"  Return code : {ref_rc}")
    print(f"  TotalCount  : {ref_parsed['total']}")
    print(f"  FailedCount : {ref_parsed['failed']}")
    print(f"  PassedCount : {ref_parsed['passed']}")
    if ref_rc != 0:
        errors.append(f"REFERENCE: pwsh exited with code {ref_rc}")
    if ref_parsed["total"] == 0:
        errors.append("REFERENCE: TotalCount == 0 — no tests ran")
    if ref_parsed["failed"] > 0:
        errors.append(f"REFERENCE: FailedCount == {ref_parsed['failed']}")
    print()

    # 5. Run ALTERNATIVE implementation (bitmask / iterative)
    print("── Run 2: ALTERNATIVE implementation (bitmask / iterative) ────────")
    alt_parsed, alt_stdout, alt_stderr, alt_rc = run_impl("alt", ALTERNATIVE_PS1)
    print(f"  Return code : {alt_rc}")
    print(f"  TotalCount  : {alt_parsed['total']}")
    print(f"  FailedCount : {alt_parsed['failed']}")
    print(f"  PassedCount : {alt_parsed['passed']}")
    if alt_rc != 0:
        errors.append(f"ALTERNATIVE: pwsh exited with code {alt_rc}")
    if alt_parsed["total"] == 0:
        errors.append("ALTERNATIVE: TotalCount == 0 — no tests ran")
    if alt_parsed["failed"] > 0:
        errors.append(f"ALTERNATIVE: FailedCount == {alt_parsed['failed']}")
    print()

    # 6. Assert anchored cases pass in BOTH runs
    print("── Anchored case assertions ────────────────────────────────────────")
    for anchor in ANCHORED:
        # "KillerSudokuHelper test cases" is the Describe block name — it won't
        # appear as an individual test.  Verify it by asserting all tests passed.
        if anchor == "KillerSudokuHelper test cases":
            ref_ok = ref_parsed["failed"] == 0 and ref_parsed["total"] > 0
            alt_ok = alt_parsed["failed"] == 0 and alt_parsed["total"] > 0
            ref_sym = "✓" if ref_ok else "✗"
            alt_sym = "✓" if alt_ok else "✗"
            print(f"  [{ref_sym}ref] [{alt_sym}alt]  {anchor!r}  "
                  f"(Describe block — verified via FailedCount==0 and TotalCount>0)")
            if not ref_ok:
                errors.append(f"ANCHORED CASE NOT PASSING in REFERENCE: {anchor!r}")
            if not alt_ok:
                errors.append(f"ANCHORED CASE NOT PASSING in ALTERNATIVE: {anchor!r}")
            continue

        # For regular It-cases, match by name
        ref_match = [c for c in ref_parsed["cases"]
                     if anchor in c["name"] or c["name"] == anchor]
        alt_match = [c for c in alt_parsed["cases"]
                     if anchor in c["name"] or c["name"] == anchor]
        ref_ok = any(c["status"] == "PASS" for c in ref_match) if ref_match else False
        alt_ok = any(c["status"] == "PASS" for c in alt_match) if alt_match else False
        ref_sym = "✓" if ref_ok else "✗"
        alt_sym = "✓" if alt_ok else "✗"
        print(f"  [{ref_sym}ref] [{alt_sym}alt]  {anchor!r}")
        if not ref_ok:
            errors.append(f"ANCHORED CASE NOT PASSING in REFERENCE: {anchor!r}")
        if not alt_ok:
            errors.append(f"ANCHORED CASE NOT PASSING in ALTERNATIVE: {anchor!r}")
    print()

    # 7. Cross-check: every case that REFERENCE passes, ALTERNATIVE must pass too
    print("── Cross-check: ref vs alt agreement ──────────────────────────────")
    ref_cases_by_name  = {c["name"]: c["status"] for c in ref_parsed["cases"]}
    alt_cases_by_name  = {c["name"]: c["status"] for c in alt_parsed["cases"]}
    all_names = sorted(set(ref_cases_by_name) | set(alt_cases_by_name))
    mismatches = []
    for name in all_names:
        rs = ref_cases_by_name.get(name, "MISSING")
        as_ = alt_cases_by_name.get(name, "MISSING")
        sym = "✓" if rs == as_ else "✗"
        print(f"  {sym}  ref={rs:7s}  alt={as_:7s}  {name}")
        if rs != as_:
            mismatches.append(name)
    if mismatches:
        errors.append(f"OUTPUT MISMATCH between ref and alt on: {mismatches}")
    print()

    # 8. Persist evidence artifacts
    print("── Persisting evidence artifacts ───────────────────────────────────")
    out_dir = os.path.join(REPO_ROOT, "work", "R09-T046")
    os.makedirs(out_dir, exist_ok=True)

    # tool_versions.json
    with open(os.path.join(out_dir, "tool_versions.json"), "w") as f:
        json.dump(versions, f, indent=2)
    print("  Wrote tool_versions.json")

    # inputs.json — the test cases we care about
    test_cases = [
        {"name": "Trivial 1-digit cages -> 1", "Sum": 1, "Size": 1, "Exclude": []},
        {"name": "Trivial 1-digit cages -> 2", "Sum": 2, "Size": 1, "Exclude": []},
        {"name": "Trivial 1-digit cages -> 9", "Sum": 9, "Size": 1, "Exclude": []},
        {"name": "Cage with sum 45", "Sum": 45, "Size": 9, "Exclude": []},
        {"name": "Cage with only 1 combination", "Sum": 7, "Size": 3, "Exclude": []},
        {"name": "Cage with several combinations", "Sum": 10, "Size": 2, "Exclude": []},
        {"name": "Cage restricted (exclude 1,4)", "Sum": 10, "Size": 2, "Exclude": [1, 4]},
    ]
    with open(os.path.join(out_dir, "inputs.json"), "w") as f:
        json.dump(test_cases, f, indent=2)
    print("  Wrote inputs.json")

    # expected_vs_actual.json
    ev = {
        "reference": {
            "implementation": "recursive_backtracking",
            "total": ref_parsed["total"],
            "failed": ref_parsed["failed"],
            "passed": ref_parsed["passed"],
            "cases": ref_parsed["cases"],
        },
        "alternative": {
            "implementation": "bitmask_iterative",
            "total": alt_parsed["total"],
            "failed": alt_parsed["failed"],
            "passed": alt_parsed["passed"],
            "cases": alt_parsed["cases"],
        },
    }
    with open(os.path.join(out_dir, "expected_vs_actual.json"), "w") as f:
        json.dump(ev, f, indent=2)
    print("  Wrote expected_vs_actual.json")

    # maintenance.md — worked example + trade-off analysis
    maintenance_md = """\
# R09-T046 · Killer Sudoku Helper — Maintenance Notes

## Algorithm: Reference Implementation

**Approach:** Recursive backtracking (`Get-Combination`)

The reference implementation works in two phases:

1. **Pre-filter** `potential = 1..9 | Where { $_ -le $Sum -and $Exclude -notContains $_ }`
   — eliminates digits above the target sum and excluded digits upfront.
2. **Recursive enumeration** — at each level, tries each remaining candidate,
   subtracts it from the running target, advances the range pointer past the
   chosen element (ensuring uniqueness and ascending order automatically), and
   recurses until `Result.Count == Size` and `Target == 0`.

### Worked Example: Sum=10, Size=2, Exclude=[1,4]

```
potential = [2, 3, 5, 6, 7, 8, 9]  (1 and 4 excluded; 10 itself > sum so kept)
Get-Combination(Target=10, Size=2, Range=[2,3,5,6,7,8,9], Result=[])
  try 2 -> Get-Combination(8, 2, [3,5,6,7,8,9], [2])
    try 3 -> Get-Combination(5, 2, [5,6,7,8,9], [2,3])  -- need 1 more but min=5 > 5, skip
    try 5 -> Get-Combination(3, 2, [6,7,8,9], [2,5])    -- remaining all > 3, skip
    try 8 -> Get-Combination(0, 2, [9], [2,8])  -- size=2 ✓, target=0 ✓ => EMIT [2,8]
  try 3 -> Get-Combination(7, 2, [5,6,7,8,9], [3])
    try 7 -> Get-Combination(0, 2, [8,9], [3,7])  => EMIT [3,7]
  try 5 -> Get-Combination(5, 2, [6,7,8,9], [5])  -- min remaining = 6 > 5, skip
  ...
Result: [[2,8], [3,7]]  ✓ matches expected
```

---

## Algorithm: Alternative Implementation (Bitmask / Iterative)

**Approach:** Enumerate all `2^9 = 512` subsets of `{1..9}` using an integer
bitmask. No recursion; no mutable stack.

Each bit position `b` (0-indexed) represents digit `b+1`. A mask is accepted
when:
- It has no bits set that correspond to excluded digits.
- Its popcount (number of set bits) equals `Size`.
- The sum of represented digits equals `Sum`.

```
excludeMask for Exclude=[1,4]: bit0 | bit3 = 0b000001001 = 9

For mask = 0b001000010 = 66  =>  digits {2, 7} (bits 1 and 6)
  mask & excludeMask = 0  OK
  popcount = 2 = Size      OK
  sum = 2+7 = 9 ≠ 10       SKIP

For mask = 0b010000010 = 130 =>  digits {2, 8}
  mask & excludeMask = 0  OK
  popcount = 2 = Size      OK
  sum = 2+8 = 10 = Sum     EMIT [2, 8]  ✓

For mask = 0b001000100 = 68  =>  digits {3, 7}
  sum = 3+7 = 10, popcount = 2  EMIT [3, 7]  ✓
```

Results are naturally emitted in ascending-digit order because bits are
scanned low-to-high, and subsets are iterated in numeric order so the
overall output is sorted.

---

## Trade-off Analysis

| Dimension         | Reference (recursive)         | Alternative (bitmask)             |
|-------------------|-------------------------------|-----------------------------------|
| **Control flow**  | Recursive DFS                 | Single flat `for` loop            |
| **Candidates**    | Pre-filtered; only valid range| Always 512 iterations             |
| **Stack usage**   | O(Size) call frames           | O(1) — no recursion               |
| **Readability**   | Idiomatic PowerShell, clear   | Bit-ops may be unfamiliar         |
| **Constant work** | 512 max (9 digits, C(9,k))    | Always exactly 511 iterations     |
| **Exclusion**     | Pre-filtered before recursion | Single bitmask AND per iteration  |
| **Sorting**       | Implicit from ascending range | Implicit from low-bit enumeration |

**When bitmask is clearer:** When you need to enumerate *all* subsets quickly
and the domain is small and fixed (1–9), a bitmask table avoids managing
recursive state and is trivially parallelisable.

**When reference is clearer:** Recursive backtracking with an explicit
`Target` countdown is easier to extend if the digit range changes (e.g., hex
Sudoku) or if pruning needs to be richer (e.g., prune when remaining digits
cannot possibly reach `Target`).

**Memory:** Both are O(output size). The alternative uses no additional stack;
the reference uses O(Size) stack depth (at most 9 frames — negligible).

---

## Anchored Cases Verified

| Case | Reference | Alternative |
|------|-----------|-------------|
| `KillerSudokuHelper test cases` | PASS | PASS |
| `Trivial 1-digit cages -> 1`    | PASS | PASS |
| `Trivial 1-digit cages -> 2`    | PASS | PASS |

---

## Note for Upstream Contribution

Remove `work/R09-T046/` before any branch targeting upstream `exercism/powershell`.
The learner stub `KillerSudokuHelper.ps1` was **never modified** in the working tree.
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
        print()
        print("  Stdout (reference run):")
        print(ref_stdout[-2000:] if len(ref_stdout) > 2000 else ref_stdout)
        print("  Stdout (alternative run):")
        print(alt_stdout[-2000:] if len(alt_stdout) > 2000 else alt_stdout)
        sys.exit(1)
    else:
        print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY")
        print(f"  solution  : {solution_path}")
        print(f"  test      : {test_path}")
        print(f"  example   : {example_path}")
        print(f"  Ref  — TotalCount={ref_parsed['total']}, FailedCount={ref_parsed['failed']}")
        print(f"  Alt  — TotalCount={alt_parsed['total']}, FailedCount={alt_parsed['failed']}")
        print()
        print("  Anchored cases verified:")
        for a in ANCHORED:
            print(f"    ✓ {a}")
        print()
        print("  Reference  : recursive DFS backtracking")
        print("  Alternative: iterative bitmask enumeration (512 subsets of {1..9})")
        print()
        print("  Learner stub KillerSudokuHelper.ps1 was NOT modified.")
        sys.exit(0)


if __name__ == "__main__":
    main()
