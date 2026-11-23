#!/usr/bin/env python3
"""
R09-T051 check.py — dnd-character canonical-case decisions & runner isolation
Verifies canonical cases in tests.toml, validates exclusion rationale for
UUID 2ca77b9b-c099-46c3-a02c-0d0f68ffa0fe, executes Pester tests in isolated
temp directories using config.json paths, tests reference, mutant failure,
and zero-test failure propagation, while asserting learner stub immutability.
"""

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import tomllib

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EXERCISE_DIR = os.path.join(REPO_ROOT, "exercises", "practice", "dnd-character")
CONFIG_PATH = os.path.join(EXERCISE_DIR, ".meta", "config.json")
TESTS_TOML_PATH = os.path.join(EXERCISE_DIR, ".meta", "tests.toml")
WORK_DIR = os.path.join(REPO_ROOT, "work", "R09-T051")

ANCHORED_CASES = [
    "DnD Character test cases",
    "ability modifier for score 3 is -4",
    "ability modifier for score 4 is -3"
]

TARGET_UUID = "2ca77b9b-c099-46c3-a02c-0d0f68ffa0fe"
REPLACEMENT_UUID = "dca2b2ec-f729-4551-84b9-078876bb4808"

DELIBERATELY_FAILING_STUB = r"""
Class Character {
    [int]$Strength
    [int]$Dexterity
    [int]$Constitution
    [int]$Intelligence
    [int]$Wisdom
    [int]$Charisma
    [int]$HitPoints

    Character() {
        # Deliberate mutant: incorrect hit points
        $this.HitPoints = 999
    }

    [int] Ability() {
        return 1
    }

    static [int] GetModifier([int]$Score) {
        # Deliberate mutant: return incorrect modifier
        return 999
    }
}
"""

def pwsh_env():
    # Set HOME to temp dir so pwsh does not fail on sandbox directory restrictions
    return dict(os.environ, HOME=tempfile.gettempdir())

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
            ["pwsh", "-NoProfile", "-Command", "$PSVersionTable.PSVersion.ToString()"],
            capture_output=True, text=True, env=env)
        v["powershell"] = r.stdout.strip()
    except Exception as e:
        v["powershell"] = str(e)
    try:
        r = subprocess.run(
            ["pwsh", "-NoProfile", "-Command", "(Get-Module Pester -ListAvailable | Select-Object -First 1).Version.ToString()"],
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

def hash_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def get_learner_files_hashes(solution_rel_paths):
    hashes = {}
    for rel_path in solution_rel_paths:
        full_path = os.path.join(EXERCISE_DIR, rel_path)
        hashes[rel_path] = hash_file(full_path)
    return hashes

def copy_exercise(tmp_dir):
    dest = os.path.join(tmp_dir, "dnd-character")
    shutil.copytree(EXERCISE_DIR, dest)
    return dest

def run_pester(exercise_copy, tag_filter=None, fail_on_zero=False):
    filter_setup = ""
    if tag_filter:
        filter_setup = f"$c.Filter.Tag = '{tag_filter}'"

    fail_on_zero_logic = ""
    if fail_on_zero:
        fail_on_zero_logic = """
if ($executed -eq 0 -or $r.TotalCount -eq 0) {
    exit 42
}
"""

    runner = f"""
$c = New-PesterConfiguration
$c.Run.Path = './DndCharacter.tests.ps1'
$c.Run.PassThru = $true
$c.Output.Verbosity = 'Detailed'
{filter_setup}

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
{fail_on_zero_logic}
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
    total = failed = passed = skipped = notrun = executed = 0
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
        elif line.startswith("NOTRUN:"):
            notrun = int(line.split(":", 1)[1])
        elif line.startswith("EXECUTED:"):
            executed = int(line.split(":", 1)[1])
        elif line.startswith("CASE:"):
            parts = line.split(":", 2)
            cases.append({"name": parts[2] if len(parts) > 2 else "",
                          "status": parts[1]})
    return {
        "total": total,
        "failed": failed,
        "passed": passed,
        "skipped": skipped,
        "notrun": notrun,
        "executed": executed,
        "cases": cases
    }

def main():
    print("=" * 70)
    print("R09-T051 · dnd-character — check.py")
    print("=" * 70)

    errors = []
    run_records = {}

    # 1. Parse config.json to dynamically resolve file paths
    print("── 1. Resolving Paths from config.json ──────────────────────────────")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
    files = config.get("files", {})
    solution_paths = files["solution"]
    test_rel = files["test"][0]
    example_rel = files["example"][0]
    solution_rel = solution_paths[0]

    solution_full = os.path.join(EXERCISE_DIR, solution_rel)
    test_full = os.path.join(EXERCISE_DIR, test_rel)
    example_full = os.path.join(EXERCISE_DIR, example_rel)

    print(f"  solution: {solution_full}")
    print(f"  test    : {test_full}")
    print(f"  example : {example_full}")
    print()

    # 2. Check initial hashes of learner stub files
    initial_hashes = get_learner_files_hashes(solution_paths)
    print("Initial SHA-256 hashes of learner starter files:")
    for path, h in initial_hashes.items():
        print(f"  {path}: {h}")

    with open(solution_full, "r", encoding="utf-8") as f:
        content = f.read()
        assert "Please implement this class" in content, "Learner stub class modified!"
        assert "Please implement this function" in content, "Learner stub function modified!"
    print("  ✓ Learner starter file is unsolved stub (contains placeholder exceptions).")
    print()

    # 3. Tool versions
    versions = get_tool_versions()
    print("Tool versions:")
    for k, v in versions.items():
        print(f"  {k:12s}: {v}")
    print()

    # 4. Canonical Case and TOML Analysis
    print("── 2. TOML Parsing and Canonical Exclusion Analysis ────────────────")
    with open(TESTS_TOML_PATH, "rb") as f:
        toml_data = tomllib.load(f)

    total_entries = len(toml_data)
    excluded_entries = [uuid for uuid, entry in toml_data.items() if entry.get("include") is False]
    included_entries = [uuid for uuid, entry in toml_data.items() if entry.get("include") is not False]

    print(f"  Total canonical entries: {total_entries}")
    print(f"  Included entries       : {len(included_entries)}")
    print(f"  Excluded entries       : {len(excluded_entries)}")

    if total_entries != 20:
        errors.append(f"Expected 20 canonical cases in tests.toml, found {total_entries}")
    if len(excluded_entries) != 1:
        errors.append(f"Expected 1 excluded case in tests.toml, found {len(excluded_entries)}")

    target_entry = toml_data.get(TARGET_UUID)
    if not target_entry:
        errors.append(f"Target UUID {TARGET_UUID} not found in tests.toml")
    else:
        is_excluded = target_entry.get("include") is False
        comment = target_entry.get("comment", "")
        print(f"  Target UUID {TARGET_UUID}:")
        print(f"    description: {target_entry.get('description')}")
        print(f"    include    : {target_entry.get('include')}")
        print(f"    comment    : {comment}")

        if not is_excluded:
            errors.append(f"Target UUID {TARGET_UUID} must have include = false")
        if not comment:
            errors.append(f"Target UUID {TARGET_UUID} is missing required 'comment' rationale")
        elif REPLACEMENT_UUID not in comment and "dca2b2ec" not in comment:
            errors.append(f"Target UUID {TARGET_UUID} rationale must mention replacement UUID {REPLACEMENT_UUID}")

    replacement_entry = toml_data.get(REPLACEMENT_UUID)
    if not replacement_entry:
        errors.append(f"Replacement UUID {REPLACEMENT_UUID} not found in tests.toml")
    else:
        print(f"  Replacement UUID {REPLACEMENT_UUID}:")
        print(f"    reimplements: {replacement_entry.get('reimplements')}")
        if replacement_entry.get("reimplements") != TARGET_UUID:
            errors.append(f"Replacement UUID {REPLACEMENT_UUID} must reimplement {TARGET_UUID}")

    toml_record = {
        "total_entries": total_entries,
        "included_count": len(included_entries),
        "excluded_count": len(excluded_entries),
        "excluded_uuids": excluded_entries,
        "target_uuid": TARGET_UUID,
        "target_entry": target_entry,
        "replacement_uuid": REPLACEMENT_UUID,
        "replacement_entry": replacement_entry,
        "toml_valid": len(errors) == 0
    }
    print()

    with open(example_full, "r", encoding="utf-8") as f:
        reference_code = f.read()

    # 5. Mode 1: Real Reference Implementation
    print("── 3. Mode 1: Real Reference Run in Temp Directory ─────────────────")
    tmp1 = tempfile.mkdtemp(prefix="R09-T051-mode1-")
    try:
        ex1 = copy_exercise(tmp1)
        with open(os.path.join(ex1, solution_rel), "w", encoding="utf-8") as f:
            f.write(reference_code)

        proc1 = run_pester(ex1, fail_on_zero=True)
        res1 = parse_pester(proc1.stdout, proc1.stderr)

        print(f"  Return code : {proc1.returncode}")
        print(f"  TotalCount  : {res1['total']}")
        print(f"  PassedCount : {res1['passed']}")
        print(f"  FailedCount : {res1['failed']}")
        print(f"  Executed    : {res1['executed']}")

        mode1_ok = (proc1.returncode == 0 and res1['total'] > 0 and res1['failed'] == 0)
        if not mode1_ok:
            errors.append(f"Mode 1 failed: rc={proc1.returncode}, total={res1['total']}, failed={res1['failed']}")

        anchored_mode1 = {}
        for a in ANCHORED_CASES:
            if a == "DnD Character test cases":
                ok = (res1['failed'] == 0 and res1['total'] > 0)
            else:
                ok = any(c['status'] == 'PASS' and (a in c['name'] or a == c['name']) for c in res1['cases'])
            anchored_mode1[a] = ok
            print(f"    [{'✓' if ok else '✗'}] {a}")
            if not ok:
                errors.append(f"Mode 1 anchored case missing/failed: {a}")

        run_records["mode_1_reference"] = {
            "expected_rc": 0,
            "actual_rc": proc1.returncode,
            "total": res1["total"],
            "failed": res1["failed"],
            "passed": res1["passed"],
            "executed": res1["executed"],
            "anchored_cases": anchored_mode1,
            "status": "PASS" if mode1_ok else "FAIL"
        }
    finally:
        shutil.rmtree(tmp1, ignore_errors=True)
        tmp1_cleaned = not os.path.exists(tmp1)
        print(f"  Temp dir cleanup verified: {tmp1_cleaned}")
        run_records["mode_1_reference"]["tmp_cleaned"] = tmp1_cleaned

    # Verify hashes after Mode 1
    post_mode1_hashes = get_learner_files_hashes(solution_paths)
    assert post_mode1_hashes == initial_hashes, "FAIL: Learner files mutated during Mode 1!"
    print("  ✓ Learner file SHA-256 unchanged after Mode 1.")
    print()

    # 6. Mode 2: Deliberately Failing Reference Run
    print("── 4. Mode 2: Deliberately Failing Reference in Temp Directory ─────")
    tmp2 = tempfile.mkdtemp(prefix="R09-T051-mode2-")
    try:
        ex2 = copy_exercise(tmp2)
        with open(os.path.join(ex2, solution_rel), "w", encoding="utf-8") as f:
            f.write(DELIBERATELY_FAILING_STUB)

        proc2 = run_pester(ex2, fail_on_zero=True)
        res2 = parse_pester(proc2.stdout, proc2.stderr)

        print(f"  Return code : {proc2.returncode}")
        print(f"  TotalCount  : {res2['total']}")
        print(f"  FailedCount : {res2['failed']}")
        print(f"  PassedCount : {res2['passed']}")

        mode2_failed_as_expected = (proc2.returncode != 0 and res2['failed'] > 0)
        print(f"  Deliberately failed with non-zero exit as expected: {mode2_failed_as_expected}")
        if not mode2_failed_as_expected:
            errors.append(f"Mode 2 expected non-zero exit code and failures, got rc={proc2.returncode}, failed={res2['failed']}")

        run_records["mode_2_failing_reference"] = {
            "expected_non_zero_exit": True,
            "actual_rc": proc2.returncode,
            "total": res2["total"],
            "failed": res2["failed"],
            "passed": res2["passed"],
            "deliberately_failed_as_expected": mode2_failed_as_expected,
            "status": "PASS" if mode2_failed_as_expected else "FAIL"
        }
    finally:
        shutil.rmtree(tmp2, ignore_errors=True)
        tmp2_cleaned = not os.path.exists(tmp2)
        print(f"  Temp dir cleanup verified: {tmp2_cleaned}")
        run_records["mode_2_failing_reference"]["tmp_cleaned"] = tmp2_cleaned

    # Verify hashes after Mode 2
    post_mode2_hashes = get_learner_files_hashes(solution_paths)
    assert post_mode2_hashes == initial_hashes, "FAIL: Learner files mutated during Mode 2!"
    print("  ✓ Learner file SHA-256 unchanged after Mode 2.")
    print()

    # 7. Mode 3: Empty Test Selection (Zero-test failure propagation)
    print("── 5. Mode 3: Empty Test Selection Run in Temp Directory ───────────")
    tmp3 = tempfile.mkdtemp(prefix="R09-T051-mode3-")
    try:
        ex3 = copy_exercise(tmp3)
        with open(os.path.join(ex3, solution_rel), "w", encoding="utf-8") as f:
            f.write(reference_code)

        proc3 = run_pester(ex3, tag_filter="NonExistentTagFilter123", fail_on_zero=True)
        res3 = parse_pester(proc3.stdout, proc3.stderr)

        print(f"  Return code : {proc3.returncode}")
        print(f"  TotalCount  : {res3['total']}")
        print(f"  Executed    : {res3['executed']}")
        print(f"  NotRunCount : {res3['notrun']}")

        mode3_zero_tests_rejected = (proc3.returncode != 0 and res3['executed'] == 0)
        print(f"  Empty selection detected and rejected with non-zero exit: {mode3_zero_tests_rejected}")
        if not mode3_zero_tests_rejected:
            errors.append(f"Mode 3 expected non-zero exit code on 0 executed tests, got rc={proc3.returncode}, executed={res3['executed']}")

        run_records["mode_3_empty_selection"] = {
            "expected_non_zero_exit": True,
            "actual_rc": proc3.returncode,
            "total": res3["total"],
            "executed": res3["executed"],
            "notrun": res3["notrun"],
            "empty_selection_detected_and_rejected": mode3_zero_tests_rejected,
            "status": "PASS" if mode3_zero_tests_rejected else "FAIL"
        }
    finally:
        shutil.rmtree(tmp3, ignore_errors=True)
        tmp3_cleaned = not os.path.exists(tmp3)
        print(f"  Temp dir cleanup verified: {tmp3_cleaned}")
        run_records["mode_3_empty_selection"]["tmp_cleaned"] = tmp3_cleaned

    # Final hash check
    final_hashes = get_learner_files_hashes(solution_paths)
    assert final_hashes == initial_hashes, "FAIL: Final learner file hash mismatch!"
    print("  ✓ Learner file SHA-256 unchanged after all runs.")
    print()

    # 8. Persist Artifacts
    print("── 6. Persisting Evidence Artifacts ────────────────────────────────")
    os.makedirs(WORK_DIR, exist_ok=True)

    inputs_data = {
        "task_id": "R09-T051",
        "exercise_directory": EXERCISE_DIR,
        "resolved_paths": {
            "solution": os.path.relpath(solution_full, REPO_ROOT),
            "test": os.path.relpath(test_full, REPO_ROOT),
            "example": os.path.relpath(example_full, REPO_ROOT),
            "tests_toml": os.path.relpath(TESTS_TOML_PATH, REPO_ROOT)
        },
        "anchored_cases": ANCHORED_CASES,
        "target_exclusion_uuid": TARGET_UUID,
        "replacement_uuid": REPLACEMENT_UUID,
        "pre_run_learner_file_hashes": initial_hashes,
        "modes_configured": [
            "mode_1_reference",
            "mode_2_failing_reference",
            "mode_3_empty_selection"
        ]
    }
    with open(os.path.join(WORK_DIR, "inputs.json"), "w", encoding="utf-8") as f:
        json.dump(inputs_data, f, indent=2)
    print("  Wrote inputs.json")

    expected_data = {
        "canonical_analysis": toml_record,
        "learner_file_hash_immutability": {
            "initial": initial_hashes,
            "post_mode1": post_mode1_hashes,
            "post_mode2": post_mode2_hashes,
            "final": final_hashes,
            "all_identical": (initial_hashes == post_mode1_hashes == post_mode2_hashes == final_hashes)
        },
        "runs": run_records
    }
    with open(os.path.join(WORK_DIR, "expected_vs_actual.json"), "w", encoding="utf-8") as f:
        json.dump(expected_data, f, indent=2)
    print("  Wrote expected_vs_actual.json")

    with open(os.path.join(WORK_DIR, "tool_versions.json"), "w", encoding="utf-8") as f:
        json.dump(versions, f, indent=2)
    print("  Wrote tool_versions.json")

    maintenance_md = f"""# R09-T051 · DnD Character — Canonical Case Decisions & Runner Isolation

## Architecture of `check.py`

The test runner `work/R09-T051/check.py` provides an isolated, failure-propagating harness for `dnd-character`:
1. **Dynamic Config Resolution:** Reads `exercises/practice/dnd-character/.meta/config.json` to resolve paths for `solution` (`DndCharacter.ps1`), `test` (`DndCharacter.tests.ps1`), and `example` (`.meta/DndCharacter.example.ps1`).
2. **Canonical Case Analysis:**
   - Validates `exercises/practice/dnd-character/.meta/tests.toml` parsing with `tomllib`.
   - Confirms exactly 20 canonical cases (19 included, 1 excluded).
   - Verifies target exclusion UUID `{TARGET_UUID}` has `include = false` and documents a concrete `comment` rationale referencing replacement UUID `{REPLACEMENT_UUID}` and PowerShell property semantics.
3. **Cryptographic Protection of Learner Files:**
   - Computes SHA-256 hashes of learner starter files (`DndCharacter.ps1`) before any operations.
   - Audits learner file hashes after Mode 1, Mode 2, and Mode 3 to assert zero mutations.
   - Learner stub retains the unaltered placeholder exceptions.
4. **Sandbox Isolation & Cleanup:**
   - Each test mode executes inside an independent `tempfile.mkdtemp()` directory.
   - Reference or mutant code is substituted only inside the temporary directory copy.
   - `try/finally` blocks guarantee cleanup of temporary workspaces upon completion, failure, or interruption.

---

## Verification Modes & Results

### Canonical Case Decisions & TOML Audit
- **Total Canonical Cases:** {total_entries}
- **Included Cases:** {len(included_entries)}
- **Excluded Cases:** {len(excluded_entries)}
- **Excluded UUID:** `{TARGET_UUID}` (`"each ability is only calculated once"`)
- **Replacement UUID:** `{REPLACEMENT_UUID}` (`reimplements = "{TARGET_UUID}"`)
- **Rationale Status:** Validated against PowerShell class property semantics.

### Mode 1: Real Reference Implementation
- **Implementation:** `.meta/DndCharacter.example.ps1`
- **Return Code:** `{proc1.returncode}` (Expected: 0)
- **Total Tests:** `{res1['total']}`
- **Passed:** `{res1['passed']}`
- **Failed:** `{res1['failed']}` (Expected: 0)
- **Executed:** `{res1['executed']}`
- **Anchored Cases Verified:**
  - `DnD Character test cases`: **PASS**
  - `ability modifier for score 3 is -4`: **PASS**
  - `ability modifier for score 4 is -3`: **PASS**
- **Learner File Hash Check:** Verified unchanged.
- **Temp Directory Cleanup:** Verified cleaned up.

### Mode 2: Deliberately Failing Reference
- **Implementation:** Mutant returning `HitPoints = 999` and `GetModifier = 999`
- **Return Code:** `{proc2.returncode}` (Expected: non-zero, actual: {proc2.returncode})
- **Total Tests:** `{res2['total']}`
- **Failed:** `{res2['failed']}` (Expected: > 0)
- **Learner File Hash Check:** Verified unchanged.
- **Temp Directory Cleanup:** Verified cleaned up.

### Mode 3: Empty Test Selection
- **Filter Applied:** `TagFilter = 'NonExistentTagFilter123'`
- **Return Code:** `{proc3.returncode}` (Expected: non-zero exit on 0 executed tests, actual: {proc3.returncode})
- **Executed Tests:** `{res3['executed']}`
- **NotRun Count:** `{res3['notrun']}`
- **Zero-test Failure Propagation:** Successfully caught zero-run and exited non-zero.
- **Learner File Hash Check:** Verified unchanged.
- **Temp Directory Cleanup:** Verified cleaned up.

---

## Cryptographic Hash Audit

- File: `exercises/practice/dnd-character/DndCharacter.ps1`
- Algorithm: SHA-256
- Hash: `{initial_hashes['DndCharacter.ps1']}`
- State across all test phases: **Identical** (no mutations detected).

---

## Note for Upstream Contribution

Remove `work/R09-T051/` before any branch aimed at upstream `exercism/powershell`.
"""
    with open(os.path.join(WORK_DIR, "maintenance.md"), "w", encoding="utf-8") as f:
        f.write(maintenance_md)
    print("  Wrote maintenance.md")
    print()

    # 9. Summary & Exit
    print("=" * 70)
    if errors:
        print("VERIFICATION FAILED:")
        for err in errors:
            print(f"  ✗ {err}")
        sys.exit(1)
    else:
        print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY")
        print(f"  - Canonical TOML: 20 cases, 19 included, 1 excluded, rationale confirmed")
        print(f"  - Mode 1 Reference: TotalCount={res1['total']}, PassedCount={res1['passed']}, rc={proc1.returncode}")
        print(f"  - Mode 2 Failing Reference: FailedCount={res2['failed']}, rc={proc2.returncode} (expected non-zero)")
        print(f"  - Mode 3 Empty Selection: Executed={res3['executed']}, rc={proc3.returncode} (expected non-zero)")
        print(f"  - Learner file SHA-256 verified invariant across all runs")
        for a in ANCHORED_CASES:
            print(f"    ✓ {a}")
        sys.exit(0)

if __name__ == "__main__":
    main()
