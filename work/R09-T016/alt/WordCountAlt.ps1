Function Get-WordCount() {
    [CmdletBinding()]
    Param(
        [string]$Phrase
    )
    $isLetter = { param([int]$c) ($c -ge 65 -and $c -le 90) -or ($c -ge 97 -and $c -le 122) }
    $isDigit = { param([int]$c) $c -ge 48 -and $c -le 57 }
    $words = [System.Collections.Generic.List[string]]::new()
    $n = $Phrase.Length
    $i = 0
    while ($i -lt $n) {
        $start = $i
        if (& $isLetter ([int]$Phrase[$i])) {
            while ($i -lt $n -and (& $isLetter ([int]$Phrase[$i]))) { $i++ }
            if ($i + 1 -lt $n -and $Phrase[$i] -eq "'" -and (& $isLetter ([int]$Phrase[$i + 1]))) {
                $i++
                while ($i -lt $n -and (& $isLetter ([int]$Phrase[$i]))) { $i++ }
            }
        }
        elseif (& $isDigit ([int]$Phrase[$i])) {
            while ($i -lt $n -and (& $isDigit ([int]$Phrase[$i]))) { $i++ }
        }
        else { $i++; continue }
        $words.Add($Phrase.Substring($start, $i - $start).ToLower())
    }
    $result = @{}
    foreach ($g in ($words | Group-Object)) { $result[$g.Name] = $g.Count }
    return $result
}
