# Hints

## PowerShell Array Handling & Pipeline Enumeration

When working with coordinates or collections of points in PowerShell (such as `[SaddlePoint]` instances), PowerShell's pipeline behavior introduces a subtle pitfall regarding array returns.

### The Pitfall: Automatic Pipeline Unrolling

By default, PowerShell functions send items across the pipeline one by one. When a function returns an array with a single item, PowerShell unrolls the collection into a scalar object:

```powershell
Class SaddlePoint {
    [int]$Row
    [int]$Column
    SaddlePoint($r, $c) { $this.Row = $r; $this.Column = $c }
}

function Get-SinglePoint {
    $points = @([SaddlePoint]::new(1, 2))
    $points
}

$res = Get-SinglePoint
$res.GetType().Name
# Output: "SaddlePoint" (scalar object, not an array!)
```

If downstream code calls `.Count` or expects an indexable array `[0]`, unexpected behavior can occur when only one saddle point exists.

### The Solution: Array Subexpression `@(...)`

To ensure that results are always treated as an array regardless of whether zero, one, or multiple saddle points are detected, wrap invocations in the array subexpression operator `@(...)`:

```powershell
$res = @(Get-SinglePoint)
$res.GetType().Name
# Output: "Object[]"
$res.Count
# Output: 1
```

For empty results:

```powershell
function Get-NoPoints {
    $points = @()
    $points
}

$res = @(Get-NoPoints)
$res.Count
# Output: 0
```

### Reference Implementation Pattern

In `SaddlePoints.example.ps1`, the helper function returns multiple collections using the comma operator `,`:
```powershell
$maxValues, $minValues = Get-MaxMinValues $Matrix $rows $columns
```
The comma `,` binary operator constructs an array of arrays and prevents PowerShell from flattening the two arrays during assignment.

For more details, see the official PowerShell documentation:
- [about_Arrays](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_arrays)
- [about_Operators - Comma operator](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_operators#comma-operator-)
