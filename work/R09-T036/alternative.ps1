function Get-HelloWorld {
    $builder = [System.Text.StringBuilder]::new()
    [void]$builder.Append("Hello, ")
    [void]$builder.Append("World!")
    $builder.ToString()
}
