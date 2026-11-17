# Ledger Exercise Maintenance

## Overview
This document records the canonical case mapping, test coverage decisions, and rationale for exclusions in the PowerShell track's `ledger` exercise (`exercises/practice/ledger`).

## Canonical Cases & Test Mapping

The exercise defines 12 canonical test cases in `.meta/tests.toml`, corresponding to upstream Exercism `problem-specifications/exercises/ledger/canonical-data.json`.

| UUID | Description | Status | Reimplemented By / Notes | Test in `Ledger.tests.ps1` |
|---|---|---|---|---|
| `d131ecae-a30e-436c-b8f3-858039a27234` | empty ledger | Included | Base header verification | `empty ledger` |
| `ce4618d2-9379-4eca-b207-9df1c4ec8aaa` | one entry | Included | Single negative entry in en-US/USD | `one entry` |
| `8d02e9cb-e6ee-4b77-9ce4-e5aec8eb5ccb` | credit and debit | Included | Entries with different dates (2015-01-01 and 2015-01-02) | `credit and debit` |
| `502c4106-0371-4e7c-a7d8-9ce33f16ccb1` | multiple entries on same date ordered by description | **Excluded** | Superseded by `9c70709f-cbbd-4b3b-b367-81d7c6101de4` | N/A (flawed canonical input) |
| `29dd3659-6c2d-4380-94a8-6d96086e28e1` | final order tie breaker is change | Included | Same date & description, ordered by amount | `final order tie breaker is change` |
| `9b9712a6-f779-4f5c-a759-af65615fcbb9` | overlong description is truncated | Included | Tests truncation at 25 characters with ellipsis (`...`) | `overlong description is truncated` |
| `67318aad-af53-4f3d-aa19-1293b4d4c924` | euros | Included | Currency formatting with EUR in en-US | `euros` |
| `bdc499b6-51f5-4117-95f2-43cb6737208e` | Dutch locale | Included | nl-NL locale formatting with USD | `Dutch locale` |
| `86591cd4-1379-4208-ae54-0ee2652b4670` | Dutch locale and euros | Included | nl-NL locale formatting with EUR | `Dutch locale and euros` |
| `876bcec8-d7d7-4ba4-82bd-b836ac87c5d2` | Dutch negative number with 3 digits before decimal point | Included | Negative currency format for nl-NL | `Dutch negative number with 3 digits before decimal point` |
| `29670d1c-56be-492a-9c5e-427e4b766309` | American negative number with 3 digits before decimal point | Included | Negative currency format for en-US | `American negative number with 3 digits before decimal point` |
| `9c70709f-cbbd-4b3b-b367-81d7c6101de4` | multiple entries on same date ordered by description | Included | Replaces `502c4106-0371-4e7c-a7d8-9ce33f16ccb1` with fixed dates | `multiple entries on same date ordered by description` |

## Rationale for Exclusion (`502c4106-0371-4e7c-a7d8-9ce33f16ccb1`)

In the original problem-specifications canonical data:
- `502c4106-0371-4e7c-a7d8-9ce33f16ccb1` was entitled *"multiple entries on same date ordered by description"*. However, its input entries contained dates `'2015-01-02'` and `'2015-01-01'` (different dates). Because the dates were not the same, the test did not actually exercise description ordering for entries sharing the same date.
- Upstream corrected this defect in case `9c70709f-cbbd-4b3b-b367-81d7c6101de4` (setting both entry dates to `'2015-01-01'`) and marked it with `reimplements = "502c4106-0371-4e7c-a7d8-9ce33f16ccb1"`.
- Consequently, `502c4106-0371-4e7c-a7d8-9ce33f16ccb1` is intentionally marked `include = false` in `tests.toml`. Its exclusion is not due to a limitation in PowerShell, but because it was superseded upstream by the corrected reimplementation `9c70709f-cbbd-4b3b-b367-81d7c6101de4`, which is actively implemented and passing in `Ledger.tests.ps1`.

## Verification Command
```bash
python3 work/R09-T001/check.py
```
