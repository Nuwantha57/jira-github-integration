# Script to update AWS Secrets Manager with webhook secret
# Adds webhook_secret to existing secret

param(
    [Parameter(Mandatory=$false)]
    [string]$SecretName = "jira-github-integration",
    
    [Parameter(Mandatory=$false)]
    [string]$WebhookSecret = ""
)

Write-Host "=== Update Webhook Secret ===" -ForegroundColor Cyan
Write-Host ""

# Generate a random webhook secret if not provided
if (-not $WebhookSecret) {
    Write-Host "Generating random webhook secret..." -ForegroundColor Yellow
    $bytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $WebhookSecret = [Convert]::ToBase64String($bytes)
    Write-Host "Generated secret: $WebhookSecret" -ForegroundColor Green
}

Write-Host "Retrieving current secret from AWS..." -ForegroundColor Yellow

try {
    # Get current secret value
    $currentSecretJson = aws secretsmanager get-secret-value --secret-id $SecretName --query SecretString --output text
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to retrieve secret from AWS Secrets Manager" -ForegroundColor Red
        exit 1
    }
    
    # Parse current secret
    $currentSecret = $currentSecretJson | ConvertFrom-Json
    
    Write-Host "Current secret retrieved successfully" -ForegroundColor Green
    Write-Host "  Keys found: $($currentSecret.PSObject.Properties.Name -join ', ')" -ForegroundColor Gray
    
    # Add webhook_secret
    $currentSecret | Add-Member -MemberType NoteProperty -Name "webhook_secret" -Value $WebhookSecret -Force
    
    # Convert back to JSON
    $updatedSecretJson = $currentSecret | ConvertTo-Json -Compress
    
    # Update secret in AWS
    Write-Host ""
    Write-Host "Updating secret in AWS Secrets Manager..." -ForegroundColor Yellow
    
    aws secretsmanager update-secret --secret-id $SecretName --secret-string $updatedSecretJson
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Secret updated successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "=== IMPORTANT: Save this webhook secret ===" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Webhook Secret: $WebhookSecret" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "You will need to configure this in Jira webhook settings:" -ForegroundColor White
        Write-Host "1. Go to Jira -> Settings -> System -> WebHooks" -ForegroundColor Gray
        Write-Host "2. Edit your webhook" -ForegroundColor Gray
        Write-Host "3. Add this secret to the webhook configuration" -ForegroundColor Gray
        Write-Host ""
    } else {
        Write-Host "Failed to update secret" -ForegroundColor Red
        exit 1
    }
    
} catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
