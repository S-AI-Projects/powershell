# Isogram Exercise Maintenance & Test Generation

## Overview

The `isogram` exercise tests whether a string contains no repeating letters (excluding spaces and hyphens). Tests are derived from Exercism's canonical problem specifications and synced via `configlet`.

## Generation & Synchronization Command

To synchronize canonical test definitions into `tests.toml`:

```bash
./bin/configlet sync --tests --exercise isogram
```

### Input Files

1. `exercises/practice/isogram/.meta/tests.toml` - Track test case inclusion/exclusion metadata.
2. Upstream `problem-specifications/exercises/isogram/canonical-data.json` - Canonical test data.
3. `exercises/practice/isogram/.meta/config.json` - Exercise configuration and file paths.

### Output File

- `exercises/practice/isogram/Isogram.tests.ps1` - Pester test suite.

## Case-to-Output Mapping

| Test Name / Case | Canonical UUID | Input (`phrase`) | Expected Output | Assertion |
| :--- | :--- | :--- | :--- | :--- |
| `Describe "IsogramTests"` | N/A | Container Block | N/A | Top-level Pester test block |
| `empty string` | `a0e97d2d-669e-47c7-8134-518a1e2c4555` | `""` | `$true` | `$got \| Should -BeTrue` |
| `isogram with only lower case characters` | `9a001b50-f194-4143-bc29-2af5ec1ef652` | `"isogram"` | `$true` | `$got \| Should -BeTrue` |
| `word with one duplicated character` | `8ddb0ca3-276e-4f8b-89da-d95d5bae78a4` | `"eleven"` | `$false` | `$got \| Should -BeFalse` |
| `word with one duplicated character from the end of the alphabet` | `6450b333-cbc2-4b24-a723-0b459b34fe18` | `"zzyzx"` | `$false` | `$got \| Should -BeFalse` |
| `longest reported english isogram` | `a15ff557-dd04-4764-99e7-02cc1a385863` | `"subdermatoglyphic"` | `$true` | `$got \| Should -BeTrue` |
| `word with duplicated character in mixed case` | `f1a7f6c7-a42f-4915-91d7-35b2ea11c92e` | `"Alphabet"` | `$false` | `$got \| Should -BeFalse` |
| `word with duplicated character in mixed case, lowercase first` | `14a4f3c1-3b47-4695-b645-53d328298942` | `"alphAbet"` | `$false` | `$got \| Should -BeFalse` |
| `hypothetical isogrammic word with hyphen` | `423b850c-7090-4a8a-b057-97f1cadd7c42` | `"thumbscrew-japingly"` | `$true` | `$got \| Should -BeTrue` |
| `hypothetical word with duplicated character following hyphen` | `93dbeaa0-3c5a-45c2-8b25-428b8eacd4f2` | `"thumbscrew-jappingly"` | `$false` | `$got \| Should -BeFalse` |
| `isogram with duplicated hyphen` | `36b30e5c-173f-49c6-a515-93a3e825553f` | `"six-year-old"` | `$true` | `$got \| Should -BeTrue` |
| `made-up name that is an isogram` | `cdabafa0-c9f4-4c1f-b142-689c6ee17d93` | `"Emily Jung Schwartzkopf"` | `$true` | `$got \| Should -BeTrue` |
| `duplicated character in the middle` | `5fc61048-d74e-48fd-bc34-abfc21552d4d` | `"accentor"` | `$false` | `$got \| Should -BeFalse` |
| `word with duplicated character and with two hyphens` | `0d0b8644-0a1e-4a31-a432-2b3ee270d847` | `"up-to-date"` | `$false` | `$got \| Should -BeFalse` |

## Reproducibility & Normalization

When generating or validating tests, timestamp or formatting headers are normalized so two runs generate identical test blocks without dropping any cases.
