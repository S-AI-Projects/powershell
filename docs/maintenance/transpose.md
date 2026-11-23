# Maintenance Notes: transpose

## Exercise metadata

- Track: PowerShell
- Slug: `transpose`
- Exercise directory: `exercises/practice/transpose/`
- Reference implementation: `exercises/practice/transpose/.meta/Transpose.example.ps1`

## Mutation record (R09-T053)

### Mutation applied

| Field | Value |
|---|---|
| **File mutated** | `.meta/Transpose.example.ps1` |
| **Original line** | `(-join ($lines \| ForEach-Object {$_[$row] ? $_[$row] : " "})).TrimEnd()` |
| **Mutant line** | `(-join ($lines \| ForEach-Object {$_[$row] ? $_[$row] : " "})).Trim()` |
| **Change** | `.TrimEnd()` → `.Trim()` |
| **Nature** | Semantic — `.Trim()` strips both leading and trailing whitespace, incorrectly removing leading spaces from output rows that represent padding for shorter input rows. |

### Rejecting test case

| Field | Value |
|---|---|
| **UUID** | `984e2ec3-b3d3-4b53-8bd6-96f5ef404102` |
| **Test name** | `second line longer than first line` |
| **Input** | `"The first line.\nThe second line."` |
| **Expected last output row** | `" ."` (space + period — leading space preserved) |
| **Mutant output last row** | `"."` (leading space stripped by `.Trim()`) |

### Why the mutant is wrong

The transpose spec requires that when a later row is longer than an earlier row, the missing characters of the earlier row become **spaces** in the transposed output. These spaces appear at the **beginning** of an output row (not the end), so `.TrimEnd()` correctly preserves them while `.Trim()` erroneously removes them.

### Smallest diagnostic input

The smallest input that distinguishes the original from the mutant:

| Input | Original output | Mutant output |
|---|---|---|
| `"AB\nDEF"` | `"AD\nBE\n F"` | `"AD\nBE\nF"` |

The third output row `" F"` has a leading space because input row 0 (`"AB"`) is shorter than row 1 (`"DEF"`). The `.Trim()` mutation strips this leading space, producing `"F"` instead.

### Cases that do NOT distinguish the mutant

The following named cases pass on both original and mutant because their inputs do not produce output rows with leading spaces:

| Test name | UUID | Reason |
|---|---|---|
| `empty string` | `404b7262-c050-4df0-a2a2-0cb06cd6a821` | Empty input, empty output — no spaces at all |
| `two characters in a row` | `a89ce8a3-c940-4703-a688-3ea39412fbcb` | Input `"A1"` → output `"A\n1"`, no leading spaces |

### Cases that DO distinguish the mutant (additional)

| Test name | Reason |
|---|---|
| `triangle` | Produces multiple output rows with leading spaces (e.g., `" EASER"`, `"  ASER"`, ...) |
| `jagged triangle` | Same reason as triangle |
| `many Text` | Long input with many rows of varying lengths produces many leading-space rows |

## hints.md rationale

The hint in `exercises/practice/transpose/.docs/hints.md` explains the leading-space padding contract and provides the diagnostic input `"AB\nDEF"` → `" F"`. It does **not** publish the reference implementation or reveal the `.TrimEnd()` function.

## Test count

Total enabled test cases in `tests.toml`: 12 (all 12 UUIDs present, none excluded).
Total `It` blocks in `Transpose.tests.ps1`: 13 (the `many Text` case is not in `tests.toml` as a canonical UUID but is present in the test file).

