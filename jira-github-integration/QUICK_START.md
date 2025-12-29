# Quick Setup Checklist

## ✅ Before You Start

- [ ] GitHub Personal Access Token (with `repo` scope)
- [ ] Jira API Token from https://id.atlassian.com/manage-profile/security/api-tokens
- [ ] Jira email address
- [ ] AWS Account access

---

## 📋 Setup Steps (5 minutes)

### 1️⃣ AWS Secrets Manager

Create secret named: `jira-github-integration`

```json
{
  "github_token": "ghp_xxxxxxxxxxxx",
  "jira_email": "your@email.com",
  "jira_api_token": "ATATTxxxxxxxxxxx"
}
```

### 2️⃣ DynamoDB Table

- Name: `jira-github-sync-state`
- Partition key: `jira_issue_key` (String)
- Billing: On-demand
- TTL: `ttl` attribute

### 3️⃣ Lambda Function

- Name: `jira-github-sync`
- Runtime: Python 3.13
- Timeout: 1 minute
- Memory: 256 MB
- Upload: `jira-sync-lambda.zip`

**Environment Variables:**

```
JIRA_BASE_URL=https://nuwanthapiumal57.atlassian.net
JIRA_PROJECT_KEY=TPFI
GITHUB_OWNER=Nuwantha57
GITHUB_REPO=jira-sync-test
TARGET_LABEL=sync-to-github
SECRET_NAME=jira-github-integration
DYNAMODB_TABLE=jira-github-sync-state
```

**IAM Permissions:**

- Read from Secrets Manager (`jira-github-integration`)
- Read/Write to DynamoDB (`jira-github-sync-state`)

### 4️⃣ EventBridge Scheduler

- Name: `jira-sync-schedule`
- Schedule: `rate(30 minutes)` (or your preference)
- Target: Lambda function `jira-github-sync`

### 5️⃣ Test

- Create Jira issue in project `TPFI`
- Add label `sync-to-github`
- Wait for next sync or trigger manually
- Check GitHub repo for new issue

---

## 🎯 What to Update

| Variable         | Current Value    | Your Value |
| ---------------- | ---------------- | ---------- |
| JIRA_PROJECT_KEY | `TPFI`           | ****\_**** |
| GITHUB_OWNER     | `Nuwantha57`     | ****\_**** |
| GITHUB_REPO      | `jira-sync-test` | ****\_**** |

---

## 📦 Files

- **Deployment Package**: `lambda_deployment_package/jira-sync-lambda.zip` (1.02 MB)
- **Full Guide**: `DEPLOYMENT_GUIDE.md`
- **Configuration**: `template.yaml`

---

## 🔗 Quick Links

- Jira Base URL: https://nuwanthapiumal57.atlassian.net
- GitHub Repo: https://github.com/Nuwantha57/jira-sync-test
- Get Jira Token: https://id.atlassian.com/manage-profile/security/api-tokens
- Get GitHub Token: https://github.com/settings/tokens

---

## 🆘 Quick Troubleshooting

**Lambda fails?**
→ Check CloudWatch Logs

**No secrets?**
→ Verify `jira-github-integration` exists in Secrets Manager

**No GitHub issues created?**
→ Ensure Jira issue has label `sync-to-github`

**Permission denied?**
→ Check Lambda IAM role has Secrets Manager + DynamoDB access
