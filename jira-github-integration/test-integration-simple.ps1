# Simple End-to-End Integration Test
# Tests complete Jira webhook to GitHub issue creation flow

param(
    [Parameter(Mandatory=$true)]
    [string]$WebhookUrl,
    
    [Parameter(Mandatory=$true)]
    [string]$GitHubToken,
    
    [Parameter(Mandatory=$true)]
    [string]$GitHubOwner,
    
    [Parameter(Mandatory=$true)]
    [string]$GitHubRepo,
    
    [Parameter(Mandatory=$false)]
    [string]$JiraBaseUrl = "https://nuwanthapiumal57.atlassian.net"
)

Write-Host "=== INTEGRATION TEST ===" -ForegroundColor Cyan
Write-Host ""

# Test payload - simulates a Jira webhook
$payload = @{
    issue = @{
        key = "TEST-100"
        fields = @{
            summary = "Integration Test Issue - GitHub Sync"
            description = "This is a test to verify end-to-end integration between Jira and GitHub"
            labels = @("sync-to-github", "bug", "high-priority", "backend")
            priority = @{
                name = "High"
            }
            assignee = @{
                displayName = "Test User"
            }
        }
    }
} | ConvertTo-Json -Depth 10

Write-Host "Step 1: Sending webhook to Lambda..." -ForegroundColor Yellow
try {
    $headers = @{
        "Content-Type" = "application/json"
        "X-Atlassian-Webhook-Identifier" = "test-webhook-123"
    }
    
    $response = Invoke-WebRequest -Uri $WebhookUrl `
        -Method POST `
        -Headers $headers `
        -Body $payload `
        -UseBasicParsing `
        -TimeoutSec 30 `
        -ErrorAction Stop
    
    $responseBody = $response.Content | ConvertFrom-Json
    
    Write-Host "  Status: $($response.StatusCode)" -ForegroundColor Green
    Write-Host "  Response: $($response.Content)" -ForegroundColor Gray
    
    if ($responseBody.github_issue_url) {
        Write-Host ""
        Write-Host "Step 2: Verifying GitHub issue..." -ForegroundColor Yellow
        
        # Extract issue number from URL
        $issueNumber = ($responseBody.github_issue_url -split '/')[-1]
        Write-Host "  GitHub Issue Number: #$issueNumber" -ForegroundColor Cyan
        
        # Wait a moment for GitHub to process
        Start-Sleep -Seconds 2
        
        # Verify the issue
        try {
            $githubIssue = Invoke-RestMethod -Uri "https://api.github.com/repos/$GitHubOwner/$GitHubRepo/issues/$issueNumber" `
                -Headers @{
                    "Authorization" = "token $GitHubToken"
                    "Accept" = "application/vnd.github.v3+json"
                } `
                -Method GET `
                -ErrorAction Stop
            
            Write-Host ""
            Write-Host "=== GITHUB ISSUE CREATED ===" -ForegroundColor Green
            Write-Host "  Title: $($githubIssue.title)" -ForegroundColor White
            Write-Host "  Number: #$($githubIssue.number)" -ForegroundColor Cyan
            Write-Host "  URL: $($githubIssue.html_url)" -ForegroundColor Cyan
            Write-Host "  State: $($githubIssue.state)" -ForegroundColor White
            Write-Host "  Labels: $($githubIssue.labels | ForEach-Object { $_.name }) -join ', ')" -ForegroundColor White
            Write-Host ""
            
            # Verify content
            $titleMatch = $githubIssue.title -eq "Integration Test Issue - GitHub Sync"
            $bodyContainsJira = $githubIssue.body -like "*TEST-100*"
            $hasLabels = $githubIssue.labels.Count -gt 0
            
            Write-Host "=== VERIFICATION ===" -ForegroundColor Cyan
            Write-Host "  Title Match: $(if ($titleMatch) { 'PASS' } else { 'FAIL' })" -ForegroundColor $(if ($titleMatch) { "Green" } else { "Red" })
            Write-Host "  Contains Jira Key: $(if ($bodyContainsJira) { 'PASS' } else { 'FAIL' })" -ForegroundColor $(if ($bodyContainsJira) { "Green" } else { "Red" })
            Write-Host "  Has Labels: $(if ($hasLabels) { 'PASS' } else { 'FAIL' })" -ForegroundColor $(if ($hasLabels) { "Green" } else { "Red" })
            
            $allPassed = $titleMatch -and $bodyContainsJira -and $hasLabels
            
            Write-Host ""
            if ($allPassed) {
                Write-Host "=== TEST RESULT: PASSED ===" -ForegroundColor Green
                exit 0
            } else {
                Write-Host "=== TEST RESULT: FAILED ===" -ForegroundColor Red
                exit 1
            }
            
        } catch {
            Write-Host "  ERROR: Failed to verify GitHub issue" -ForegroundColor Red
            Write-Host "  $($_.Exception.Message)" -ForegroundColor Red
            exit 1
        }
        
    } else {
        Write-Host "  ERROR: No GitHub issue URL in response" -ForegroundColor Red
        Write-Host "  Response: $($response.Content)" -ForegroundColor Gray
        exit 1
    }
    
} catch {
    Write-Host "  ERROR: Webhook request failed" -ForegroundColor Red
    Write-Host "  Status: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
    Write-Host "  Message: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
