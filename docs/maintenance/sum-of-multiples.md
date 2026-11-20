# Sum of Multiples mutation check

## Contract and existing regression

Each value below `Limit` that is divisible by at least one factor is included once in the sum. The factor matches form a union; a shared multiple is not a separate contribution for every factor that divides it.

The reference's inner loop stops after its first matching factor. The scratch mutant removes that `break`, so a value shared by multiple factors is added more than once. The existing canonical case catches it:

| Case | Input | Reference expected and actual | Mutant actual |
| --- | --- | --- | --- |
| `factors not relatively prime` (`2d0d5faa-f177-4ad6-bde9-ebb865083751`) | `Multiples = @(4, 6)`, `Limit = 15` | `30` | `42` |

The enabled Pester assertion is `Given the factors 4 6 and to a limit of 15 the sum of multiples should be 30`. This is the existing rejection; no new canonical test is needed.

## Reduced diagnostic input

The smallest distinct positive factors that can overlap are `1` and `2`. With a strict limit of `3`, the only values below the limit are `1` and `2`. The expected sum is `3`; the mutant returns `5` because it counts `2` twice. Factor `1` is already part of the exercise's tested contract.

## Reproducing the check

`work/R09-T033/check.py` reads the configured file paths, copies the exercise including dotfiles into isolated temporary directories, and puts the example implementation in both copies. It mutates only the temporary reference copy. It runs the complete Pester suite against the original and mutant with identical test files, then records both reduced probes. A successful checker run requires all original tests to pass and the named mutation assertion to fail with expected `30` and actual `42`.

```sh
python3 work/R09-T033/check.py
```

The recorded input, expected and actual values, Pester counts, PowerShell/Pester versions, and child output are saved under `work/R09-T033/`.
