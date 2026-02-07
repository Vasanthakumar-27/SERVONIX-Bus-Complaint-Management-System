<#
Creates timestamped backups of tracked files into the .backups folder.
Usage: .\create_snapshot.ps1
#>
param(
    [string[]] $Files = @(
        "frontend/html/user_dashboard.html",
        "frontend/css/user_dashboard.css",
        "frontend/html/admin_dashboard.html",
        "frontend/css/admin_dashboard.css"
    )
)

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
$backupDir = Join-Path $scriptRoot "..\.backups" | Resolve-Path -ErrorAction SilentlyContinue
if (-not $backupDir) {
    $backupDir = Join-Path $scriptRoot "..\.backups"
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
}

$ts = (Get-Date).ToString("yyyy-MM-ddTHH-mm-ss")
Write-Host "Creating snapshot at $ts"
foreach ($f in $Files) {
    if (Test-Path $f) {
        $original = Get-Content $f -Raw
        $basename = [IO.Path]::GetFileName($f)
        $outPath = Join-Path $backupDir "$basename.backup.$ts"
        $header = "# ORIGINAL_PATH: $f`n# BACKUP_CREATED: $(Get-Date -Format o)`n"
        $header + $original | Out-File -FilePath $outPath -Encoding UTF8
        Write-Host "Saved backup: $outPath"
    } else {
        Write-Host "Skipped missing: $f"
    }
}

Write-Host "Snapshot complete."
