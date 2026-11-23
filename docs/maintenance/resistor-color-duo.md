# Maintenance Notes: resistor-color-duo

## Exercise metadata

- Track: PowerShell
- Slug: `resistor-color-duo`
- Exercise directory: `exercises/practice/resistor-color-duo/`
- Reference implementation: `exercises/practice/resistor-color-duo/.meta/ResistorColorDuo.example.ps1`

## Language Guidance (R09-T057)

### Language construct in reference

The reference implementation uses an **explicit return statement** with integer arithmetic:
```powershell
return $firstColor * 10 + $secondColor
```

### Purpose of guidance

PowerShell provides multiple ways to return values from functions, including implicit pipeline output and explicit `return`. A frequent point of confusion for learners in `resistor-color-duo` is the distinction between integer scalars (`[int]`) and string representations (`[string]`):

1. **Arithmetic computation (`return $first * 10 + $second`)**: produces an `Int32` scalar matching the Pester expectation `Should -BeExactly $want` where `$want` is an integer.
2. **String formatting (`return "$first$second"`)**: produces a `String` scalar. Even though `"10"` prints identically to `10` in interactive sessions, Pester's `Should -BeExactly` strictly validates runtime types, rejecting `"10"` when `10` is expected.

### Verification of micro-examples

The two micro-examples in `.docs/hints.md` were executed and verified:
1. `Get-Code`: outputs `Int32` and `10`.
2. `Get-CodePitfall`: outputs `String` and `10`.

Both micro-examples are tested by `work/R09-T057/check.py` to ensure that published examples remain executable and accurate.

### Test suite status

All 7 test cases in `ResistorColorDuo.tests.ps1` pass against the reference implementation, including:
- `Brown and blac` (expected 10)
- `Blue and grey` (expected 68)
- `Yellow and violet` (expected 47)
- `White and red` (expected 92)
- `Orange and orange` (expected 33)
- `Ignore extra colors` (expected 51)
- `Black and brown, one-digit` (expected 1)
