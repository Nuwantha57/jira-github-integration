# Task 01 - Jira to GitHub Integration - Daily Deliverables

**Date:** December 22, 2025  
**Developer:** Nuwantha Karunarathna  
**Project:** Jira-GitHub Integration using AWS Lambda

---

## ✅ Deliverables Completed

### 1. Lambda Function Created

**Function Details:**

- **Name:** `JiraWebhookFunction`
- **Runtime:** Python 3.13
- **Region:** eu-north-1
- **Handler:** `app.lambda_handler`
- **Timeout:** 30 seconds
- **Memory:** 256 MB

**Environment Variables Configured:**

```
GITHUB_OWNER = Nuwantha57
GITHUB_REPO = jira-sync-test
JIRA_BASE_URL = https://eyepax.atlassian.net
TARGET_LABEL = sync-to-github
SECRET_NAME = jira-github-integration
```

**IAM Permissions:**

- SecretsManagerReadWrite (for GitHub token retrieval)
- Basic Lambda execution role

**Security:**

- GitHub Personal Access Token stored securely in AWS Secrets Manager
- Secret Name: `jira-github-integration`
- ARN: `arn:aws:secretsmanager:eu-north-1:811146558818:secret:jira-github-integration-HG8n4v`

---

### 2. API Gateway Webhook URL

**Endpoint URL:**

```
https://lmccuh0gra.execute-api.eu-north-1.amazonaws.com/default/JiraWebhookFunction
```

**Configuration:**

- **Type:** REST API
- **Method:** POST
- **Integration:** Lambda Function (JiraWebhookFunction)
- **Authentication:** None (Public endpoint)
- **Region:** eu-north-1

**Usage:**

- Ready for Jira webhook configuration
- Accepts POST requests with Jira issue data
- Returns JSON response with created GitHub issue URL

---

### 3. Test Environment Ready

**Testing Completed:**
✅ **Manual Test via PowerShell Script**

- Test Date: December 22, 2025
- Test Result: SUCCESS
- GitHub Issue Created: https://github.com/Nuwantha57/jira-sync-test/issues/8

**Test Script Location:**
`test-webhook.ps1` (included in project)

**Test Capabilities:**

- Simulates Jira webhook payload
- Tests label filtering (sync-to-github)
- Validates GitHub API integration
- Verifies field mapping

**AWS Console Test:**

- Test event configured in Lambda console
- CloudWatch Logs enabled for monitoring
- Can be executed directly from AWS Console

**Verification:**

- Lambda execution: ✅ Successful
- GitHub issue creation: ✅ Working
- Label mapping: ✅ Correct
- Jira link in issue body: ✅ Present

---

### 4. Label Mapping Document

#### **Jira Label → GitHub Label Mapping**

| Jira Label        | GitHub Label         | Category   |
| ----------------- | -------------------- | ---------- |
| `bug`             | `type:bug`           | Issue Type |
| `feature`         | `type:feature`       | Issue Type |
| `backend`         | `component:backend`  | Component  |
| `frontend`        | `component:frontend` | Component  |
| `high-priority`   | `priority:high`      | Priority   |
| `medium-priority` | `priority:medium`    | Priority   |
| `low-priority`    | `priority:low`       | Priority   |

#### **Special Labels**

**Trigger Label:**

- `sync-to-github` - Must be present for issue to sync to GitHub (not copied to GitHub)

#### **Mapping Logic**

**Implementation:** `map_labels()` function in `app.py`

```python
def map_labels(jira_labels):
    mapping = {
        "bug": "type:bug",
        "feature": "type:feature",
        "backend": "component:backend",
        "frontend": "component:frontend",
        "high-priority": "priority:high",
        "medium-priority": "priority:medium",
        "low-priority": "priority:low"
    }
    # Filters out 'sync-to-github' trigger label
    return [mapping.get(label, label) for label in jira_labels if label != "sync-to-github"]
```

#### **Example:**

**Jira Issue Labels:**

```
["sync-to-github", "bug", "backend", "high-priority"]
```

**GitHub Issue Labels:**

```
["type:bug", "component:backend", "priority:high"]
```

_(Note: sync-to-github is filtered out)_

---

## 📊 Integration Flow

```
┌──────────────┐
│  Jira Issue  │
│  (Created/   │
│   Updated)   │
└──────┬───────┘
       │
       │ Webhook POST
       ▼
┌─────────────────────────────────────────────┐
│  API Gateway                                 │
│  https://lmccuh0gra.execute-api...          │
└──────┬──────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────┐
│  Lambda Function (JiraWebhookFunction)      │
│  - Check for 'sync-to-github' label         │
│  - Extract Jira fields                      │
│  - Map labels                               │
│  - Get GitHub token from Secrets Manager    │
└──────┬──────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────┐
│  GitHub REST API                            │
│  POST /repos/{owner}/{repo}/issues          │
└──────┬──────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────┐
│  GitHub Issue Created                       │
│  - Title from Jira summary                  │
│  - Description from Jira description        │
│  - Mapped labels                            │
│  - Jira link in body                        │
│  - Priority & Assignee info                 │
└─────────────────────────────────────────────┘
```

---

## 🔧 Technical Implementation

**Architecture Components:**

1. **AWS Lambda** - Core integration logic
2. **API Gateway** - REST endpoint for webhooks
3. **AWS Secrets Manager** - Secure token storage
4. **GitHub REST API** - Issue creation
5. **Python 3.13** - Runtime environment

**Dependencies:**

- `requests` - HTTP library for GitHub API calls
- `boto3` - AWS SDK for Secrets Manager access

**Code Structure:**

```
jira-github-integration/
├── jira_handler/
│   ├── app.py                  # Main Lambda handler
│   └── requirements.txt        # Python dependencies
├── events/
│   └── event.json             # Test event payload
├── test-webhook.ps1           # Testing script
├── template.yaml              # SAM template
└── lambda-package.zip         # Deployment package
```

---

## 📝 GitHub Issue Format

**Example Created Issue:**

**Title:**

```
Test Issue from Console Deployment
```

**Body:**

```markdown
Testing Jira to GitHub integration

Acceptance Criteria:

- Lambda works
- GitHub issue created
- All fields mapped

---

### Jira Details

- **Issue**: [TEST-100](https://eyepax.atlassian.net/browse/TEST-100)
- **Priority**: High
- **Assignee**: Nuwantha
```

**Labels:**

```
["component:backend", "priority:high"]
```

---

## ✅ Next Steps

### For Production Deployment:

1. **Configure Jira Webhook:**

   - URL: `https://lmccuh0gra.execute-api.eu-north-1.amazonaws.com/default/JiraWebhookFunction`
   - Events: Issue Created, Issue Updated
   - JQL Filter: `labels = sync-to-github`

2. **Monitoring Setup:**

   - Enable CloudWatch alarms for Lambda errors
   - Set up CloudWatch Logs retention policy
   - Configure SNS notifications for failures

3. **Additional Enhancements (Optional):**
   - Add authentication to API Gateway
   - Implement rate limiting
   - Add bi-directional sync (GitHub → Jira)

---

## 📈 Test Results

**Test Execution Summary:**

| Test Type          | Status  | Details                              |
| ------------------ | ------- | ------------------------------------ |
| Lambda Function    | ✅ PASS | Successfully deployed and executable |
| API Gateway        | ✅ PASS | Endpoint accessible and responding   |
| GitHub Integration | ✅ PASS | Issue #8 created successfully        |
| Label Mapping      | ✅ PASS | All labels mapped correctly          |
| Secrets Manager    | ✅ PASS | Token retrieved successfully         |
| Error Handling     | ✅ PASS | Returns proper error messages        |

**Sample Response:**

```json
{
  "statusCode": 200,
  "body": {
    "message": "GitHub issue created",
    "url": "https://github.com/Nuwantha57/jira-sync-test/issues/8"
  }
}
```

---

## 📁 Project Files Delivered

1. ✅ `app.py` - Lambda function code
2. ✅ `requirements.txt` - Python dependencies
3. ✅ `template.yaml` - SAM/CloudFormation template
4. ✅ `test-webhook.ps1` - Testing script
5. ✅ `event.json` - Sample test event
6. ✅ `lambda-package.zip` - Deployment package
7. ✅ `DELIVERABLES.md` - This document

---

**Status:** ✅ **COMPLETED & PRODUCTION READY**

**Developer:** Nuwantha Karunarathna  
**Supervisor:** [Your Supervisor Name]  
**Date:** December 22, 2025
