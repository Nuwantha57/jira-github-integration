# 🎯 Jira-GitHub Scheduled Sync - Ready to Deploy!

## ✅ What's Changed

Your integration is now configured as a **scheduled sync** instead of a webhook:

**Before (Webhook):**

```
Jira → Webhook → API Gateway → Lambda → GitHub
```

**Now (Scheduled):**

```
EventBridge Scheduler → Lambda → Jira API → GitHub
                           ↓
                      DynamoDB (tracks synced issues)
```

---

## 📦 Deployment Package

**File Ready:** `lambda_deployment_package/jira-sync-lambda.zip` (1.02 MB)

**Location:**

```
C:\Jira_Github_Integration\SAM_Project\jira-github-integration\jira-github-integration\lambda_deployment_package\jira-sync-lambda.zip
```

**What's included:**

- ✅ Updated `app.py` with scheduled sync logic
- ✅ All dependencies (requests, boto3, etc.)
- ✅ DynamoDB integration for duplicate prevention
- ✅ Jira API polling
- ✅ Error handling and logging

---

## 🔧 Configuration Already Set

In `template.yaml` and the code:

- ✅ JIRA_BASE_URL: `https://nuwanthapiumal57.atlassian.net`
- ✅ JIRA_PROJECT_KEY: `TPFI`
- ✅ GITHUB_OWNER: `Nuwantha57`
- ✅ GITHUB_REPO: `jira-sync-test`
- ✅ TARGET_LABEL: `sync-to-github`

---

## 📝 What You Need to Provide

### 1. AWS Secrets Manager Secret

Create a secret named `jira-github-integration` with:

```json
{
  "github_token": "YOUR_GITHUB_TOKEN_HERE",
  "jira_email": "YOUR_EMAIL_HERE",
  "jira_api_token": "YOUR_JIRA_TOKEN_HERE"
}
```

**Where to get these:**

| Credential         | Where to Get It                                                                               |
| ------------------ | --------------------------------------------------------------------------------------------- |
| **GitHub Token**   | https://github.com/settings/tokens<br>→ Generate new token (classic)<br>→ Select `repo` scope |
| **Jira API Token** | https://id.atlassian.com/manage-profile/security/api-tokens<br>→ Create API token             |
| **Jira Email**     | Email used for your Atlassian account<br>(likely ending in @gmail.com or your company domain) |

### 2. Update Environment Variables (if needed)

Review these in Lambda configuration:

| Variable         | Current Value    | Update?                      |
| ---------------- | ---------------- | ---------------------------- |
| JIRA_PROJECT_KEY | `TPFI`           | ❓ Is this correct?          |
| GITHUB_OWNER     | `Nuwantha57`     | ❓ Is this correct?          |
| GITHUB_REPO      | `jira-sync-test` | ❓ Is this your target repo? |

---

## 🚀 Deployment Steps (5 minutes)

### Step 1: Create AWS Secrets Manager Secret

```bash
# AWS CLI
aws secretsmanager create-secret \
  --name jira-github-integration \
  --secret-string '{"github_token":"ghp_xxx","jira_email":"you@email.com","jira_api_token":"ATATTxxx"}'
```

Or use AWS Console → Secrets Manager → Store a new secret

### Step 2: Create DynamoDB Table

- Name: `jira-github-sync-state`
- Partition key: `jira_issue_key` (String)
- On-demand billing

### Step 3: Create Lambda Function

1. AWS Console → Lambda → Create function
2. Name: `jira-github-sync`
3. Runtime: Python 3.13
4. Upload `jira-sync-lambda.zip`
5. Set environment variables (see above)
6. Memory: 256 MB, Timeout: 1 minute
7. Add IAM permissions:
   - Secrets Manager: `GetSecretValue`
   - DynamoDB: `GetItem`, `PutItem`

### Step 4: Create EventBridge Schedule

1. EventBridge → Schedules → Create schedule
2. Name: `jira-sync-schedule`
3. Schedule: `rate(30 minutes)` (or `rate(1 hour)`, `rate(2 hours)`, etc.)
4. Target: Lambda function `jira-github-sync`

### Step 5: Test

1. Create a Jira issue in project `TPFI`
2. Add label `sync-to-github`
3. Wait for next scheduled run (or manually invoke Lambda)
4. Check GitHub repo for new issue!

---

## 🎯 How It Works

1. **EventBridge** triggers Lambda every X hours (you configure)
2. **Lambda** queries Jira API for issues with label `sync-to-github`
3. For each issue found:
   - Checks **DynamoDB** to see if already synced
   - If new, creates **GitHub issue**
   - Records in **DynamoDB** to prevent duplicates
4. Returns summary of what was synced

---

## 📊 Monitoring

**CloudWatch Logs** (Lambda → Monitor tab):

```
=== Starting scheduled Jira sync ===
Querying Jira with JQL: project = TPFI AND labels = "sync-to-github"
Found 3 Jira issues with label 'sync-to-github'
Creating GitHub issue for TPFI-123...
✓ Created GitHub issue: https://github.com/...
✓ Marked TPFI-123 as synced in DynamoDB
⊘ Skipping TPFI-124 - already synced
=== Sync completed: 1 synced, 2 skipped, 0 errors ===
```

---

## 🔍 Common Questions

**Q: How often should I schedule it?**
A: Depends on your needs:

- `rate(30 minutes)` - For active projects
- `rate(1 hour)` - Most common
- `rate(6 hours)` - For low-traffic projects
- `cron(0 9 * * ? *)` - Once daily at 9 AM UTC

**Q: What if I manually sync a Jira issue?**
A: Add the `sync-to-github` label to any Jira issue. Next scheduled run will pick it up.

**Q: Will it create duplicate GitHub issues?**
A: No! DynamoDB tracks synced issues. Each Jira issue only creates one GitHub issue.

**Q: Can I re-sync an issue?**
A: Yes! Delete the record from DynamoDB table, and it will sync again on next run.

**Q: What about Jira updates?**
A: Currently this is one-time sync. Updates to Jira issues won't update GitHub. (Could be enhanced later!)

**Q: Can I change the label?**
A: Yes! Update `TARGET_LABEL` environment variable to any label you want.

---

## 📖 Documentation Files

| File                  | Purpose                                  |
| --------------------- | ---------------------------------------- |
| `DEPLOYMENT_GUIDE.md` | Complete step-by-step setup instructions |
| `QUICK_START.md`      | Quick reference checklist                |
| `README.md`           | Project overview                         |

---

## ⚠️ Important Notes

1. **No webhook needed** - This is purely scheduled polling
2. **One-way sync** - Jira → GitHub only (no reverse)
3. **Label-based** - Only syncs issues with `sync-to-github` label
4. **Idempotent** - Won't create duplicates (DynamoDB prevents it)
5. **Credentials in Secrets Manager** - Never hardcode tokens!

---

## 🎉 You're Ready!

All you need now:

1. ✅ Upload `jira-sync-lambda.zip` to Lambda
2. ✅ Set up AWS Secrets Manager with your tokens
3. ✅ Create DynamoDB table
4. ✅ Configure EventBridge schedule
5. ✅ Test with a Jira issue!

**Questions?** Check `DEPLOYMENT_GUIDE.md` for detailed troubleshooting.

Good luck! 🚀
