# Jira-GitHub Integration - Complete Deployment Guide

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Architecture](#architecture)
4. [Pre-Deployment Setup](#pre-deployment-setup)
5. [AWS Configuration](#aws-configuration)
6. [Deployment Steps](#deployment-steps)
7. [Post-Deployment Configuration](#post-deployment-configuration)
8. [Testing](#testing)
9. [Troubleshooting](#troubleshooting)
10. [Maintenance](#maintenance)

---

## Overview

This serverless application syncs Jira issues and comments to GitHub automatically (one-way sync: Jira → GitHub).

### Key Features

- ✅ Sync Jira issues to GitHub issues using the `sync-to-github` label
- ✅ Sync Jira comments to GitHub (one-way)
- ✅ User mapping from Jira to GitHub
- ✅ Duplicate prevention using DynamoDB
- ✅ Acceptance criteria and label mapping support
- ✅ Webhook signature verification for security

### What Gets Synced

**From Jira to GitHub:**

- Issue title and description
- Assignee (with user mapping)
- Labels
- Acceptance criteria
- Comments (with author attribution)

**Note:** This is a one-way sync. GitHub changes are NOT synced back to Jira.

---

## Prerequisites

### Required Tools

1. **AWS CLI** (v2.x or later)

   - [Installation Guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
   - Verify: `aws --version`
2. **AWS SAM CLI** (v1.100.0 or later)

   - [Installation Guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
   - Verify: `sam --version`
3. **Python 3.13**

   - [Download Python](https://www.python.org/downloads/)
   - Verify: `python --version`
4. **Docker Desktop**

   - [Install Docker](https://www.docker.com/products/docker-desktop/)
   - Required for building Lambda functions locally
   - Verify: `docker --version`
5. **Git**

   - For cloning and version control
   - Verify: `git --version`

### Required Accounts & Permissions

#### AWS Account Requirements

- Active AWS account with billing enabled
- IAM user or role with the following permissions:
  - CloudFormation (full access)
  - Lambda (full access)
  - API Gateway (full access)
  - DynamoDB (full access)
  - Secrets Manager (full access)
  - S3 (for SAM deployment artifacts)
  - IAM (role creation)

#### GitHub Requirements

- GitHub account with repository access
- Repository where issues will be synced
- **Admin or Write** permissions on the target repository
- GitHub Personal Access Token (PAT) with the following scopes:
  - `repo` (full control of private repositories)
  - `write:discussion` (write access to discussions)

#### Jira Requirements

- Atlassian Jira Cloud account
- Project where issues will be synced from
- **Admin** permissions to configure webhooks
- Jira API Token for authentication

---

## Architecture

```
┌─────────────────┐
│   Jira Cloud    │
│  (Issue Events) │
└────────┬────────┘
         │ Webhook (POST)
         ▼
┌─────────────────────────────┐
│  AWS API Gateway            │
│  /webhook endpoint          │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  Lambda Function            │
│  (JiraWebhookFunction)      │
│  - Parse Jira payload       │
│  - Check sync label         │
│  - Map users                │
│  - Create GitHub issue      │
│  - Sync comments            │
└──────┬──────────────┬───────┘
       │              │
       ▼              ▼
┌─────────────┐  ┌──────────────┐
│  DynamoDB   │  │   GitHub API │
│  Sync State │  │   Issues     │
│  Mappings   │  │   Comments   │
└─────────────┘  └──────────────┘
       ▲
       │
       │ Read Secrets
       │
┌─────────────────────┐
│  AWS Secrets Manager│
│  - GitHub Token     │
│  - Jira Token       │
└─────────────────────┘
```

---

## Pre-Deployment Setup

### Step 1: Clone or Download the Project

```bash
# If using Git
git clone <repository-url>
cd jira-github-integration

# Or extract the provided zip file
unzip jira-github-integration.zip
cd jira-github-integration
```

### Step 2: Verify Project Structure

Ensure your project has the following structure:

```
jira-github-integration/
├── README.md
├── DEPLOYMENT_GUIDE.md (this file)
├── template.yaml
├── samconfig.toml
├── events/
│   └── event.json
├── jira_handler/
│   ├── __init__.py
│   ├── app.py
│   └── requirements.txt
└── tests/
    ├── __init__.py
    ├── requirements.txt
    ├── integration/
    │   ├── __init__.py
    │   └── test_api_gateway.py
    └── unit/
        ├── __init__.py
        └── test_handler.py
```

### Step 3: Generate GitHub Personal Access Token

1. Log in to GitHub
2. Navigate to **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**
3. Click **"Generate new token"** → **"Generate new token (classic)"**
4. Set a descriptive note (e.g., "Jira-GitHub Integration")
5. Select expiration (recommend: 90 days or No expiration for production)
6. Select scopes:
   - ✅ `repo` (Full control of private repositories)
   - ✅ `write:discussion`
7. Click **"Generate token"**
8. **IMPORTANT:** Copy the token immediately (you won't see it again!)
9. Save it securely (you'll need it in Step 5)

### Step 4: Generate Jira API Token

1. Log in to Jira (https://your-domain.atlassian.net)
2. Click your profile picture → **Account settings**
3. Select **Security** → **Create and manage API tokens**
4. Click **"Create API token"**
5. Enter a label (e.g., "GitHub Integration")
6. Click **"Create"**
7. **Copy the token** immediately
8. Save it securely (you'll need it in Step 5)

### Step 5: Gather Configuration Information

Create a configuration worksheet with the following information:

| Parameter                              | Example                             | Your Value |
| -------------------------------------- | ----------------------------------- | ---------- |
| **GitHub Owner**                 | `mycompany` or `myusername`     |            |
| **GitHub Repository**            | `project-issues`                  |            |
| **GitHub Token**                 | `ghp_xxxxxxxxxxxx`                |            |
| **Jira Base URL**                | `https://mycompany.atlassian.net` |            |
| **Jira Email**                   | `admin@mycompany.com`             |            |
| **Jira API Token**               | `ATATT3xFfGF0xxxx`                |            |
| **Jira Project Key**             | `PROJ`                            |            |
| **AWS Region**                   | `us-east-1`                       |            |
| **Stack Name**                   | `jira-github-integration`         |            |
| **Acceptance Criteria Field ID** | `customfield_10034`               |            |

**User Mapping (Optional but Recommended):**
Map Jira users to GitHub usernames for proper assignee attribution:

| Jira Email                 | GitHub Username |
| -------------------------- | --------------- |
| `john.doe@company.com`   | `johndoe`     |
| `jane.smith@company.com` | `janesmith`   |

Format: `email1:githubuser1,email2:githubuser2`

### Step 6: Find Your Jira Custom Field IDs

**CRITICAL:** The Acceptance Criteria field ID is unique to your Jira instance. You must find your specific field ID.

**Quick Method - Using Jira REST API:**

```bash
# Find all custom fields in your Jira
curl -u "YOUR_JIRA_EMAIL:YOUR_JIRA_TOKEN" \
  "https://YOUR_DOMAIN.atlassian.net/rest/api/3/field" \
  | jq '.[] | select(.custom==true) | {id, name}'
```

Look for a field named "Acceptance Criteria" or similar and note its `id` value (e.g., `customfield_10034`).

**Alternative Methods:**

- See [CUSTOM_FIELD_SETUP.md](CUSTOM_FIELD_SETUP.md) for detailed instructions
- Use browser DevTools to inspect Jira issue API responses
- Check an issue JSON that has Acceptance Criteria filled in

**Important:** If you don't configure the correct field ID, Acceptance Criteria will not sync to GitHub.

---

## AWS Configuration

### Step 1: Configure AWS CLI

```bash
# Configure AWS credentials
aws configure

# You'll be prompted for:
# - AWS Access Key ID
# - AWS Secret Access Key
# - Default region name (e.g., us-east-1, eu-west-1)
# - Default output format (json)
```

### Step 2: Verify AWS Configuration

```bash
# Test AWS credentials
aws sts get-caller-identity

# Should return your AWS account ID and user/role information
```

### Step 3: Choose AWS Region

Select a region close to your users for better latency:

- **US East (N. Virginia):** `us-east-1`
- **US West (Oregon):** `us-west-2`
- **EU (Ireland):** `eu-west-1`
- **EU (Stockholm):** `eu-north-1`
- **Asia Pacific (Singapore):** `ap-southeast-1`

**Note:** Ensure Lambda, API Gateway, DynamoDB, and Secrets Manager are available in your chosen region.

---

## Deployment Steps

### Step 1: Update Configuration Files

#### 1.1 Edit `template.yaml`

Open [template.yaml](template.yaml) and update the following environment variables:

```yaml
Environment:
  Variables:
    GITHUB_OWNER: your-github-username-or-org    # Change this
    GITHUB_REPO: your-repository-name            # Change this
    JIRA_BASE_URL: https://your-domain.atlassian.net  # Change this
    JIRA_EMAIL: your-jira-email@example.com      # Change this
    TARGET_LABEL: sync-to-github                 # Optional: change label name
    SECRET_NAME: jira-github-integration         # Keep default or change
    DYNAMODB_TABLE: jira-github-sync-state       # Keep default or change
    USER_MAPPING: "user1@example.com:githubuser1,user2@example.com:githubuser2"  # Update with your mappings
```

**User Mapping Format Examples:**

```yaml
# Single user mapping
USER_MAPPING: "john.doe@company.com:johndoe"

# Multiple users (comma-separated)
USER_MAPPING: "john.doe@company.com:johndoe,jane.smith@company.com:janesmith"

# Using Jira Account IDs (alternative format)
USER_MAPPING: "712020:8dcd81ff-57c6-432c-88aa-bded8d0e6c10:GithubUser1"

# Mixed format
USER_MAPPING: "email@company.com:githubuser,5f2c3e4a5b6c7d8e9f0a1b2c:githubuser2"
```

#### 1.2 Edit `samconfig.toml`

Open [samconfig.toml](samconfig.toml) and update:

```toml
[default.global.parameters]
stack_name = "jira-github-integration"   # Your preferred stack name
region = "us-east-1"                     # Your AWS region

[default.deploy.parameters]
region = "us-east-1"                     # Match the region above
```

### Step 2: Create AWS Secrets

Store your GitHub and Jira tokens securely in AWS Secrets Manager:

```bash
# Create the secret with both tokens
aws secretsmanager create-secret \
    --name jira-github-integration \
    --description "Tokens for Jira-GitHub integration" \
    --secret-string '{
        "github_token":"YOUR_GITHUB_TOKEN_HERE",
        "jira_api_token":"YOUR_JIRA_API_TOKEN_HERE"
    }' \
    --region YOUR_AWS_REGION
```

**Example:**

```bash
aws secretsmanager create-secret \
    --name jira-github-integration \
    --description "Tokens for Jira-GitHub integration" \
    --secret-string '{
        "github_token":"ghp_xxxxxxxxxxxxxxxxxxxx",
        "jira_api_token":"ATATT3xFfGF0xxxxxxxxxxxx"
    }' \
    --region us-east-1
```

**Verify Secret Creation:**

```bash
aws secretsmanager describe-secret \
    --secret-id jira-github-integration \
    --region YOUR_AWS_REGION
```

### Step 3: Build the Application

```bash
# Build using Docker container (recommended)
sam build --use-container

# Or build without container (requires Python 3.13 installed locally)
sam build
```

**Expected Output:**

```
Build Succeeded

Built Artifacts  : .aws-sam/build
Built Template   : .aws-sam/build/template.yaml
```

### Step 4: Deploy to AWS

#### Option A: Guided Deployment (First Time)

```bash
sam deploy --guided
```

You'll be prompted for:

1. **Stack Name:** `jira-github-integration` (or your custom name)
2. **AWS Region:** `us-east-1` (or your chosen region)
3. **Confirm changes before deploy:** `Y` (recommended)
4. **Allow SAM CLI IAM role creation:** `Y` (required)
5. **Disable rollback:** `N` (recommended for production)
6. **JiraWebhookFunction may not have authorization defined:** `Y` (this is expected)
7. **Save arguments to configuration file:** `Y` (saves to samconfig.toml)
8. **SAM configuration file:** Press Enter (uses samconfig.toml)
9. **SAM configuration environment:** Press Enter (uses default)

#### Option B: Quick Deployment (After First Deploy)

```bash
# Uses saved configuration from samconfig.toml
sam deploy
```

### Step 5: Capture Deployment Outputs

After successful deployment, you'll see output similar to:

```
CloudFormation outputs from deployed stack
----------------------------------------------------
Outputs
----------------------------------------------------
Key                 JiraWebhookUrl
Description         API Gateway endpoint URL for Jira webhook
Value               https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/Prod/webhook
----------------------------------------------------
```

**IMPORTANT:** Copy the `JiraWebhookUrl` - you'll need this for Jira webhook configuration.

---

## Post-Deployment Configuration

### Step 1: Configure Jira Webhook

1. **Navigate to Jira Settings:**

   - Go to your Jira instance (https://your-domain.atlassian.net)
   - Click **Settings (⚙️)** → **System**
2. **Access Webhooks:**

   - In the left sidebar, find **WebHooks** under "ADVANCED"
   - Click **"Create a WebHook"**
3. **Configure Webhook:**

   | Field                 | Value                                                                                            |
   | --------------------- | ------------------------------------------------------------------------------------------------ |
   | **Name**        | `GitHub Integration`                                                                           |
   | **Status**      | ✅ Enabled                                                                                       |
   | **URL**         | `https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/Prod/webhook` (from deployment output) |
   | **Description** | `Syncs Jira issues to GitHub`                                                                  |
4. **Select Events:**

   - ✅ `Issue` → `created`
   - ✅ `Issue` → `updated`
   - ✅ `Comment` → `created,updated`
5. **Optional: Configure JQL Filter**

   ```jql
   labels = sync-to-github
   ```

   This ensures only issues with the `sync-to-github` label trigger the webhook.
6. **Click "Create"**

### Step 2: Test the Integration

#### Test 1: Create a Jira Issue

1. Go to your Jira project
2. Click **"Create"**
3. Fill in the issue details:
   - **Summary:** `Test GitHub Integration`
   - **Description:** `Testing Jira to GitHub sync`
   - **Assignee:** Select a user (should be mapped in USER_MAPPING)
4. Add label: `sync-to-github`
5. Click **"Create"**

#### Test 2: Verify GitHub Issue Creation

1. Go to your GitHub repository
2. Navigate to **Issues** tab
3. You should see a new issue with:
   - Title matching Jira summary
   - Description with Jira details and link
   - Assignee (if user mapping configured correctly)
   - Label: `jira-sync`

#### Test 3: Test Comment Sync (Jira → GitHub)

1. In Jira, open the test issue
2. Add a comment: `This comment should appear in GitHub`
3. Check GitHub issue - comment should appear with:
   ```
   Author: @githubuser (Full Name)

   This comment should appear in GitHub

   [View in Jira](<link>)
   ```

**Note:** Comments added in GitHub will NOT sync back to Jira (one-way sync only).

### Step 3: Monitor CloudWatch Logs

```bash
# View recent logs
sam logs --stack-name jira-github-integration --tail

# Or view in AWS Console
# Navigate to CloudWatch → Log Groups → /aws/lambda/jira-github-integration-JiraWebhookFunction-xxxxx
```

---

## Testing

### Local Testing

#### Test with Sample Event

```bash
# Invoke function locally with test event
sam local invoke JiraWebhookFunction --event events/event.json
```

#### Start Local API

```bash
# Start API Gateway locally
sam local start-api

# In another terminal, test the endpoint
curl -X POST http://localhost:3000/webhook \
  -H "Content-Type: application/json" \
  -d @events/event.json
```

### Unit Tests

```bash
# Install test dependencies
pip install -r tests/requirements.txt

# Run unit tests
python -m pytest tests/unit/ -v
```

### Integration Tests

```bash
# Run integration tests (requires deployed stack)
python -m pytest tests/integration/ -v
```

---

## Troubleshooting

### Issue: GitHub Issue Not Created

**Symptoms:** Jira issue created with `sync-to-github` label, but no GitHub issue appears.

**Diagnosis:**

1. Check CloudWatch Logs:

   ```bash
   sam logs --stack-name jira-github-integration --tail
   ```
2. Common causes:

   - ❌ Label name mismatch (check `TARGET_LABEL` in template.yaml)
   - ❌ GitHub token invalid or expired
   - ❌ GitHub repository name incorrect
   - ❌ Network/permissions issue

**Solutions:**

```bash
# Verify GitHub token permissions
curl -H "Authorization: token YOUR_GITHUB_TOKEN" \
     https://api.github.com/repos/OWNER/REPO

# Should return repository details (not 404 or 403)

# Update token if expired
aws secretsmanager update-secret \
    --secret-id jira-github-integration \
    --secret-string '{
        "github_token":"NEW_TOKEN_HERE",
        "jira_api_token":"YOUR_JIRA_TOKEN"
    }'
```

### Issue: Duplicate GitHub Issues

**Symptoms:** Multiple GitHub issues created for the same Jira issue.

**Diagnosis:**

- DynamoDB sync state not working properly

**Solution:**

```bash
# Check DynamoDB table
aws dynamodb scan \
    --table-name jira-github-sync-state \
    --region YOUR_AWS_REGION

# If needed, clear the table and re-sync
aws dynamodb delete-item \
    --table-name jira-github-sync-state \
    --key '{"jira_issue_key":{"S":"PROJ-123"}}' \
    --region YOUR_AWS_REGION
```

### Issue: Comments Not Syncing

**Symptoms:** Comments added in Jira/GitHub don't appear in the other platform.

**Diagnosis:**

1. Check webhook configuration in Jira (ensure "Comment created" event is enabled)
2. Check CloudWatch logs for errors
3. Verify comment mapping in DynamoDB

**Solution:**

```bash
# Check comment mappings
aws dynamodb get-item \
    --table-name jira-github-sync-state \
    --key '{"jira_issue_key":{"S":"PROJ-123"}}' \
    --region YOUR_AWS_REGION

# Look for "comments" attribute with mappings
```

### Issue: User Not Assigned in GitHub

**Symptoms:** GitHub issue created but assignee is not set, even with user mapping.

**Diagnosis:**

- User mapping format incorrect
- GitHub user doesn't exist
- GitHub user doesn't have repository access

**Solution:**

```bash
# Verify GitHub user exists and has repo access
curl -H "Authorization: token YOUR_GITHUB_TOKEN" \
     https://api.github.com/repos/OWNER/REPO/collaborators/USERNAME

# Should return 204 (No Content) if user has access
# Returns 404 if user doesn't exist or lacks access

# Add user as collaborator
# Navigate to GitHub → Repository → Settings → Collaborators → Add people
```

### Issue: Lambda Timeout

**Symptoms:** Error: Task timed out after 30.00 seconds

**Solution:**
Increase timeout in [template.yaml](template.yaml):

```yaml
Globals:
  Function:
    Runtime: python3.13
    Timeout: 60  # Increase from 30 to 60 seconds
    MemorySize: 256
```

Then redeploy:

```bash
sam build --use-container
sam deploy
```

### Issue: Webhook Signature Verification Failed

**Symptoms:** Logs show "Signature mismatch" or "403 Forbidden"

**Solution:**
Webhook signature verification is currently optional. If you want to add it:

1. Generate a webhook secret:

   ```bash
   openssl rand -hex 32
   ```
2. Add to Jira webhook configuration
3. Add to AWS Secrets:

   ```bash
   aws secretsmanager update-secret \
       --secret-id jira-github-integration \
       --secret-string '{
           "github_token":"YOUR_GITHUB_TOKEN",
           "jira_api_token":"YOUR_JIRA_TOKEN",
           "webhook_secret":"YOUR_GENERATED_SECRET"
       }'
   ```

---

## Maintenance

### Updating the Application

```bash
# 1. Make code changes in jira_handler/app.py or template.yaml

# 2. Rebuild
sam build --use-container

# 3. Deploy updates
sam deploy

# 4. Verify deployment
sam logs --stack-name jira-github-integration --tail
```

### Rotating Secrets

#### Rotate GitHub Token

```bash
# 1. Generate new token in GitHub (see Step 3 in Pre-Deployment)

# 2. Update secret
aws secretsmanager update-secret \
    --secret-id jira-github-integration \
    --secret-string '{
        "github_token":"NEW_GITHUB_TOKEN",
        "jira_api_token":"EXISTING_JIRA_TOKEN"
    }' \
    --region YOUR_AWS_REGION

# 3. No redeployment needed - Lambda will use new token on next invocation
```

#### Rotate Jira Token

```bash
# 1. Generate new token in Jira (see Step 4 in Pre-Deployment)

# 2. Update secret
aws secretsmanager update-secret \
    --secret-id jira-github-integration \
    --secret-string '{
        "github_token":"EXISTING_GITHUB_TOKEN",
        "jira_api_token":"NEW_JIRA_TOKEN"
    }' \
    --region YOUR_AWS_REGION
```

### Monitoring

#### CloudWatch Metrics

Navigate to AWS Console → CloudWatch → Metrics → Lambda:

- **Invocations:** Number of webhook calls
- **Errors:** Failed executions
- **Duration:** Execution time
- **Throttles:** Rate limit hits

#### Set Up Alarms

```bash
# Create alarm for Lambda errors
aws cloudwatch put-metric-alarm \
    --alarm-name jira-github-integration-errors \
    --alarm-description "Alert on Lambda errors" \
    --metric-name Errors \
    --namespace AWS/Lambda \
    --statistic Sum \
    --period 300 \
    --threshold 5 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 1 \
    --dimensions Name=FunctionName,Value=jira-github-integration-JiraWebhookFunction-xxxxx
```

### Cost Optimization

**Estimated Monthly Costs (for 1000 syncs/month):**

- Lambda: $0.20 (free tier: 1M requests/month)
- API Gateway: $3.50 (free tier: 1M requests/month for 12 months)
- DynamoDB: $1.25 (pay-per-request pricing)
- Secrets Manager: $0.40 per secret per month
- **Total: ~$5.35/month** (after free tier)

**Tips:**

- Use DynamoDB on-demand pricing (default)
- Set appropriate TTL for DynamoDB items (default: 90 days)
- Monitor CloudWatch logs retention (default: Never expire - consider changing to 30 days)

### Cleanup / Uninstallation

To completely remove the application:

```bash
# 1. Delete CloudFormation stack
aws cloudformation delete-stack \
    --stack-name jira-github-integration \
    --region YOUR_AWS_REGION

# 2. Delete secrets (optional - contains sensitive data)
aws secretsmanager delete-secret \
    --secret-id jira-github-integration \
    --force-delete-without-recovery \
    --region YOUR_AWS_REGION

# 3. Remove Jira webhook
# Navigate to Jira → Settings → System → WebHooks → Delete the webhook

# 4. Verify stack deletion
aws cloudformation describe-stacks \
    --stack-name jira-github-integration \
    --region YOUR_AWS_REGION
# Should return: Stack with id jira-github-integration does not exist
```

---

## Security Best Practices

1. **Token Management:**

   - Never commit tokens to version control
   - Use AWS Secrets Manager for all sensitive data
   - Rotate tokens every 90 days
2. **IAM Permissions:**

   - Use least privilege principle
   - Create dedicated IAM role for Lambda
   - Restrict Secrets Manager access
3. **Network Security:**

   - API Gateway is public but only accepts webhook payloads
   - Consider adding IP allowlisting if Jira has fixed IPs
   - Enable CloudWatch logging for audit trails
4. **Data Retention:**

   - DynamoDB items auto-expire after 90 days (TTL enabled)
   - Set CloudWatch Logs retention to 30 days
   - Regularly review and clean up old data

---

## Support & Resources

### AWS Documentation

- [AWS SAM Documentation](https://docs.aws.amazon.com/serverless-application-model/)
- [Lambda Developer Guide](https://docs.aws.amazon.com/lambda/)
- [API Gateway Documentation](https://docs.aws.amazon.com/apigateway/)
- [DynamoDB Documentation](https://docs.aws.amazon.com/dynamodb/)

### API References

- [GitHub REST API](https://docs.github.com/en/rest)
- [Jira Cloud REST API](https://developer.atlassian.com/cloud/jira/platform/rest/v3/)
- [Jira Webhooks](https://developer.atlassian.com/cloud/jira/platform/webhooks/)

### Common Commands Reference

```bash
# Build and deploy
sam build --use-container && sam deploy

# View logs (real-time)
sam logs --stack-name jira-github-integration --tail

# View specific log stream
sam logs --stack-name jira-github-integration --name JiraWebhookFunction --tail

# Test locally
sam local invoke JiraWebhookFunction --event events/event.json

# Start local API
sam local start-api

# Validate template
sam validate

# Delete stack
sam delete --stack-name jira-github-integration

# Get stack outputs
aws cloudformation describe-stacks \
    --stack-name jira-github-integration \
    --query 'Stacks[0].Outputs' \
    --region YOUR_AWS_REGION
```

---

## Frequently Asked Questions (FAQ)

**Q: Can I sync multiple Jira projects to different GitHub repositories?**
A: Currently, the application supports one Jira-to-GitHub mapping. To support multiple, deploy separate stacks with different configurations.

**Q: What happens if I delete a Jira issue?**
A: The GitHub issue remains unchanged. Issue deletion is not synced for data preservation.

**Q: Can I sync existing Jira issues?**
A: Yes, add the `sync-to-github` label to any existing issue, and it will be synced on the next update.

**Q: How do I change the sync label name?**
A: Update the `TARGET_LABEL` environment variable in [template.yaml](template.yaml) and redeploy.

**Q: Does this work with Jira Server/Data Center?**
A: This implementation is designed for Jira Cloud. Jira Server/Data Center may require modifications to the authentication method.

**Q: What's the maximum issue size?**
A: Limited by API Gateway payload size (10 MB). Large issues with extensive descriptions should work fine.

**Q: Can I sync attachments?**
A: Attachments are not currently synced. Only text content (description, comments, labels) is synchronized.

**Q: How do I add more users to the mapping?**
A: Update the `USER_MAPPING` environment variable in [template.yaml](template.yaml), rebuild, and redeploy.

---

## Change Log

### Version 1.0.0 (Current)

- Initial release
- One-way Jira-to-GitHub integration
- User mapping support
- DynamoDB-based duplicate prevention
- Comment synchronization (Jira → GitHub)
- Label mapping
- Acceptance criteria support

---

## License & Credits

This project is provided as-is for integration purposes.

**Technologies Used:**

- AWS Lambda (Python 3.13)
- AWS SAM (Serverless Application Model)
- AWS API Gateway
- AWS DynamoDB
- AWS Secrets Manager
- GitHub REST API v3
- Jira Cloud REST API v3

---

**Need Help?** Review the [Troubleshooting](#troubleshooting) section or check CloudWatch Logs for detailed error messages.
