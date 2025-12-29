# Jira-GitHub Integration - Scheduled Sync Setup Guide

## 📦 Deployment Package

**File Location**: `lambda_deployment_package/jira-sync-lambda.zip`
**Size**: 1.02 MB
**Ready to upload**: ✅ Yes

---

## 🔧 Configuration Requirements

### 1. AWS Secrets Manager Setup

You need to create a secret named `jira-github-integration` with the following JSON structure:

```json
{
  "github_token": "your_github_personal_access_token",
  "jira_email": "your_email@example.com",
  "jira_api_token": "your_jira_api_token"
}
```

#### How to get these credentials:

**GitHub Token:**

1. Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token with `repo` scope (full control of private repositories)
3. Copy the token

**Jira API Token:**

1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Give it a name (e.g., "GitHub Sync")
4. Copy the token

**Jira Email:**

- Use the email address associated with your Atlassian account

#### Create the secret in AWS:

```bash
aws secretsmanager create-secret \
  --name jira-github-integration \
  --secret-string '{"github_token":"ghp_xxx","jira_email":"your@email.com","jira_api_token":"ATATTxxx"}'
```

---

## 🚀 AWS Lambda Setup

### Step 1: Create Lambda Function

1. Go to AWS Lambda Console
2. Click **Create function**
3. Choose **Author from scratch**
4. Function name: `jira-github-sync`
5. Runtime: **Python 3.13** (or 3.12, 3.11)
6. Architecture: **x86_64**
7. Click **Create function**

### Step 2: Upload Deployment Package

1. In the Lambda function page, go to **Code** tab
2. Click **Upload from** → **.zip file**
3. Upload `jira-sync-lambda.zip`
4. Wait for upload to complete

### Step 3: Configure Environment Variables

Go to **Configuration** → **Environment variables** and add:

| Key                  | Value                                      | Notes                    |
| -------------------- | ------------------------------------------ | ------------------------ |
| `JIRA_BASE_URL`    | `https://nuwanthapiumal57.atlassian.net` | ✅ Already set           |
| `JIRA_PROJECT_KEY` | `TPFI`                                   | Your Jira project key    |
| `GITHUB_OWNER`     | `Nuwantha57`                             | Your GitHub username     |
| `GITHUB_REPO`      | `jira-sync-test`                         | Your GitHub repository   |
| `TARGET_LABEL`     | `sync-to-github`                         | Label to trigger sync    |
| `SECRET_NAME`      | `jira-github-integration`                | AWS Secrets Manager name |
| `DYNAMODB_TABLE`   | `jira-github-sync-state`                 | DynamoDB table name      |

**Note**: Update `JIRA_PROJECT_KEY`, `GITHUB_OWNER`, and `GITHUB_REPO` if needed.

### Step 4: Configure Lambda Settings

**Configuration** → **General configuration**:

- Memory: **256 MB**
- Timeout: **1 minute**

### Step 5: Add IAM Permissions

**Configuration** → **Permissions** → Click on the execution role → **Add permissions** → **Attach policies**

Add these policies:

1. `SecretsManagerReadWrite` (or create custom policy for `jira-github-integration` secret)
2. `AmazonDynamoDBFullAccess` (or create custom policy for the table)

Or create an inline policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": "arn:aws:secretsmanager:*:*:secret:jira-github-integration*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/jira-github-sync-state"
    }
  ]
}
```

---

## 🗄️ DynamoDB Setup

### Create DynamoDB Table

1. Go to DynamoDB Console
2. Click **Create table**
3. Table name: `jira-github-sync-state`
4. Partition key: `jira_issue_key` (String)
5. Table settings: **On-demand** (or Provisioned with minimal capacity)
6. Click **Create table**

### Enable Time-To-Live (Optional)

1. Go to your table → **Additional settings**
2. Enable TTL
3. TTL attribute name: `ttl`
4. This will auto-delete records after 90 days

---

## ⏰ EventBridge Scheduler Setup

### Create Schedule

1. Go to **Amazon EventBridge** → **Scheduler** → **Schedules**
2. Click **Create schedule**
3. Name: `jira-sync-schedule`
4. Description: `Poll Jira every X hours and sync to GitHub`

### Schedule Pattern

Choose one:

- **Every 30 minutes**: `rate(30 minutes)`
- **Every 1 hour**: `rate(1 hour)`
- **Every 2 hours**: `rate(2 hours)`
- **Every 6 hours**: `rate(6 hours)`

Or use cron expression for specific times:

- **Every day at 9 AM UTC**: `cron(0 9 * * ? *)`
- **Every 4 hours**: `cron(0 */4 * * ? *)`

### Target

- Target API: **AWS Lambda Invoke**
- Lambda function: `jira-github-sync`
- Payload: (leave empty or use `{}`)

### Action After Schedule Completion

- None (for recurring schedules)

---

## 🧪 Testing

### Manual Test

1. Go to Lambda function → **Test** tab
2. Create new test event
3. Event JSON:

```json
{
  "source": "aws.events",
  "detail-type": "Scheduled Event"
}
```

4. Click **Test**
5. Check CloudWatch Logs for output

### Verify Sync

1. Create a Jira issue in project `TPFI`
2. Add label `sync-to-github` to the issue
3. Wait for next scheduled run (or manually trigger)
4. Check if GitHub issue is created in `Nuwantha57/jira-sync-test`

---

## 📊 Monitoring

### CloudWatch Logs

- Go to Lambda → **Monitor** → **View CloudWatch logs**
- Check for:
  - `Starting scheduled Jira sync`
  - `Found X Jira issues`
  - `Created GitHub issue: <url>`
  - `Sync completed: X synced, Y skipped`

### DynamoDB

- Check the `jira-github-sync-state` table
- You should see records for each synced issue

---

## 🔍 Troubleshooting

### Common Issues

**1. "Failed to retrieve secrets"**

- Check if secret `jira-github-integration` exists
- Verify Lambda has permission to access Secrets Manager
- Ensure secret has all three keys: `github_token`, `jira_email`, `jira_api_token`

**2. "Jira query failed"**

- Verify `JIRA_BASE_URL` is correct
- Check Jira API token is valid
- Ensure project key `JIRA_PROJECT_KEY` exists
- Verify your Jira account has access to the project

**3. "GitHub creation failed"**

- Check GitHub token has `repo` scope
- Verify repository exists and you have access
- Ensure `GITHUB_OWNER` and `GITHUB_REPO` are correct

**4. "DynamoDB error"**

- Verify table `jira-github-sync-state` exists
- Check Lambda has DynamoDB permissions
- Ensure partition key is `jira_issue_key` (String)

**5. No issues syncing**

- Verify Jira issues have the label `sync-to-github`
- Check CloudWatch logs to see if issues are being found
- Ensure issues haven't already been synced (check DynamoDB)

---

## 🎯 What This Does

1. **Every X hours** (you configure), EventBridge triggers the Lambda
2. Lambda queries Jira for all issues with label `sync-to-github` in project `TPFI`
3. For each issue:
   - Checks if it's already been synced (via DynamoDB)
   - If not synced, creates a GitHub issue
   - Records it in DynamoDB to prevent duplicates
4. Returns summary: how many synced, skipped, errors

---

## 📝 Important Notes

- **No webhook needed**: This is purely scheduled polling
- **Idempotent**: Won't create duplicate GitHub issues (thanks to DynamoDB tracking)
- **Label-based**: Only Jira issues with `sync-to-github` label are processed
- **One-way sync**: Jira → GitHub only (no reverse sync)
- **Auto-cleanup**: DynamoDB records expire after 90 days (TTL)

---

## 🔄 Configuration You Need to Update

Before deploying, update these in Environment Variables:

1. **JIRA_PROJECT_KEY**: ✅ Currently set to `TPFI` - **Update if your project key is different**
2. **GITHUB_OWNER**: ✅ Currently set to `Nuwantha57` - **Confirm this is correct**
3. **GITHUB_REPO**: ✅ Currently set to `jira-sync-test` - **Update to your actual repo**
4. **TARGET_LABEL**: ✅ Currently set to `sync-to-github` - **Change if you want a different label**

---

## 📧 Questions?

If you need help:

1. Check CloudWatch Logs first
2. Verify all credentials are correct
3. Ensure IAM permissions are set up
4. Test with a simple Jira issue with the label

Good luck! 🚀
