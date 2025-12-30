# Load Testing Script for Jira-GitHub Integration
# Sends concurrent webhook requests to test performance

param(
    [Parameter(Mandatory=$true)]
    [string]$WebhookUrl,
    
    [Parameter(Mandatory=$false)]
    [int]$ConcurrentRequests = 25,
    
    [Parameter(Mandatory=$false)]
    [string]$JiraSecret = ""
)

Write-Host "=== LOAD TESTING ===" -ForegroundColor Cyan
Write-Host "Webhook URL: $WebhookUrl" -ForegroundColor White
Write-Host "Concurrent Requests: $ConcurrentRequests" -ForegroundColor White
Write-Host ""

# Test payload template
function Get-TestPayload {
    param([int]$Id)
    
    return @{
        issue = @{
            key = "LOAD-$Id"
            fields = @{
                summary = "Load Test Issue #$Id"
                description = "This is a load test issue created at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
                labels = @("sync-to-github", "load-test")
                priority = @{
                    name = "Medium"
                }
                assignee = @{
                    displayName = "Load Tester"
                }
            }
        }
    } | ConvertTo-Json -Depth 10
}

# Function to generate HMAC signature
function Get-Signature {
    param([string]$Payload, [string]$Secret)
    
    if (-not $Secret) { return $null }
    
    $hmac = New-Object System.Security.Cryptography.HMACSHA256
    $hmac.Key = [Text.Encoding]::UTF8.GetBytes($Secret)
    $hash = $hmac.ComputeHash([Text.Encoding]::UTF8.GetBytes($Payload))
    return "sha256=" + [BitConverter]::ToString($hash).Replace("-", "").ToLower()
}

# Function to send a single request
function Send-WebhookRequest {
    param([int]$Id, [string]$Url, [string]$Secret)
    
    $payload = Get-TestPayload -Id $Id
    $startTime = Get-Date
    
    try {
        $headers = @{
            "Content-Type" = "application/json"
        }
        
        if ($Secret) {
            $signature = Get-Signature -Payload $payload -Secret $Secret
            $headers["X-Hub-Signature"] = $signature
        }
        
        $response = Invoke-WebRequest -Uri $Url `
            -Method POST `
            -Headers $headers `
            -Body $payload `
            -TimeoutSec 30 `
            -ErrorAction Stop
        
        $duration = (Get-Date) - $startTime
        
        return [PSCustomObject]@{
            Id = $Id
            StatusCode = $response.StatusCode
            Duration = $duration.TotalMilliseconds
            Success = $true
            Error = $null
        }
    } catch {
        $duration = (Get-Date) - $startTime
        
        return [PSCustomObject]@{
            Id = $Id
            StatusCode = $_.Exception.Response.StatusCode.value__
            Duration = $duration.TotalMilliseconds
            Success = $false
            Error = $_.Exception.Message
        }
    }
}

# Run concurrent requests
Write-Host "Starting load test with $ConcurrentRequests concurrent requests..." -ForegroundColor Yellow
Write-Host ""

$jobs = @()
$startTime = Get-Date

for ($i = 1; $i -le $ConcurrentRequests; $i++) {
    $jobs += Start-Job -ScriptBlock {
        param($Id, $Url, $Secret, $FunctionDef, $PayloadFuncDef, $SignatureFuncDef)
        
        # Re-define functions in job scope
        Invoke-Expression $PayloadFuncDef
        Invoke-Expression $SignatureFuncDef
        Invoke-Expression $FunctionDef
        
        Send-WebhookRequest -Id $Id -Url $Url -Secret $Secret
    } -ArgumentList $i, $WebhookUrl, $JiraSecret, ${function:Send-WebhookRequest}, ${function:Get-TestPayload}, ${function:Get-Signature}
    
    Write-Host "." -NoNewline -ForegroundColor Green
}

Write-Host ""
Write-Host "Waiting for all requests to complete..." -ForegroundColor Yellow

# Wait for all jobs to complete
$results = $jobs | Wait-Job | Receive-Job
$jobs | Remove-Job

$totalTime = (Get-Date) - $startTime

# Calculate statistics
$successful = ($results | Where-Object { $_.Success }).Count
$failed = $results.Count - $successful
$avgDuration = ($results | Measure-Object -Property Duration -Average).Average
$minDuration = ($results | Measure-Object -Property Duration -Minimum).Minimum
$maxDuration = ($results | Measure-Object -Property Duration -Maximum).Maximum

# Display results
Write-Host ""
Write-Host "=== LOAD TEST RESULTS ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Total Requests:       $($results.Count)" -ForegroundColor White
Write-Host "Successful:           $successful" -ForegroundColor Green
Write-Host "Failed:               $failed" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "White" })
Write-Host ""
Write-Host "Total Time:           $([math]::Round($totalTime.TotalSeconds, 2)) seconds" -ForegroundColor White
Write-Host "Requests/Second:      $([math]::Round($results.Count / $totalTime.TotalSeconds, 2))" -ForegroundColor White
Write-Host ""
Write-Host "Response Times (ms):" -ForegroundColor White
Write-Host "  Average:            $([math]::Round($avgDuration, 2)) ms" -ForegroundColor White
Write-Host "  Min:                $([math]::Round($minDuration, 2)) ms" -ForegroundColor White
Write-Host "  Max:                $([math]::Round($maxDuration, 2)) ms" -ForegroundColor White
Write-Host ""

# Show failed requests if any
if ($failed -gt 0) {
    Write-Host "Failed Requests:" -ForegroundColor Red
    $results | Where-Object { -not $_.Success } | ForEach-Object {
        Write-Host "  ID $($_.Id): $($_.Error)" -ForegroundColor Red
    }
    Write-Host ""
}

# Status code breakdown
Write-Host "Status Code Breakdown:" -ForegroundColor White
$results | Group-Object StatusCode | ForEach-Object {
    $color = if ($_.Name -eq "200" -or $_.Name -eq "201") { "Green" } else { "Yellow" }
    Write-Host "  $($_.Name): $($_.Count)" -ForegroundColor $color
}

Write-Host ""
Write-Host "=== LOAD TEST COMPLETE ===" -ForegroundColor Cyan

# Export detailed results to CSV
$csvPath = "load-test-results-$(Get-Date -Format 'yyyyMMdd-HHmmss').csv"
$results | Export-Csv -Path $csvPath -NoTypeInformation
Write-Host ""
Write-Host "Detailed results exported to: $csvPath" -ForegroundColor Gray
