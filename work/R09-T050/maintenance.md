# R09-T050 · Knapsack — Decision Table & Specification Guidance

## 1. Specification Derivation for Anchored Test Cases

The 0-1 Knapsack problem defines the optimal value:
max sum(v_i) subject to sum(w_i) <= W, where subset S is chosen from {item_1, ..., item_n}.

### `no items`
- **Input:** `MaxWeight = 100`, `Items = @()`
- **Derivation:** The set of available items is empty ($n = 0$). The only subset is the empty set.
  - Total weight: 0 <= 100 (feasible).
  - Total value: 0.
- **Expected Outcome:** `0`.

### `one item, too heavy`
- **Input:** `MaxWeight = 10`, `Items = @([PSCustomObject]@{Weight = 100; Value = 1})`
- **Derivation:** The available items are {item_1} with weight = 100, value = 1.
  - Subset {item_1}: weight = 100 > 10 (infeasible, exceeds capacity).
  - Subset {}: total weight 0 <= 10 (feasible), total value 0.
- **Expected Outcome:** `0`.

---

## 2. Decision Table

| Condition | Test Input (`Items`, `MaxWeight`) | Admissible Subsets | Required Outcome | Contract Status |
|-----------|----------------------------------|--------------------|------------------|-----------------|
| Items is empty ($n=0$) | `Items = @()`, `MaxWeight = 100` | {empty} | `0` | **Specified** |
| All items exceed $MaxWeight$ | `Items = [{W: 100, V: 1}]`, `MaxWeight = 10` | {empty} | `0` | **Specified** |
| Admissible non-empty subsets exist | General cases (`5 items`, `example`, `8 items`, `15 items`) | Feasible subsets with sum(w_i) <= W | max total value | **Specified** |
| Out-of-contract inputs (negative weight/value, null, non-integers) | weight <= 0, value <= 0, W < 0, etc. | Undefined | **Unspecified** | **Out-of-Contract** |

---

## 3. Explicit Statement on Unspecified Behavior

The exercise instructions specify:
- "All values given will be strictly positive."
- "Lhakpa can take only one of each item."
- Knapsack has a carrying capacity.

**What the specification leaves unspecified:**
- Behavior on negative carrying capacity (`MaxWeight < 0`).
- Non-integer weights or non-object item elements.
- Custom exceptions, type coercions, parameter error messages, or specific return types beyond standard integer output.

**Guideline for Maintainers and Learners:**
Do **NOT** invent or impose additional exception rules, parameter assertions, type coercions, or ordering requirements that are not required by the canonical test suite. If an input is outside the positive-value domain, behavior is deliberately left unspecified by Exercism problem specifications.

---

## 4. Learner Hint

> When solving 0-1 Knapsack, begin by verifying base boundary conditions:
> - If there are no items, the maximum attainable value is always 0.
> - If an item's weight exceeds the available capacity, that item cannot be included in any feasible selection.
> Standard dynamic programming table entries for capacity less than an item's weight naturally carry forward the value without that item: `table[i, j] = table[i - 1, j]`.

---

## 5. Verification Results

- **Pester TotalCount:** `7`
- **Pester PassedCount:** `7`
- **Pester FailedCount:** `0`
- **Anchored Cases:**
  - `Knapsack test cases` (Describe block): **PASS**
  - `no items`: **PASS** (reproduced: `0`)
  - `one item, too heavy`: **PASS** (reproduced: `0`)

### Learner Stub Protection
- `exercises/practice/knapsack/Knapsack.ps1` remains untouched and contains the initial stub.
- All testing performed in isolated temporary directories.

*Note for Upstream Contribution: Remove `work/R09-T050/` before submitting to `exercism/powershell`.*
