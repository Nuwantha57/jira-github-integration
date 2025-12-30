# Security Testing Script for Jira Webhook
# Tests signature verification and unauthorized access attempts

param(
    [Parameter(Mandatory=$true)]
    [string]$WebhookUrl,
    
    [Parameter(Mandatory=$false)]
    [string]$JiraSecret = ""
)

# Test payload
$payload = @{
    issue = @{
        key = "TEST-123"
        fields = @{
            summary = "Security Test Issue"
            description = "Testing webhook security"
            labels = @("sync-to-github", "test")
            priority = @{
                name = "High"
            }
        }
    }
} | ConvertTo-Json -Depth 10

Write-Host "`n=== SECURITY TESTING ===" -ForegroundColor Cyan

# Test 1: Missing Signature Header
Write-Host "`n[Test 1] Testing without signature header..." -ForegroundColor Yellow
try {
    $response1 = Invoke-WebRequest -Uri $WebhookUrl `
        -Method POST `
        -Body $payload `
        -ContentType "application/json" `
        -ErrorAction Stop
    Write-Host "Status: $($response1.StatusCode)" -ForegroundColor Red
    Write-Host "FAIL: Should have rejected request without signature" -ForegroundColor Red
} catch {
    Write-Host "Status: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Green
    if ($_.Exception.Response.StatusCode.value__ -eq 401 -or $_.Exception.Response.StatusCode.value__ -eq 403) {
        Write-Host "PASS: Correctly rejected unauthorized request" -ForegroundColor Green
    } else {
        Write-Host "FAIL: Expected 401/403, got different error" -ForegroundColor Red
    }
}

# Test 2: Invalid Signature
Write-Host "`n[Test 2] Testing with invalid signature..." -ForegroundColor Yellow
try {
    $headers = @{
        "X-Hub-Signature" = "sha256=invalid_signature_here"
    }
    $response2 = Invoke-WebRequest -Uri $WebhookUrl `
        -Method POST `
        -Headers $headers `
        -Body $payload `
        -ContentType "application/json" `
        -ErrorAction Stop
    Write-Host "Status: $($response2.StatusCode)" -ForegroundColor Red
    Write-Host "FAIL: Should have rejected request with invalid signature" -ForegroundColor Red
} catch {
    Write-Host "Status: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Green
    if ($_.Exception.Response.StatusCode.value__ -eq 401 -or $_.Exception.Response.StatusCode.value__ -eq 403) {
        Write-Host "PASS: Correctly rejected invalid signature" -ForegroundColor Green
    } else {
        Write-Host "FAIL: Expected 401/403, got different error" -ForegroundColor Red
    }
}

# Test 3: Valid Signature (if secret provided)
if ($JiraSecret) {
    Write-Host "`n[Test 3] Testing with valid signature..." -ForegroundColor Yellow
    
    # Generate HMAC SHA256 signature
    $hmac = New-Object System.Security.Cryptography.HMACSHA256
    $hmac.Key = [Text.Encoding]::UTF8.GetBytes($JiraSecret)
    $hash = $hmac.ComputeHash([Text.Encoding]::UTF8.GetBytes($payload))
    $signature = "sha256=" + [BitConverter]::ToString($hash).Replace("-", "").ToLower()
    
    try {
        $headers = @{
            "X-Hub-Signature" = $signature
        }
        $response3 = Invoke-WebRequest -Uri $WebhookUrl `
            -Method POST `
            -Headers $headers `
            -Body $payload `
            -ContentType "application/json" `
            -ErrorAction Stop
        
        Write-Host "Status: $($response3.StatusCode)" -ForegroundColor Green
        if ($response3.StatusCode -eq 200) {
            Write-Host "PASS: Valid signature accepted" -ForegroundColor Green
        } else {
            Write-Host "WARN: Unexpected status code" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "Status: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
        Write-Host "FAIL: Valid signature was rejected" -ForegroundColor Red
    }
} else {
    Write-Host "`n[Test 3] Skipped - No Jira secret provided" -ForegroundColor Gray
}

# Test 4: Malformed JSON
Write-Host "`n[Test 4] Testing with malformed JSON..." -ForegroundColor Yellow
try {
    $response4 = Invoke-WebRequest -Uri $WebhookUrl `
        -Method POST `
        -Body "{invalid json" `
        -ContentType "application/json" `
        -ErrorAction Stop
    Write-Host "Status: $($response4.StatusCode)" -ForegroundColor Yellow
} catch {
    Write-Host "Status: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Green
    if ($_.Exception.Response.StatusCode.value__ -eq 400) {
        Write-Host "PASS: Correctly rejected malformed JSON" -ForegroundColor Green
    }
}

Write-Host "`n=== SECURITY TESTING COMPLETE ===" -ForegroundColor Cyan
