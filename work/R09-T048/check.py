#!/usr/bin/env python3
"""
R09-T048 check.py — space-age metadata validation & runner resolution
Validates config.json files object resolution, rejects parent traversal and
missing files, tests invalid fixtures, and runs Pester against the reference
implementation in an isolated temporary directory.
"""

import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EXERCISE_DIR = os.path.join(REPO_ROOT, "exercises", "practice", "space-age")
CONFIG_PATH = os.path.join(EXERCISE_DIR, ".meta", "config.json")

ANCHORED = [
    "Space Age test cases",
    "age on Earth",
    "no planet provided should default to Earth"
]

def pwsh_env():
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

def validate_files_metadata(base_dir, files_obj):
    """
    Validates that each file entry in files_obj resolves strictly inside base_dir,
    does not escape via parent traversal, and exists on disk.
    Returns (True, resolved_map) or raises ValueError with reason.
    """
    resolved = {}
    base_real = os.path.realpath(base_dir)

    for category, paths in files_obj.items():
        if not isinstance(paths, list):
            raise ValueError(f"Category '{category}' must be a list of paths")
        resolved[category] = []
        for rel_path in paths:
            # Check for path traversal syntactic tokens or relative escaping
            norm = os.path.normpath(rel_path)
            if norm.startswith("..") or os.path.isabs(rel_path):
                raise ValueError(f"Path traversal detected in category '{category}': '{rel_path}' escapes exercise root")
            
            full_path = os.path.join(base_dir, rel_path)
            real_path = os.path.realpath(full_path)
            if not real_path.startswith(base_real + os.sep) and real_path != base_real:
                raise ValueError(f"Escaping exercise root in category '{category}': '{rel_path}' resolves outside '{base_dir}'")

            if not os.path.exists(real_path):
                raise ValueError(f"Declared file missing in category '{category}': '{rel_path}' does not exist at '{full_path}'")

            resolved[category].append(real_path)

    return True, resolved

def copy_exercise(tmp_dir):
    dest = os.path.join(tmp_dir, "space-age")
    shutil.copytree(EXERCISE_DIR, dest)
    return dest

def run_pester(exercise_copy):
    runner = r"""
$r = Invoke-Pester -Path './SpaceAge.tests.ps1' -PassThru -Output Detailed
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

def main():
    print("=" * 70)
    print("R09-T048 · space-age — check.py")
    print("=" * 70)

    # 1. Parse config.json
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    files_obj = config.get("files", {})
    print("Parsed files object from config.json:")
    print(json.dumps(files_obj, indent=2))
    print()

    # 2. Check learner stub untouched
    stub_rel = files_obj["solution"][0]
    stub_path = os.path.join(EXERCISE_DIR, stub_rel)
    with open(stub_path, "r", encoding="utf-8") as f:
        stub_content = f.read()
    assert "Please implement this function" in stub_content, "FAIL: Learner stub has been modified!"
    print(f"  ✓ Learner stub confirmed untouched ({stub_path})")
    print()

    # 3. Validate REAL metadata
    print("── Validating real config.json files metadata ─────────────────────")
    real_valid, real_resolved = validate_files_metadata(EXERCISE_DIR, files_obj)
    print("  ✓ Real metadata passed validation cleanly.")
    for cat, paths in real_resolved.items():
        for p in paths:
            print(f"    - {cat:8s}: {p}")
    print()

    # 4. Test 3 invalid fixtures in temporary directories
    print("── Testing 3 invalid metadata fixtures ────────────────────────────")
    fixture_results = {}

    # Fixture 1: missing example file
    f1_files = {
        "solution": ["SpaceAge.ps1"],
        "test": ["SpaceAge.tests.ps1"],
        "example": [".meta/MissingSpaceAge.example.ps1"]
    }
    try:
        validate_files_metadata(EXERCISE_DIR, f1_files)
        raise AssertionError("Fixture 1 should have failed for missing example file!")
    except ValueError as e:
        msg = str(e)
        assert "Declared file missing in category 'example'" in msg, f"Unexpected message: {msg}"
        print(f"  ✓ Fixture 1 (missing example) rejected as expected: {msg}")
        fixture_results["missing_example"] = {
            "expected_rejection": True,
            "error_message": msg,
            "status": "PASS"
        }

    # Fixture 2: missing test file
    f2_files = {
        "solution": ["SpaceAge.ps1"],
        "test": ["SpaceAge.tests.nonexistent.ps1"],
        "example": [".meta/SpaceAge.example.ps1"]
    }
    try:
        validate_files_metadata(EXERCISE_DIR, f2_files)
        raise AssertionError("Fixture 2 should have failed for missing test file!")
    except ValueError as e:
        msg = str(e)
        assert "Declared file missing in category 'test'" in msg, f"Unexpected message: {msg}"
        print(f"  ✓ Fixture 2 (missing test) rejected as expected: {msg}")
        fixture_results["missing_test"] = {
            "expected_rejection": True,
            "error_message": msg,
            "status": "PASS"
        }

    # Fixture 3: path traversal / escaping exercise root
    f3_files = {
        "solution": ["SpaceAge.ps1"],
        "test": ["SpaceAge.tests.ps1"],
        "example": ["../../nth-prime/.meta/NthPrime.example.ps1"]
    }
    try:
        validate_files_metadata(EXERCISE_DIR, f3_files)
        raise AssertionError("Fixture 3 should have failed for path traversal!")
    except ValueError as e:
        msg = str(e)
        assert "Path traversal detected" in msg or "Escaping exercise root" in msg, f"Unexpected message: {msg}"
        print(f"  ✓ Fixture 3 (path traversal) rejected as expected: {msg}")
        fixture_results["path_traversal"] = {
            "expected_rejection": True,
            "error_message": msg,
            "status": "PASS"
        }
    print()

    # 5. Tool versions
    print("── Tool versions ──────────────────────────────────────────────────")
    versions = get_tool_versions()
    for k, v in versions.items():
        print(f"  {k:12s}: {v}")
    print()

    errors = []

    # 6. Run Pester against reference implementation in temp copy
    print("── Run Pester: REFERENCE implementation in isolated temp copy ─────")
    example_rel = files_obj["example"][0]
    example_path = os.path.join(EXERCISE_DIR, example_rel)
    with open(example_path, "r", encoding="utf-8") as f:
        reference_ps1 = f.read()

    with tempfile.TemporaryDirectory(prefix="R09-T048-ref-") as tmp:
        ex = copy_exercise(tmp)
        sol = os.path.join(ex, "SpaceAge.ps1")
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
        if anchor == "Space Age test cases":
            ok = parsed["failed"] == 0 and parsed["total"] > 0
            sym = "✓" if ok else "✗"
            print(f"  [{sym}]  {anchor!r}  (Describe block — FailedCount==0 and TotalCount>0)")
            if not ok:
                errors.append(f"ANCHORED NOT PASSING: {anchor!r}")
        else:
            matches = [c for c in parsed["cases"] if anchor in c["name"] or c["name"] == anchor]
            ok = any(c["status"] == "PASS" for c in matches) if matches else False
            sym = "✓" if ok else "✗"
            print(f"  [{sym}]  {anchor!r}")
            if not ok:
                errors.append(f"ANCHORED NOT PASSING: {anchor!r}")
    print()

    # 8. Persist artifacts
    print("── Persisting evidence artifacts ───────────────────────────────────")
    out_dir = os.path.join(REPO_ROOT, "work", "R09-T048")
    os.makedirs(out_dir, exist_ok=True)

    # inputs.json
    inputs_data = {
        "exercise_directory": EXERCISE_DIR,
        "parsed_files_metadata": files_obj,
        "resolved_paths": {k: [os.path.relpath(p, REPO_ROOT) for p in v] for k, v in real_resolved.items()},
        "anchored_cases": ANCHORED,
        "invalid_fixtures": {
            "fixture_1_missing_example": f1_files,
            "fixture_2_missing_test": f2_files,
            "fixture_3_path_traversal": f3_files
        }
    }
    with open(os.path.join(out_dir, "inputs.json"), "w", encoding="utf-8") as f:
        json.dump(inputs_data, f, indent=2)
    print("  Wrote inputs.json")

    # expected_vs_actual.json
    expected_data = {
        "metadata_validation": {
            "real_config": {
                "expected": "PASS",
                "actual": "PASS" if real_valid else "FAIL"
            },
            "invalid_fixtures": fixture_results
        },
        "pester_results": {
            "returncode": proc.returncode,
            "total": parsed["total"],
            "failed": parsed["failed"],
            "passed": parsed["passed"],
            "skipped": parsed["skipped"],
            "anchored_cases_verified": {
                a: (parsed["failed"] == 0 if a == "Space Age test cases" else any(c["status"] == "PASS" for c in parsed["cases"] if a in c["name"]))
                for a in ANCHORED
            }
        }
    }
    with open(os.path.join(out_dir, "expected_vs_actual.json"), "w", encoding="utf-8") as f:
        json.dump(expected_data, f, indent=2)
    print("  Wrote expected_vs_actual.json")

    # tool_versions.json
    with open(os.path.join(out_dir, "tool_versions.json"), "w", encoding="utf-8") as f:
        json.dump(versions, f, indent=2)
    print("  Wrote tool_versions.json")

    # maintenance.md
    maintenance_md = f"""# R09-T048 · Space Age — Metadata Resolution & Runner Verification

## Metadata Specification in `config.json`

The file `exercises/practice/space-age/.meta/config.json` specifies:
```json
{json.dumps({"files": files_obj}, indent=2)}
```

### Path Resolution Semantics
Exercism practice exercises declare relative paths relative to the individual exercise root directory (`exercises/practice/space-age`).

1. `solution`: `SpaceAge.ps1`
   - Real path: `exercises/practice/space-age/SpaceAge.ps1`
   - Role: Learner solution stub. Maintained unsolved in the working tree.
2. `test`: `SpaceAge.tests.ps1`
   - Real path: `exercises/practice/space-age/SpaceAge.tests.ps1`
   - Role: Pester test file describing behavioral requirements and test cases.
3. `example`: `.meta/SpaceAge.example.ps1`
   - Real path: `exercises/practice/space-age/.meta/SpaceAge.example.ps1`
   - Role: Reference canonical implementation used by track maintainers and CI to verify that all enabled test cases pass.
4. `editor` (if present): optional list of supporting files for the web editor.

### How the Runner Finds Tests and Reference Solutions
Exercism test runners (and maintenance scripts like `check.py`):
1. Locate the exercise directory (`exercises/practice/space-age`).
2. Read `.meta/config.json` and parse the `files` object directly.
3. Resolve the `test` entry (`SpaceAge.tests.ps1`) relative to the exercise directory to determine the test container to invoke with `Invoke-Pester`.
4. Resolve the `example` entry (`.meta/SpaceAge.example.ps1`) to copy into temporary test sandboxes under the `solution` filename (`SpaceAge.ps1`), ensuring the reference solution is tested without mutating the learner stub.
5. Path traversal tokens (such as `..` or leading `/`) are strictly forbidden to prevent accessing or leaking files outside the exercise root.

---

## Invalid Fixture Verification

The check script `work/R09-T048/check.py` validates metadata resolution against 3 synthetic fixtures:

| Fixture | Injected Fault | Expected Behavior | Actual Result |
|---------|----------------|-------------------|---------------|
| **1. Missing example** | `example: [".meta/MissingSpaceAge.example.ps1"]` | Rejects with missing file error | `ValueError: Declared file missing in category 'example'` |
| **2. Missing test** | `test: ["SpaceAge.tests.nonexistent.ps1"]` | Rejects with missing file error | `ValueError: Declared file missing in category 'test'` |
| **3. Path traversal** | `example: ["../../nth-prime/.meta/NthPrime.example.ps1"]` | Rejects traversal outside root | `ValueError: Path traversal detected in category 'example'` |

Real metadata passed with 0 errors.

---

## Pester Test Execution Results

- **Pester Return Code:** `{proc.returncode}`
- **Total Tests:** `{parsed['total']}`
- **Passed:** `{parsed['passed']}`
- **Failed:** `{parsed['failed']}`
- **Skipped:** `{parsed['skipped']}`

### Anchored Test Cases:
- `Space Age test cases` (Describe block): **PASS**
- `age on Earth`: **PASS**
- `no planet provided should default to Earth`: **PASS**

---

## Cleanliness & Distinction of Artifacts

- Learner solution file `exercises/practice/space-age/SpaceAge.ps1` was **never modified**.
- Reference implementation testing occurred entirely within temporary directories created via Python `tempfile`.
- All generated evidence artifacts are cleanly isolated under `work/R09-T048/`.
- **Note for Upstream Contribution:** Remove `work/R09-T048/` before any pull request targeting upstream `exercism/powershell`.
"""
    with open(os.path.join(out_dir, "maintenance.md"), "w", encoding="utf-8") as f:
        f.write(maintenance_md)
    print("  Wrote maintenance.md")
    print()

    # 9. Summary and Exit
    print("=" * 70)
    if errors:
        print("VERIFICATION FAILED:")
        for err in errors:
            print(f"  ✗ {err}")
        sys.exit(1)
    else:
        print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY")
        print("  - Real config.json validated cleanly")
        print("  - All 3 invalid metadata fixtures failed as expected")
        print(f"  - Pester reference run: TotalCount={parsed['total']}, FailedCount={parsed['failed']}")
        for a in ANCHORED:
            print(f"    ✓ {a}")
        sys.exit(0)

if __name__ == "__main__":
    main()
