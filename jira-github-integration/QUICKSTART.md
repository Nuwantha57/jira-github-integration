# Quick Start Guide - Jira-GitHub Integration

## 5-Minute Setup

This guide gets you up and running quickly. For detailed instructions, see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md).

**Sync Direction:** Jira → GitHub (one-way)

---

## Prerequisites Checklist

- [ ] AWS CLI installed and configured
- [ ] AWS SAM CLI installed
- [ ] Docker Desktop running
- [ ] Python 3.13 installed
- [ ] GitHub Personal Access Token (with `repo` scope)
- [ ] Jira API Token
- [ ] Admin access to both GitHub repository and Jira project

---

## Step 1: Configure (5 minutes)

### 1.1 Create Configuration File

Copy this template and fill in your values:

```bash
# Save as: config.env (don't commit to git!)

# AWS Configuration
AWS_REGION="us-east-1"
STACK_NAME="jira-github-integration"

# GitHub Configuration
GITHUB_OWNER="your-username-or-org"
GITHUB_REPO="your-repo-name"
GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxx"

# Jira Configuration
JIRA_BASE_URL="https://your-domain.atlassian.net"
JIRA_EMAIL="your-email@example.com"
JIRA_API_TOKEN="ATATT3xFfGF0xxxxxxxxxxxx"

# User Mapping (Optional)
USER_MAPPING="jira.email@example.com:githubusername"
```

### 1.2 Update template.yaml

Edit [template.yaml](template.yaml) - Replace these lines:

```yaml
Environment:
  Variables:
    GITHUB_OWNER: your-username-or-org        # YOUR GITHUB USERNAME/ORG
    GITHUB_REPO: your-repo-name               # YOUR REPOSITORY NAME
    JIRA_BASE_URL: https://your-domain.atlassian.net  # YOUR JIRA URL
    JIRA_EMAIL: your-email@example.com        # YOUR JIRA EMAIL
    USER_MAPPING: "email@example.com:githubuser"  # YOUR USER MAPPINGS
    ACCEPTANCE_CRITERIA_FIELD: "customfield_10074"  # YOUR CUSTOM FIELD ID
```

**IMPORTANT:** Find your Acceptance Criteria field ID:

```bash
# Find your custom field ID
curl -u "YOUR_EMAIL:YOUR_JIRA_TOKEN" \
  "https://YOUR_DOMAIN.atlassian.net/rest/api/3/field" \
  | jq '.[] | select(.custom==true and (.name | contains("Acceptance"))) | {id, name}'
```

Copy the `id` value (e.g., `customfield_10034`) and use it for `ACCEPTANCE_CRITERIA_FIELD`.

**If you skip this step**, Acceptance Criteria will not sync! See [CUSTOM_FIELD_SETUP.md](CUSTOM_FIELD_SETUP.md) for details.

### 1.3 Update samconfig.toml

Edit [samconfig.toml](samconfig.toml):

```toml
[default.global.parameters]
region = "us-east-1"  # YOUR AWS REGION
```

---

## Step 2: Create AWS Secret (2 minutes)

```bash
# Replace YOUR_* placeholders with actual values
aws secretsmanager create-secret \
    --name jira-github-integration \
    --secret-string '{
        "github_token":"YOUR_GITHUB_TOKEN",
        "jira_api_token":"YOUR_JIRA_TOKEN"
    }' \
    --region YOUR_AWS_REGION
```

**Verify:**
```bash
aws secretsmanager describe-secret --secret-id jira-github-integration
```

---

## Step 3: Deploy (3 minutes)

```bash
# Build
sam build --use-container

# Deploy
sam deploy --guided
```

**When prompted:**
- Stack Name: `jira-github-integration` (or your choice)
- AWS Region: Your region (e.g., `us-east-1`)
- Confirm changes: `Y`
- Allow IAM role creation: `Y`
- Disable rollback: `N`
- Authorization warning: `Y`
- Save config: `Y`

**Copy the output URL:**
```
JiraWebhookUrl: https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/Prod/webhook
```

---

## Step 4: Configure Jira Webhook (2 minutes)

1. Go to: `https://your-domain.atlassian.net/plugins/servlet/webhooks`
2. Click **"Create a WebHook"**
3. Fill in:
   - **Name:** `GitHub Integration`
   - **Status:** ✅ Enabled
   - **URL:** Paste the JiraWebhookUrl from Step 3
   - **Events:** 
     - ✅ Issue → created
     - ✅ Issue → updated  
     - ✅ Comment → created
4. Click **"Create"**

---

## Step 5: Test (1 minute)

1. Create a Jira issue in your project
2. Add label: `sync-to-github`
3. Check your GitHub repository → Issues tab
4. ✅ New issue should appear!
5. Add a comment in Jira
6. ✅ Comment should appear in GitHub!

**Note:** This is one-way sync. GitHub comments do NOT sync back to Jira.

---

## Troubleshooting

### Issue Not Syncing?

**Check CloudWatch Logs:**
```bash
sam logs --stack-name jira-github-integration --tail
```

**Common Issues:**
1. ❌ Wrong label → Check `TARGET_LABEL` in template.yaml (default: `sync-to-github`)
2. ❌ Token invalid → Verify tokens in AWS Secrets Manager
3. ❌ Wrong repo name → Check `GITHUB_OWNER` and `GITHUB_REPO` in template.yaml
4. ❌ Permissions → GitHub token needs `repo` scope

### Test GitHub Token

```bash
curl -H "Authorization: token YOUR_GITHUB_TOKEN" \
     https://api.github.com/repos/OWNER/REPO
```

Should return repository details (not 404 or 403).

### Test Jira Token

```bash
curl -u "YOUR_JIRA_EMAIL:YOUR_JIRA_TOKEN" \
     "https://your-domain.atlassian.net/rest/api/3/myself"
```

Should return your user profile.

---

## Next Steps

- 📖 Read [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for detailed documentation
- ⚙️ Configure user mappings for assignee sync
- 🧪 Set up integration tests
- 📊 Create CloudWatch alarms for monitoring

---

## Commands Cheat Sheet

```bash
# View logs (real-time)
sam logs --stack-name jira-github-integration --tail

# Redeploy after changes
sam build --use-container && sam deploy

# Test locally
sam local invoke JiraWebhookFunction --event events/event.json

# Update secrets
aws secretsmanager update-secret \
    --secret-id jira-github-integration \
    --secret-string '{"github_token":"NEW_TOKEN","jira_api_token":"TOKEN"}'

# Delete everything
sam delete --stack-name jira-github-integration
```

---

## Configuration Reference

### Required Environment Variables (template.yaml)

| Variable | Description | Example |
|----------|-------------|---------|
| `GITHUB_OWNER` | GitHub username or org | `mycompany` |
| `GITHUB_REPO` | Repository name | `project-issues` |
| `JIRA_BASE_URL` | Jira instance URL | `https://company.atlassian.net` |
| `JIRA_EMAIL` | Jira account email | `admin@company.com` |
| `TARGET_LABEL` | Label to trigger sync | `sync-to-github` |
| `USER_MAPPING` | User email to GitHub username mapping | `email@example.com:githubuser` |

### User Mapping Format

```yaml
# Single user
USER_MAPPING: "john@company.com:johngithub"

# Multiple users (comma-separated)
USER_MAPPING: "john@company.com:johngithub,jane@company.com:janegithub"

# Using Jira Account IDs
USER_MAPPING: "712020:8dcd81ff-57c6:GithubUser"
```

---

## Support

- **Detailed Guide:** [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **AWS SAM Docs:** https://docs.aws.amazon.com/serverless-application-model/
- **GitHub API:** https://docs.github.com/en/rest
- **Jira API:** https://developer.atlassian.com/cloud/jira/platform/rest/v3/

---

**✅ You're all set!** Create a Jira issue with the `sync-to-github` label and watch the magic happen! 🚀
