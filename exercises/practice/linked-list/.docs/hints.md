# Hints

## Returning a removed value in PowerShell

The reference's `Pop()` and `Shift()` methods use `return $data` to send the removed station value to the caller. For a numeric station ID, the result is one scalar:

```powershell
$route = [LinkedList]::new()
$route.Push(7)
$station = $route.Pop()
"{0}|{1}|{2}" -f $station, $station.GetType().Name, @($station).Count
```

Expected output:

```text
7|Int32|1
```

The exercise uses numbers as station IDs. If you accidentally store an array as one node's value, the method can return that array object, but sending it into a pipeline enumerates its elements:

```powershell
$route.Push([object[]]@(7, 8)) # Outside the number-valued station contract
$removed = $route.Pop()
$removed | ForEach-Object { $_ }
```

That pipeline emits `7` and `8` as two records. Keep one station ID as one scalar value; use array capture only when you intentionally want a collection. See Microsoft's [about_Return](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_Return), [about_Pipelines](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_Pipelines), and [about_Classes_Methods](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_Classes_Methods) references for how explicit class-method returns and pipeline collection enumeration work.
