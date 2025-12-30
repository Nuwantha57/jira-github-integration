# Security & Final Testing Guide

## Overview

This guide covers testing procedures for the Jira-GitHub integration security features and performance validation.

## Prerequisites

1. **AWS Lambda Deployed**: Your Lambda function must be deployed and accessible
2. **API Gateway Configured**: Webhook endpoint URL available
3. **Secrets Manager**: GitHub token stored in AWS Secrets Manager
4. **GitHub Access**: Personal access token with repo permissions
5. **PowerShell**: Windows PowerShell 5.1 or PowerShell Core 7+

## Test Categories

### 1. Security Testing (Unauthorized Access)

**Purpose**: Verify webhook signature verification prevents unauthorized requests

**Test Script**: `test-security.ps1`

**Usage**:

```powershell
# Without signature verification (if not implemented yet)
.\test-security.ps1 -WebhookUrl "https://your-api-gateway-url.amazonaws.com/webhook"

# With signature verification
.\test-security.ps1 -WebhookUrl "https://your-api-gateway-url.amazonaws.com/webhook" -JiraSecret "your_webhook_secret"
```

**Expected Results**:

- ❌ **Test 1**: Request without signature → **401/403 Unauthorized**
- ❌ **Test 2**: Request with invalid signature → **401/403 Unauthorized**
- ✅ **Test 3**: Request with valid signature → **200 OK**
- ❌ **Test 4**: Malformed JSON → **400 Bad Request**

**What to Check**:

- [ ] All unauthorized attempts are properly rejected
- [ ] Error messages don't leak sensitive information
- [ ] CloudWatch logs show security violations
- [ ] No GitHub issues created from unauthorized requests

---

### 2. Load Testing (Performance)

**Purpose**: Test system behavior under concurrent load

**Test Script**: `test-load.ps1`

**Usage**:

```powershell
# Test with 25 concurrent requests (default)
.\test-load.ps1 -WebhookUrl "https://your-api-gateway-url.amazonaws.com/webhook"

# Test with 30 concurrent requests
.\test-load.ps1 -WebhookUrl "https://your-api-gateway-url.amazonaws.com/webhook" -ConcurrentRequests 30

# With signature verification
.\test-load.ps1 -WebhookUrl "https://your-api-gateway-url.amazonaws.com/webhook" `
    -ConcurrentRequests 25 `
    -JiraSecret "your_webhook_secret"
```

**Performance Targets**:

- **Success Rate**: > 95% (19+ out of 20 requests successful)
- **Average Response Time**: < 3000ms
- **Max Response Time**: < 10000ms
- **No Timeouts**: All requests complete within 30s
- **Throughput**: Handle 20-30 concurrent webhooks

**What to Monitor**:

- [ ] Lambda concurrent executions (CloudWatch)
- [ ] API Gateway throttling errors
- [ ] Lambda duration and memory usage
- [ ] GitHub API rate limits
- [ ] Secrets Manager API calls

**CloudWatch Metrics to Check**:

```bash
# View Lambda metrics
aws cloudwatch get-metric-statistics \
    --namespace AWS/Lambda \
    --metric-name Duration \
    --dimensions Name=FunctionName,Value=your-function-name \
    --start-time 2025-12-30T00:00:00Z \
    --end-time 2025-12-30T23:59:59Z \
    --period 3600 \
    --statistics Average,Maximum
```

**Load Test Scenarios**:

1. **Baseline Test** (10 requests)

   - Verify system works under light load
   - Establish baseline metrics

2. **Standard Load** (25 requests)

   - Simulate typical busy period
   - All requests should succeed

3. **Stress Test** (30+ requests)

   - Test system limits
   - Identify breaking points

4. **Sustained Load** (Run multiple times)
   - Run test 5 times consecutively
   - Check for memory leaks or degradation

---

### 3. End-to-End Integration Testing

**Purpose**: Validate complete workflow from Jira webhook to GitHub issue creation

**Test Script**: `test-integration.ps1`

**Usage**:

```powershell
.\test-integration.ps1 `
    -WebhookUrl "https://your-api-gateway-url.amazonaws.com/webhook" `
    -GitHubToken "ghp_your_github_token" `
    -GitHubOwner "your-github-username" `
    -GitHubRepo "your-repo-name" `
    -JiraSecret "your_webhook_secret" `
    -JiraBaseUrl "https://your-company.atlassian.net"
```

**Test Scenarios Covered**:

1. **Basic Issue Creation**

   - Simple issue with minimal fields
   - Validates core functionality

2. **Bug with High Priority**

   - Tests label mapping (bug → type:bug)
   - Tests priority mapping (high-priority → priority:high)
   - Tests component mapping (backend → component:backend)

3. **Feature Request**

   - Tests feature label mapping
   - Tests frontend component
   - Tests medium priority

4. **Unassigned Issue**

   - Tests handling of null assignee
   - Should show "Unassigned" in GitHub

5. **Issue Without Description**
   - Tests handling of missing description
   - Should show fallback text

**What to Verify**:

- [ ] GitHub issue created successfully
- [ ] Issue title matches Jira summary
- [ ] Issue body contains Jira link
- [ ] Labels correctly mapped
- [ ] Priority information included
- [ ] Assignee information correct
- [ ] Jira issue key present in body

**Manual Verification Checklist**:
After running automated tests, manually verify:

1. **GitHub Issues**:

   - [ ] Issues appear in correct repository
   - [ ] Formatting is correct (no markdown errors)
   - [ ] Jira links are clickable and work
   - [ ] Labels are properly color-coded
   - [ ] Issues are searchable

2. **Lambda Logs** (CloudWatch):

   - [ ] No error logs for successful requests
   - [ ] Failed requests logged appropriately
   - [ ] Sensitive data not logged (tokens, secrets)

3. **GitHub API**:
   - [ ] Check rate limit usage
   - [ ] Verify no API abuse flags

---

## Test Execution Schedule

### Pre-Deployment Testing

1. Run security tests against staging environment
2. Run integration tests with test Jira/GitHub repos
3. Run small load test (10 requests)

### Post-Deployment Testing

1. Run full security suite
2. Run integration tests with production repos
3. Run full load test (25-30 requests)
4. Monitor for 24 hours

### Ongoing Testing

- Weekly: Run integration tests
- Monthly: Run load tests
- After changes: Run full test suite

---

## Troubleshooting

### Common Issues

**1. All Requests Failing (401/403)**

- Check API Gateway URL is correct
- Verify Lambda has permission to access Secrets Manager
- Check environment variables are set

**2. Timeouts During Load Testing**

- Increase Lambda timeout (default 30s may not be enough)
- Check Lambda memory allocation
- Verify GitHub API is responsive

**3. GitHub Issues Not Created**

- Verify GitHub token has correct permissions
- Check GitHub API rate limits
- Review Lambda CloudWatch logs for errors

**4. Label Mapping Incorrect**

- Verify label mapping in code matches expectations
- Check Jira webhook payload has correct labels

**5. Signature Verification Failing**

- Ensure secret is stored correctly in Secrets Manager
- Verify signature algorithm matches (HMAC SHA-256)
- Check header name is correct (X-Hub-Signature)

---

## Monitoring During Tests

### CloudWatch Dashboard

Create a dashboard to monitor:

- Lambda invocations
- Lambda duration
- Lambda errors
- API Gateway 4xx/5xx errors
- Secrets Manager API calls

### Real-Time Monitoring

```powershell
# Watch Lambda logs in real-time
aws logs tail /aws/lambda/your-function-name --follow

# Filter for errors
aws logs tail /aws/lambda/your-function-name --follow --filter-pattern "ERROR"
```

---

## Test Results Documentation

After each test run, document:

1. Test date/time
2. Environment (staging/production)
3. Test results (pass/fail counts)
4. Performance metrics
5. Issues discovered
6. Actions taken

**Example**:

```
Test Run: 2025-12-30 14:30:00
Environment: Staging
Test Type: Load Test (25 concurrent)

Results:
- Successful: 24/25 (96%)
- Failed: 1/25 (GitHub rate limit)
- Avg Response: 2,345ms
- Max Response: 8,123ms

Issues:
- One request failed due to GitHub rate limit
- Need to implement retry logic

Actions:
- Added exponential backoff for GitHub API
- Increased Lambda timeout to 45s
```

---

## Success Criteria

### Security Testing

- ✅ 100% of unauthorized requests rejected
- ✅ No sensitive data in error messages
- ✅ Proper logging of security events

### Load Testing

- ✅ 95%+ success rate under load
- ✅ Average response time < 3s
- ✅ No Lambda timeouts
- ✅ Stable performance across multiple runs

### Integration Testing

- ✅ All test scenarios pass
- ✅ GitHub issues match Jira data
- ✅ Labels correctly mapped
- ✅ Error handling works properly

---

## Next Steps After Testing

1. **Address Issues**: Fix any bugs discovered
2. **Performance Tuning**: Optimize based on metrics
3. **Documentation**: Update README with findings
4. **Production Readiness**: Sign off on production deployment
5. **Monitoring Setup**: Configure CloudWatch alarms
6. **Incident Response**: Document runbook for issues
