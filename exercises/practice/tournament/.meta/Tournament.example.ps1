Function Invoke-Tournament {
    <#
    .SYNOPSIS
    Tally the results of a small football competition.

    .DESCRIPTION
    Given an array of string containing which team played against which and what the outcome was, create a tally table.

    .PARAMETER Results
    An array of the string, each line represent a match being played and its outcome.

    .EXAMPLE
    Invoke-Tournament -Results @("Annalyn;Elyses;win")
    
    return:
    @"
    Team                           | MP |  W |  D |  L |  P
    Annalyn                        |  1 |  1 |  0 |  0 |  3
    Elyses                         |  1 |  0 |  0 |  1 |  0
    "@
    #>
    [CmdletBinding()]
    Param(
        [string[]]$Results
    )

    $resultTable = @{}

    $Results | ForEach-Object {
        LineProcessing $resultTable $_
    }
    return DrawTable $resultTable
}

Function LineProcessing($Table, $Line) { 
    # Each team's tally is [MP, W, D, L, P], in the same order as the output columns.
    # Invariants: MP = W + D + L, and P = 3 * W + D.
    $played, $wins, $draws, $losses, $points = 0..4

    $winner, $loser, $result = $Line -split ';'

    if ($result -eq 'loss') {
        $winner, $loser = $loser, $winner
    }

    ($winner, $loser) | ForEach-Object {
        if (-not $Table.ContainsKey($_)) {
            $Table[$_] = @(0) * 5
        }
    }

    switch ($result) {
        'draw'  {
            $Table[$winner][$played]++
            $Table[$winner][$draws]++
            $Table[$winner][$points]++
            $Table[$loser][$played]++
            $Table[$loser][$draws]++
            $Table[$loser][$points]++
        }
        Default {
            $Table[$winner][$played]++
            $Table[$winner][$wins]++
            $Table[$winner][$points] += 3
            $Table[$loser][$played]++
            $Table[$loser][$losses]++
        }
    }
}

Function DrawTable($Table) {
    $formatFrame = "{0,-31}| {1,2} | {2,2} | {3,2} | {4,2} | {5,2}"
    $sortedTeamsArray = $Table.GetEnumerator() | Sort-Object -Property @{ Expression = { $_.Value[-1] }; Descending = $true }, Key
    
    $header = $formatFrame -f @("Team", "MP", "W", "D", "L", "P")
    $body = $sortedTeamsArray | ForEach-Object {
        $scores = @($_.Key) + $_.Value
        $formatFrame -f $scores
    }
    return @($header) + $body -join "`n"
}