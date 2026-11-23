Function Invoke-Panagram() {
    <#
    .SYNOPSIS
    Determine if a sentence is a pangram using an alphabet query with early exit.
    
    .DESCRIPTION
    A pangram is a sentence using every letter of the alphabet at least once.
    This alternative queries each of the 26 letters of the Latin alphabet and
    returns $false immediately upon encountering the first missing letter.
    #>
    [CmdletBinding()]
    Param(
        [string]$Sentence
    )

    $lower = $Sentence.ToLower()
    foreach ($letter in [char]97..[char]122) {
        if (-not $lower.Contains($letter)) {
            return $false
        }
    }
    return $true
}
