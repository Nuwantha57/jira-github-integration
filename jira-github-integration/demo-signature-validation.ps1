# DEMO: Webhook Signature Validation
# Shows valid vs invalid signatures in a clear, visual way

param(
    [Parameter(Mandatory=$false)]
    [string]$WebhookUrl = "",
    [Parameter(Mandatory=$false)]
    [string]$Secret = "demo_secret_12345"
)

$payload = @{
    issue = @{
        key = "DEMO-001"
        fields = @{
            summary = "Demo Issue"
            description = "Demonstrating signature validation"
            labels = @("sync-to-github")
        }
    }
} | ConvertTo-Json -Depth 10

Write-Host "`n" 
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     WEBHOOK SIGNATURE VALIDATION DEMO                      ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

Write-Host "`nPayload to send:" -ForegroundColor White
Write-Host $payload.Substring(0, [Math]::Min(100, $payload.Length)) -ForegroundColor Gray
Write-Host "..." -ForegroundColor Gray

Write-Host "`nSecret Key: " -NoNewline -ForegroundColor White
Write-Host $Secret -ForegroundColor Yellow

# Generate valid signature
$hmac = New-Object System.Security.Cryptography.HMACSHA256
$hmac.Key = [Text.Encoding]::UTF8.GetBytes($Secret)
$hash = $hmac.ComputeHash([Text.Encoding]::UTF8.GetBytes($payload))
$validSignature = "sha256=" + [BitConverter]::ToString($hash).Replace("-", "").ToLower()

Write-Host "`n" 
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor White

# DEMO 1: Valid Signature
Write-Host "`n📝 SCENARIO 1: Valid Signature" -ForegroundColor Green
Write-Host "─────────────────────────────────────────────────────────" -ForegroundColor Gray
Write-Host "Signature: " -NoNewline -ForegroundColor White
Write-Host $validSignature.Substring(0, 40) -NoNewline -ForegroundColor Green
Write-Host "..." -ForegroundColor Green
Write-Host "Expected: ✅ Request ACCEPTED (200 OK)" -ForegroundColor Green

if ($WebhookUrl) {
    try {
        $headers = @{ "X-Hub-Signature" = $validSignature }
        $response = Invoke-WebRequest -Uri $WebhookUrl -Method POST -Headers $headers -Body $payload -ContentType "application/json" -ErrorAction Stop
        Write-Host "Result: ✅ " -NoNewline -ForegroundColor Green
        Write-Host "Status $($response.StatusCode) - Request Accepted!" -ForegroundColor Green
    } catch {
        Write-Host "Result: ❌ Status $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
    }
} else {
    Write-Host "Result: " -NoNewline -ForegroundColor White
    Write-Host "[SIMULATION] ✅ Request would be ACCEPTED" -ForegroundColor Green
}

# DEMO 2: Invalid Signature
Write-Host "`n" 
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor White
Write-Host "`n📝 SCENARIO 2: Invalid Signature" -ForegroundColor Red
Write-Host "─────────────────────────────────────────────────────────" -ForegroundColor Gray
$invalidSignature = "sha256=WRONG_SIGNATURE_MALICIOUS_ATTEMPT_12345abcdef"
Write-Host "Signature: " -NoNewline -ForegroundColor White
Write-Host $invalidSignature.Substring(0, 40) -NoNewline -ForegroundColor Red
Write-Host "..." -ForegroundColor Red
Write-Host "Expected: ❌ Request REJECTED (401 Unauthorized)" -ForegroundColor Red

if ($WebhookUrl) {
    try {
        $headers = @{ "X-Hub-Signature" = $invalidSignature }
        $response = Invoke-WebRequest -Uri $WebhookUrl -Method POST -Headers $headers -Body $payload -ContentType "application/json" -ErrorAction Stop
        Write-Host "Result: ⚠️ " -NoNewline -ForegroundColor Yellow
        Write-Host "Status $($response.StatusCode) - Should have been rejected!" -ForegroundColor Yellow
    } catch {
        Write-Host "Result: ✅ " -NoNewline -ForegroundColor Green
        Write-Host "Status $($_.Exception.Response.StatusCode.value__) - Correctly Rejected!" -ForegroundColor Green
    }
} else {
    Write-Host "Result: " -NoNewline -ForegroundColor White
    Write-Host "[SIMULATION] ❌ Request would be REJECTED" -ForegroundColor Red
}

# DEMO 3: Missing Signature
Write-Host "`n" 
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor White
Write-Host "`n📝 SCENARIO 3: No Signature Header" -ForegroundColor Red
Write-Host "─────────────────────────────────────────────────────────" -ForegroundColor Gray
Write-Host "Signature: " -NoNewline -ForegroundColor White
Write-Host "(missing)" -ForegroundColor Red
Write-Host "Expected: ❌ Request REJECTED (401 Unauthorized)" -ForegroundColor Red

if ($WebhookUrl) {
    try {
        $response = Invoke-WebRequest -Uri $WebhookUrl -Method POST -Body $payload -ContentType "application/json" -ErrorAction Stop
        Write-Host "Result: ⚠️ " -NoNewline -ForegroundColor Yellow
        Write-Host "Status $($response.StatusCode) - Should have been rejected!" -ForegroundColor Yellow
    } catch {
        Write-Host "Result: ✅ " -NoNewline -ForegroundColor Green
        Write-Host "Status $($_.Exception.Response.StatusCode.value__) - Correctly Rejected!" -ForegroundColor Green
    }
} else {
    Write-Host "Result: " -NoNewline -ForegroundColor White
    Write-Host "[SIMULATION] ❌ Request would be REJECTED" -ForegroundColor Red
}

Write-Host "`n" 
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                    DEMO COMPLETE                           ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host "`n"

Write-Host "KEY TAKEAWAYS:" -ForegroundColor Yellow
Write-Host "  • Only requests with valid signatures are accepted" -ForegroundColor White
Write-Host "  • Invalid/missing signatures are rejected with 401" -ForegroundColor White
Write-Host "  • HMAC SHA-256 ensures payload integrity" -ForegroundColor White
Write-Host "  • Prevents unauthorized access and tampering" -ForegroundColor White

if (-not $WebhookUrl) {
    Write-Host "`n💡 TIP: Run with -WebhookUrl to test against live API:" -ForegroundColor Cyan
    Write-Host "   .\demo-signature-validation.ps1 -WebhookUrl 'https://your-api.amazonaws.com/webhook' -Secret 'your_secret'" -ForegroundColor Gray
}

Write-Host "`n"
