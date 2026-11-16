# Binary Search Exercise Maintenance & File-Role Mapping

## Overview

This document specifies the file layout, maintenance roles, and configuration validation for `exercises/practice/binary-search`.

## File Role Map

| Relative Path | Role | Description |
| :--- | :--- | :--- |
| `BinarySearch.ps1` | **Learner Stub** | Initial unsolved template provided to students. Contains function signatures and parameter declarations with empty or throwing body. |
| `BinarySearch.tests.ps1` | **Test Suite** | Pester test specifications checking contract compliance against canonical cases (e.g. `finds a value in an array with one element`, `finds a value in the middle of an array`). |
| `.meta/BinarySearch.example.ps1` | **Reference Implementation** | Maintained complete reference solution used by continuous integration and track test runners. |
| `.meta/config.json` | **Exercise Metadata** | Declarative configuration mapping student-visible files (`solution`, `test`) and instructor reference files (`example`). |
| `.meta/tests.toml` | **Canonical Test Tracking** | Synchronized test tracking metadata tracking upstream canonical-data status. |
| `.docs/instructions.md` | **Documentation** | Problem instructions presented to the learner. |
| `.docs/introduction.md` | **Documentation** | Introductory concept background. |

## Validation Command

To validate that all configured paths resolve strictly within the exercise boundary and reject path traversal:

```bash
python3 tools/course_checks/r09-t028.py
```

To run the Pester test suite against the reference solution in an isolated environment:

```bash
python3 work/R09-T028/check.py
```
