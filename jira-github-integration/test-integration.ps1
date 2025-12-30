# End-to-End Integration Testing Script
# Tests the complete flow from Jira webhook to GitHub issue creation

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
    [string]$JiraSecret = "",
    
    [Parameter(Mandatory=$false)]
    [string]$JiraBaseUrl = "https://your-company.atlassian.net"
)

Write-Host "=== END-TO-END INTEGRATION TEST ===" -ForegroundColor Cyan
Write-Host ""

# Test scenarios
$testScenarios = @(
    @{
        Name = "Basic Issue Creation"
        JiraKey = "TEST-001"
        Summary = "Test Issue - Basic Creation"
        Description = "This is a basic test issue to verify end-to-end integration"
        Labels = @("sync-to-github", "test")
        Priority = "Medium"
        Assignee = "Test User"
        ExpectedLabels = @("test")
    },
    @{
        Name = "Bug with High Priority"
        JiraKey = "TEST-002"
        Summary = "Test Bug - Critical Production Issue"
        Description = "Testing bug creation with high priority and multiple labels"
        Labels = @("sync-to-github", "bug", "high-priority", "backend")
        Priority = "High"
        Assignee = "Backend Team"
        ExpectedLabels = @("type:bug", "priority:high", "component:backend")
    },
    @{
        Name = "Feature Request"
        JiraKey = "TEST-003"
        Summary = "Test Feature - New Dashboard Widget"
        Description = "Testing feature request with frontend component"
        Labels = @("sync-to-github", "feature", "frontend", "medium-priority")
        Priority = "Medium"
        Assignee = "Frontend Team"
        ExpectedLabels = @("type:feature", "component:frontend", "priority:medium")
    },
    @{
        Name = "Unassigned Issue"
        JiraKey = "TEST-004"
        Summary = "Test Issue - No Assignee"
        Description = "Testing issue creation without an assignee"
        Labels = @("sync-to-github", "bug", "low-priority")
        Priority = "Low"
        Assignee = $null
        ExpectedLabels = @("type:bug", "priority:low")
    },
    @{
        Name = "Issue Without Description"
        JiraKey = "TEST-005"
        Summary = "Test Issue - No Description"
        Description = $null
        Labels = @("sync-to-github")
        Priority = "Medium"
        Assignee = "Test User"
        ExpectedLabels = @()
    }
)

# Function to generate HMAC signature
function Get-Signature {
    param([string]$Payload, [string]$Secret)
    
    if (-not $Secret) { return $null }
    
    $hmac = New-Object System.Security.Cryptography.HMACSHA256
    $hmac.Key = [Text.Encoding]::UTF8.GetBytes($Secret)
    $hash = $hmac.ComputeHash([Text.Encoding]::UTF8.GetBytes($Payload))
    return "sha256=" + [BitConverter]::ToString($hash).Replace("-", "").ToLower()
}

# Function to create Jira webhook payload
function Get-JiraWebhookPayload {
    param($Scenario)
    
    $payload = @{
        webhookEvent = "jira:issue_created"
        issue = @{
            key = $Scenario.JiraKey
            fields = @{
                summary = $Scenario.Summary
                labels = $Scenario.Labels
                priority = @{
                    name = $Scenario.Priority
                }
            }
        }
    }
    
    if ($Scenario.Description) {
        $payload.issue.fields.description = $Scenario.Description
    }
    
    if ($Scenario.Assignee) {
        $payload.issue.fields.assignee = @{
            displayName = $Scenario.Assignee
        }
    }
    
    return $payload | ConvertTo-Json -Depth 10
}

# Function to send webhook
function Send-Webhook {
    param([string]$Payload, [string]$Url, [string]$Secret)
    
    try {
        $headers = @{
            "Content-Type" = "application/json"
        }
        
        if ($Secret) {
            $signature = Get-Signature -Payload $Payload -Secret $Secret
            $headers["X-Hub-Signature"] = $signature
        }
        
        $response = Invoke-WebRequest -Uri $Url `
            -Method POST `
            -Headers $headers `
            -Body $Payload `
            -TimeoutSec 30 `
            -ErrorAction Stop
        
        $responseBody = $response.Content | ConvertFrom-Json
        return @{
            Success = $true
            StatusCode = $response.StatusCode
            Response = $responseBody
        }
    } catch {
        return @{
            Success = $false
            StatusCode = $_.Exception.Response.StatusCode.value__
            Error = $_.Exception.Message
        }
    }
}

# Function to verify GitHub issue
function Verify-GitHubIssue {
    param([string]$IssueUrl, [string]$Token, $ExpectedData)
    
    try {
        # Extract issue number from URL
        $issueNumber = ($IssueUrl -split '/')[-1]
        
        $response = Invoke-RestMethod -Uri "https://api.github.com/repos/$GitHubOwner/$GitHubRepo/issues/$issueNumber" `
            -Headers @{
                "Authorization" = "token $Token"
                "Accept" = "application/vnd.github.v3+json"
            } `
            -Method GET `
            -ErrorAction Stop
        
        # Verify title
        $titleMatch = $response.title -eq $ExpectedData.Summary
        
        # Verify body contains Jira key
        $bodyContainsJiraKey = $response.body -like "*$($ExpectedData.JiraKey)*"
        
        # Verify labels
        $actualLabels = $response.labels | ForEach-Object { $_.name }
        $labelMatch = $true
        foreach ($expectedLabel in $ExpectedData.ExpectedLabels) {
            if ($actualLabels -notcontains $expectedLabel) {
                $labelMatch = $false
                break
            }
        }
        
        return @{
            Success = $true
            TitleMatch = $titleMatch
            BodyContainsJiraKey = $bodyContainsJiraKey
            LabelMatch = $labelMatch
            ActualLabels = $actualLabels
            IssueNumber = $issueNumber
        }
    } catch {
        return @{
            Success = $false
            Error = $_.Exception.Message
        }
    }
}

# Run test scenarios
$testResults = @()

foreach ($scenario in $testScenarios) {
    Write-Host ""
    Write-Host "Testing: $($scenario.Name)" -ForegroundColor Yellow
    Write-Host "  Jira Key: $($scenario.JiraKey)" -ForegroundColor Gray
    
    # Send webhook
    $payload = Get-JiraWebhookPayload -Scenario $scenario
    $webhookResult = Send-Webhook -Payload $payload -Url $WebhookUrl -Secret $JiraSecret
    
    if (-not $webhookResult.Success) {
        Write-Host "  ❌ Webhook failed: $($webhookResult.Error)" -ForegroundColor Red
        $testResults += [PSCustomObject]@{
            Scenario = $scenario.Name
            JiraKey = $scenario.JiraKey
            WebhookSuccess = $false
            GitHubIssueCreated = $false
            AllVerificationsPassed = $false
            Error = $webhookResult.Error
        }
        continue
    }
    
    Write-Host "  ✓ Webhook accepted (Status: $($webhookResult.StatusCode))" -ForegroundColor Green
    
    # Wait a bit for Lambda to process
    Start-Sleep -Seconds 2
    
    # Verify GitHub issue
    if ($webhookResult.Response.github_issue_url) {
        $verification = Verify-GitHubIssue -IssueUrl $webhookResult.Response.github_issue_url `
            -Token $GitHubToken `
            -ExpectedData $scenario
        
        if ($verification.Success) {
            $allPassed = $verification.TitleMatch -and $verification.BodyContainsJiraKey -and $verification.LabelMatch
            
            Write-Host "  ✓ GitHub Issue #$($verification.IssueNumber) created" -ForegroundColor Green
            Write-Host "    Title Match: $(if ($verification.TitleMatch) { '✓' } else { '✗' })" -ForegroundColor $(if ($verification.TitleMatch) { "Green" } else { "Red" })
            Write-Host "    Jira Link: $(if ($verification.BodyContainsJiraKey) { '✓' } else { '✗' })" -ForegroundColor $(if ($verification.BodyContainsJiraKey) { "Green" } else { "Red" })
            Write-Host "    Labels Match: $(if ($verification.LabelMatch) { '✓' } else { '✗' })" -ForegroundColor $(if ($verification.LabelMatch) { "Green" } else { "Red" })
            Write-Host "    Actual Labels: $($verification.ActualLabels -join ', ')" -ForegroundColor Gray
            
            $testResults += [PSCustomObject]@{
                Scenario = $scenario.Name
                JiraKey = $scenario.JiraKey
                WebhookSuccess = $true
                GitHubIssueCreated = $true
                GitHubIssueNumber = $verification.IssueNumber
                TitleMatch = $verification.TitleMatch
                JiraLinkPresent = $verification.BodyContainsJiraKey
                LabelsMatch = $verification.LabelMatch
                AllVerificationsPassed = $allPassed
                Error = $null
            }
        } else {
            Write-Host "  ❌ Failed to verify GitHub issue: $($verification.Error)" -ForegroundColor Red
            $testResults += [PSCustomObject]@{
                Scenario = $scenario.Name
                JiraKey = $scenario.JiraKey
                WebhookSuccess = $true
                GitHubIssueCreated = $false
                AllVerificationsPassed = $false
                Error = $verification.Error
            }
        }
    } else {
        Write-Host "  ❌ No GitHub issue URL in response" -ForegroundColor Red
        $testResults += [PSCustomObject]@{
            Scenario = $scenario.Name
            JiraKey = $scenario.JiraKey
            WebhookSuccess = $true
            GitHubIssueCreated = $false
            AllVerificationsPassed = $false
            Error = "No GitHub issue URL returned"
        }
    }
}

# Summary
Write-Host ""
Write-Host "=== TEST SUMMARY ===" -ForegroundColor Cyan
Write-Host ""

$totalTests = $testResults.Count
$passedTests = ($testResults | Where-Object { $_.AllVerificationsPassed }).Count
$failedTests = $totalTests - $passedTests

Write-Host "Total Test Scenarios: $totalTests" -ForegroundColor White
Write-Host "Passed: $passedTests" -ForegroundColor Green
Write-Host "Failed: $failedTests" -ForegroundColor $(if ($failedTests -gt 0) { "Red" } else { "White" })
Write-Host ""

if ($failedTests -gt 0) {
    Write-Host "Failed Tests:" -ForegroundColor Red
    $testResults | Where-Object { -not $_.AllVerificationsPassed } | ForEach-Object {
        Write-Host "  - $($_.Scenario): $($_.Error)" -ForegroundColor Red
    }
    Write-Host ""
}

# Export results
$csvPath = "integration-test-results-$(Get-Date -Format 'yyyyMMdd-HHmmss').csv"
$testResults | Export-Csv -Path $csvPath -NoTypeInformation
Write-Host "Detailed results exported to: $csvPath" -ForegroundColor Gray
Write-Host ""
Write-Host "=== INTEGRATION TEST COMPLETE ===" -ForegroundColor Cyan

# Exit with appropriate code
if ($failedTests -gt 0) {
    exit 1
} else {
    exit 0
}
