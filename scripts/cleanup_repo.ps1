Write-Host "Repository cleanup helper"

# List files larger than 5MB to review for removal
Write-Host "Scanning for files > 5MB (recommend review)"
Get-ChildItem -Recurse -File | Where-Object { $_.Length -gt 5MB } | Sort-Object Length -Descending | Format-Table FullName, @{Name='MB';Expression={ [math]::Round($_.Length/1MB,2) }} -AutoSize

Write-Host "\nSuggested .gitignore entries (not applied):"
@(
    "# Large binary assets",
    "*.mp4",
    "*.mov",
    "*.zip",
    "*.tar",
    "*.tar.gz"
) | ForEach-Object { Write-Host $_ }

Write-Host "\nTo remove a file from git history, use the BFG or git filter-repo outside this script."
