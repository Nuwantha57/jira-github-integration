# How to Update AWS Secret with Jira API Token

## Step 1: Create GitHub Personal Access Token

1. Go to: https://github.com/settings/tokens
2. Click **Generate new token** (classic)
3. Give it a name: "Jira Integration"
4. Select scopes: `repo` (full control of repositories)
5. Click **Generate token**
6. **Copy the token** (you won't see it again!)

---

## Step 2: Update AWS Secrets Manager

### Option A: Using AWS Console

1. Go to: https://console.aws.amazon.com/secretsmanager
2. Find secret: `jira-github-integration`
3. Click **Retrieve secret value**
4. Click **Edit**
5. Replace the JSON with:

```json
{
  "github_token": "YOUR_GITHUB_PAT_TOKEN"
}
```

6. Click **Save**

---

### Option B: Using AWS CLI (Recommended)

Run this PowerShell command (replace with your token):

```powershell
aws secretsmanager update-secret `
  --secret-id jira-github-integration `
  --secret-string '{\"github_token\":\"YOUR_GITHUB_PAT_TOKEN\"}'
```

---

## Step 3: Verify

After updating, verify the secret with:

```powershell
aws secretsmanager get-secret-value --secret-id jira-github-integration
```

You should see only the `github_token` in the response.

---

## Note: Why No Jira API Token?

Jira webhooks automatically send all issue data to your Lambda function, so you don't need to authenticate back to Jira. The Jira API token would only be needed if you wanted to:

- Fetch additional data from Jira
- Update Jira issues from GitHub
- Add comments to Jira issues
- Transition issues to different statuses

For this basic integration (Jira → GitHub sync), only the GitHub token is required.

```powershell
aws secretsmanager get-secret-value --secret-id jira-github-integration --query SecretString --output text
```

You should see all three keys: `github_token`, `jira_email`, `jira_api_token`

---

## Important Notes

- ✅ Keep your Jira API token secure
- ✅ Jira API token format: `ATATT3xFfGF0...` (starts with ATATT)
- ✅ Email must match your Jira account: `nuwantha.k@eyepax.com`
- ⚠️ Don't share these tokens in code or commits
