#!/usr/bin/env python3
"""
Path and configuration checker for binary-search (R09-T028).
Validates that solution, test, and example files declared in config.json exist,
rejects path traversal, and verifies invalid fixture rejection.
"""
import copy
import json
import os
import sys

def validate_config(exercise_dir, config_dict):
    """
    Validates file configuration dictionary against exercise directory.
    Returns (True, "OK") or (False, error_reason).
    """
    if "files" not in config_dict:
        return False, "Missing 'files' object in config"

    files_obj = config_dict["files"]
    required_keys = ["solution", "test", "example"]

    for key in required_keys:
        if key not in files_obj or not files_obj[key]:
            return False, f"Missing or empty required file key: {key}"

        for rel_path in files_obj[key]:
            # Reject path traversal or absolute paths
            if os.path.isabs(rel_path) or ".." in rel_path.split(os.sep):
                return False, f"Path traversal or absolute path rejected: {rel_path}"

            full_path = os.path.normpath(os.path.join(exercise_dir, rel_path))
            if not full_path.startswith(os.path.abspath(exercise_dir)):
                return False, f"File path resolves outside exercise root: {rel_path}"

            if not os.path.isfile(full_path):
                return False, f"Declared file does not exist: {rel_path}"

    return True, "Valid configuration"

def test_fixtures(exercise_dir, real_config):
    # Fixture 1: Missing reference
    f1 = copy.deepcopy(real_config)
    f1["files"]["example"] = [".meta/NonExistent.example.ps1"]
    ok1, reason1 = validate_config(exercise_dir, f1)
    if ok1 or "Declared file does not exist" not in reason1:
        print(f"FAIL: Fixture 1 (missing reference) did not fail properly: {ok1}, {reason1}")
        return False

    # Fixture 2: Missing test
    f2 = copy.deepcopy(real_config)
    f2["files"]["test"] = ["Missing.tests.ps1"]
    ok2, reason2 = validate_config(exercise_dir, f2)
    if ok2 or "Declared file does not exist" not in reason2:
        print(f"FAIL: Fixture 2 (missing test) did not fail properly: {ok2}, {reason2}")
        return False

    # Fixture 3: Outside exercise path traversal
    f3 = copy.deepcopy(real_config)
    f3["files"]["solution"] = ["../outside.ps1"]
    ok3, reason3 = validate_config(exercise_dir, f3)
    if ok3 or "Path traversal" not in reason3:
        print(f"FAIL: Fixture 3 (outside exercise) did not fail properly: {ok3}, {reason3}")
        return False

    return True

def main():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    exercise_dir = os.path.join(repo_root, "exercises", "practice", "binary-search")
    config_file = os.path.join(exercise_dir, ".meta", "config.json")

    with open(config_file) as f:
        real_config = json.load(f)

    # Validate real configuration
    ok, reason = validate_config(exercise_dir, real_config)
    if not ok:
        print(f"FAIL: Real config validation failed: {reason}")
        sys.exit(1)

    # Test deliberately invalid fixtures
    if not test_fixtures(exercise_dir, real_config):
        sys.exit(1)

    print("SUCCESS: Real config passed and all 3 invalid fixtures failed as expected.")

if __name__ == "__main__":
    main()
