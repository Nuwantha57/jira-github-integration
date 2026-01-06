# How to Test with Valid Signatures

## Overview

This guide explains **step-by-step** how to generate and use valid HMAC SHA-256 signatures for testing webhook authentication. Valid signatures are required to test that legitimate, authorized requests are accepted by your webhook endpoint.

---

## Table of Contents

1. [Understanding Webhook Signatures](#understanding-webhook-signatures)
2. [Prerequisites](#prerequisites)
3. [Method 1: Using PowerShell](#method-1-using-powershell)
4. [Method 2: Using Python](#method-2-using-python)
5. [Method 3: Using the Test Script](#method-3-using-the-test-script)
6. [Method 4: Using curl](#method-4-using-curl)
7. [Troubleshooting](#troubleshooting)
8. [Complete Examples](#complete-examples)

---

## Understanding Webhook Signatures

### What is a Webhook Signature?

A webhook signature is a cryptographic hash that proves:

1. The request came from someone who knows the secret
2. The payload hasn't been tampered with

### How It Works

```
┌─────────────────────────────────────────────────┐
│ 1. Sender (Jira or Test Script)                 │
│    - Has: Payload + Secret                      │
│    - Creates: HMAC SHA-256 hash                 │
│    - Sends: Payload + Signature in header       │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ 2. API Gateway                                   │
│    - Forwards request to Lambda                  │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ 3. Lambda Function                               │
│    - Receives: Payload + Signature              │
│    - Has: Same Secret (from Secrets Manager)    │
│    - Computes: Expected signature               │
│    - Compares: Expected vs. Received            │
│    - If match: ✅ Accept                        │
│    - If no match: ❌ Reject (401)               │
└─────────────────────────────────────────────────┘
```

### Signature Format

```
Header Name: X-Hub-Signature
Header Value: sha256=<64_character_hex_hash>

Example:
X-Hub-Signature: sha256=a1b2c3d4e5f6...890
```

### Algorithm: HMAC SHA-256

```
signature = HMAC-SHA256(secret, payload_body)
header = "sha256=" + hex(signature)
```

---

## Prerequisites

### 1. Get Your Webhook Secret

The webhook secret is stored in AWS Secrets Manager. Retrieve it:

#### Using AWS CLI

```powershell
# Get the secret value
$secretJson = aws secretsmanager get-secret-value `
    --secret-id jira-github-webhook-secret `
    --query SecretString `
    --output text

# Parse the JSON
$secretObj = $secretJson | ConvertFrom-Json
$webhookSecret = $secretObj.webhook_secret

# Display the secret
Write-Host "Webhook Secret: $webhookSecret"
```

#### Using AWS Console

1. Open AWS Secrets Manager
2. Find secret: `jira-github-webhook-secret`
3. Click "Retrieve secret value"
4. Copy the `webhook_secret` value

**Example Secret Value**:

```json
{
  "webhook_secret": "my_super_secret_key_12345"
}
```

### 2. Get Your Webhook URL

```powershell
# Get from CloudFormation outputs
aws cloudformation describe-stacks `
    --stack-name jira-github-integration `
    --query 'Stacks[0].Outputs[?OutputKey==`WebhookUrl`].OutputValue' `
    --output text
```

**Example URL**:

```
https://abc123xyz.execute-api.us-east-1.amazonaws.com/Prod/webhook
```

### 3. Prepare Test Payload

```powershell
$payload = @{
    issue = @{
        key = "TEST-123"
        fields = @{
            summary = "Test Issue with Valid Signature"
            description = "Testing authentication"
            labels = @("sync-to-github", "test")
            priority = @{ name = "High" }
        }
    }
} | ConvertTo-Json -Depth 10
```

---

## Method 1: Using PowerShell

### Step-by-Step Instructions

#### Step 1: Set Variables

```powershell
# Your webhook URL
$webhookUrl = "https://abc123xyz.execute-api.us-east-1.amazonaws.com/Prod/webhook"

# Your webhook secret (from Secrets Manager)
$webhookSecret = "my_super_secret_key_12345"

# Test payload
$payload = @{
    issue = @{
        key = "TEST-123"
        fields = @{
            summary = "Test Issue"
            description = "Testing with valid signature"
            labels = @("sync-to-github", "test")
            priority = @{ name = "Medium" }
        }
    }
} | ConvertTo-Json -Depth 10

Write-Host "Payload prepared" -ForegroundColor Green
```

#### Step 2: Generate HMAC Signature

```powershell
# Create HMAC SHA-256 object
$hmac = New-Object System.Security.Cryptography.HMACSHA256

# Set the secret key (convert to bytes)
$hmac.Key = [Text.Encoding]::UTF8.GetBytes($webhookSecret)

# Compute hash of payload (convert payload to bytes)
$hash = $hmac.ComputeHash([Text.Encoding]::UTF8.GetBytes($payload))

# Convert hash to hex string (lowercase)
$signatureHex = [BitConverter]::ToString($hash).Replace("-", "").ToLower()

# Format as header value
$signature = "sha256=$signatureHex"

Write-Host "Generated Signature: $signature" -ForegroundColor Cyan
```

#### Step 3: Send Request with Signature

```powershell
# Create headers with signature
$headers = @{
    "X-Hub-Signature" = $signature
    "Content-Type" = "application/json"
}

# Send the request
try {
    $response = Invoke-WebRequest `
        -Uri $webhookUrl `
        -Method POST `
        -Headers $headers `
        -Body $payload `
        -ErrorAction Stop

    Write-Host "`n✅ SUCCESS!" -ForegroundColor Green
    Write-Host "Status Code: $($response.StatusCode)" -ForegroundColor Green
    Write-Host "Response: $($response.Content)" -ForegroundColor Gray
} catch {
    Write-Host "`n❌ FAILED!" -ForegroundColor Red
    Write-Host "Status Code: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
}
```

### Complete PowerShell Script

Save this as `test-valid-signature.ps1`:

```powershell
param(
    [Parameter(Mandatory=$true)]
    [string]$WebhookUrl,

    [Parameter(Mandatory=$true)]
    [string]$WebhookSecret
)

Write-Host "`n=== TESTING WITH VALID SIGNATURE ===" -ForegroundColor Cyan
Write-Host "URL: $WebhookUrl" -ForegroundColor Gray
Write-Host ""

# Prepare payload
$payload = @{
    issue = @{
        key = "TEST-$(Get-Random -Minimum 100 -Maximum 999)"
        fields = @{
            summary = "Test Issue - Valid Signature $(Get-Date -Format 'HH:mm:ss')"
            description = "Testing webhook with valid HMAC signature"
            labels = @("sync-to-github", "test")
            priority = @{ name = "Medium" }
            assignee = @{
                displayName = "Test User"
            }
        }
    }
} | ConvertTo-Json -Depth 10

Write-Host "Step 1: Payload prepared ✓" -ForegroundColor Green
Write-Host "Payload size: $($payload.Length) bytes" -ForegroundColor Gray

# Generate signature
$hmac = New-Object System.Security.Cryptography.HMACSHA256
$hmac.Key = [Text.Encoding]::UTF8.GetBytes($WebhookSecret)
$hash = $hmac.ComputeHash([Text.Encoding]::UTF8.GetBytes($payload))
$signature = "sha256=" + [BitConverter]::ToString($hash).Replace("-", "").ToLower()

Write-Host "Step 2: Signature generated ✓" -ForegroundColor Green
Write-Host "Signature: $($signature.Substring(0, 30))..." -ForegroundColor Gray

# Send request
$headers = @{
    "X-Hub-Signature" = $signature
}

Write-Host "Step 3: Sending request..." -ForegroundColor Yellow

try {
    $startTime = Get-Date
    $response = Invoke-WebRequest `
        -Uri $WebhookUrl `
        -Method POST `
        -Headers $headers `
        -Body $payload `
        -ContentType "application/json" `
        -ErrorAction Stop
    $duration = ((Get-Date) - $startTime).TotalMilliseconds

    Write-Host "`n✅ SUCCESS!" -ForegroundColor Green
    Write-Host "Status Code: $($response.StatusCode)" -ForegroundColor Green
    Write-Host "Duration: $([math]::Round($duration, 2)) ms" -ForegroundColor Gray
    Write-Host "`nResponse:" -ForegroundColor White
    Write-Host $response.Content -ForegroundColor Gray

} catch {
    $duration = ((Get-Date) - $startTime).TotalMilliseconds
    Write-Host "`n❌ FAILED!" -ForegroundColor Red
    Write-Host "Status Code: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
    Write-Host "Duration: $([math]::Round($duration, 2)) ms" -ForegroundColor Gray
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n=== TEST COMPLETE ===" -ForegroundColor Cyan
```

**Usage**:

```powershell
# Retrieve secret
$secret = (aws secretsmanager get-secret-value --secret-id jira-github-webhook-secret --query SecretString --output text | ConvertFrom-Json).webhook_secret

# Run test
.\test-valid-signature.ps1 `
    -WebhookUrl "https://your-url.amazonaws.com/Prod/webhook" `
    -WebhookSecret $secret
```

---

## Method 2: Using Python

### Step-by-Step Instructions

#### Step 1: Install Requirements

```bash
pip install requests
```

#### Step 2: Create Test Script

Save this as `test-valid-signature.py`:

```python
#!/usr/bin/env python3
import hmac
import hashlib
import json
import requests
import sys

def generate_signature(payload_str, secret):
    """Generate HMAC SHA-256 signature"""
    signature = hmac.new(
        key=secret.encode('utf-8'),
        msg=payload_str.encode('utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"

def test_valid_signature(webhook_url, webhook_secret):
    """Send test request with valid signature"""

    print("\n" + "="*60)
    print("TESTING WITH VALID SIGNATURE")
    print("="*60)
    print(f"URL: {webhook_url}")
    print()

    # Prepare payload
    payload = {
        "issue": {
            "key": "TEST-123",
            "fields": {
                "summary": "Test Issue - Valid Signature",
                "description": "Testing webhook with valid HMAC signature",
                "labels": ["sync-to-github", "test"],
                "priority": {"name": "Medium"},
                "assignee": {"displayName": "Test User"}
            }
        }
    }

    # Convert to JSON string (important: same format for signing)
    payload_str = json.dumps(payload, separators=(',', ':'))

    print(f"Step 1: Payload prepared ✓")
    print(f"Payload size: {len(payload_str)} bytes")

    # Generate signature
    signature = generate_signature(payload_str, webhook_secret)

    print(f"Step 2: Signature generated ✓")
    print(f"Signature: {signature[:30]}...")

    # Prepare headers
    headers = {
        "X-Hub-Signature": signature,
        "Content-Type": "application/json"
    }

    # Send request
    print(f"Step 3: Sending request...")

    try:
        response = requests.post(
            webhook_url,
            json=payload,
            headers=headers,
            timeout=30
        )

        print(f"\n✅ SUCCESS!")
        print(f"Status Code: {response.status_code}")
        print(f"\nResponse:")
        print(response.text)

        return True

    except requests.exceptions.RequestException as e:
        print(f"\n❌ FAILED!")
        print(f"Error: {str(e)}")
        return False

    finally:
        print("\n" + "="*60)
        print("TEST COMPLETE")
        print("="*60)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python test-valid-signature.py <webhook_url> <webhook_secret>")
        sys.exit(1)

    webhook_url = sys.argv[1]
    webhook_secret = sys.argv[2]

    success = test_valid_signature(webhook_url, webhook_secret)
    sys.exit(0 if success else 1)
```

#### Step 3: Run the Script

```bash
# Get secret from AWS (if in PowerShell)
$secret = (aws secretsmanager get-secret-value --secret-id jira-github-webhook-secret --query SecretString --output text | ConvertFrom-Json).webhook_secret

# Run Python test
python test-valid-signature.py `
    "https://your-url.amazonaws.com/Prod/webhook" `
    "$secret"
```

---

## Method 3: Using the Test Script

Your existing `test-security.ps1` script already supports valid signature testing!

### Quick Usage

```powershell
# Get the webhook secret
$secret = (aws secretsmanager get-secret-value `
    --secret-id jira-github-webhook-secret `
    --query SecretString `
    --output text | ConvertFrom-Json).webhook_secret

# Run the security test with secret
.\test-security.ps1 `
    -WebhookUrl "https://your-url.amazonaws.com/Prod/webhook" `
    -JiraSecret $secret
```

This will run:

- ❌ Test 1: No signature (should fail)
- ❌ Test 2: Invalid signature (should fail)
- ✅ **Test 3: Valid signature (should succeed)** ← This is what you need!
- ❌ Test 4: Malformed JSON (should fail)

### Expected Output

```
=== SECURITY TESTING ===

[Test 1] Testing without signature header...
Status: 401
PASS: Correctly rejected unauthorized request

[Test 2] Testing with invalid signature...
Status: 401
PASS: Correctly rejected invalid signature

[Test 3] Testing with valid signature...
Status: 200
PASS: Valid signature accepted  ← SUCCESS!

[Test 4] Testing with malformed JSON...
Status: 400
PASS: Correctly rejected malformed JSON

=== SECURITY TESTING COMPLETE ===
```

---

## Method 4: Using curl

### For Linux/Mac

```bash
#!/bin/bash

WEBHOOK_URL="https://your-url.amazonaws.com/Prod/webhook"
WEBHOOK_SECRET="your_secret_here"

# Create payload
PAYLOAD='{
  "issue": {
    "key": "TEST-123",
    "fields": {
      "summary": "Test Issue",
      "description": "Testing with valid signature",
      "labels": ["sync-to-github", "test"],
      "priority": {"name": "Medium"}
    }
  }
}'

# Generate signature
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" | sed 's/^.* //')

# Send request
curl -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature: sha256=$SIGNATURE" \
  -d "$PAYLOAD" \
  -v
```

### For Windows (PowerShell with curl)

```powershell
$webhookUrl = "https://your-url.amazonaws.com/Prod/webhook"
$webhookSecret = "your_secret_here"

$payload = '{"issue":{"key":"TEST-123","fields":{"summary":"Test Issue","description":"Testing","labels":["sync-to-github"],"priority":{"name":"Medium"}}}}'

# Generate signature
$hmac = New-Object System.Security.Cryptography.HMACSHA256
$hmac.Key = [Text.Encoding]::UTF8.GetBytes($webhookSecret)
$hash = $hmac.ComputeHash([Text.Encoding]::UTF8.GetBytes($payload))
$signature = "sha256=" + [BitConverter]::ToString($hash).Replace("-", "").ToLower()

# Send with curl
curl -X POST $webhookUrl `
    -H "Content-Type: application/json" `
    -H "X-Hub-Signature: $signature" `
    -d $payload `
    -v
```

---

## Troubleshooting

### Issue 1: Valid Signature Returns 401

**Symptoms**: Test 3 fails even though signature is valid

**Possible Causes**:

#### A. Wrong Secret

```powershell
# Verify you have the correct secret
$secretJson = aws secretsmanager get-secret-value `
    --secret-id jira-github-webhook-secret `
    --query SecretString `
    --output text

Write-Host $secretJson

# Make sure you extract the "webhook_secret" field
$secret = ($secretJson | ConvertFrom-Json).webhook_secret
Write-Host "Secret: $secret"
```

#### B. Payload Encoding Mismatch

The payload must be **exactly the same** when computing the signature and sending the request.

**Problem**:

```powershell
# ❌ WRONG: Using -Depth parameter inconsistently
$payload1 = $data | ConvertTo-Json -Depth 5
$payload2 = $data | ConvertTo-Json -Depth 10  # Different!
```

**Solution**:

```powershell
# ✅ CORRECT: Use same exact string
$payload = $data | ConvertTo-Json -Depth 10
# Use $payload for both signature AND request body
```

#### C. Character Encoding Issues

**Problem**: Different encoding between signature and body

**Solution**:

```powershell
# Always use UTF-8
[Text.Encoding]::UTF8.GetBytes($payload)
```

#### D. Whitespace Differences

**Problem**: JSON formatting adds/removes spaces

**Solution**:

```powershell
# Store payload as single string, use everywhere
$payload = @{...} | ConvertTo-Json -Depth 10 -Compress

# Use this EXACT string for:
# 1. Computing signature
# 2. Request body
```

### Issue 2: CloudWatch Shows Signature Mismatch

**Check CloudWatch Logs**:

```powershell
# View recent logs
aws logs tail /aws/lambda/JiraWebhookFunction --since 5m --follow
```

**Look for**:

```
Invalid signature provided
Expected: sha256=abc123...
Received: sha256=xyz789...
```

**Debug Steps**:

1. **Print what you're signing**:

```powershell
Write-Host "Payload for signature:"
Write-Host $payload
Write-Host "Payload length: $($payload.Length)"
```

2. **Print the signature**:

```powershell
Write-Host "Generated signature: $signature"
```

3. **Verify Lambda uses same secret**:

```powershell
# Check Lambda environment or Secrets Manager
aws lambda get-function-configuration `
    --function-name JiraWebhookFunction `
    --query 'Environment.Variables.GITHUB_TOKEN_SECRET_NAME'
```

### Issue 3: Signature Format Wrong

**Correct Format**:

```
sha256=a1b2c3d4e5f6789012345678901234567890abcdef...
```

**Common Mistakes**:

```powershell
# ❌ WRONG: No prefix
$signature = $signatureHex

# ❌ WRONG: Wrong prefix
$signature = "SHA256=$signatureHex"

# ❌ WRONG: Uppercase hex
$signature = "sha256=$($signatureHex.ToUpper())"

# ✅ CORRECT: Lowercase hex with sha256 prefix
$signature = "sha256=$($signatureHex.ToLower())"
```

### Issue 4: Request Body Different from Signed Payload

**Problem**: You sign one payload but send different payload

**Bad Example**:

```powershell
# ❌ WRONG
$payload1 = $data | ConvertTo-Json
$signature = Get-Signature $payload1

$payload2 = $data | ConvertTo-Json -Compress  # Different format!
Invoke-WebRequest -Body $payload2  # Signature won't match!
```

**Good Example**:

```powershell
# ✅ CORRECT
$payload = $data | ConvertTo-Json -Depth 10
$signature = Get-Signature $payload
Invoke-WebRequest -Body $payload  # Same payload!
```

---

## Complete Examples

### Example 1: Simple Valid Signature Test

```powershell
# Configuration
$url = "https://abc123.execute-api.us-east-1.amazonaws.com/Prod/webhook"
$secret = "my_webhook_secret_12345"

# Payload (keep as string)
$payload = '{"issue":{"key":"TEST-1","fields":{"summary":"Test","labels":["sync-to-github"]}}}'

# Generate signature
$hmac = New-Object System.Security.Cryptography.HMACSHA256
$hmac.Key = [Text.Encoding]::UTF8.GetBytes($secret)
$hash = $hmac.ComputeHash([Text.Encoding]::UTF8.GetBytes($payload))
$sig = "sha256=" + [BitConverter]::ToString($hash).Replace("-", "").ToLower()

# Send request
Invoke-WebRequest -Uri $url -Method POST -Headers @{"X-Hub-Signature"=$sig} -Body $payload -ContentType "application/json"
```

### Example 2: Complete Test with Error Handling

```powershell
function Test-WebhookWithValidSignature {
    param(
        [string]$WebhookUrl,
        [string]$Secret
    )

    Write-Host "Testing webhook with valid signature..." -ForegroundColor Cyan

    # Create payload
    $payload = @{
        issue = @{
            key = "TEST-001"
            fields = @{
                summary = "Valid Signature Test"
                description = "This request has a valid HMAC signature"
                labels = @("sync-to-github", "test")
            }
        }
    } | ConvertTo-Json -Depth 10

    # Generate signature
    try {
        $hmac = New-Object System.Security.Cryptography.HMACSHA256
        $hmac.Key = [Text.Encoding]::UTF8.GetBytes($Secret)
        $hash = $hmac.ComputeHash([Text.Encoding]::UTF8.GetBytes($payload))
        $signature = "sha256=" + [BitConverter]::ToString($hash).Replace("-", "").ToLower()

        Write-Host "✓ Signature generated" -ForegroundColor Green
        Write-Host "  $($signature.Substring(0, 40))..." -ForegroundColor Gray

    } catch {
        Write-Host "✗ Failed to generate signature: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }

    # Send request
    try {
        $headers = @{
            "X-Hub-Signature" = $signature
            "Content-Type" = "application/json"
        }

        $response = Invoke-WebRequest `
            -Uri $WebhookUrl `
            -Method POST `
            -Headers $headers `
            -Body $payload `
            -ErrorAction Stop

        Write-Host "✓ Request successful" -ForegroundColor Green
        Write-Host "  Status: $($response.StatusCode)" -ForegroundColor Gray
        Write-Host "  Response: $($response.Content)" -ForegroundColor Gray

        return $true

    } catch {
        Write-Host "✗ Request failed" -ForegroundColor Red
        Write-Host "  Status: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
        Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red

        return $false
    }
}

# Usage
$secret = (aws secretsmanager get-secret-value --secret-id jira-github-webhook-secret --query SecretString --output text | ConvertFrom-Json).webhook_secret

Test-WebhookWithValidSignature `
    -WebhookUrl "https://your-url.amazonaws.com/Prod/webhook" `
    -Secret $secret
```

### Example 3: Comparing Valid vs Invalid Signatures

```powershell
$url = "https://your-url.amazonaws.com/Prod/webhook"
$secret = "your_secret"
$payload = '{"issue":{"key":"TEST-1","fields":{"summary":"Test"}}}'

Write-Host "`n=== SIGNATURE COMPARISON TEST ===" -ForegroundColor Cyan

# Generate VALID signature
$hmac = New-Object System.Security.Cryptography.HMACSHA256
$hmac.Key = [Text.Encoding]::UTF8.GetBytes($secret)
$hash = $hmac.ComputeHash([Text.Encoding]::UTF8.GetBytes($payload))
$validSig = "sha256=" + [BitConverter]::ToString($hash).Replace("-", "").ToLower()

Write-Host "`nValid Signature:   $validSig"

# Create INVALID signature
$invalidSig = "sha256=0000000000000000000000000000000000000000000000000000000000000000"

Write-Host "Invalid Signature: $invalidSig"

# Test with INVALID signature (should fail)
Write-Host "`n[Test 1] Sending with INVALID signature..." -ForegroundColor Yellow
try {
    Invoke-WebRequest -Uri $url -Method POST -Headers @{"X-Hub-Signature"=$invalidSig} -Body $payload -ContentType "application/json" -ErrorAction Stop
    Write-Host "  Result: ❌ ACCEPTED (Bad! Should reject)" -ForegroundColor Red
} catch {
    Write-Host "  Result: ✅ REJECTED (Good!)" -ForegroundColor Green
    Write-Host "  Status: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Gray
}

# Test with VALID signature (should succeed)
Write-Host "`n[Test 2] Sending with VALID signature..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri $url -Method POST -Headers @{"X-Hub-Signature"=$validSig} -Body $payload -ContentType "application/json" -ErrorAction Stop
    Write-Host "  Result: ✅ ACCEPTED (Good!)" -ForegroundColor Green
    Write-Host "  Status: $($response.StatusCode)" -ForegroundColor Gray
} catch {
    Write-Host "  Result: ❌ REJECTED (Bad! Should accept)" -ForegroundColor Red
    Write-Host "  Status: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Gray
}

Write-Host "`n=== TEST COMPLETE ===" -ForegroundColor Cyan
```

---

## Summary

### Quick Reference

**To test with a valid signature, you need**:

1. ✅ Webhook URL
2. ✅ Webhook Secret (from Secrets Manager)
3. ✅ Test Payload (JSON)

**Steps**:

1. Create payload as JSON string
2. Generate HMAC SHA-256 hash of payload using secret
3. Format as `sha256=<hex>`
4. Send request with `X-Hub-Signature` header

**PowerShell One-Liner**:

```powershell
$payload='{"issue":{"key":"TEST-1","fields":{"summary":"Test","labels":["sync-to-github"]}}}'; $hmac=New-Object System.Security.Cryptography.HMACSHA256; $hmac.Key=[Text.Encoding]::UTF8.GetBytes("YOUR_SECRET"); $sig="sha256="+[BitConverter]::ToString($hmac.ComputeHash([Text.Encoding]::UTF8.GetBytes($payload))).Replace("-","").ToLower(); Invoke-WebRequest -Uri "YOUR_URL" -Method POST -Headers @{"X-Hub-Signature"=$sig} -Body $payload -ContentType "application/json"
```

**Or use the provided script**:

```powershell
.\test-security.ps1 -WebhookUrl "YOUR_URL" -JiraSecret "YOUR_SECRET"
```

This will automatically test all scenarios including valid signatures!
