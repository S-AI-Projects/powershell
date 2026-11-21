# R09-T047 · nth-prime — Maintenance Notes

## Language Construct in `NthPrime.example.ps1`

The reference implementation uses **three interacting constructs**:

### 1. Array accumulation with `+=`

```powershell
$primes = @()
# ...
$primes += $i   # appends $i to the array and reassigns $primes
```

In PowerShell, `+=` on an array creates a **new array** each time (copying
all existing elements plus the new one). For small primes this is fine; for
very large N (e.g., `big prime` test: n=10001) the quadratic copy cost is
noticeable but tolerable.

### 2. Negative indexing with `$arr[-1]`

```powershell
return $primes[-1]
```

PowerShell supports negative indices: `-1` is the last element, `-2` is
second-to-last, etc. This is the natural way to retrieve the most recently
accumulated prime without tracking an extra variable.

### 3. Explicit `return` with a scalar result

The function ends with `return $primes[-1]`. The `return` keyword:
- Immediately exits the function.
- Emits **exactly one value** to the pipeline (the scalar integer `$primes[-1]`).
- Prevents any earlier pipeline output from being accidentally included
  in the return value (see pitfall below).

---

## Standalone Micro-Example (does NOT solve nth-prime)

```powershell
function Get-LastEven {
    param([int]$Count)
    $evens = @()
    $n = 2
    while ($evens.Count -lt $Count) {
        $evens += $n
        $n += 2
    }
    return $evens[-1]   # returns 6 when Count=3  (evens: 2, 4, 6)
}

$result = Get-LastEven -Count 3
Write-Output "MICRO:$result"   # → MICRO:6
```

**Key behaviour:** The caller receives the integer `6`, not the full array
`@(2, 4, 6)`. The `return` keyword + `-1` index together select a single
scalar from the accumulated collection.

---

## Contrasting Pitfall — Pipeline Pollution

```powershell
function Get-LastEvenPolluted {
    param([int]$Count)
    $evens = @()
    $n = 2
    while ($evens.Count -lt $Count) {
        $evens += $n
        $n += 2
    }
    Write-Output "debug: computing..."   # <─── pipeline pollution!
    return $evens[-1]
}

$result = Get-LastEvenPolluted -Count 3
# $result is @("debug: computing...", 6) — an ARRAY, not a scalar!
```

**Why outcomes differ:**

| Construct | Pipeline output | `$result` type |
|-----------|----------------|----------------|
| `return $evens[-1]` only | single integer | scalar `[int]` |
| `Write-Output "debug..."` **then** `return $evens[-1]` | two items | `[array]` with 2 elements |

PowerShell functions collect *all* values emitted to the pipeline into the
caller's result. Any `Write-Output`, `Write-Host` to pipeline, or bare
expression that isn't captured will appear in the return value. This is
why the reference uses `return $primes[-1]` with no intermediate pipeline
writes — it guarantees the caller always gets a scalar integer.

---

## Connection to `nth-prime` Specification

The test cases check for **exact integer equality**:

```powershell
$got = Get-NthPrime -Number 1
$want = 2
$got | Should -Be $want      # would fail if $got is @(..., 2)
```

`Should -Be` on an array vs a scalar would fail or behave unexpectedly.
So `return $primes[-1]` is not just a style choice — it's what makes
`$got | Should -Be $want` reliable.

---

## Learner Hint

> When your function accumulates results into `$arr` and needs to return
> only the **last** one, use `return $arr[-1]`. Avoid any `Write-Output`
> or bare expressions inside the function body before that `return`, or
> PowerShell will bundle all pipeline emissions into an array and your
> caller will get a collection instead of a scalar.

---

## Anchored Cases Verified

| Case | Reference |
|------|-----------|
| `NthPrime Tests` (Describe block) | PASS (FailedCount=0) |
| `first prime`  | PASS |
| `second prime` | PASS |

---

## Note for Upstream Contribution

Remove `work/R09-T047/` before any branch targeting upstream `exercism/powershell`.
The learner stub `NthPrime.ps1` was **never modified** in the working tree.
All substitution occurred inside Python `tempfile.mkdtemp()` directories.
