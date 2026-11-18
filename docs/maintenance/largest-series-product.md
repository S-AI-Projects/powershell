# Largest Series Product Maintenance & File-Role Mapping

## Overview
This document specifies the file-role map for `exercises/practice/largest-series-product` and documents how the Exercism test runner resolves the solution stub, test suite, and exemplar reference implementation.

## File-Role Map

All file paths are declared relative to the exercise root directory (`exercises/practice/largest-series-product`):

| Role | Config Key | Declared Path | Description & Maintenance Status |
|---|---|---|---|
| **Solution Stub** | `files.solution` | `LargestSeriesProduct.ps1` | Starter code given to learners. Contains empty function throwing `"Please implement this function."`. Maintained by hand. |
| **Test Suite** | `files.test` | `LargestSeriesProduct.tests.ps1` | Executable Pester 5/6 test assertions covering all canonical cases. Maintained by hand. |
| **Exemplar Reference** | `files.example` | `.meta/LargestSeriesProduct.example.ps1` | Reference implementation used by CI to verify that all enabled tests pass. Maintained by hand. |
| **Test Manifest** | N/A (Internal) | `.meta/tests.toml` | Track test manifest synchronized via `configlet sync --tests -e largest-series-product`. Auto-generated/synced. |
| **Exercise Metadata** | N/A (Internal) | `.meta/config.json` | Exercise metadata declaring author, files list, blurb, and upstream source. Maintained by hand. |

## How the Test Runner Resolves Files
The Exercism CI runner and track script (`bin/run-tests.ps1`):
1. Reads `exercises/practice/largest-series-product/.meta/config.json`.
2. Locates the test suite (`LargestSeriesProduct.tests.ps1`) via `files.test`.
3. Locates the exemplar reference (`.meta/LargestSeriesProduct.example.ps1`) via `files.example`.
4. Copies the files to an isolated temporary directory, placing the example solution at `LargestSeriesProduct.ps1` (replacing the starter stub only in the temporary environment).
5. Invokes `Invoke-Pester -PassThru` against the temporary directory.

## Reproducible Validation Command
```bash
python3 tools/course_checks/r09-t008.py
# or
python3 work/R09-T008/check.py
```
This checker verifies that:
1. `config.json` correctly parses and all declared paths resolve inside the exercise root (preventing path traversal).
2. All declared files exist.
3. Three deliberately malformed fixtures (missing reference, missing test, and directory traversal) are rejected with exact error classifications.
4. The reference solution passes all 13 test cases in an isolated temporary directory.
