# AWS Lambda Deployment Guide

## ✅ Deployment Package Ready!

**File:** `lambda-function.zip` (1.01 MB)
**Location:** `c:\Jira_Github_Integration\SAM_Project\jira-github-integration\jira-github-integration\lambda-function.zip`

---

## Upload to AWS Lambda Console

### Step 1: Open AWS Lambda Console

1. Go to: https://console.aws.amazon.com/lambda/
2. Select region: **eu-north-1** (Stockholm)
3. Find your function: **JiraWebhookFunction**

### Step 2: Upload the ZIP file

1. Click on the function name
2. Scroll to **"Code source"** section
3. Click **"Upload from"** → **".zip file"**
4. Click **"Upload"** button
5. Select: `lambda-function.zip`
6. Click **"Save"**

### Step 3: Verify Handler Configuration

Make sure the handler is set to: `app.lambda_handler`

- Go to **"Runtime settings"** section
- Click **"Edit"**
- Handler should be: `app.lambda_handler`
- Click **"Save"**

### Step 4: Verify Environment Variables

Check that these are set:

- `GITHUB_OWNER`: Nuwantha57
- `GITHUB_REPO`: jira-sync-test
- `JIRA_BASE_URL`: https://nuwanthapiumal57.atlassian.net
- `TARGET_LABEL`: sync-to-github
- `SECRET_NAME`: jira-github-integration

---

## After Deployment

### Test Security (Expected Results)

```powershell
.\test-security.ps1 -WebhookUrl "https://lmccuh0gra.execute-api.eu-north-1.amazonaws.com/default/JiraWebhookFunction" -JiraSecret "YOUR_WEBHOOK_SECRET"
```

**Expected:**

- ✅ Test 1 (No signature): **401 Unauthorized**
- ✅ Test 2 (Invalid signature): **401 Unauthorized**
- ✅ Test 3 (Valid signature): **200 OK**
- ✅ Test 4 (Malformed JSON): **400 Bad Request**

### Run Load Testing

```powershell
.\test-load.ps1 -WebhookUrl "https://lmccuh0gra.execute-api.eu-north-1.amazonaws.com/default/JiraWebhookFunction" -ConcurrentRequests 25
```

### Run Integration Testing

```powershell
.\test-integration.ps1 `
    -WebhookUrl "https://lmccuh0gra.execute-api.eu-north-1.amazonaws.com/default/JiraWebhookFunction" `
    -GitHubToken "YOUR_GITHUB_TOKEN" `
    -GitHubOwner "Nuwantha57" `
    -GitHubRepo "jira-sync-test"
```

---

## What's Included in the ZIP

✅ Updated `app.py` with signature verification
✅ All dependencies:

- requests
- urllib3
- certifi
- charset_normalizer
- idna

Total: 194 files (1.01 MB)

---

## Troubleshooting

**Issue:** Function returns 500 error

- Check CloudWatch logs for errors
- Verify `webhook_secret` exists in Secrets Manager

**Issue:** All requests return 401

- Make sure webhook secret in AWS matches Jira
- Check CloudWatch logs for "Signature mismatch" messages

**Issue:** Old code still running

- Wait 30 seconds after upload for changes to take effect
- Try invoking the function directly in AWS Console test
