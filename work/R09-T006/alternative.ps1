Function Get-Annotate() {
    [CmdletBinding()]
    Param(
        [ValidatePattern('^[\s*]*$')]
        [string[]]$Garden
    )
    if ($null -eq $Garden -or $Garden.Count -eq 0) { return $Garden }
    $rows = $Garden.Count
    $cols = $Garden[0].Length
    if ($cols -eq 0) { return $Garden }

    # Approach 2: Accumulator / Scatter Grid
    $counts = New-Object 'int[,]' $rows, $cols
    $deltas = @(
        @(-1, -1), @(-1, 0), @(-1, 1),
        @( 0, -1),           @( 0, 1),
        @( 1, -1), @( 1, 0), @( 1, 1)
    )

    for ($r = 0; $r -lt $rows; $r++) {
        for ($c = 0; $c -lt $cols; $c++) {
            if ($Garden[$r][$c] -eq '*') {
                foreach ($d in $deltas) {
                    $nr = $r + $d[0]
                    $nc = $c + $d[1]
                    if ($nr -ge 0 -and $nr -lt $rows -and $nc -ge 0 -and $nc -lt $cols) {
                        $counts[$nr, $nc]++
                    }
                }
            }
        }
    }

    $result = [string[]]::new($rows)
    for ($r = 0; $r -lt $rows; $r++) {
        $sb = [System.Text.StringBuilder]::new($cols)
        for ($c = 0; $c -lt $cols; $c++) {
            if ($Garden[$r][$c] -eq '*') {
                [void]$sb.Append('*')
            } elseif ($counts[$r, $c] -gt 0) {
                [void]$sb.Append($counts[$r, $c])
            } else {
                [void]$sb.Append(' ')
            }
        }
        $result[$r] = $sb.ToString()
    }
    return $result
}
