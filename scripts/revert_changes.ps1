<#
Restores the most recent backup for each tracked file that was created within the last N hours (default 12).
Usage: .\revert_changes.ps1 -Hours 12
#>
param(
    [int]$Hours = 12
)

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
$backupDir = Join-Path $scriptRoot "..\.backups"
if (-not (Test-Path $backupDir)) {
    Write-Error "No backups folder found at $backupDir"
    exit 1
}

$cutoff = (Get-Date).AddHours(-$Hours)
$backups = Get-ChildItem -Path $backupDir -File | Where-Object { $_.LastWriteTime -ge $cutoff } | Sort-Object LastWriteTime -Descending
if ($backups.Count -eq 0) {
    Write-Host "No backups within last $Hours hours."
    exit 0
}

# Build restore map: original_path -> latest backup file within cutoff
$restoreMap = @{}
foreach ($b in $backups) {
    $firstLines = Get-Content $b.FullName -TotalCount 10
    $origLine = $firstLines | Where-Object { $_ -match '^# ORIGINAL_PATH:' } | Select-Object -First 1
    if ($origLine) {
        $orig = $origLine -replace '^# ORIGINAL_PATH:\s*',''
        if (-not $restoreMap.ContainsKey($orig)) {
            $restoreMap[$orig] = $b
        }
    }
}

if ($restoreMap.Keys.Count -eq 0) {
    Write-Host "No recognizable backup headers found in recent backups."
    exit 0
}

Write-Host "The following files will be restored to their latest backup within last $Hours hours:"
foreach ($k in $restoreMap.Keys) { Write-Host "  $k  <-  $($restoreMap[$k].Name)" }

$consent = Read-Host "Type YES to confirm restore"
if ($consent -ne 'YES') { Write-Host "Aborted"; exit 0 }

foreach ($kv in $restoreMap.GetEnumerator()) {
    $target = $kv.Key
    $backupFile = $kv.Value.FullName
    $content = Get-Content $backupFile -Raw
    # remove header lines starting with '# ORIGINAL_PATH' and '# BACKUP_CREATED'
    $lines = $content -split "`n"
    $bodyLines = $lines | Where-Object { $_ -notmatch '^# ORIGINAL_PATH:' -and $_ -notmatch '^# BACKUP_CREATED:' }
    $body = $bodyLines -join "`n"
    $targetDir = Split-Path $target -Parent
    if (-not (Test-Path $targetDir)) { New-Item -ItemType Directory -Path $targetDir -Force | Out-Null }
    $body | Out-File -FilePath $target -Encoding UTF8 -Force
    Write-Host "Restored $target from $backupFile"
}

Write-Host "Restore complete."
