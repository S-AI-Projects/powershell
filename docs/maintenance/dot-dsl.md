# Dot DSL reference cost

## Input size and method

For this exercise, input size is the number of graph records passed to `Graph([object[]] $Data)`. The reference accepts variable-length node, edge, and attribute lists, so this check measures three valid graph sizes rather than treating the exercise as fixed-size.

The checker constructs graphs containing only distinct `Node` records at sizes 10, 50, and 100. It builds the node arrays before timing, loads the PowerShell classes once, performs an untimed warm-up, and then times graph construction five times per size. The reported time is the median of those five runs. Process startup, class loading, and input creation are outside the measured interval.

## Algorithm work

`Graph([object[]] $Data)` visits each record once. For each node it appends to a PowerShell array with `+=`; this preserves insertion order, but creates a new array and copies the existing node slots. For `n` nodes, the loop visits `n` records and performs `n` appends, while the append operations copy `n(n-1)/2` existing slots in total. The array-building cost for this homogeneous input is therefore quadratic in `n`, in addition to the linear record dispatch.

| Node records (`n`) | Expected/actual nodes | Edge and attribute count | Record visits | Node appends | Existing node slots copied |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 10 | 10 / 10 | 0 / 0 | 10 | 10 | 45 |
| 50 | 50 / 50 | 0 / 0 | 50 | 50 | 1,225 |
| 100 | 100 / 100 | 0 / 0 | 100 | 100 | 4,950 |

## Measurements

| Node records | Median constructor time (ms) |
| ---: | ---: |
| 10 | 0.1572 |
| 50 | 0.6477 |
| 100 | 1.8050 |

These five-run medians were measured with PowerShell 7.7.0; all five samples per size are in `work/R09-T035/results.json`. They describe this environment and workload only. The operation count explains the scaling implied by the current implementation; the small sample does not establish performance for all PowerShell versions or workloads.

The same checker runs the configured Pester suite first. It fails on a zero-test run, failed assertions, or a non-zero child process, and records the PowerShell and Pester versions along with benchmark inputs and construction counts.

```sh
python3 work/R09-T035/check.py
```
