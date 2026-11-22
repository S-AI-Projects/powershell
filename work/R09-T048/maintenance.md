# R09-T048 · Space Age — Metadata Resolution & Runner Verification

## Metadata Specification in `config.json`

The file `exercises/practice/space-age/.meta/config.json` specifies:
```json
{
  "files": {
    "solution": [
      "SpaceAge.ps1"
    ],
    "test": [
      "SpaceAge.tests.ps1"
    ],
    "example": [
      ".meta/SpaceAge.example.ps1"
    ]
  }
}
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

- **Pester Return Code:** `0`
- **Total Tests:** `10`
- **Passed:** `10`
- **Failed:** `0`
- **Skipped:** `0`

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
