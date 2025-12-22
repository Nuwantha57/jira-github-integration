# Test script for Jira Webhook
# Replace the URL below with your actual API Gateway endpoint URL

$apiUrl = "https://lmccuh0gra.execute-api.eu-north-1.amazonaws.com/default/JiraWebhookFunction"

$body = @{
    issue = @{
        key = "TEST-100"
        fields = @{
            summary = "Test Issue from Console Deployment"
            description = "Testing Jira to GitHub integration`n`nAcceptance Criteria:`n- Lambda works`n- GitHub issue created`n- All fields mapped"
            priority = @{
                name = "High"
            }
            assignee = @{
                displayName = "Nuwantha"
            }
            labels = @("sync-to-github", "backend", "high-priority")
        }
    }
} | ConvertTo-Json -Depth 10

Write-Host "Sending test webhook to Lambda..." -ForegroundColor Yellow
Write-Host "URL: $apiUrl" -ForegroundColor Cyan

$response = Invoke-RestMethod -Uri $apiUrl -Method Post -Body $body -ContentType "application/json"

Write-Host "`nResponse:" -ForegroundColor Green
$response | ConvertTo-Json

Write-Host "`nCheck your GitHub repo for the new issue!" -ForegroundColor Green
