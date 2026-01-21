# Jira-GitHub Integration - Complete Deployment Guide

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Architecture](#architecture)
4. [Pre-Deployment Setup](#pre-deployment-setup)
5. [AWS Configuration](#aws-configuration)
6. [Deployment Steps](#deployment-steps)
7. [Post-Deployment Configuration](#post-deployment-configuration)
8. [Troubleshooting](#troubleshooting)

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

### Step 2: Generate GitHub Personal Access Token

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

### Step 3: Generate Jira API Token

1. Log in to Jira (https://your-domain.atlassian.net)
2. Click your profile picture → **Account settings**
3. Select **Security** → **Create and manage API tokens**
4. Click **"Create API token"**
5. Enter a label (e.g., "GitHub Integration")
6. Click **"Create"**
7. **Copy the token** immediately
8. Save it securely (you'll need it in Step 5)

### Step 4: Gather Configuration Information

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

### Step 5: Find Your Jira Custom Field IDs

**CRITICAL:** The Acceptance Criteria field ID is unique to your Jira instance. You must find your specific field ID.

**Quick Method - Using Jira REST API:**

```bash
# Find all custom fields in your Jira
curl -u "YOUR_JIRA_EMAIL:YOUR_JIRA_TOKEN" \
  "https://YOUR_DOMAIN.atlassian.net/rest/api/3/field" \
  | jq '.[] | select(.custom==true) | {id, name}'
```

Look for a field named "Acceptance Criteria" or similar and note its `id` value (e.g., `customfield_10034`).

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

### Step 1: Configure Acceptance Criteria Custom Field in Jira

The integration syncs Acceptance Criteria from Jira to GitHub. Follow these steps to configure the field:

#### Option A: If the Field Already Exists

1. **Find the Field ID:**

   - Log in to Jira as Admin
   - Click **Settings (⚙️)** → **Work items** → **Fields**
   - Search for "Acceptance Criteria" field (or similar name)
   - Click **•••** (More actions) next to the field
   - Select **Contexts and default values**
   - When the page opens, look at the browser **URL**
   - You will see a URL similar to:
     ```
     https://your-domain.atlassian.net/.../customFields/10074
     ```
   - Copy the **number** at the end of the URL (e.g., `10074`)
   - Construct the Field ID as: `customfield_10074`
   - **Important:** Note this full Field ID for configuration
2. **Update Lambda Configuration (if Field ID differs from customfield_10074):**

   - Open `template.yaml`
   - Find the `Environment` section under `JiraWebhookFunction`
   - Add or update:
     ```yaml
     ACCEPTANCE_CRITERIA_FIELD: customfield_XXXXX  # Your actual field ID
     ```
   - Redeploy: `sam build && sam deploy --no-confirm-changeset`
3. **Verify Field is on Screens:**

   - Go to **Settings (⚙️)** → **Issues** → **Screens**
   - For each screen used by your project (Create, Edit, View):
     - Click screen name → Check if "Acceptance Criteria" field is listed
     - If not, click **Add Field** → Select "Acceptance Criteria" → **Add**

#### Option B: Create New Acceptance Criteria Field

1. **Create the Custom Field:**

   - Log in to Jira as Admin
   - Click **Settings (⚙️)** → **Work items** → **Fields**
   - Click **Create field** (top right)
   - Select **Paragraph (supports rich text)** → Click **Next**
   - Name: `Acceptance Criteria`
   - Description: `Criteria that must be met for this issue to be considered complete`
   - Click **Create**
2. **Add Field to Screens Manually**

   1. Log in to **Jira as an Admin**
   2. Go to **Settings (⚙️)** → **Work items** → **Fields**
   3. Find **Acceptance Criteria**
   4. Click **••• (More actions)**
   5. Select **Add field to screen** 🔗
3. **Select Screens**

   In the popup, select the screens used by your project:

   * ✅ Default Screen
   * ✅ Workflow Screen
   * ✅ Scrum Default Issue Screen *(if using Scrum)*

   Click **Add**

   ✅ The field will now appear on **Create / Edit / View issue screens**
4. **Get the Field ID:**

   - In Fields list, find "Acceptance Criteria"
   - Click **•••** (More actions) next to the field
   - Select **Contexts and default values**
   - When the page opens, look at the browser **URL**
   - You will see a URL similar to:
     ```
     https://your-domain.atlassian.net/.../customFields/10074
     ```
   - Copy the **number** at the end of the URL (e.g., `10074`)
   - Construct the Field ID as: `customfield_10074`
   - **Important:** Note this full Field ID for configuration
5. **Update Lambda Configuration:**

   - If the Field ID is **NOT** `customfield_10074`, update `template.yaml`:
     ```yaml
     Environment:
       Variables:
         ACCEPTANCE_CRITERIA_FIELD: customfield_XXXXX  # Your field ID
     ```
   - Redeploy: `sam build && sam deploy --no-confirm-changeset`

### Step 2: Configure Jira Webhook

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
5. **Configure JQL Filter**

   ```jql
   labels = sync-to-github
   ```

   This ensures only issues with the `sync-to-github` label trigger the webhook.
6. **Click "Create"**

### Step 3: Test the Integration

#### Test 1: Create a Jira Issue with Acceptance Criteria

1. Go to your Jira project
2. Click **"Create"**
3. Fill in the issue details:
   - **Summary:** `Test GitHub Integration`
   - **Description:** `Testing Jira to GitHub sync`
   - **Acceptance Criteria:** `AC1: User can login\nAC2: User can view dashboard`
   - **Assignee:** Select a user (should be mapped in USER_MAPPING)
4. Add label: `sync-to-github`
5. Click **"Create"**

#### Test 2: Verify GitHub Issue Creation

1. Go to your GitHub repository
2. Navigate to **Issues** tab
3. You should see a new issue with:
   - Title matching Jira summary
   - Description with Jira details and link
   - **🎯 Acceptance Criteria** section showing the AC content
   - Assignee (if user mapping configured correctly)

#### Test 3: Test Acceptance Criteria Update

1. In Jira, open the test issue
2. Edit **Acceptance Criteria**: Change to `AC1: User can login with 2FA`
3. Save the issue
4. Check GitHub issue - the Acceptance Criteria section should update automatically

#### Test 4: Test Comment Sync (Jira → GitHub)

1. In Jira, open the test issue
2. Add a comment: `This comment should appear in GitHub`
3. Check GitHub issue - comment should appear with:
   ```
   Author: @githubuser (Full Name)

   This comment should appear in GitHub

   [View in Jira](<link>)
   ```

#### Test 5: Verify CloudWatch Logs

1. Go to AWS Console → CloudWatch → Log Groups
2. Find `/aws/lambda/jira-github-integration-JiraWebhookFunction-xxxxx`
3. Check recent logs for:
   - `✓ Acceptance Criteria found: X characters`
   - `✓ Built new AC section`
   - `✓ Updated GitHub issue #X`
   - No errors related to custom fields

### Step 4: Monitor CloudWatch Logs

```bash
# View recent logs
sam logs --stack-name jira-github-integration --tail

# Or view in AWS Console
# Navigate to CloudWatch → Log Groups → /aws/lambda/jira-github-integration-JiraWebhookFunction-xxxxx
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

### Issue: Acceptance Criteria Not Syncing/Updating

**Symptoms:** Acceptance Criteria field changes in Jira don't appear or update in GitHub issues.

**Diagnosis:**

1. Check CloudWatch logs for:
   - `⚠ No AC content found in Jira`
   - `Failed to fetch from Jira API`
   - Field ID mismatch errors
2. Verify custom field configuration in Jira
3. Check field permissions

**Solution:**

```bash
# Step 1: Verify the correct Field ID
# Log in to Jira → Settings → Work items → Fields
# Find "Acceptance Criteria" → Click ••• → Contexts and default values
# Check the browser URL: https://your-domain.atlassian.net/.../customFields/10074
# Copy the number (10074) and construct: customfield_10074

# Step 2: Update Lambda environment variable if ID differs
# Edit template.yaml and add under Environment Variables:
# ACCEPTANCE_CRITERIA_FIELD: customfield_XXXXX

# Step 3: Ensure field is on screens
# Jira → Settings → Work items → Screens
# For Create/Edit/View screens, ensure "Acceptance Criteria" is added

# Step 4: Verify field permissions
# Jira → Settings → Work items → Permission schemes
# Ensure integration user can "Edit Issues" and "View Issue"

# Step 5: Redeploy
sam build
sam deploy --no-confirm-changeset

# Step 6: Test by updating AC in Jira
# Check CloudWatch logs for:
# - "✓ Fetched fresh AC from API"
# - "✓ Built new AC section"
# - "Detected AC change vs GitHub body; will update"
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

Version 1.0.0

- Initial release
- One-way Jira-to-GitHub integration
- User mapping support
- DynamoDB-based duplicate prevention
- Comment synchronization (Jira → GitHub)
- Label mapping
- Acceptance criteria support

**Technologies Used:**

- AWS Lambda (Python 3.13)
- AWS SAM (Serverless Application Model)
- AWS API Gateway
- AWS DynamoDB
- AWS Secrets Manager
- GitHub REST API v3
- Jira Cloud REST API v3
