# Configuration Template

Use this template to document your specific deployment configuration. Fill in the values and keep this secure (DO NOT commit to version control).

---

## Deployment Information

**Deployment Date:** `____________________`

**Deployed By:** `____________________`

**Environment:** `☐ Development  ☐ Staging  ☐ Production`

---

## AWS Configuration

| Parameter | Value |
|-----------|-------|
| **AWS Account ID** | |
| **AWS Region** | |
| **Stack Name** | `jira-github-integration` |
| **CloudFormation Stack ARN** | |
| **API Gateway Endpoint** | |
| **Lambda Function Name** | |
| **DynamoDB Table Name** | `jira-github-sync-state` |
| **Secrets Manager Secret Name** | `jira-github-integration` |

---

## GitHub Configuration

| Parameter | Value |
|-----------|-------|
| **GitHub Organization/Owner** | |
| **Repository Name** | |
| **Repository URL** | `https://github.com/___/___` |
| **GitHub Token Created** | Date: `____________________` |
| **Token Expiration** | Date: `____________________` |
| **Token Scopes** | `repo`, `write:discussion` |
| **Admin Contact** | |

---

## Jira Configuration

| Parameter | Value |
|-----------|-------|
| **Jira Instance URL** | `https://___________.atlassian.net` |
| **Jira Project Key** | |
| **Jira Project Name** | |
| **Jira Email** | |
| **Jira Token Created** | Date: `____________________` |
| **Jira Admin Contact** | |
| **Webhook ID** | |

---

## Integration Settings

| Parameter | Value |
|-----------|-------|
| **Sync Label** | `sync-to-github` |
| **Sync Direction** | `☑ Jira → GitHub only` |
| **Comment Sync** | `☑ Enabled (Jira → GitHub)  ☐ Disabled` |
| **User Mapping Enabled** | `☐ Yes  ☐ No` |
| **Acceptance Criteria Field ID** | `customfield_______` |

### Finding Your Acceptance Criteria Field ID

```bash
# Run this command to find your Jira custom field IDs:
curl -u "YOUR_JIRA_EMAIL:YOUR_API_TOKEN" \
  "https://YOUR_DOMAIN.atlassian.net/rest/api/3/field" \
  | jq '.[] | select(.custom==true and (.name | contains("Acceptance"))) | {id, name}'
```

**See [CUSTOM_FIELD_SETUP.md](CUSTOM_FIELD_SETUP.md) for detailed instructions.**

---

## User Mapping

Map Jira users to GitHub usernames for proper assignee attribution:

| Jira Email | Jira Display Name | GitHub Username | Verified |
|------------|-------------------|-----------------|----------|
| `example@company.com` | John Doe | `johndoe` | ☐ Yes ☐ No |
| | | | ☐ Yes ☐ No |
| | | | ☐ Yes ☐ No |
| | | | ☐ Yes ☐ No |
| | | | ☐ Yes ☐ No |

**USER_MAPPING Environment Variable:**
```
email1@company.com:githubuser1,email2@company.com:githubuser2
```

---

## Testing Checklist

- [ ] **Test 1:** Created Jira issue with `sync-to-github` label
  - Jira Issue Key: `____________________`
  - GitHub Issue Number: `____________________`
  - Status: ☐ ✅ Success  ☐ ❌ Failed
  - Notes: `____________________`

- [ ] **Test 2:** Added comment in Jira
  - Comment synced to GitHub: ☐ Yes  ☐ No
  - GitHub Comment ID: `____________________`
  - Status: ☐ ✅ Success  ☐ ❌ Failed
  - Notes: `____________________`

- [ ] **Test 3:** Added comment in GitHub
  - Comment synced to Jira: ☐ Yes  ☐ No
  - Jira Comment ID: `____________________`
  - Status: ☐ ✅ Success  ☐ ❌ Failed
  - Notes: `____________________`

- [ ] **Test 4:** User mapping verification
  - Jira Assignee: `____________________`
  - GitHub Assignee: `____________________`
  - Status: ☐ ✅ Success  ☐ ❌ Failed
  - Notes: `____________________`

- [ ] **Test 5:** CloudWatch Logs reviewed
  - Log Group: `____________________`
  - Errors Found: ☐ Yes  ☐ No
  - Notes: `____________________`

---

## Monitoring & Alerts

| Alert Type | Configured | SNS Topic | Recipients |
|------------|------------|-----------|------------|
| Lambda Errors | ☐ Yes ☐ No | | |
| Lambda Throttles | ☐ Yes ☐ No | | |
| API Gateway 4xx | ☐ Yes ☐ No | | |
| API Gateway 5xx | ☐ Yes ☐ No | | |
| DynamoDB Throttles | ☐ Yes ☐ No | | |

**CloudWatch Dashboard:** `____________________`

---

## Cost Estimate

**Monthly Volume:**
- Estimated Jira issues synced: `____________________`
- Estimated comments synced: `____________________`

**Estimated Monthly Costs:**
| Service | Cost |
|---------|------|
| Lambda | $ |
| API Gateway | $ |
| DynamoDB | $ |
| Secrets Manager | $ |
| CloudWatch Logs | $ |
| **Total** | **$** |

---

## Maintenance Schedule

| Task | Frequency | Last Performed | Next Due |
|------|-----------|----------------|----------|
| Rotate GitHub Token | 90 days | | |
| Rotate Jira Token | 90 days | | |
| Review CloudWatch Logs | Weekly | | |
| Review DynamoDB Usage | Monthly | | |
| Test Integration | Monthly | | |
| Review Cost Report | Monthly | | |
| Update Documentation | As needed | | |

---

## Rollback Plan

**Steps to Rollback:**
1. Remove webhook from Jira: `____________________` (Webhook URL)
2. Delete CloudFormation stack:
   ```bash
   aws cloudformation delete-stack --stack-name jira-github-integration --region ___
   ```
3. Delete AWS Secrets (if needed):
   ```bash
   aws secretsmanager delete-secret --secret-id jira-github-integration --force-delete-without-recovery
   ```
4. Backup DynamoDB data (if needed):
   ```bash
   aws dynamodb scan --table-name jira-github-sync-state > backup.json
   ```

---

## Support Contacts

| Role | Name | Email | Phone |
|------|------|-------|-------|
| **AWS Administrator** | | | |
| **GitHub Administrator** | | | |
| **Jira Administrator** | | | |
| **DevOps Lead** | | | |
| **On-Call Engineer** | | | |

---

## Troubleshooting Quick Reference

### CloudWatch Logs
```bash
sam logs --stack-name jira-github-integration --tail
```

### Check Secrets
```bash
aws secretsmanager get-secret-value --secret-id jira-github-integration
```

### Check DynamoDB
```bash
aws dynamodb scan --table-name jira-github-sync-state --max-items 10
```

### Test GitHub Connection
```bash
curl -H "Authorization: token YOUR_TOKEN" \
     https://api.github.com/repos/OWNER/REPO
```

### Test Jira Connection
```bash
curl -u "EMAIL:TOKEN" \
     "https://YOUR_DOMAIN.atlassian.net/rest/api/3/myself"
```

---

## Change History

| Date | Changed By | Change Description | Version |
|------|------------|-------------------|---------|
| | | Initial deployment | 1.0.0 |
| | | | |
| | | | |
| | | | |

---

## Notes & Special Considerations

```
(Add any environment-specific notes, special configurations, or known issues here)




```

---

## Approval Signatures

**Deployed By:**

Name: `____________________`  
Signature: `____________________`  
Date: `____________________`

**Approved By:**

Name: `____________________`  
Signature: `____________________`  
Date: `____________________`

---

**Document Version:** 1.0  
**Last Updated:** `____________________`  
**Next Review Date:** `____________________`
