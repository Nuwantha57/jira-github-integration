# Troubleshooting Guide - Jira-GitHub Integration

Complete troubleshooting reference for common issues and solutions.

## Table of Contents
1. [Diagnostic Tools](#diagnostic-tools)
2. [Common Issues](#common-issues)
3. [Error Messages](#error-messages)
4. [Performance Issues](#performance-issues)
5. [Data Issues](#data-issues)
6. [Advanced Debugging](#advanced-debugging)

---

## Diagnostic Tools

### Check System Health

```bash
# 1. Check CloudFormation stack status
aws cloudformation describe-stacks \
    --stack-name jira-github-integration \
    --region YOUR_REGION \
    --query 'Stacks[0].StackStatus'

# 2. View recent Lambda logs
sam logs --stack-name jira-github-integration --tail

# 3. Check DynamoDB table
aws dynamodb describe-table \
    --table-name jira-github-sync-state \
    --region YOUR_REGION

# 4. Verify secrets exist
aws secretsmanager describe-secret \
    --secret-id jira-github-integration \
    --region YOUR_REGION
```

### Test Connections

#### Test GitHub Connection
```bash
# Replace YOUR_TOKEN with actual token
curl -H "Authorization: token YOUR_TOKEN" \
     https://api.github.com/repos/OWNER/REPO

# Expected: Repository details (JSON)
# 404 = Repository not found or token lacks access
# 403 = Token invalid or lacks permissions
```

#### Test Jira Connection
```bash
# Replace with your credentials
curl -u "YOUR_EMAIL:YOUR_TOKEN" \
     "https://YOUR_DOMAIN.atlassian.net/rest/api/3/myself"

# Expected: Your user profile (JSON)
# 401 = Invalid credentials
# 403 = Insufficient permissions
```

#### Test Lambda Function
```bash
# Invoke function directly
sam local invoke JiraWebhookFunction --event events/event.json

# Check exit code
echo $?  # Should be 0 for success
```

---

## Common Issues

### Issue 1: GitHub Issue Not Created

**Symptoms:**
- Jira issue created with `sync-to-github` label
- No GitHub issue appears
- No errors visible in Jira

**Diagnostic Steps:**

1. **Check CloudWatch Logs:**
   ```bash
   sam logs --stack-name jira-github-integration --tail
   ```

2. **Look for these patterns:**
   ```
   ✗ Label 'sync-to-github' not found - Skipping sync
   → Label name mismatch
   
   ✗ GitHub API error 404
   → Repository not found or incorrect name
   
   ✗ GitHub API error 403
   → Token invalid or insufficient permissions
   
   ✗ Already synced: PROJ-123
   → Issue was previously synced (check DynamoDB)
   ```

**Solutions:**

**A. Label Name Mismatch**
```bash
# Check current label in template.yaml
grep "TARGET_LABEL" template.yaml

# Update if needed
# Edit template.yaml: TARGET_LABEL: your-label-name
sam build --use-container && sam deploy
```

**B. GitHub Repository Incorrect**
```bash
# Verify repository exists
curl -H "Authorization: token YOUR_TOKEN" \
     https://api.github.com/repos/OWNER/REPO

# If 404, update template.yaml:
# GITHUB_OWNER: correct-owner
# GITHUB_REPO: correct-repo
sam build --use-container && sam deploy
```

**C. GitHub Token Invalid**
```bash
# Test token permissions
curl -H "Authorization: token YOUR_TOKEN" \
     https://api.github.com/user

# Generate new token if expired:
# GitHub → Settings → Developer settings → Personal access tokens

# Update secret
aws secretsmanager update-secret \
    --secret-id jira-github-integration \
    --secret-string '{"github_token":"NEW_TOKEN","jira_api_token":"EXISTING_TOKEN"}'
```

**D. Duplicate Prevention**
```bash
# Check if already synced
aws dynamodb get-item \
    --table-name jira-github-sync-state \
    --key '{"jira_issue_key":{"S":"PROJ-123"}}'

# If exists, remove to allow re-sync
aws dynamodb delete-item \
    --table-name jira-github-sync-state \
    --key '{"jira_issue_key":{"S":"PROJ-123"}}'
```

---

### Issue 2: Comments Not Syncing

**Symptoms:**
- GitHub issue created successfully
- Comments added in Jira don't appear in GitHub

**Diagnostic Steps:**

1. **Check Webhook Configuration:**
   - Jira → Settings → System → WebHooks
   - Verify "Comment created" event is enabled

2. **Check CloudWatch Logs:**
   ```bash
   sam logs --stack-name jira-github-integration --tail
   ```

3. **Look for:**
   ```
   Comment already synced: Jira 12345 -> GitHub 67890
   → Duplicate prevention working (expected)
   
   GitHub comment created: https://...
   → Success
   
   Failed to create GitHub comment
   → Error (investigate further)
   ```

**Solutions:**

**A. Webhook Event Not Configured**
1. Go to Jira → Settings → System → WebHooks
2. Edit your webhook
3. Ensure these events are checked:
   - ✅ Issue → created
   - ✅ Issue → updated
   - ✅ Comment → created
4. Save

**B. Comment Mapping Corrupted**
```bash
# View comment mappings
aws dynamodb get-item \
    --table-name jira-github-sync-state \
    --key '{"jira_issue_key":{"S":"PROJ-123"}}'

# Clear corrupted mappings
aws dynamodb update-item \
    --table-name jira-github-sync-state \
    --key '{"jira_issue_key":{"S":"PROJ-123"}}' \
    --update-expression "REMOVE comments"
```

**C. Duplicate Prevention**
- Check logs for duplicate prevention messages
- This is expected behavior (prevents duplicate comments)
- Comments are tracked in DynamoDB to prevent re-sync

**Note:** This integration only syncs Jira → GitHub. GitHub comments do NOT sync back to Jira.

---

### Issue 3: User Not Assigned in GitHub

**Symptoms:**
- GitHub issue created
- Description shows "Assignee (Jira): Full Name"
- User not actually assigned in GitHub

**Diagnostic Steps:**

1. **Check User Mapping:**
   ```bash
   # View current mapping
   grep "USER_MAPPING" template.yaml
   ```

2. **Verify GitHub User Exists:**
   ```bash
   # Replace with mapped username
   curl -H "Authorization: token YOUR_TOKEN" \
        https://api.github.com/users/GITHUB_USERNAME
   
   # 404 = User doesn't exist
   # 200 = User exists
   ```

3. **Verify User is Collaborator:**
   ```bash
   curl -H "Authorization: token YOUR_TOKEN" \
        https://api.github.com/repos/OWNER/REPO/collaborators/USERNAME
   
   # 204 = User has access
   # 404 = User doesn't have access
   ```

4. **Check Logs:**
   ```bash
   sam logs --stack-name jira-github-integration --tail | grep "assignee"
   ```

**Solutions:**

**A. User Mapping Not Configured**
```yaml
# Edit template.yaml
Environment:
  Variables:
    USER_MAPPING: "jira.email@example.com:githubusername"

# Redeploy
sam build --use-container && sam deploy
```

**B. User Not Repository Collaborator**
1. Go to GitHub repository
2. Settings → Collaborators
3. Click "Add people"
4. Search for username and add

**C. Format Incorrect**
```yaml
# CORRECT formats:
USER_MAPPING: "email@example.com:githubuser"
USER_MAPPING: "email1@ex.com:user1,email2@ex.com:user2"
USER_MAPPING: "712020:8dcd81ff-57c6:GithubUser"

# WRONG formats:
USER_MAPPING: "email@example.com,githubuser"  # Missing colon
USER_MAPPING: "email@example.com;githubuser"  # Wrong separator
```

---

### Issue 4: Lambda Timeout

**Symptoms:**
- Error: "Task timed out after 30.00 seconds"
- Large issues or many comments fail to sync

**Diagnostic Steps:**

1. **Check Execution Duration:**
   ```bash
   # View CloudWatch metrics
   aws cloudwatch get-metric-statistics \
       --namespace AWS/Lambda \
       --metric-name Duration \
       --dimensions Name=FunctionName,Value=jira-github-integration-JiraWebhookFunction-XXX \
       --start-time 2024-01-01T00:00:00Z \
       --end-time 2024-12-31T23:59:59Z \
       --period 3600 \
       --statistics Average,Maximum
   ```

**Solutions:**

**A. Increase Timeout**
```yaml
# Edit template.yaml
Globals:
  Function:
    Runtime: python3.13
    Timeout: 60  # Increase from 30 to 60 seconds
    MemorySize: 256

# Redeploy
sam build --use-container && sam deploy
```

**B. Increase Memory (speeds up execution)**
```yaml
Globals:
  Function:
    Timeout: 60
    MemorySize: 512  # Increase from 256 to 512 MB
```

**C. Optimize Code (if custom changes made)**
- Reduce API calls
- Implement caching
- Batch operations

---

### Issue 5: DynamoDB Throttling

**Symptoms:**
- Errors: "ProvisionedThroughputExceededException"
- Intermittent sync failures during high volume

**Diagnostic Steps:**

```bash
# Check throttle metrics
aws cloudwatch get-metric-statistics \
    --namespace AWS/DynamoDB \
    --metric-name UserErrors \
    --dimensions Name=TableName,Value=jira-github-sync-state \
    --start-time 2024-01-01T00:00:00Z \
    --end-time 2024-12-31T23:59:59Z \
    --period 3600 \
    --statistics Sum
```

**Solutions:**

**A. Switch to On-Demand Mode (if not already)**
```yaml
# template.yaml (default setting)
JiraGithubSyncTable:
  Type: AWS::DynamoDB::Table
  Properties:
    BillingMode: PAY_PER_REQUEST  # On-demand (recommended)
```

**B. If Using Provisioned Mode**
```yaml
JiraGithubSyncTable:
  Type: AWS::DynamoDB::Table
  Properties:
    BillingMode: PROVISIONED
    ProvisionedThroughput:
      ReadCapacityUnits: 10  # Increase if needed
      WriteCapacityUnits: 10  # Increase if needed
```

---

### Issue 6: Webhook Not Triggering

**Symptoms:**
- Jira issue created with label
- No Lambda invocation (no logs)
- Jira webhook shows failures

**Diagnostic Steps:**

1. **Check Jira Webhook Status:**
   - Jira → Settings → System → WebHooks
   - Click on your webhook
   - View "Recent deliveries"

2. **Common Error Codes:**
   - 404 = Webhook URL incorrect
   - 403 = Authorization issue
   - 500 = Lambda error
   - Timeout = Lambda taking too long

**Solutions:**

**A. Webhook URL Incorrect**
```bash
# Get correct URL
aws cloudformation describe-stacks \
    --stack-name jira-github-integration \
    --query 'Stacks[0].Outputs[?OutputKey==`JiraWebhookUrl`].OutputValue' \
    --output text

# Update in Jira webhook configuration
```

**B. API Gateway Issue**
```bash
# Check API Gateway exists
aws apigateway get-rest-apis --query 'items[?name==`jira-github-integration`]'

# If missing, redeploy
sam build --use-container && sam deploy
```

**C. Test Webhook Manually**
```bash
# Get webhook URL
WEBHOOK_URL=$(aws cloudformation describe-stacks \
    --stack-name jira-github-integration \
    --query 'Stacks[0].Outputs[?OutputKey==`JiraWebhookUrl`].OutputValue' \
    --output text)

# Test with curl
curl -X POST "$WEBHOOK_URL" \
    -H "Content-Type: application/json" \
    -d @events/event.json

# Should return 200 OK
```

---

## Error Messages

### "Secret not found"

```
ClientError: An error occurred (ResourceNotFoundException) when calling the GetSecretValue operation
```

**Cause:** AWS Secrets Manager secret doesn't exist or wrong region

**Solution:**
```bash
# Check if secret exists
aws secretsmanager describe-secret \
    --secret-id jira-github-integration \
    --region YOUR_REGION

# If not found, create it
aws secretsmanager create-secret \
    --name jira-github-integration \
    --secret-string '{"github_token":"TOKEN","jira_api_token":"TOKEN"}' \
    --region YOUR_REGION
```

---

### "403 Forbidden" from GitHub API

```
GitHub API error 403: {"message":"Bad credentials"}
```

**Cause:** Invalid or expired GitHub token

**Solution:**
```bash
# Test token
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user

# Generate new token:
# GitHub → Settings → Developer settings → Personal access tokens
# Scopes: repo, write:discussion

# Update secret
aws secretsmanager update-secret \
    --secret-id jira-github-integration \
    --secret-string '{"github_token":"NEW_TOKEN","jira_api_token":"EXISTING_TOKEN"}'
```

---

### "404 Not Found" from GitHub API

```
GitHub API error 404: {"message":"Not Found"}
```

**Cause:** Repository doesn't exist or token lacks access

**Solution:**
```bash
# Verify repository exists
curl -H "Authorization: token YOUR_TOKEN" \
     https://api.github.com/repos/OWNER/REPO

# If 404, check:
# 1. Repository name spelling
# 2. Repository visibility (private repos need 'repo' scope)
# 3. Token has access to organization repos

# Update template.yaml if needed
GITHUB_OWNER: correct-owner
GITHUB_REPO: correct-repo-name
```

---

### "401 Unauthorized" from Jira API

```
Jira API error 401: {"errorMessages":["Unauthorized"]}
```

**Cause:** Invalid Jira credentials

**Solution:**
```bash
# Test Jira credentials
curl -u "YOUR_EMAIL:YOUR_TOKEN" \
     "https://YOUR_DOMAIN.atlassian.net/rest/api/3/myself"

# If 401:
# 1. Verify email address is correct
# 2. Generate new API token:
#    Jira → Profile → Security → Create API token

# Update secret
aws secretsmanager update-secret \
    --secret-id jira-github-integration \
    --secret-string '{"github_token":"EXISTING_TOKEN","jira_api_token":"NEW_TOKEN"}'
```

---

## Performance Issues

### Slow Sync Times

**Symptoms:** Issues take >10 seconds to sync

**Diagnostic:**
```bash
# Check average duration
sam logs --stack-name jira-github-integration | grep "Duration"
```

**Solutions:**
1. Increase Lambda memory (more memory = more CPU):
   ```yaml
   MemorySize: 512  # Up from 256
   ```

2. Optimize user mapping (use account IDs instead of email lookups)

3. Review network connectivity (Lambda VPC configuration if applicable)

---

### High Costs

**Symptoms:** AWS bill higher than expected

**Diagnostic:**
```bash
# Check Lambda invocations
aws cloudwatch get-metric-statistics \
    --namespace AWS/Lambda \
    --metric-name Invocations \
    --dimensions Name=FunctionName,Value=jira-github-integration-JiraWebhookFunction-XXX \
    --start-time 2024-01-01T00:00:00Z \
    --end-time 2024-01-31T23:59:59Z \
    --period 86400 \
    --statistics Sum
```

**Solutions:**
1. Implement stricter JQL filter in Jira webhook
2. Set CloudWatch Logs retention (default: Never expire)
   ```bash
   aws logs put-retention-policy \
       --log-group-name /aws/lambda/jira-github-integration-JiraWebhookFunction-XXX \
       --retention-in-days 30
   ```

3. Review DynamoDB usage (should be minimal with on-demand pricing)

---

## Data Issues

### Duplicate GitHub Issues

**Cause:** DynamoDB sync state not working

**Solution:**
```bash
# Check sync state
aws dynamodb scan --table-name jira-github-sync-state

# Delete duplicate entry
aws dynamodb delete-item \
    --table-name jira-github-sync-state \
    --key '{"jira_issue_key":{"S":"PROJ-123"}}'

# Delete duplicate GitHub issue manually
# Sync will work correctly after clearing state
```

---

### Missing Comments

**Cause:** Comment mapping corrupted or webhook delayed

**Solution:**
```bash
# Check comment mappings
aws dynamodb get-item \
    --table-name jira-github-sync-state \
    --key '{"jira_issue_key":{"S":"PROJ-123"}}'

# Look for "comments" attribute
# If missing or corrupted, remove and re-sync:
aws dynamodb update-item \
    --table-name jira-github-sync-state \
    --key '{"jira_issue_key":{"S":"PROJ-123"}}' \
    --update-expression "REMOVE comments"

# Add comments again in Jira to trigger re-sync
```

---

## Advanced Debugging

### Enable Detailed Logging

Add debug logging to Lambda function:

```python
# Edit jira_handler/app.py
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Add debug statements
logger.debug(f"Received event: {json.dumps(event)}")
```

Redeploy:
```bash
sam build --use-container && sam deploy
```

---

### X-Ray Tracing

Enable AWS X-Ray for detailed execution tracing:

```yaml
# template.yaml
Globals:
  Function:
    Tracing: Active  # Add this line

# Redeploy
sam build --use-container && sam deploy
```

View traces:
```bash
# AWS Console → X-Ray → Traces
# Filter by Lambda function name
```

---

### Replay Webhook Event

```bash
# 1. Capture event from CloudWatch Logs
sam logs --stack-name jira-github-integration | grep "Received event"

# 2. Save to file: replay-event.json

# 3. Invoke locally
sam local invoke JiraWebhookFunction --event replay-event.json

# 4. Or invoke remotely
aws lambda invoke \
    --function-name jira-github-integration-JiraWebhookFunction-XXX \
    --payload file://replay-event.json \
    response.json
```

---

## Getting Help

### Collect Diagnostic Information

Run this script to collect all diagnostic information:

```bash
#!/bin/bash
# Save as: diagnose.sh

echo "=== CloudFormation Stack ==="
aws cloudformation describe-stacks --stack-name jira-github-integration

echo "=== Recent Lambda Logs ==="
sam logs --stack-name jira-github-integration | tail -100

echo "=== DynamoDB Table Info ==="
aws dynamodb describe-table --table-name jira-github-sync-state

echo "=== Secret Info (metadata only) ==="
aws secretsmanager describe-secret --secret-id jira-github-integration

echo "=== Lambda Function Config ==="
aws lambda get-function-configuration \
    --function-name jira-github-integration-JiraWebhookFunction-XXX

echo "=== Recent CloudWatch Metrics ==="
aws cloudwatch get-metric-statistics \
    --namespace AWS/Lambda \
    --metric-name Errors \
    --dimensions Name=FunctionName,Value=jira-github-integration-JiraWebhookFunction-XXX \
    --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
    --period 300 \
    --statistics Sum
```

---

## Checklist: Issue Not Syncing

Use this checklist to diagnose sync failures:

- [ ] **Jira issue has correct label** (`sync-to-github` by default)
- [ ] **Jira webhook is enabled** and configured correctly
- [ ] **Jira webhook URL matches** CloudFormation output
- [ ] **Jira webhook events** include "Issue created" and "Comment created"
- [ ] **GitHub token is valid** (test with curl)
- [ ] **GitHub token has correct scopes** (`repo` minimum)
- [ ] **GitHub repository exists** and token has access
- [ ] **GITHUB_OWNER and GITHUB_REPO** in template.yaml are correct
- [ ] **AWS Secret exists** with both `github_token` and `jira_api_token`
- [ ] **Lambda function has permissions** to read secret and write to DynamoDB
- [ ] **DynamoDB table exists** (`jira-github-sync-state`)
- [ ] **CloudWatch Logs show invocations** (if not, webhook issue)
- [ ] **No throttling errors** in CloudWatch
- [ ] **Issue not already synced** (check DynamoDB)

---

For more help, see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) or review CloudWatch Logs for detailed error messages.
