# Hints

## PowerShell-Specific Guidance: Iterative Divisor Accumulation

When calculating the aliquot sum (the sum of proper positive divisors less than $N$), pay careful attention to boundary conditions and PowerShell language constructs.

### The Range Operator Pitfall (`..`)
A common pitfall is using PowerShell's range operator `1..($Number - 1)`. In PowerShell, the range operator evaluates directionally:
- When `$Number = 6`, `1..5` yields `@(1, 2, 3, 4, 5)`.
- However, when `$Number = 1` (the edge case), `1..($Number - 1)` evaluates to `1..0`. Instead of returning an empty collection, PowerShell creates a descending array: `@(1, 0)`.
- If you pipe this into a modulo check (`$Number % $_`), evaluating `$Number % 0` results in a fatal `DivideByZeroException` (or incorrect factor counting).

#### Executable Micro-Example 1 (Pitfall Demonstration)
```powershell
$n = 1
$range = 1..($n - 1)
$range -join ","
```
**Expected Output:**
```text
1,0
```

### The Reference Approach: `for` Loop with Strict Guard
The reference solution (`exercises/practice/perfect-numbers/.meta/PerfectNumbers.example.ps1`) uses a traditional `for` loop with a strict condition `$i -lt $Number`:
- When `$Number = 1`, the condition `$i -lt 1` evaluates to `$false` immediately before the loop executes.
- The loop body is never entered, leaving `$sum = 0`, which correctly classifies `1` as `"deficient"`.

#### Executable Micro-Example 2 (Safe Accumulation)
```powershell
$n = 1
$sum = 0
for ($i = 1; $i -lt $n; $i++) {
    if ($n % $i -eq 0) { $sum += $i }
}
$sum
```
**Expected Output:**
```text
0
```

### Reference Documentation
- [Microsoft Learn: about_For](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_for)
- [Microsoft Learn: about_Operators (Range Operator)](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_operators#range-operator-)
