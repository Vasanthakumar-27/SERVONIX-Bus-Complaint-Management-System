$files = @(
'ADMIN_HEAD_MESSAGING_SYSTEM.md',
'COMPLETION_SUMMARY.md',
'DEPLOYMENT.md',
'GITHUB_PAGES.md',
'MESSAGING_IMPLEMENTATION_COMPLETE.md',
'MESSAGING_QUICK_START.md',
'MESSAGING_VISUAL_DEMO_GUIDE.md',
'MIGRATION_GUIDE.md',
'PDF_GENERATION_SYSTEM.md',
'QUICK_START.md',
'REAME_MESSAGING.md',
'REAME_MESSAGING.md',
'REAME_MESSAGING.md',
'REAME_MESSAGING.md'
)
# NOTE: actual filenames must match. We'll attempt a smaller known list instead
$files = @('ADMIN_HEAD_MESSAGING_SYSTEM.md','COMPLETION_SUMMARY.md','DEPLOYMENT.md','GITHUB_PAGES.md','MESSAGING_IMPLEMENTATION_COMPLETE.md','MESSAGING_QUICK_START.md','MESSAGING_VISUAL_DEMO_GUIDE.md','MIGRATION_GUIDE.md','PDF_GENERATION_SYSTEM.md','QUICK_START.md','README_MESSAGING.md','REFACTORING_PROGRESS.md','SERVICE_LAYER.md','SETUP.md','TODOS_COMPLETE.md')
New-Item -ItemType Directory -Force -Path docs-md | Out-Null
foreach ($f in $files) {
    $out = Join-Path 'docs-md' $f
    git -C 'V:\Documents\VS CODE\DT project\SERVONIX' show 676b188:docs/$f 2>$null | Out-File -FilePath $out -Encoding utf8
    if (Test-Path $out) {
        $len = (Get-Item $out).Length
        if ($len -gt 0) { Write-Host "Restored: $f" } else { Remove-Item $out -ErrorAction SilentlyContinue; Write-Host "Missing in commit: $f" }
    } else {
        Write-Host "Failed to create: $f"
    }
}
