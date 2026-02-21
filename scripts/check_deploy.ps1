Param(
    [string]$Url = 'https://servonix-bus-complaint-management-system.onrender.com'
)

Write-Host "Checking health endpoint for $Url"
try {
    $h = Invoke-RestMethod -Uri "$Url/api/health" -UseBasicParsing -TimeoutSec 10
    Write-Host "Health:" ($h | ConvertTo-Json -Compress)
    exit 0
} catch {
    Write-Host "Health check failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 2
}
