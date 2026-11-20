# Hints

## Debugging overlapping multiples

A number that is divisible by more than one factor still contributes only once. For a small check, use factors `1` and `2` with a limit of `3`: the matching values below the limit are `1` and `2`, so the sum is `3`. A result of `5` means `2` was counted once for each factor. The existing “factors not relatively prime” case checks the same contract with a larger overlap.
