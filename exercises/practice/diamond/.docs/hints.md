# Hints

## PowerShell: one row, or many?

Building the rows one at a time and joining them with `-join` is a natural fit for this exercise. When a pipeline such as `ForEach-Object` produces output, PowerShell collects it for you: several results become an array, but a single result is **not** wrapped in an array. This matters because the `'A'` diamond has only one row.

### Several rows

```powershell
$rows = 'A', 'B' | ForEach-Object { "row $_" }
$rows.GetType().Name
$rows[0]
```

Output:

```text
Object[]
row A
```

### One row

```powershell
$rows = 'A' | ForEach-Object { "row $_" }
$rows.GetType().Name
$rows[0]
@($rows)[0]
```

Output:

```text
String
r
row A
```

With one result, `$rows` is a string, so `$rows[0]` is its first character, not the first row. The array sub-expression operator `@( )` always gives an array, even for zero or one item, so wrap the pipeline in it when you index or count rows.

Check the `'A'` diamond on its own, because it is the only one with a single row. See [about_Arrays](https://learn.microsoft.com/powershell/module/microsoft.powershell.core/about/about_arrays) for more.
