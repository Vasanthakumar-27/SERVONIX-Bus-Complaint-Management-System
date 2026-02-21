# Render Deployment Setup & Verification Script
# This script helps you configure and verify your Render deployment

param(
    [string]$RenderUrl = "https://servonix-bus-complaint-management-system.onrender.com",
    [string]$RenderApiKey = "",
    [string]$RenderServiceId = ""
)

Write-Host "=== SERVONIX Render Setup & Verification ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check if Render service is accessible
Write-Host "[1/5] Checking Render service health..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "$RenderUrl/api/health" -Method Get -TimeoutSec 10
    Write-Host "Service is UP: $($health | ConvertTo-Json -Compress)" -ForegroundColor Green
    $serviceUp = $true
} catch {
    Write-Host "Service is DOWN or unreachable" -ForegroundColor Red
    Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "  This usually means the service needs to be redeployed or there is a build error." -ForegroundColor Yellow
    $serviceUp = $false
}
Write-Host ""

# Step 2: Required Environment Variables Checklist
Write-Host "[2/5] Environment Variables Checklist" -ForegroundColor Yellow
Write-Host "Please ensure these are set in Render Dashboard (Environment tab):" -ForegroundColor White
Write-Host ""
Write-Host "Core:" -ForegroundColor Cyan
Write-Host "  SECRET_KEY          (long random string)" -ForegroundColor White
Write-Host "  FRONTEND_URL        (e.g., https://yourusername.github.io/SERVONIX)" -ForegroundColor White
Write-Host ""
Write-Host "Email/SMTP (for OTP delivery):" -ForegroundColor Cyan
Write-Host "  EMAIL_SENDER        (e.g., noreply@yourdomain.com)" -ForegroundColor White
Write-Host "  EMAIL_PASSWORD      (SMTP app password)" -ForegroundColor White
Write-Host "  SMTP_SERVER         (e.g., smtp.gmail.com)" -ForegroundColor White
Write-Host "  SMTP_PORT           (587)" -ForegroundColor White
Write-Host ""
Write-Host "Debug/Admin:" -ForegroundColor Cyan
Write-Host "  DEBUG_API_KEY       (long random for /debug/status)" -ForegroundColor White
Write-Host "  DEBUG               (optional, set to false in production)" -ForegroundColor White
Write-Host ""

# Step 3: Generate sample values
Write-Host "[3/5] Sample Values (copy these to Render)" -ForegroundColor Yellow
$secretKey = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_})
$debugKey = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 64 | ForEach-Object {[char]$_})
Write-Host "SECRET_KEY=$secretKey" -ForegroundColor Gray
Write-Host "DEBUG_API_KEY=$debugKey" -ForegroundColor Gray
Write-Host ""

# Step 4: SMTP Setup Guide
Write-Host "[4/5] SMTP Setup Instructions" -ForegroundColor Yellow
Write-Host ""
Write-Host "For Gmail:" -ForegroundColor Cyan
Write-Host "  1. Go to https://myaccount.google.com/apppasswords"
Write-Host "  2. Create a new app password (select Mail and Other)"
Write-Host "  3. Copy the 16-character password"
Write-Host "  4. Set in Render:"
Write-Host "     EMAIL_SENDER=your-email@gmail.com"
Write-Host "     EMAIL_PASSWORD=<16-char-app-password>"
Write-Host "     SMTP_SERVER=smtp.gmail.com"
Write-Host "     SMTP_PORT=587"
Write-Host ""

# Step 5: Test debug endpoint if service is up
if ($serviceUp) {
    Write-Host "[5/5] Testing Debug Endpoint" -ForegroundColor Yellow
    Write-Host "To test /debug/status, you need to provide DEBUG_API_KEY:" -ForegroundColor White
    
    if ($RenderApiKey -and $RenderServiceId) {
        Write-Host "Render API integration detected. You can use Render API to set env vars." -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "Manual test command (replace YOUR_DEBUG_KEY):" -ForegroundColor Cyan
        Write-Host 'curl -H "X-DEBUG-KEY: YOUR_DEBUG_KEY" ' -NoNewline -ForegroundColor Gray
        Write-Host "$RenderUrl/debug/status" -ForegroundColor Gray
    }
} else {
    Write-Host "[5/5] Service Not Available - Skipping Debug Test" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== Next Steps ===" -ForegroundColor Cyan
Write-Host "1. Add all environment variables in Render Dashboard"
Write-Host "2. Trigger Manual Deploy or use GitHub Action"
Write-Host "3. Wait 2-5 minutes for deployment to complete"
Write-Host "4. Re-run this script to verify"
Write-Host "5. Test OTP: Create account via frontend and check email delivery"
Write-Host ""
Write-Host "For automated Render API setup, provide -RenderApiKey and -RenderServiceId" -ForegroundColor Yellow
Write-Host ""
