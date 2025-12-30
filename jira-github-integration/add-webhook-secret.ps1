# Simple script to add webhook_secret to AWS Secrets Manager
# Run this before deploying the updated Lambda function

Write-Host "=== Add Webhook Secret to AWS Secrets Manager ===" -ForegroundColor Cyan
Write-Host ""

$SecretName = "jira-github-integration"

# Generate secure random webhook secret
$bytes = New-Object byte[] 32
[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
$WebhookSecret = [Convert]::ToBase64String($bytes)

Write-Host "Generated webhook secret: $WebhookSecret" -ForegroundColor Green
Write-Host ""

# Get current secret
Write-Host "Fetching current secret from AWS..." -ForegroundColor Yellow
$currentSecretJson = aws secretsmanager get-secret-value --secret-id $SecretName --query SecretString --output text

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error fetching secret from AWS" -ForegroundColor Red
    exit 1
}

# Parse and update
$secret = $currentSecretJson | ConvertFrom-Json
$secret | Add-Member -NotePropertyName "webhook_secret" -NotePropertyValue $WebhookSecret -Force

# Convert to JSON
$updatedJson = $secret | ConvertTo-Json -Compress

# Update in AWS
Write-Host "Updating secret in AWS..." -ForegroundColor Yellow
aws secretsmanager update-secret --secret-id $SecretName --secret-string $updatedJson | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host "Secret updated successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "SAVE THIS WEBHOOK SECRET:" -ForegroundColor Yellow
    Write-Host $WebhookSecret -ForegroundColor Cyan
    Write-Host ""
    Write-Host "You will need this for Jira webhook configuration" -ForegroundColor White
} else {
    Write-Host "Failed to update secret" -ForegroundColor Red
    exit 1
}
