# Simplified Load Testing Script
# Tests concurrent webhook requests without background jobs

param(
    [Parameter(Mandatory=$true)]
    [string]$WebhookUrl,
    
    [Parameter(Mandatory=$false)]
    [int]$TotalRequests = 25
)

Write-Host "=== SIMPLE LOAD TEST ===" -ForegroundColor Cyan
Write-Host "URL: $WebhookUrl"
Write-Host "Total Requests: $TotalRequests"
Write-Host ""

# Test payload
$payload = @{
    issue = @{
        key = "LOAD-TEST"
        fields = @{
            summary = "Load Test Issue"
            description = "Testing performance"
            labels = @("sync-to-github", "load-test")
            priority = @{ name = "Medium" }
        }
    }
} | ConvertTo-Json -Depth 10

$results = @()
$startTime = Get-Date

Write-Host "Sending $TotalRequests requests..." -ForegroundColor Yellow

for ($i = 1; $i -le $TotalRequests; $i++) {
    $requestStart = Get-Date
    
    try {
        $response = Invoke-WebRequest -Uri $WebhookUrl `
            -Method POST `
            -Body $payload `
            -ContentType "application/json" `
            -UseBasicParsing `
            -TimeoutSec 30 `
            -ErrorAction Stop
        
        $duration = ((Get-Date) - $requestStart).TotalMilliseconds
        
        $results += [PSCustomObject]@{
            Id = $i
            StatusCode = $response.StatusCode
            Duration = $duration
            Success = $true
        }
        
        Write-Host "." -NoNewline -ForegroundColor Green
    }
    catch {
        $duration = ((Get-Date) - $requestStart).TotalMilliseconds
        $statusCode = if ($_.Exception.Response) { 
            $_.Exception.Response.StatusCode.value__ 
        } else { 0 }
        
        $results += [PSCustomObject]@{
            Id = $i
            StatusCode = $statusCode
            Duration = $duration
            Success = $false
        }
        
        Write-Host "x" -NoNewline -ForegroundColor Red
    }
}

$totalDuration = ((Get-Date) - $startTime).TotalSeconds

Write-Host ""
Write-Host ""
Write-Host "=== LOAD TEST RESULTS ===" -ForegroundColor Cyan
Write-Host ""

$successful = ($results | Where-Object { $_.Success }).Count
$failed = $results.Count - $successful

Write-Host "Total Requests:     $($results.Count)" -ForegroundColor White
Write-Host "Successful:         $successful" -ForegroundColor $(if ($successful -gt 0) { "Green" } else { "Red" })
Write-Host "Failed:             $failed" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "White" })
Write-Host ""
Write-Host "Total Time:         $([math]::Round($totalDuration, 2)) seconds" -ForegroundColor White
Write-Host "Requests/Second:    $([math]::Round($results.Count / $totalDuration, 2))" -ForegroundColor White
Write-Host ""

if ($results.Count -gt 0) {
    $avgDuration = ($results | Measure-Object -Property Duration -Average).Average
    $minDuration = ($results | Measure-Object -Property Duration -Minimum).Minimum
    $maxDuration = ($results | Measure-Object -Property Duration -Maximum).Maximum
    
    Write-Host "Response Times:" -ForegroundColor White
    Write-Host "  Average:          $([math]::Round($avgDuration, 2)) ms" -ForegroundColor White
    Write-Host "  Min:              $([math]::Round($minDuration, 2)) ms" -ForegroundColor White
    Write-Host "  Max:              $([math]::Round($maxDuration, 2)) ms" -ForegroundColor White
    Write-Host ""
}

# Status code breakdown
Write-Host "Status Code Breakdown:" -ForegroundColor White
$results | Group-Object StatusCode | ForEach-Object {
    $color = switch ($_.Name) {
        "200" { "Green" }
        "201" { "Green" }
        "401" { "Yellow" }
        "403" { "Yellow" }
        default { "Red" }
    }
    Write-Host "  $($_.Name): $($_.Count)" -ForegroundColor $color
}

Write-Host ""
Write-Host "=== TEST COMPLETE ===" -ForegroundColor Cyan

# Export results
$csvPath = "load-test-simple-$(Get-Date -Format 'yyyyMMdd-HHmmss').csv"
$results | Export-Csv -Path $csvPath -NoTypeInformation
Write-Host "Results exported to: $csvPath" -ForegroundColor Gray
