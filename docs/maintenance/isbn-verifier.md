# ISBN verifier file map

## Declared exercise files

The exercise's `.meta/config.json` declares paths relative to `exercises/practice/isbn-verifier`:

| Role | Declared path | Purpose |
| --- | --- | --- |
| solution | `IsbnVerifier.ps1` | Learner stub; keep it unsolved in the reference check. |
| test | `IsbnVerifier.tests.ps1` | Checked-in Pester test source, including valid ISBN and invalid check-digit cases. |
| example | `.meta/IsbnVerifier.example.ps1` | Reference implementation copied to the configured solution name for the reference run. |
| editor | Not declared | This exercise has no editor file in its `files` object. |

The checker reads the `files` object directly, requires the solution/test/example roles, and validates every declared path, including an optional editor role if one is added. Each path must be relative, stay inside the exercise after resolution, and name an existing file. `tools/course_checks/r09-t038.py` also has negative fixtures for missing reference, missing test, and a path outside the exercise. The assignment checker runs all three fixtures and confirms each is rejected for the expected reason.

## How the track runner finds the Pester files

`bin/run-tests.ps1` walks the practice exercise directories. For each exercise, it copies files matching `*.tests.ps1` into a temporary directory, searches that exercise's `.meta` directory for `*.example.ps1`, and renames `IsbnVerifier.example.ps1` by removing `example.` to create `IsbnVerifier.ps1` in the temporary directory. It then runs Pester there. The current track runner discovers these two files by their filename patterns; it does not read `.meta/config.json`. The focused task checker uses the config paths directly so the declarations are independently verified and used without filename guessing.

## Generated metadata

`.meta/tests.toml` is marked auto-generated in its header and stores canonical test-case descriptions. Configlet sync maintains that metadata. `IsbnVerifier.tests.ps1` is the Pester source copied by the track runner; it is not created by `bin/run-tests.ps1`. No exercise-specific test template is present. Keep the learner stub, reference example, test source, and canonical metadata in their respective roles.

Run the exercise-specific reference and configuration check with:

```sh
python3 work/R09-T038/check.py
```
