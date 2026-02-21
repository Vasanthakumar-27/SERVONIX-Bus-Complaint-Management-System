param(
    [string]$BaseUrl = 'https://servonix-bus-complaint-management-system.onrender.com'
)

$ts = Get-Date -Format 'yyyyMMddHHmmss'
$email = "servonix_test_${ts}@mailnull.com"
$pass  = 'TestPass123!'

Write-Host "`n=== SERVONIX DEPLOYMENT VERIFICATION ===" -ForegroundColor Cyan
Write-Host "Base URL : $BaseUrl"
Write-Host "Test user: $email`n"

# ---- 1. Health ----
Write-Host "[1/5] Health check..." -ForegroundColor Yellow
try {
    $h = Invoke-RestMethod -Uri "$BaseUrl/api/health" -Method Get -TimeoutSec 10
    Write-Host "  PASS  status=$($h.status) service=$($h.service)" -ForegroundColor Green
} catch {
    Write-Host "  FAIL  $_" -ForegroundColor Red; exit 1
}

# ---- 2. register-request ----
Write-Host "[2/5] register-request..." -ForegroundColor Yellow
$b = @{name='Deploy Tester'; email=$email; password=$pass} | ConvertTo-Json -Compress
try {
    $r = Invoke-RestMethod -Uri "$BaseUrl/api/register-request" -Method Post -Body $b -ContentType 'application/json' -TimeoutSec 30
    Write-Host "  PASS  message=$($r.message)" -ForegroundColor Green
    if ($r.dev_otp) { $otp = $r.dev_otp; Write-Host "  DEV_OTP=$otp" -ForegroundColor Magenta }
    else { Write-Host "  NOTE: production mode - OTP sent to email (not shown here)" -ForegroundColor Yellow }
} catch {
    $sc = $_.Exception.Response.StatusCode.value__
    Write-Host "  FAIL  HTTP $sc  $_" -ForegroundColor Red; exit 2
}

# ---- 3. register-verify (only if we got a dev OTP) ----
if ($otp) {
    Write-Host "[3/5] register-verify with OTP=$otp ..." -ForegroundColor Yellow
    $bv = @{email=$email; otp=$otp} | ConvertTo-Json -Compress
    try {
        $rv = Invoke-RestMethod -Uri "$BaseUrl/api/register-verify" -Method Post -Body $bv -ContentType 'application/json' -TimeoutSec 30
        Write-Host "  PASS  message=$($rv.message)  userId=$($rv.user.id)" -ForegroundColor Green
    } catch {
        $sc = $_.Exception.Response.StatusCode.value__
        Write-Host "  FAIL  HTTP $sc  $_" -ForegroundColor Red; exit 3
    }

    # ---- 4. login ----
    Write-Host "[4/5] login..." -ForegroundColor Yellow
    $bl = @{email=$email; password=$pass} | ConvertTo-Json -Compress
    try {
        $rl = Invoke-RestMethod -Uri "$BaseUrl/api/login" -Method Post -Body $bl -ContentType 'application/json' -TimeoutSec 30
        $token = $rl.token
        Write-Host "  PASS  role=$($rl.role)  token=${token:0:20}..." -ForegroundColor Green
    } catch {
        $sc = $_.Exception.Response.StatusCode.value__
        Write-Host "  FAIL  HTTP $sc  $_" -ForegroundColor Red; exit 4
    }

    # ---- 5. profile (authenticated) ----
    if ($token) {
        Write-Host "[5/5] profile (authenticated)..." -ForegroundColor Yellow
        $hdrs = @{ Authorization = "Bearer $token" }
        try {
            $rp = Invoke-RestMethod -Uri "$BaseUrl/api/profile" -Method Get -Headers $hdrs -TimeoutSec 10
            Write-Host "  PASS  name=$($rp.name)  email=$($rp.email)  role=$($rp.role)" -ForegroundColor Green
        } catch {
            Write-Host "  FAIL  $_" -ForegroundColor Red; exit 5
        }
    }
} else {
    Write-Host "[3/5] register-verify  SKIPPED (no dev_otp - production mode)" -ForegroundColor Yellow
    Write-Host "[4/5] login            SKIPPED" -ForegroundColor Yellow
    Write-Host "[5/5] profile          SKIPPED" -ForegroundColor Yellow
}

Write-Host "`n=== VERIFICATION COMPLETE ===" -ForegroundColor Cyan
