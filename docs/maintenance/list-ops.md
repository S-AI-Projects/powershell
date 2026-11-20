# List Ops reference check

Use `work/R09-T039/check.py` to validate the runner's success, assertion-failure, and zero-test paths:

```sh
python3 work/R09-T039/check.py
```

The task checker calls `tools/course_checks/r09-t039.py`. That runner reads solution, test, and example paths from `exercises/practice/list-ops/.meta/config.json`, copies the exercise including dotfiles into a temporary directory, and substitutes the example only for the configured learner solution inside that copy. It runs `Invoke-Pester -PassThru`, checks child exit status, rejects zero tests and failed assertions, and records learner-file hashes before and after the run. Temporary files are removed when the run finishes.

Requirements: Python 3, PowerShell 7, and Pester. To run only the reference scenario directly:

```sh
python3 tools/course_checks/r09-t039.py --mode reference
```

The task checker additionally exercises a deliberately failing append reference and an empty Pester selection. Those runs must return non-zero, report their failure or zero-test count, clean up their temporary directories, and leave the learner file hash unchanged.
