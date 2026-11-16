# Swift-Scheduling Exercise Maintenance & Mutation Regression

## Overview

This document tracks regression analysis and mutation testing for `exercises/practice/swift-scheduling`.

## Target Component

- **Reference Function**: `function Now($Date)` located in `exercises/practice/swift-scheduling/.meta/SwiftScheduling.example.ps1` (Line 31).
- **Original Implementation**:
  ```powershell
  function Now($Date) {
      $Date.AddHours(2)
  }
  ```

## Introduced Mutant

- **Mutant Description**: Add a 1-hour offset instead of the specified 2-hour duration:
  ```powershell
  function Now($Date) {
      $Date.AddHours(1)
  }
  ```

## Rejecting Test Case

- **Test Name**: `NOW translates to two hours later`
- **Container**: `Describe "SwiftScheduling test cases"`
- **Test Input**:
  - `MeetingStart`: `[Datetime]::New(2012, 2, 13, 9, 0, 0)`
  - `Description`: `"NOW"`
- **Expected Outcome**: `[Datetime]::New(2012, 2, 13, 11, 0, 0)`
- **Mutant Outcome**: `[Datetime]::New(2012, 2, 13, 10, 0, 0)`
- **Failure Mode**: Pester assertion `$got | Should -BeExactly $want` fails with value mismatch.

## Validation Strategy

1. The unmodified reference passes 100% of test cases (10 total test cases).
2. The mutated reference fails specifically on `NOW translates to two hours later`.
3. The learner stub remains unsolved and fails the test suite.
