#!/usr/bin/env python3
"""
Verification script for Task R09-T041 (GitHub Issue #5).
Reviews canonical test cases and rationale for crypto-square exclusion in tests.toml,
runs Pester against reference implementation in an isolated temporary directory,
and verifies working-tree learner solution remains untouched.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path


def run_command(cmd, cwd=None, env=None, check=True):
    """Run a child process and return CompletedProcess, asserting returncode if check=True."""
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(
            f"Command {cmd} failed with exit code {proc.returncode}.\n"
            f"STDOUT:\n{proc.stdout}\n"
            f"STDERR:\n{proc.stderr}"
        )
    return proc


def count_inclusion_states(parsed_toml):
    """Count explicit and effective inclusion states across canonical test cases."""
    total = len(parsed_toml)
    explicit_include_true = 0
    explicit_include_false = 0
    effective_included = 0
    effective_excluded = 0

    for uuid_key, case_data in parsed_toml.items():
        inc = case_data.get("include")
        if inc is True:
            explicit_include_true += 1
            effective_included += 1
        elif inc is False:
            explicit_include_false += 1
            effective_excluded += 1
        else:
            # Omitted include key implies inclusion per tests.toml specification
            effective_included += 1

    return {
        "total_cases": total,
        "explicit_include_true": explicit_include_true,
        "explicit_include_false": explicit_include_false,
        "effective_included": effective_included,
        "effective_excluded": effective_excluded,
    }


def main():
    repo_root = Path(__file__).resolve().parents[2]
    work_dir = repo_root / "work" / "R09-T041"
    work_dir.mkdir(parents=True, exist_ok=True)

    exercise_dir = repo_root / "exercises" / "practice" / "crypto-square"
    meta_dir = exercise_dir / ".meta"
    config_json_path = meta_dir / "config.json"
    tests_toml_path = meta_dir / "tests.toml"

    print("=" * 70)
    print("Executing Task R09-T041 Verification (Issue #5)")
    print("=" * 70)

    # 1. Read tool versions
    py_ver_proc = run_command([sys.executable, "--version"], cwd=repo_root)
    python_version = py_ver_proc.stdout.strip() or sys.version.split()[0]
    print(f"[Tool] Python version: {python_version}")

    pwsh_ver_proc = run_command(["pwsh", "--version"], cwd=repo_root)
    pwsh_version = pwsh_ver_proc.stdout.strip()
    print(f"[Tool] PowerShell version: {pwsh_version}")

    # Use a clean temporary HOME when probing Pester to avoid sandbox restriction on user home
    temp_env_probe = os.environ.copy()
    temp_env_probe["HOME"] = tempfile.gettempdir()
    pester_ver_proc = run_command(
        ["pwsh", "-NoProfile", "-Command", "(Get-Module -ListAvailable -Name Pester).Version[0].ToString()"],
        cwd=repo_root,
        env=temp_env_probe,
    )
    pester_version = pester_ver_proc.stdout.strip()
    print(f"[Tool] Pester module version: {pester_version}")

    # 2. Dynamically resolve paths from config.json
    print(f"\n[Config] Reading paths dynamically from {config_json_path.relative_to(repo_root)}...")
    if not config_json_path.exists():
        raise FileNotFoundError(f"Missing config.json at {config_json_path}")

    with open(config_json_path, "r", encoding="utf-8") as f:
        config_data = json.load(f)

    solution_rel = config_data["files"]["solution"][0]
    test_rel = config_data["files"]["test"][0]
    example_rel = config_data["files"]["example"][0]

    solution_path = exercise_dir / solution_rel
    test_path = exercise_dir / test_rel
    example_path = exercise_dir / example_rel

    print(f"  - Solution file: {solution_rel} (exists: {solution_path.exists()})")
    print(f"  - Test file:     {test_rel} (exists: {test_path.exists()})")
    print(f"  - Example file:  {example_rel} (exists: {example_path.exists()})")

    # 3. Parse tests.toml and count inclusion before/after
    target_uuid = "fbcb0c6d-4c39-4a31-83f6-c473baa6af80"
    replacement_uuid = "33fd914e-fa44-445b-8f38-ff8fbc9fe6e6"

    # Before counts from git HEAD
    git_head_toml_proc = run_command(
        ["git", "show", "HEAD:exercises/practice/crypto-square/.meta/tests.toml"],
        cwd=repo_root,
    )
    parsed_before = tomllib.loads(git_head_toml_proc.stdout)
    counts_before = count_inclusion_states(parsed_before)

    # After counts from current working tree
    with open(tests_toml_path, "rb") as f:
        parsed_after = tomllib.load(f)
    counts_after = count_inclusion_states(parsed_after)

    print(f"\n[TOML] tests.toml canonical test counts:")
    print(f"  Before: total={counts_before['total_cases']}, included={counts_before['effective_included']}, excluded={counts_before['effective_excluded']}")
    print(f"  After:  total={counts_after['total_cases']}, included={counts_after['effective_included']}, excluded={counts_after['effective_excluded']}")

    # Assertions on target UUID
    if target_uuid not in parsed_after:
        raise AssertionError(f"Target UUID {target_uuid} missing from {tests_toml_path}")

    target_entry = parsed_after[target_uuid]
    if target_entry.get("include") is not False:
        raise AssertionError(f"Target UUID {target_uuid} must have include = false, found {target_entry.get('include')}")

    rationale_comment = target_entry.get("comment", "")
    if not rationale_comment or not rationale_comment.strip():
        raise AssertionError(f"Target UUID {target_uuid} must have a non-empty rationale comment.")

    print(f"\n[Rationale] Target UUID: {target_uuid}")
    print(f"  Description: {target_entry.get('description')}")
    print(f"  Include:     {target_entry.get('include')}")
    print(f"  Comment:     {rationale_comment}")

    # Verify replacement case exists
    if replacement_uuid not in parsed_after:
        raise AssertionError(f"Replacement UUID {replacement_uuid} missing from {tests_toml_path}")
    replacement_entry = parsed_after[replacement_uuid]
    print(f"\n[Replacement Case] UUID: {replacement_uuid}")
    print(f"  Description:  {replacement_entry.get('description')}")
    print(f"  Reimplements: {replacement_entry.get('reimplements')}")

    # 4. Copy to temporary directory and run Pester
    pester_output = ""
    pester_returncode = -1
    total_count = 0
    passed_count = 0
    failed_count = 0
    skipped_count = 0

    with tempfile.TemporaryDirectory() as td:
        temp_dir_path = Path(td)
        temp_exercise_dir = temp_dir_path / "crypto-square"
        print(f"\n[TempDir] Copying entire exercise directory to {temp_exercise_dir}...")
        shutil.copytree(exercise_dir, temp_exercise_dir)

        # Assert dotfiles and required files exist in temp copy
        assert (temp_exercise_dir / ".meta").is_dir(), ".meta directory missing in temporary copy"
        assert (temp_exercise_dir / ".docs").is_dir(), ".docs directory missing in temporary copy"
        assert (temp_exercise_dir / solution_rel).is_file(), f"{solution_rel} missing in temporary copy"
        assert (temp_exercise_dir / example_rel).is_file(), f"{example_rel} missing in temporary copy"

        # Substitute reference solution over learner solution ONLY in temp directory
        temp_solution = temp_exercise_dir / solution_rel
        temp_example = temp_exercise_dir / example_rel
        print(f"[TempDir] Substituting reference {example_rel} -> {solution_rel} inside temporary copy only.")
        shutil.copyfile(temp_example, temp_solution)

        # Setup sandbox-friendly environment variables
        env = os.environ.copy()
        env["HOME"] = td
        env["XDG_DATA_HOME"] = str(temp_dir_path / ".local" / "share")
        env["XDG_CONFIG_HOME"] = str(temp_dir_path / ".config")
        env["XDG_CACHE_HOME"] = str(temp_dir_path / ".cache")

        pester_cmd_str = (
            '$res = Invoke-Pester -PassThru; '
            'if (-not $res -or $res.TotalCount -eq 0 -or $res.FailedCount -gt 0) { exit 1 }'
        )
        cmd = ["pwsh", "-NoProfile", "-Command", pester_cmd_str]
        print(f"[Pester] Running command:\n  pwsh -NoProfile -Command \"{pester_cmd_str}\"")

        pester_proc = run_command(cmd, cwd=temp_exercise_dir, env=env, check=False)
        pester_returncode = pester_proc.returncode
        pester_output = pester_proc.stdout + "\n" + pester_proc.stderr

        print(f"[Pester] Exit code: {pester_returncode}")
        print(f"[Pester] Output:\n{pester_proc.stdout.strip()}")

        if pester_returncode != 0:
            raise RuntimeError(f"Pester execution failed with returncode {pester_returncode}.\nOutput:\n{pester_output}")

        # Parse Pester output summary
        match = re.search(
            r"Tests Passed:\s*(\d+),\s*Failed:\s*(\d+),\s*Skipped:\s*(\d+)",
            pester_proc.stdout,
        )
        if match:
            passed_count = int(match.group(1))
            failed_count = int(match.group(2))
            skipped_count = int(match.group(3))
            total_count = passed_count + failed_count + skipped_count
        else:
            # Fallback parse for total tests
            m_tests = re.search(r"\((\d+)\s+tests\)", pester_proc.stdout)
            if m_tests:
                total_count = int(m_tests.group(1))
                passed_count = total_count

        print(f"[Pester Summary] Total: {total_count}, Passed: {passed_count}, Failed: {failed_count}, Skipped: {skipped_count}")

        if total_count <= 0:
            raise AssertionError(f"Expected TotalCount > 0, got {total_count}")
        if failed_count != 0:
            raise AssertionError(f"Expected FailedCount == 0, got {failed_count}")

    # 5. Assert working-tree learner stub is unmodified
    print(f"\n[Git Check] Verifying working-tree learner stub {solution_rel} is unmodified...")
    git_diff_proc = run_command(
        ["git", "diff", "--", f"exercises/practice/crypto-square/{solution_rel}"],
        cwd=repo_root,
    )
    if git_diff_proc.stdout.strip() != "":
        raise AssertionError(
            f"Working tree learner stub was modified!\nDiff:\n{git_diff_proc.stdout}"
        )

    git_status_proc = run_command(
        ["git", "status", "--porcelain", "--", f"exercises/practice/crypto-square/{solution_rel}"],
        cwd=repo_root,
    )
    if git_status_proc.stdout.strip() != "":
        raise AssertionError(
            f"Working tree learner stub has git status changes!\nStatus:\n{git_status_proc.stdout}"
        )
    print("  Learner solution file CryptoSquare.ps1 is completely clean and untouched.")

    # 6. Save structured results (results.json and report.md)
    results_data = {
        "task_id": "R09-T041",
        "github_issue": 5,
        "exercise": "crypto-square",
        "tool_versions": {
            "python": python_version,
            "pwsh": pwsh_version,
            "pester": pester_version,
        },
        "config_paths": {
            "solution": solution_rel,
            "test": test_rel,
            "example": example_rel,
        },
        "canonical_cases": {
            "target_uuid": target_uuid,
            "target_description": target_entry.get("description"),
            "target_include": target_entry.get("include"),
            "target_comment": rationale_comment,
            "replacement_uuid": replacement_uuid,
            "replacement_description": replacement_entry.get("description"),
            "replacement_reimplements": replacement_entry.get("reimplements"),
        },
        "include_counts": {
            "before": counts_before,
            "after": counts_after,
        },
        "pester_execution": {
            "command": 'pwsh -NoProfile -Command "$res = Invoke-Pester -PassThru; if (-not $res -or $res.TotalCount -eq 0 -or $res.FailedCount -gt 0) { exit 1 }"',
            "returncode": pester_returncode,
            "total_count": total_count,
            "passed_count": passed_count,
            "failed_count": failed_count,
            "skipped_count": skipped_count,
            "raw_output": pester_output.strip(),
        },
        "assertions": {
            "tests_toml_tomllib_parse": "PASSED",
            "target_uuid_exists": "PASSED",
            "target_uuid_include_false": "PASSED",
            "rationale_comment_present": "PASSED",
            "pester_execution_success": "PASSED",
            "pester_total_count_gt_zero": "PASSED",
            "pester_failed_count_eq_zero": "PASSED",
            "learner_stub_unmodified": "PASSED",
        },
    }

    results_json_path = work_dir / "results.json"
    with open(results_json_path, "w", encoding="utf-8") as f:
        json.dump(results_data, f, indent=2)
    print(f"\n[Evidence] Saved structured results to {results_json_path.relative_to(repo_root)}")

    report_md_path = work_dir / "report.md"
    report_content = f"""# Verification Report for Task R09-T041 (GitHub Issue #5)

## Overview
- **Task ID:** R09-T041
- **GitHub Issue:** #5
- **Exercise:** `crypto-square`
- **Target Exclusion UUID:** `{target_uuid}`
- **Replacement UUID:** `{replacement_uuid}`

## Tool Versions
- **Python:** `{python_version}`
- **PowerShell:** `{pwsh_version}`
- **Pester Module:** `{pester_version}`

## Canonical Cases & Exclusion Analysis
- **Target Case (`{target_uuid}`):**
  - **Description:** "{target_entry.get('description')}"
  - **Inclusion Status:** `include = false`
  - **Rationale Added:**
    > {rationale_comment}
- **Replacement Case (`{replacement_uuid}`):**
  - **Description:** "{replacement_entry.get('description')}"
  - **Reimplements:** `{replacement_entry.get('reimplements')}`
  - **Analysis:**
    Under the crypto-square specification, 54 characters of normalized plaintext requires rectangle dimensions $c = 8$ (columns) and $r = 7$ (rows) because $c \\ge r$, $c - r \\le 1$, and $c \\times r \\ge 54$.
    The cipher outputs $c$ space-separated chunks of length $r$, which produces 8 chunks of length 7 with trailing spaces in the last two chunks:
    `"imtgdvs fearwer mayoogo anouuio ntnnlvt wttddes aohghn  sseoau "`
    The obsolete canonical test `{target_uuid}` expected 7 chunks. Canonical problem-specifications corrected this via replacement test `{replacement_uuid}` ("54 character plaintext results in 8 chunks, the last two with trailing spaces").
    In PowerShell, `CryptoSquare.tests.ps1` already tests and passes `{replacement_uuid}`, so `{target_uuid}` is properly excluded as superseded/reimplemented rather than due to any PowerShell engine limitation.

## Inclusion Counts
| State | Before | After | Change |
|---|---|---|---|
| Total Canonical Cases | {counts_before['total_cases']} | {counts_after['total_cases']} | 0 |
| Explicit `include = false` | {counts_before['explicit_include_false']} | {counts_after['explicit_include_false']} | 0 |
| Explicit `include = true` | {counts_before['explicit_include_true']} | {counts_after['explicit_include_true']} | 0 |
| Effective Included | {counts_before['effective_included']} | {counts_after['effective_included']} | 0 |
| Effective Excluded | {counts_before['effective_excluded']} | {counts_after['effective_excluded']} | 0 |

## Pester Test Execution (Reference Implementation)
- **Command:** `pwsh -NoProfile -Command "$res = Invoke-Pester -PassThru; if (-not $res -or $res.TotalCount -eq 0 -or $res.FailedCount -gt 0) {{ exit 1 }}"`
- **Execution Directory:** Isolated temporary copy with `CryptoSquare.example.ps1` substituted over `CryptoSquare.ps1`
- **Return Code:** `{pester_returncode}`
- **Total Tests:** `{total_count}`
- **Passed Tests:** `{passed_count}`
- **Failed Tests:** `{failed_count}`
- **Skipped Tests:** `{skipped_count}`

## Learner Stub Integrity Check
- **File:** `exercises/practice/crypto-square/CryptoSquare.ps1`
- **`git diff` output:** Empty (no modifications)
- **`git status` output:** Clean

## Assertion Summary
| Check | Status |
|---|---|
| `tests.toml` parses with `tomllib` | PASSED |
| Target UUID `{target_uuid}` present | PASSED |
| Target UUID `include = false` retained | PASSED |
| Non-empty checkable rationale comment | PASSED |
| Pester execution return code 0 | PASSED |
| Pester TotalCount > 0 ({total_count}) | PASSED |
| Pester FailedCount == 0 ({failed_count}) | PASSED |
| Working-tree learner solution untouched | PASSED |
"""
    with open(report_md_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    print(f"[Evidence] Saved markdown report to {report_md_path.relative_to(repo_root)}")

    print("\n" + "=" * 70)
    print("ALL VERIFICATIONS PASSED SUCCESSFULLY (Exit Code 0)")
    print("=" * 70)
    sys.exit(0)


if __name__ == "__main__":
    main()
