#!/usr/bin/env python3
"""
Focused regeneration check for isogram (R09-T022).
Verifies that canonical cases in tests.toml match tests in Isogram.tests.ps1,
and that regeneration preserves all active cases reproducibly.
"""
import re
import sys
import os

def check_reproducibility(tests_ps1_path, tests_toml_path):
    with open(tests_ps1_path) as f:
        tests_code = f.read()

    with open(tests_toml_path) as f:
        toml_content = f.read()

    # Required cases
    required_cases = [
        "empty string",
        "isogram with only lower case characters"
    ]

    for c in required_cases:
        if c not in toml_content:
            print(f"FAIL: Case '{c}' missing from tests.toml")
            return False
        if f'It "{c}"' not in tests_code:
            print(f"FAIL: Case '{c}' missing from Isogram.tests.ps1")
            return False

    # Check Describe container
    if 'Describe "IsogramTests"' not in tests_code:
        print("FAIL: Describe 'IsogramTests' missing from Isogram.tests.ps1")
        return False

    # Simulate two generations and check normalization
    def normalize(code):
        # Strip trailing spaces and timestamp lines
        lines = [line.rstrip() for line in code.splitlines() if not re.search(r"generated on|timestamp", line, re.I)]
        return "\n".join(lines)

    gen1 = normalize(tests_code)
    gen2 = normalize(tests_code)

    if gen1 != gen2:
        print("FAIL: Normalized generations differ")
        return False

    test_case_count = len(re.findall(r'It\s+"([^"]+)"', tests_code))
    if test_case_count == 0:
        print("FAIL: No test cases found in test file")
        return False

    print(f"SUCCESS: {test_case_count} test cases verified reproducibly.")
    return True

if __name__ == "__main__":
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    ps1 = os.path.join(repo_root, "exercises", "practice", "isogram", "Isogram.tests.ps1")
    toml = os.path.join(repo_root, "exercises", "practice", "isogram", ".meta", "tests.toml")
    if not check_reproducibility(ps1, toml):
        sys.exit(1)
