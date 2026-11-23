Function Invoke-MicroBlog() {
    <#
    .SYNOPSIS
    Implement a function to make micro blog post that only of 5 or less characters.

    .DESCRIPTION
    Given a string, truncate it into a string of maximum 5 characters.

    .PARAMETER Post
    A string object contains Unicode text encoding: alphabets, symbols or even emojis.

    .EXAMPLE
    Invoke-MicroBlog -Post "Lightning"
    Returns: "Light"
    #>
    [CmdletBinding()]
    Param(
        [string]$Post
    )
    # Parse the starting character offsets of each Unicode text element (grapheme cluster).
    # [System.Globalization.StringInfo]::ParseCombiningCharacters returns an int[] of string indices, not characters.
    $textElementOffsets = [System.Globalization.StringInfo]::ParseCombiningCharacters($Post)

    # Invariant: a micro-blog post is limited to at most 5 Unicode text elements (grapheme clusters).
    if ($textElementOffsets.Length -le 5) {
        return $Post
    }

    # Truncate at the start offset of the 6th text element
    $cutoffOffset = $textElementOffsets[5]
    return $Post.Substring(0, $cutoffOffset)
}
