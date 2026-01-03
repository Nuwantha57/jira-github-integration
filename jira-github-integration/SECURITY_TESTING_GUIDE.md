# Security Testing Guide

## Overview

This guide provides step-by-step instructions for performing comprehensive security testing on the Jira-GitHub integration webhook endpoint. Security testing ensures that only authorized requests from your specific Jira instance can create GitHub issues.

---

## Table of Contents

1. [Security Architecture](#security-architecture)
2. [Prerequisites](#prerequisites)
3. [Test Environment Setup](#test-environment-setup)
4. [Security Test Scenarios](#security-test-scenarios)
5. [Running Security Tests](#running-security-tests)
6. [Validating Results](#validating-results)
7. [Common Security Issues](#common-security-issues)
8. [Best Practices](#best-practices)

---

## Security Architecture

### Multi-Layer Security Model

The integration implements defense-in-depth with multiple security layers:

```
┌─────────────────────────────────────────────────────┐
│ Layer 1: HTTPS Encryption                           │
│ ✓ All traffic encrypted in transit                  │
└─────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────┐
│ Layer 2: API Gateway URL Obfuscation                │
│ ✓ Long, random, hard-to-guess URL                   │
└─────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────┐
│ Layer 3: Jira Instance Validation                   │
│ ✓ Validates webhook is from YOUR Jira instance      │
│ ✓ Checks X-Atlassian-Webhook-Identifier header      │
│ ✓ Validates User-Agent, Referer, Origin             │
└─────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────┐
│ Layer 4: HMAC Signature Verification (Optional)     │
│ ✓ Validates X-Hub-Signature header                  │
│ ✓ Uses webhook_secret from Secrets Manager          │
└─────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────┐
│ Layer 5: Business Logic Validation                  │
│ ✓ Only processes issues with sync-to-github label   │
│ ✓ Validates payload structure                       │
└─────────────────────────────────────────────────────┘
```

### What Each Layer Protects Against

| Layer           | Protects Against            | Attack Vectors Prevented               |
| --------------- | --------------------------- | -------------------------------------- |
| HTTPS           | Man-in-the-middle attacks   | Eavesdropping, packet sniffing         |
| URL Obfuscation | Brute force discovery       | Random scanning, URL guessing          |
| Jira Validation | Unauthorized Jira instances | Spoofed webhooks, other Jira instances |
| HMAC Signatures | Request tampering           | Modified payloads, replay attacks      |
| Business Logic  | Unwanted processing         | Unnecessary API calls, resource abuse  |

---

## Prerequisites

### Required Information

Before starting security testing, gather the following:

1. **Webhook URL**: Your deployed API Gateway endpoint

   ```
   https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/Prod/webhook
   ```

2. **Jira Base URL**: Your Jira instance URL

   ```
   https://your-company.atlassian.net
   ```

3. **Webhook Secret** (if implemented): From AWS Secrets Manager

   ```powershell
   # Retrieve from Secrets Manager
   aws secretsmanager get-secret-value --secret-id jira-github-webhook-secret
   ```

4. **AWS Credentials**: For accessing CloudWatch logs

5. **PowerShell**: Version 5.1+ or PowerShell Core 7+

### Required Tools

- PowerShell
- AWS CLI (configured with credentials)
- Access to AWS CloudWatch Logs
- Text editor for reviewing logs

### Permissions Needed

- Read access to AWS Secrets Manager
- Read access to CloudWatch Logs
- Execute access to deployed Lambda function (via API Gateway)

---

## Test Environment Setup

### Step 1: Verify Lambda Deployment

```powershell
# Check Lambda function exists and is active
aws lambda get-function --function-name JiraWebhookFunction

# Check recent invocations
aws lambda get-function --function-name JiraWebhookFunction --query 'Configuration.LastModified'
```

### Step 2: Verify Environment Variables

```powershell
# Check Lambda environment variables
aws lambda get-function-configuration --function-name JiraWebhookFunction --query 'Environment.Variables'
```

Expected variables:

- `GITHUB_TOKEN_SECRET_NAME`: Name of secret containing GitHub token
- `JIRA_BASE_URL`: Your Jira instance URL
- `GITHUB_OWNER`: GitHub username/organization
- `GITHUB_REPO`: Repository name

### Step 3: Prepare Test Script

The `test-security.ps1` script is already provided in your workspace. Review it:

```powershell
# View the script
Get-Content .\test-security.ps1
```

### Step 4: Set Up CloudWatch Monitoring

Open CloudWatch Logs in AWS Console or use CLI:

```powershell
# Start tailing logs in a separate PowerShell window
aws logs tail /aws/lambda/JiraWebhookFunction --follow
```

---

## Security Test Scenarios

### Test 1: Missing Authentication Header

**Purpose**: Verify that requests without any authentication are rejected

**Expected Behavior**:

- HTTP Status: `401 Unauthorized` or `403 Forbidden`
- No GitHub issue created
- Security violation logged in CloudWatch

**Attack Scenario Simulated**:

- Random attacker discovers webhook URL
- Sends request without proper headers
- System should reject immediately

**What to Check**:

- [ ] Response status is 401 or 403
- [ ] Response body doesn't leak sensitive information
- [ ] CloudWatch logs show "Missing authentication header" or similar
- [ ] No GitHub API calls made

---

### Test 2: Invalid Signature

**Purpose**: Verify that requests with tampered or incorrect signatures are rejected

**Expected Behavior**:

- HTTP Status: `401 Unauthorized` or `403 Forbidden`
- No GitHub issue created
- Invalid signature logged in CloudWatch

**Attack Scenario Simulated**:

- Attacker intercepts legitimate webhook
- Modifies payload to create different issue
- Signature no longer matches payload
- System should detect and reject

**What to Check**:

- [ ] Response status is 401 or 403
- [ ] Error message indicates signature mismatch
- [ ] CloudWatch logs show "Invalid signature" or "Signature verification failed"
- [ ] No GitHub API calls made

---

### Test 3: Valid Signature (Authorized Request)

**Purpose**: Verify that legitimate requests with proper authentication are accepted

**Expected Behavior**:

- HTTP Status: `200 OK`
- Request processed successfully
- GitHub issue created (if payload is valid)
- Success logged in CloudWatch

**Legitimate Scenario**:

- Request from your Jira instance
- Proper headers and signature
- Valid payload structure
- System should process normally

**What to Check**:

- [ ] Response status is 200
- [ ] Response body confirms processing
- [ ] CloudWatch logs show successful authentication
- [ ] GitHub issue created (if sync-to-github label present)

---

### Test 4: Malformed JSON Payload

**Purpose**: Verify that requests with invalid JSON are rejected gracefully

**Expected Behavior**:

- HTTP Status: `400 Bad Request`
- Error message indicates JSON parsing error
- No GitHub issue created
- Error logged appropriately

**Attack Scenario Simulated**:

- Attacker sends malformed data
- Attempts to exploit JSON parser
- System should handle gracefully

**What to Check**:

- [ ] Response status is 400
- [ ] Error message is clear but not revealing
- [ ] No Lambda crashes or unhandled exceptions
- [ ] CloudWatch logs show JSON parsing error

---

### Test 5: Jira Instance Validation

**Purpose**: Verify that only YOUR specific Jira instance can send webhooks

**Expected Behavior**:

- Requests from your Jira: `200 OK`
- Requests from other Jira instances: `401 Unauthorized`
- Requests without Jira headers: `401 Unauthorized`

**Attack Scenario Simulated**:

- Different Jira instance tries to use your webhook
- Attacker spoofs Jira headers
- System validates source domain

**What to Check**:

- [ ] Requests with correct Jira domain accepted
- [ ] Requests from different Jira domain rejected
- [ ] CloudWatch logs show instance validation
- [ ] User-Agent, Referer, Origin headers checked

---

## Running Security Tests

### Automated Testing with PowerShell Script

#### Basic Security Test (Without Signature Verification)

```powershell
# Test unauthorized access attempts
.\test-security.ps1 -WebhookUrl "https://your-api-gateway-url.execute-api.us-east-1.amazonaws.com/Prod/webhook"
```

**What This Tests**:

- Missing signature header
- Invalid signature
- Malformed JSON

**Expected Output**:

```
=== SECURITY TESTING ===

[Test 1] Testing without signature header...
Status: 401
PASS: Correctly rejected unauthorized request

[Test 2] Testing with invalid signature...
Status: 401
PASS: Correctly rejected invalid signature

[Test 4] Testing with malformed JSON...
Status: 400
PASS: Correctly rejected malformed JSON

=== SECURITY TESTING COMPLETE ===
```

#### Full Security Test (With Signature Verification)

```powershell
# Retrieve webhook secret from Secrets Manager
$secret = aws secretsmanager get-secret-value --secret-id jira-github-webhook-secret --query SecretString --output text | ConvertFrom-Json
$webhookSecret = $secret.webhook_secret

# Run full security test suite
.\test-security.ps1 `
    -WebhookUrl "https://your-api-gateway-url.execute-api.us-east-1.amazonaws.com/Prod/webhook" `
    -JiraSecret $webhookSecret
```

**What This Tests**:

- Missing signature header
- Invalid signature
- **Valid signature (should succeed)**
- Malformed JSON

**Expected Output**:

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
PASS: Valid signature accepted

[Test 4] Testing with malformed JSON...
Status: 400
PASS: Correctly rejected malformed JSON

=== SECURITY TESTING COMPLETE ===
```

### Manual Testing with cURL or Invoke-WebRequest

#### Test 1: No Authentication Header

```powershell
$payload = @{
    issue = @{
        key = "TEST-001"
        fields = @{
            summary = "Test Issue"
            description = "Security test"
            labels = @("sync-to-github")
        }
    }
} | ConvertTo-Json -Depth 10

# Send request without authentication
Invoke-WebRequest `
    -Uri "https://your-webhook-url.execute-api.us-east-1.amazonaws.com/Prod/webhook" `
    -Method POST `
    -Body $payload `
    -ContentType "application/json"
```

**Expected Result**: Error with 401 status code

#### Test 2: Invalid Signature

```powershell
# Send request with fake signature
$headers = @{
    "X-Hub-Signature" = "sha256=this_is_a_fake_signature_12345"
}

Invoke-WebRequest `
    -Uri "https://your-webhook-url.execute-api.us-east-1.amazonaws.com/Prod/webhook" `
    -Method POST `
    -Headers $headers `
    -Body $payload `
    -ContentType "application/json"
```

**Expected Result**: Error with 401 status code

#### Test 3: Valid Signature

```powershell
# Generate valid HMAC signature
$secret = "your_webhook_secret"
$hmac = New-Object System.Security.Cryptography.HMACSHA256
$hmac.Key = [Text.Encoding]::UTF8.GetBytes($secret)
$hash = $hmac.ComputeHash([Text.Encoding]::UTF8.GetBytes($payload))
$signature = "sha256=" + [BitConverter]::ToString($hash).Replace("-", "").ToLower()

# Send request with valid signature
$headers = @{
    "X-Hub-Signature" = $signature
}

Invoke-WebRequest `
    -Uri "https://your-webhook-url.execute-api.us-east-1.amazonaws.com/Prod/webhook" `
    -Method POST `
    -Headers $headers `
    -Body $payload `
    -ContentType "application/json"
```

**Expected Result**: Success with 200 status code

---

## Validating Results

### 1. Check HTTP Response Codes

| Test Scenario       | Expected Status Code | Pass/Fail Criteria           |
| ------------------- | -------------------- | ---------------------------- |
| No signature header | 401 or 403           | PASS if 401/403, FAIL if 200 |
| Invalid signature   | 401 or 403           | PASS if 401/403, FAIL if 200 |
| Valid signature     | 200                  | PASS if 200, FAIL if 401/403 |
| Malformed JSON      | 400                  | PASS if 400, FAIL if 200     |
| Wrong Jira instance | 401 or 403           | PASS if 401/403, FAIL if 200 |

### 2. Review CloudWatch Logs

#### View Recent Logs

```powershell
# View last 50 log events
aws logs tail /aws/lambda/JiraWebhookFunction --since 10m --format short
```

#### Look for Security Events

**Successful Authentication**:

```
Webhook authenticated successfully
Processing webhook: TEST-001
```

**Failed Authentication - Missing Header**:

```
Missing authentication header: X-Hub-Signature
Returning 401 Unauthorized
```

**Failed Authentication - Invalid Signature**:

```
Invalid signature provided
Expected: sha256=abc123...
Received: sha256=xyz789...
Returning 401 Unauthorized
```

**Jira Instance Validation Failed**:

```
Webhook not from trusted Jira instance
User-Agent: SomeOtherService/1.0
Expected domain: your-company.atlassian.net
Returning 401 Unauthorized
```

### 3. Verify No GitHub Issues Created

For unauthorized requests, verify no issues were created:

```powershell
# Check recent GitHub issues
gh issue list --repo your-username/your-repo --limit 10

# Or use GitHub API
curl -H "Authorization: token your_github_token" \
  https://api.github.com/repos/your-username/your-repo/issues?state=all&per_page=10
```

**Expected**: No new issues created during failed security tests

### 4. Check Metrics

#### Lambda Invocations

```powershell
# Check Lambda invocation count
aws cloudwatch get-metric-statistics `
    --namespace AWS/Lambda `
    --metric-name Invocations `
    --dimensions Name=FunctionName,Value=JiraWebhookFunction `
    --start-time (Get-Date).AddMinutes(-15).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") `
    --end-time (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") `
    --period 60 `
    --statistics Sum
```

#### Lambda Errors

```powershell
# Check for errors during test period
aws cloudwatch get-metric-statistics `
    --namespace AWS/Lambda `
    --metric-name Errors `
    --dimensions Name=FunctionName,Value=JiraWebhookFunction `
    --start-time (Get-Date).AddMinutes(-15).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") `
    --end-time (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") `
    --period 60 `
    --statistics Sum
```

**Expected**:

- Invocations: Count matches number of test requests
- Errors: 0 (rejected requests should not cause errors, just return 401)

---

## Common Security Issues

### Issue 1: All Requests Returning 200 (Accepting Unauthorized)

**Symptom**: Test 1 and Test 2 both return 200 status code

**Cause**: Signature verification not implemented or bypassed

**Fix**:

1. Check Lambda code has signature verification enabled
2. Verify `JIRA_BASE_URL` environment variable is set
3. Check authentication logic is not commented out

**Verification**:

```powershell
# Check Lambda code
aws lambda get-function --function-name JiraWebhookFunction --query 'Code.Location' --output text | % { Invoke-WebRequest $_ -OutFile lambda.zip }
```

### Issue 2: Valid Signature Returning 401 (Rejecting Authorized)

**Symptom**: Test 3 fails - valid signature rejected

**Possible Causes**:

1. Incorrect webhook secret
2. Signature algorithm mismatch
3. Payload encoding issue
4. Jira instance validation too strict

**Debugging Steps**:

```powershell
# Verify secret in Secrets Manager
aws secretsmanager get-secret-value --secret-id jira-github-webhook-secret

# Check CloudWatch logs for signature comparison
aws logs filter-log-events `
    --log-group-name /aws/lambda/JiraWebhookFunction `
    --filter-pattern "signature" `
    --start-time (Get-Date).AddMinutes(-15).Ticks
```

**Common Fixes**:

- Ensure secret matches between test script and Secrets Manager
- Verify payload is UTF-8 encoded before signing
- Check header name is exactly `X-Hub-Signature` (case-sensitive)
- Verify signature format is `sha256=<hex_string>`

### Issue 3: Error Messages Reveal Sensitive Information

**Symptom**: Error responses contain stack traces, file paths, or token values

**Security Risk**: Information leakage aids attackers

**Fix**:

- Review Lambda code for proper error handling
- Ensure try-catch blocks return generic errors to client
- Log detailed errors only to CloudWatch (not in response)

**Example Secure Error Handling**:

```python
try:
    # Verify signature
    if not verify_signature(payload, signature, secret):
        logger.error(f"Invalid signature: {signature}")  # Log details
        return {
            'statusCode': 401,
            'body': json.dumps({'error': 'Unauthorized'})  # Generic error
        }
except Exception as e:
    logger.error(f"Error: {str(e)}", exc_info=True)  # Log full error
    return {
        'statusCode': 500,
        'body': json.dumps({'error': 'Internal server error'})  # Generic error
    }
```

### Issue 4: No Logs in CloudWatch

**Symptom**: Tests run but no logs appear in CloudWatch

**Possible Causes**:

1. Lambda doesn't have CloudWatch Logs permission
2. Looking at wrong log group
3. Log retention expired

**Fix**:

```powershell
# Check Lambda execution role has logging permission
aws lambda get-function --function-name JiraWebhookFunction --query 'Configuration.Role'

# List all log groups
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/

# Check Lambda IAM role has CloudWatch Logs policy
aws iam get-role-policy --role-name YourLambdaExecutionRole --policy-name CloudWatchLogsPolicy
```

---

## Best Practices

### 1. Test in Non-Production First

Always run security tests against a staging/development environment before production:

```
Development → Security Testing → Staging → Security Testing → Production
```

### 2. Rotate Secrets Regularly

```powershell
# Generate new webhook secret
$newSecret = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | % {[char]$_})

# Update in Secrets Manager
aws secretsmanager update-secret `
    --secret-id jira-github-webhook-secret `
    --secret-string "{`"webhook_secret`":`"$newSecret`"}"

# Update in Jira webhook configuration
# Then re-test
```

### 3. Monitor Security Metrics

Set up CloudWatch alarms for security events:

```powershell
# Create alarm for high rate of 401 responses
aws cloudwatch put-metric-alarm `
    --alarm-name JiraWebhook-HighUnauthorizedRate `
    --alarm-description "Alert when too many unauthorized requests detected" `
    --metric-name Invocations `
    --namespace AWS/Lambda `
    --statistic Sum `
    --period 300 `
    --evaluation-periods 1 `
    --threshold 10 `
    --comparison-operator GreaterThanThreshold
```

### 4. Document Test Results

After each security test, document:

```markdown
## Security Test Results - [Date]

**Environment**: Staging/Production
**Tester**: [Your Name]
**Duration**: [Test Duration]

### Test Results

| Test # | Scenario          | Expected | Actual | Status  |
| ------ | ----------------- | -------- | ------ | ------- |
| 1      | No auth header    | 401      | 401    | ✅ PASS |
| 2      | Invalid signature | 401      | 401    | ✅ PASS |
| 3      | Valid signature   | 200      | 200    | ✅ PASS |
| 4      | Malformed JSON    | 400      | 400    | ✅ PASS |

### Issues Found

- None

### Actions Taken

- All tests passed
- No vulnerabilities detected
- Ready for production deployment

### Next Test Date

- [Next scheduled test date]
```

### 5. Keep Test Scripts Updated

When you modify security implementation:

1. Update test scripts to match
2. Add new test cases for new security features
3. Update this documentation
4. Re-run full test suite

### 6. Principle of Least Privilege

Ensure Lambda has only necessary permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": "arn:aws:secretsmanager:us-east-1:123456789012:secret:jira-github-webhook-secret-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:us-east-1:123456789012:log-group:/aws/lambda/JiraWebhookFunction:*"
    }
  ]
}
```

---

## Security Testing Checklist

Use this checklist for each security test run:

### Pre-Test

- [ ] Lambda function deployed and running
- [ ] Environment variables configured correctly
- [ ] Webhook secret stored in Secrets Manager
- [ ] CloudWatch logs accessible
- [ ] Test scripts downloaded and reviewed
- [ ] Non-production environment (if first test)

### During Test

- [ ] Monitor CloudWatch logs in real-time
- [ ] Record all HTTP response codes
- [ ] Note any unexpected behaviors
- [ ] Check GitHub for unauthorized issue creation
- [ ] Monitor Lambda metrics

### Test Execution

- [ ] Test 1: Missing auth header → 401 ✅
- [ ] Test 2: Invalid signature → 401 ✅
- [ ] Test 3: Valid signature → 200 ✅
- [ ] Test 4: Malformed JSON → 400 ✅
- [ ] Test 5: Wrong Jira instance → 401 ✅

### Post-Test

- [ ] Review all CloudWatch logs
- [ ] Verify no unauthorized GitHub issues created
- [ ] Check for any error messages or exceptions
- [ ] Document results
- [ ] Update security documentation if needed
- [ ] Plan remediation for any failures

### Sign-Off

- [ ] All tests passed
- [ ] No security vulnerabilities detected
- [ ] Results documented
- [ ] Approved for production (if applicable)

**Tested by**: ******\_\_\_******  
**Date**: ******\_\_\_******  
**Approved by**: ******\_\_\_******  
**Date**: ******\_\_\_******

---

## Conclusion

Security testing is critical for protecting your webhook endpoint from unauthorized access. By following this guide and regularly running security tests, you ensure that:

✅ Only your Jira instance can create GitHub issues  
✅ Unauthorized requests are properly rejected  
✅ Sensitive information is not leaked  
✅ The system handles errors gracefully  
✅ Monitoring and logging capture security events

**Remember**: Security is an ongoing process. Retest after any code changes, infrastructure updates, or when security concerns arise.

---

## Additional Resources

- [TESTING_GUIDE.md](TESTING_GUIDE.md) - Complete testing guide including load and integration tests
- [SECURITY_ENHANCEMENT.md](SECURITY_ENHANCEMENT.md) - Details on security architecture
- [DEPLOYMENT_SECURITY.md](DEPLOYMENT_SECURITY.md) - Security considerations for deployment
- [test-security.ps1](test-security.ps1) - Automated security test script

For questions or issues, review CloudWatch logs first, then consult the troubleshooting section above.
