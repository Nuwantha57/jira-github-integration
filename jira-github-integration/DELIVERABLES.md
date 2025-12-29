# Task 01 - Jira to GitHub Integration - Final Deliverables

**Date Started:** December 22, 2025  
**Date Completed:** December 29, 2025  
**Developer:** Nuwantha Karunarathna  
**Project:** Jira-GitHub Integration using AWS Lambda

---

## 🎯 Project Overview

**Two Integration Methods Implemented:**

1. **Event-Driven (Webhook)** - Real-time sync when Jira issues are created/updated
2. **Scheduled (EventBridge)** - Periodic sync every 30 minutes (configurable)

**Both methods share:**

- DynamoDB for duplicate prevention
- AWS Secrets Manager for credentials
- Same GitHub repository target
- Label-based filtering (`sync-to-github`)

---

## ✅ Deliverables Completed

### 1. Lambda Functions Created

#### **A. Webhook Lambda (Event-Driven)**

**Function Details:**

- **Name:** `JiraWebhookFunction`
- **Runtime:** Python 3.13
- **Region:** eu-north-1
- **Handler:** `app.lambda_handler`
- **Timeout:** 30 seconds
- **Memory:** 128 MB
- **Trigger:** API Gateway (Jira Webhook)

**Environment Variables:**

```
GITHUB_OWNER = Nuwantha57
GITHUB_REPO = jira-sync-test
JIRA_BASE_URL = https://nuwanthapiumal57.atlassian.net
JIRA_PROJECT_KEY = SCRUM
TARGET_LABEL = sync-to-github
SECRET_NAME = jira-github-integration
DYNAMODB_TABLE = jira-github-sync-state
```

**Features:**

- ✅ Real-time sync on Jira webhook events
- ✅ DynamoDB duplicate prevention
- ✅ Handles multiple webhook events (issue_created, issue_updated)
- ✅ Validates label before processing
- ✅ Error handling and logging

**Deployment Package:** `webhook-fixed.zip` (1.03 MB)

---

#### **B. Scheduled Lambda (EventBridge)**

**Function Details:**

- **Name:** `jira-github-sync`
- **Runtime:** Python 3.13
- **Region:** eu-north-1
- **Handler:** `app.lambda_handler`
- **Timeout:** 60 seconds
- **Memory:** 256 MB
- **Trigger:** EventBridge Scheduler (every 30 minutes)

**Environment Variables:**

```
GITHUB_OWNER = Nuwantha57
GITHUB_REPO = jira-sync-test
JIRA_BASE_URL = https://nuwanthapiumal57.atlassian.net
JIRA_PROJECT_KEY = SCRUM
TARGET_LABEL = sync-to-github
SECRET_NAME = jira-github-integration
DYNAMODB_TABLE = jira-github-sync-state
```

**Features:**

- ✅ Polls Jira API every 30 minutes
- ✅ Processes multiple issues in batch
- ✅ DynamoDB duplicate prevention
- ✅ Continues on error (processes remaining issues)
- ✅ Returns sync summary with statistics

**Deployment Package:** `jira-sync-COMPLETE.zip` (1.02 MB)

---

### 2. DynamoDB Table

**Table Details:**

- **Name:** `jira-github-sync-state`
- **Partition Key:** `jira_issue_key` (String)
- **Billing Mode:** On-demand
- **TTL:** Enabled (90 days auto-cleanup)
- **Purpose:** Prevents duplicate GitHub issues across both Lambda functions

**Schema:**

```
{
  "jira_issue_key": "SCRUM-123",
  "github_issue_url": "https://github.com/.../issues/25",
  "synced_at": "2025-12-29T08:22:12.730Z",
  "ttl": 1748256132
}
```

---

### 3. API Gateway Webhook URL

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

### 4. EventBridge Scheduler

**Schedule Configuration:**

- **Name:** `jira-sync-schedule`
- **Schedule:** `rate(30 minutes)` (configurable)
- **Target:** Lambda function `jira-github-sync`
- **Status:** Enabled
- **Timezone:** UTC

**Execution History:**

- Successful runs: Multiple
- Issues synced: 2+ confirmed
- Errors: Minor (null field handling - fixed)

---

### 5. AWS Secrets Manager

**Secret Details:**

- **Name:** `jira-github-integration`
- **ARN:** `arn:aws:secretsmanager:eu-north-1:811146558818:secret:jira-github-integration-HG8n4v`
- **Region:** eu-north-1

**Secret Structure:**

```json
{
  "github_token": "ghp_xxxxxxxxxxxxx",
  "jira_email": "your@email.com",
  "jira_api_token": "ATATTxxxxxxxxxxxxx"
}
```

**Security:**

- Encrypted at rest
- IAM policy controls access
- Both Lambda functions have read access

---

### 6. Test Environment & Results

**Testing Completed:**

✅ **Webhook Lambda Testing**

- Test Date: December 29, 2025
- Test Result: SUCCESS (after duplicate prevention fix)
- GitHub Issues Created: #20, #21, #23, #24
- Duplicate Prevention: Working after fix

✅ **Scheduled Lambda Testing**

- Test Date: December 29, 2025
- Test Result: SUCCESS
- Jira Issues Found: 3 (SCRUM-7, SCRUM-6, SCRUM-1)
- Synced Successfully: 2 issues
- Errors Fixed: Null field handling

✅ **DynamoDB Integration**

- Records Created: Multiple
- Duplicate Prevention: Working
- TTL: Configured (90 days)

✅ **Jira API Integration**

- API Version: v3 (`/rest/api/3/search/jql`)
- Authentication: Working
- JQL Queries: Successful
- Project: SCRUM

✅ **GitHub API Integration**

- Issues Created: 20+
- Repository: Nuwantha57/jira-sync-test
- Labels Mapped: Correctly
- Jira Links: Present in issue body

---

### 7. Label Mapping Configuration

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

## 📊 Integration Flows

### **Method 1: Event-Driven (Webhook)**

```
┌──────────────────────────────────────┐
│  Jira Issue Created/Updated          │
│  with 'sync-to-github' label         │
└──────────────┬───────────────────────┘
               │
               │ HTTP POST Webhook
               ▼
┌──────────────────────────────────────┐
│  API Gateway                         │
│  POST /JiraWebhookFunction           │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  Lambda: JiraWebhookFunction         │
│  1. Parse webhook payload            │
│  2. Check DynamoDB (duplicate?)      │
│  3. Validate 'sync-to-github' label  │
│  4. Get tokens from Secrets Manager  │
│  5. Create GitHub issue              │
│  6. Mark as synced in DynamoDB       │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  GitHub Issue Created                │
│  - Real-time (within seconds)        │
│  - Includes Jira details & link      │
└──────────────────────────────────────┘
```

### **Method 2: Scheduled Sync (EventBridge)**

```
┌──────────────────────────────────────┐
│  EventBridge Scheduler               │
│  (Triggers every 30 minutes)         │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  Lambda: jira-github-sync            │
│  1. Get credentials from Secrets     │
│  2. Query Jira API (JQL search)      │
│  3. Find all issues with label       │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  For Each Jira Issue:                │
│  1. Check DynamoDB (already synced?) │
│  2. If new → Create GitHub issue     │
│  3. Mark as synced in DynamoDB       │
│  4. Continue to next issue           │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  Sync Summary Returned               │
│  - Total processed: X                │
│  - Synced: X                         │
│  - Skipped: X                        │
│  - Errors: X                         │
└──────────────────────────────────────┘
```

### **Shared: DynamoDB Duplicate Prevention**

```
┌──────────────────────────────────────┐
│  DynamoDB Table                      │
│  jira-github-sync-state              │
│                                      │
│  Records:                            │
│  ┌────────────────────────────────┐ │
│  │ SCRUM-7 → GitHub Issue #20     │ │
│  │ SCRUM-6 → GitHub Issue #21     │ │
│  │ SCRUM-8 → GitHub Issue #23     │ │
│  └────────────────────────────────┘ │
│                                      │
│  Prevents both methods from creating │
│  duplicate issues for same Jira key  │
└──────────────────────────────────────┘
```

---

       │ Webhook POST
       ▼

┌─────────────────────────────────────────────┐
│ API Gateway │
│ https://lmccuh0gra.execute-api... │
└──────┬──────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────┐
│ Lambda Function (JiraWebhookFunction) │
│ - Check for 'sync-to-github' label │
│ - Extract Jira fields │
│ - Map labels │
│ - Get GitHub token from Secrets Manager │
└──────┬──────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────┐
│ GitHub REST API │
│ POST /repos/{owner}/{repo}/issues │
└──────┬──────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────┐
│ GitHub Issue Created │
│ - Title from Jira summary │
│ - Description from Jira description │
│ - Mapped labels │
│ - Jira link in body │
│ - Priority & Assignee info │
└─────────────────────────────────────────────┘

```

---

## 🔧 Technical Implementation

**Architecture Components:**

1. **AWS Lambda (2 functions)** - Webhook + Scheduled sync
2. **API Gateway** - REST endpoint for webhooks (Method 1)
3. **EventBridge Scheduler** - Periodic trigger (Method 2)
4. **DynamoDB** - Duplicate tracking across both methods
5. **AWS Secrets Manager** - Secure credential storage
6. **Jira REST API v3** - Query issues with JQL
7. **GitHub REST API** - Issue creation
8. **Python 3.13** - Runtime environment

**Dependencies:**
- `requests` - HTTP library for API calls
- `boto3` - AWS SDK for Secrets Manager and DynamoDB

**Key Features:**
- ✅ Idempotent (no duplicates)
- ✅ Two trigger methods (webhook + scheduled)
- ✅ Label-based filtering
- ✅ Comprehensive error handling
- ✅ Null-safe field extraction
- ✅ TTL-based cleanup (90 days)

**Code Structure:**
```

jira-github-integration/
├── jira_handler/
│ ├── app.py # Webhook Lambda handler
│ └── requirements.txt # Python dependencies
├── lambda_deployment_package/
│ ├── app.py # Scheduled Lambda handler
│ └── [dependencies] # requests, boto3, etc.
├── lambda_package/
│ ├── app.py # Webhook with dependencies
│ └── [dependencies]
├── events/
│ └── event.json # Test event payloads
├── test-webhook.ps1 # PowerShell test script
├── template.yaml # SAM/CloudFormation template
├── webhook-fixed.zip # Webhook deployment (1.03 MB)
├── jira-sync-COMPLETE.zip # Scheduled deployment (1.02 MB)
├── DEPLOYMENT_GUIDE.md # Full setup instructions
├── QUICK_START.md # Quick reference checklist
└── READY_TO_DEPLOY.md # Deployment overview

```

---

## 📝 GitHub Issue Format

**Example Created Issue:**

**Title:**
```

Fix login button alignment on mobile

````

**Body:**
```markdown
The login button is misaligned on mobile devices with screen width < 768px.

Steps to reproduce:
1. Open app on mobile device
2. Navigate to login page
3. Observe button position

---

### Jira Details
- **Jira Issue**: [SCRUM-7](https://nuwanthapiumal57.atlassian.net/browse/SCRUM-7)
- **Priority**: High
- **Assignee**: John Doe
````

**Labels:**

```
["type:bug", "component:frontend", "priority:high"]
```

---

### Jira Details

- **Issue**: [TEST-100](https://eyepax.atlassian.net/browse/TEST-100)
- **Priority**: High
- **Assignee**: Nuwantha

```

**Labels:**

```

["component:backend", "priority:high"]

````


## 📈 Test Results & Production Status

### **Test Execution Summary**

| Component | Method | Status | Details |
|-----------|--------|--------|---------|
| **Webhook Lambda** | Event-Driven | ✅ PASS | Real-time sync working |
| **Scheduled Lambda** | EventBridge | ✅ PASS | Polling & batch sync working |
| **DynamoDB** | Both | ✅ PASS | Duplicate prevention working |
| **API Gateway** | Webhook | ✅ PASS | Endpoint accessible |
| **EventBridge** | Scheduled | ✅ PASS | Triggers every 30 minutes |
| **Jira API v3** | Both | ✅ PASS | `/rest/api/3/search/jql` working |
| **GitHub API** | Both | ✅ PASS | 20+ issues created successfully |
| **Secrets Manager** | Both | ✅ PASS | Credentials retrieved successfully |
| **Label Mapping** | Both | ✅ PASS | All labels mapped correctly |
| **Error Handling** | Both | ✅ PASS | Null-safe, continues on error |

### **Sample Responses**

**Webhook Lambda Response:**
```json
{
  "statusCode": 200,
  "body": {
    "message": "GitHub issue created successfully",
    "jira_issue": "SCRUM-8",
    "github_issue_url": "https://github.com/Nuwantha57/jira-sync-test/issues/23"
  }
}
````

**Scheduled Lambda Response:**

```json
{
  "statusCode": 200,
  "body": {
    "status": "completed",
    "synced": 2,
    "skipped": 0,
    "errors": 0,
    "error_details": [],
    "total_processed": 3
  }
}
```

### **Known Issues & Fixes**

| Issue                       | Status     | Solution                             |
| --------------------------- | ---------- | ------------------------------------ |
| Webhook creating duplicates | ✅ FIXED   | Added DynamoDB check before creation |
| Jira API v2 deprecated      | ✅ FIXED   | Updated to `/rest/api/3/search/jql`  |
| Null priority field error   | ✅ FIXED   | Added null-safe field extraction     |
| Multiple webhook events     | ✅ HANDLED | DynamoDB prevents duplicate creation |

---

## ✅ Production Readiness Checklist

### **Completed:**

- [x] Two Lambda functions deployed and tested
- [x] DynamoDB table created with TTL
- [x] API Gateway configured and accessible
- [x] EventBridge Scheduler configured (30 min interval)
- [x] Secrets Manager with credentials
- [x] IAM permissions configured
- [x] Duplicate prevention implemented
- [x] Error handling and logging
- [x] Null-safe field extraction
- [x] CloudWatch Logs enabled
- [x] Test environment validated
- [x] Documentation complete

### **Optional Enhancements:**

- [ ] Add API Gateway authentication (API key/IAM)
- [ ] Implement rate limiting
- [ ] Add SNS notifications for failures
- [ ] Set up CloudWatch alarms
- [ ] Add bi-directional sync (GitHub → Jira)
- [ ] Implement webhook signature verification
- [ ] Add custom field mapping
- [ ] Create admin dashboard

---

## 📁 Project Files Delivered

### **Lambda Deployment Packages**

1. ✅ `webhook-fixed.zip` (1.03 MB) - Webhook Lambda with DynamoDB duplicate prevention
2. ✅ `jira-sync-COMPLETE.zip` (1.02 MB) - Scheduled Lambda with batch processing

### **Source Code**

3. ✅ `jira_handler/app.py` - Webhook Lambda source code
4. ✅ `lambda_deployment_package/app.py` - Scheduled Lambda source code
5. ✅ `jira_handler/requirements.txt` - Python dependencies

### **Infrastructure**

6. ✅ `template.yaml` - SAM/CloudFormation template
7. ✅ `samconfig.toml` - SAM CLI configuration

### **Testing**

8. ✅ `test-webhook.ps1` - PowerShell testing script
9. ✅ `events/event.json` - Sample test event

### **Documentation**

10. ✅ `DELIVERABLES.md` - This document (comprehensive deliverables)
11. ✅ `DEPLOYMENT_GUIDE.md` - Complete step-by-step setup guide
12. ✅ `QUICK_START.md` - Quick reference checklist
13. ✅ `READY_TO_DEPLOY.md` - Deployment overview
14. ✅ `README.md` - Project overview

---

## 🎯 Implementation Comparison

| Feature                  | Webhook (Event-Driven)      | Scheduled (EventBridge) |
| ------------------------ | --------------------------- | ----------------------- |
| **Trigger**              | Jira webhook events         | Every 30 minutes        |
| **Latency**              | Real-time (< 5 seconds)     | Up to 30 minutes        |
| **Processing**           | Single issue per event      | Batch (multiple issues) |
| **API Calls**            | Per webhook event           | Periodic polling        |
| **Cost**                 | Per webhook invocation      | Fixed schedule cost     |
| **Reliability**          | Depends on webhook delivery | Guaranteed execution    |
| **Best For**             | Immediate sync needs        | Scheduled/batch sync    |
| **Duplicate Prevention** | ✅ DynamoDB                 | ✅ DynamoDB             |

---

## 📊 Project Statistics

- **Total Development Time:** 7 days (Dec 22-29, 2025)
- **Lambda Functions:** 2
- **API Endpoints:** 1 (API Gateway)
- **Scheduled Jobs:** 1 (EventBridge)
- **Database Tables:** 1 (DynamoDB)
- **Secrets:** 1 (Secrets Manager)
- **GitHub Issues Created:** 20+
- **Jira Project:** SCRUM
- **GitHub Repository:** Nuwantha57/jira-sync-test
- **Deployment Packages:** 2
- **Lines of Code:** ~600+
- **Documentation Pages:** 4

---

## 🚀 Quick Start Guide

### **For Webhook Method:**

1. Upload `webhook-fixed.zip` to Lambda
2. Configure environment variables
3. Add DynamoDB permissions
4. Configure Jira webhook to API Gateway URL
5. Test by creating Jira issue with `sync-to-github` label

### **For Scheduled Method:**

1. Upload `jira-sync-COMPLETE.zip` to Lambda
2. Configure environment variables
3. Add DynamoDB + Secrets Manager permissions
4. Create EventBridge schedule (30 minutes)
5. Test by adding `sync-to-github` label to existing Jira issues

---

**Status:** ✅ **PRODUCTION READY - BOTH METHODS FULLY FUNCTIONAL**

**Developer:** Nuwantha Karunarathna  
**Completion Date:** December 29, 2025  
**Project:** Jira-GitHub Integration (Dual Method Implementation)
