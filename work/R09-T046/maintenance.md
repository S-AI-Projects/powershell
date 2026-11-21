# R09-T046 · Killer Sudoku Helper — Maintenance Notes

## Algorithm: Reference Implementation

**Approach:** Recursive backtracking (`Get-Combination`)

The reference implementation works in two phases:

1. **Pre-filter** `potential = 1..9 | Where { $_ -le $Sum -and $Exclude -notContains $_ }`
   — eliminates digits above the target sum and excluded digits upfront.
2. **Recursive enumeration** — at each level, tries each remaining candidate,
   subtracts it from the running target, advances the range pointer past the
   chosen element (ensuring uniqueness and ascending order automatically), and
   recurses until `Result.Count == Size` and `Target == 0`.

### Worked Example: Sum=10, Size=2, Exclude=[1,4]

```
potential = [2, 3, 5, 6, 7, 8, 9]  (1 and 4 excluded; 10 itself > sum so kept)
Get-Combination(Target=10, Size=2, Range=[2,3,5,6,7,8,9], Result=[])
  try 2 -> Get-Combination(8, 2, [3,5,6,7,8,9], [2])
    try 3 -> Get-Combination(5, 2, [5,6,7,8,9], [2,3])  -- need 1 more but min=5 > 5, skip
    try 5 -> Get-Combination(3, 2, [6,7,8,9], [2,5])    -- remaining all > 3, skip
    try 8 -> Get-Combination(0, 2, [9], [2,8])  -- size=2 ✓, target=0 ✓ => EMIT [2,8]
  try 3 -> Get-Combination(7, 2, [5,6,7,8,9], [3])
    try 7 -> Get-Combination(0, 2, [8,9], [3,7])  => EMIT [3,7]
  try 5 -> Get-Combination(5, 2, [6,7,8,9], [5])  -- min remaining = 6 > 5, skip
  ...
Result: [[2,8], [3,7]]  ✓ matches expected
```

---

## Algorithm: Alternative Implementation (Bitmask / Iterative)

**Approach:** Enumerate all `2^9 = 512` subsets of `{1..9}` using an integer
bitmask. No recursion; no mutable stack.

Each bit position `b` (0-indexed) represents digit `b+1`. A mask is accepted
when:
- It has no bits set that correspond to excluded digits.
- Its popcount (number of set bits) equals `Size`.
- The sum of represented digits equals `Sum`.

```
excludeMask for Exclude=[1,4]: bit0 | bit3 = 0b000001001 = 9

For mask = 0b001000010 = 66  =>  digits {2, 7} (bits 1 and 6)
  mask & excludeMask = 0  OK
  popcount = 2 = Size      OK
  sum = 2+7 = 9 ≠ 10       SKIP

For mask = 0b010000010 = 130 =>  digits {2, 8}
  mask & excludeMask = 0  OK
  popcount = 2 = Size      OK
  sum = 2+8 = 10 = Sum     EMIT [2, 8]  ✓

For mask = 0b001000100 = 68  =>  digits {3, 7}
  sum = 3+7 = 10, popcount = 2  EMIT [3, 7]  ✓
```

Results are naturally emitted in ascending-digit order because bits are
scanned low-to-high, and subsets are iterated in numeric order so the
overall output is sorted.

---

## Trade-off Analysis

| Dimension         | Reference (recursive)         | Alternative (bitmask)             |
|-------------------|-------------------------------|-----------------------------------|
| **Control flow**  | Recursive DFS                 | Single flat `for` loop            |
| **Candidates**    | Pre-filtered; only valid range| Always 512 iterations             |
| **Stack usage**   | O(Size) call frames           | O(1) — no recursion               |
| **Readability**   | Idiomatic PowerShell, clear   | Bit-ops may be unfamiliar         |
| **Constant work** | 512 max (9 digits, C(9,k))    | Always exactly 511 iterations     |
| **Exclusion**     | Pre-filtered before recursion | Single bitmask AND per iteration  |
| **Sorting**       | Implicit from ascending range | Implicit from low-bit enumeration |

**When bitmask is clearer:** When you need to enumerate *all* subsets quickly
and the domain is small and fixed (1–9), a bitmask table avoids managing
recursive state and is trivially parallelisable.

**When reference is clearer:** Recursive backtracking with an explicit
`Target` countdown is easier to extend if the digit range changes (e.g., hex
Sudoku) or if pruning needs to be richer (e.g., prune when remaining digits
cannot possibly reach `Target`).

**Memory:** Both are O(output size). The alternative uses no additional stack;
the reference uses O(Size) stack depth (at most 9 frames — negligible).

---

## Anchored Cases Verified

| Case | Reference | Alternative |
|------|-----------|-------------|
| `KillerSudokuHelper test cases` | PASS | PASS |
| `Trivial 1-digit cages -> 1`    | PASS | PASS |
| `Trivial 1-digit cages -> 2`    | PASS | PASS |

---

## Note for Upstream Contribution

Remove `work/R09-T046/` before any branch targeting upstream `exercism/powershell`.
The learner stub `KillerSudokuHelper.ps1` was **never modified** in the working tree.
All substitution occurred inside Python `tempfile.mkdtemp()` directories.
