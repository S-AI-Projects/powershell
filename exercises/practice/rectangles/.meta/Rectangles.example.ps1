Function Get-Rectangles() {
    <#
    .SYNOPSIS
    Count the rectangles in an ASCII diagram.

    .DESCRIPTION
    Given an ASCII diagram, count all the rectangles exist in it.
    A complete rectangle should have 4 corners and 4 valid sides.
    Example of possilbe sides:
    Valid: "+--+", "++"
    Invalid: "+--  +", "-+"

    .PARAMETER Strings
    An array of string that represent an ASCII diagram.
    You may assume that the input is always a proper rectangle (every string in the array has equal length).
    
    .EXAMPLE
    $diagram = @(
        "+-+-+",
        "+-+-+"
    )

    Get-Rectangles -Strings $diagram
    Returns: 3
    #>
    [CmdletBinding()]
    Param(
        [string[]]$Strings
    )
    # Complexity:
    # Time: O(R * C * (R + C) + E_H^2) where R is row count, C is column width,
    # and E_H <= R * C^2 / 2 is the total number of detected horizontal edges.
    # Edge extraction checks horizontal and vertical line segments from each '+' vertex.
    # Rectangle counting iterates over pairs of horizontal edges with O(1) hash lookups
    # for the matching left and right vertical edges.
    # Space: O(E_H + E_V) auxiliary memory for edge collections.
    if ($Strings.Count -eq 0) {return 0}
    $validEdges = ExtractEdge $Strings
    CountRectangle @validEdges
}

Function CountRectangle() {
    <#
    .DESCRIPTION
    From the extracted edges, do some logic to check if the 4 edges can create a rectangle.
    #>
    param (
        [object[]]  $HorizontalEdges,
        [hashtable] $VerticalEdges
    )
    $hozEdgesCount = $HorizontalEdges.Count
    $count = 0
    for ($i = 0; $i -lt $hozEdgesCount; $i++) {
        for ($j = $i+1; $j -lt $hozEdgesCount; $j++) {
            $topEdge = $HorizontalEdges[$i]
            $botEdge = $HorizontalEdges[$j]
            if ($topEdge[1] -eq $botEdge[1] -and $topEdge[-1] -eq $botEdge[-1]) {
                $leftEdge = "$($topEdge[0])$($topEdge[1])$($botEdge[0])$($botEdge[1])"
                $rightEdge = "$($topEdge[2])$($topEdge[3])$($botEdge[2])$($botEdge[3])"
                if ($VerticalEdges.ContainsKey($leftEdge) -and $VerticalEdges.ContainsKey($rightEdge)) {
                    $count++
                }
            }
        }
    }
    $count
}

Function ExtractEdge([string[]]$strings) {
    <#
    .DESCRIPTION
    From the array of strings, extract all the valid edge (side) and store them into two groups : horizontal and vertical.
    #>
    $validEdges = @{
        HorizontalEdges = @()
        VerticalEdges   = [ordered]@{}
    }
    for ($l = 0; $l -lt $strings.Count; $l++) {
        $line = $strings[$l]
        for ($i = 0; $i -lt $line.Length; $i++) {
            if ($line[$i] -eq "+") {
                #horizontal
                for ($j = $i+1; $j -lt $line.Length; $j++) {
                    $hozEdge = $line.Substring($i, $j-$i+1)
                    if($hozEdge -match '^\+(-|\+)*\+$') {
                        $validEdges.HorizontalEdges += ,@($l,$i,$l,$j)
                    }
                }
                #vertical
                $vertEdge = "$($line[$i])"
                for ($l2 = $l+1; $l2 -lt $strings.Count; $l2++) {
                    $vertEdge += $strings[$l2][$i]
                    if($vertEdge -match '^\+(\||\+)*\+$') {
                        $validEdges.VerticalEdges["$l$i$l2$i"] = $true
                    }
                }
            }
        }
    }
    $validEdges
}