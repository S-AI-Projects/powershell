# Hamming Exercise Maintenance & Mutation Analysis

## Overview
This document records a deliberate mutation of the `hamming` reference implementation, the specific test case that catches it, and the debugging guidance provided to learners.

## Reference Implementation vs. Mutant

### Original Reference Implementation (`exercises/practice/hamming/.meta/HammingDifference.example.ps1`)
```powershell
function Get-HammingDifference([string]$strand1, [string]$strand2) {
    if ( $strand1.length -ne $strand2.length) {
        Throw "strands must be of equal length."
    }
    $first = [char[]][string]$strand1
    $second = [char[]][string]$strand2
    $result = 0
    for ($i=0; $i -lt $first.length; $i++) {
        if ( $first[$i] -ne $second[$i] ) {
            $result += 1
        }
    }
    return $result
}
```

### Deliberate Mutant
A common mistaken assumption is inverting the mismatch test, inadvertently counting character matches (`-eq`) instead of mismatches (`-ne`):
```powershell
function Get-HammingDifference([string]$strand1, [string]$strand2) {
    if ( $strand1.length -ne $strand2.length) {
        Throw "strands must be of equal length."
    }
    $first = [char[]][string]$strand1
    $second = [char[]][string]$strand2
    $result = 0
    for ($i=0; $i -lt $first.length; $i++) {
        if ( $first[$i] -eq $second[$i] ) {   # MUTATION: -ne changed to -eq
            $result += 1
        }
    }
    return $result
}
```

## Rejecting Test Case Details

- **Test Suite**: `HammingDifference.tests.ps1`
- **Describe Block**: `Get-Hamming Test cases`
- **Context**: `Passing Tests`
- **Test Name**: `single letter identical strands`
- **Canonical UUID**: `d419a696-a818-4221-827c-674457e3f890`
- **Minimal Input**: `strand1 = 'A'`, `strand2 = 'A'`
- **Expected Outcome**: `0`
- **Mutant Actual Outcome**: `1`
- **Failure Message**: `Expected 0, but got 1.`

## Automated Check
Run the automated check:
```bash
python3 work/R09-T003/check.py
```
This check runs both the genuine reference implementation (which passes all 9 test cases) and the mutated implementation in isolated temporary copies, verifying that:
1. All 9 test cases pass against the reference.
2. The mutant fails specifically on `single letter identical strands`.
3. The learner starter file `HammingDifference.ps1` remains untouched.
