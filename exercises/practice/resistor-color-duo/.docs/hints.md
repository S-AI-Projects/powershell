# Hints

## PowerShell: Explicit return values and scalar types

In PowerShell, functions emit values onto the output pipeline. The `return` keyword exits the function scope immediately and returns the value of the provided expression.

For `resistor-color-duo`, the test suite asserts that the returned value is an integer (`Int32`), not a string (`String`), using Pester's `Should -BeExactly` assertion. A common pitfall is constructing the two-digit number by string concatenation rather than arithmetic calculation.

### Expected integer calculation with explicit return

Computing the two-digit value using numeric arithmetic ($10 \times \text{first} + \text{second}$) produces a strongly-typed integer scalar:

```powershell
function Get-Code {
    param([int]$first, [int]$second)
    return $first * 10 + $second
}
$result = Get-Code -first 1 -second 0
$result.GetType().Name
$result
```

Output:

```text
Int32
10
```

### Pitfall: String concatenation produces a string scalar

Using string interpolation or string concatenation creates a `[string]` object. Although the characters look identical when printed, the type differs:

```powershell
function Get-CodePitfall {
    param([int]$first, [int]$second)
    return "$first$second"
}
$result = Get-CodePitfall -first 1 -second 0
$result.GetType().Name
$result
```

Output:

```text
String
10
```

Because `Should -BeExactly` requires both the value and the type to match, returning `"10"` (a string) causes tests expecting `10` (an integer) to fail.

See [about_Return](https://learn.microsoft.com/powershell/module/microsoft.powershell.core/about/about_return) for more details on function return semantics in PowerShell.
