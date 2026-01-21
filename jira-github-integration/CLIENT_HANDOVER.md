# Client Handover Document

## Project: Jira-GitHub Integration

**Date:** January 20, 2026  
**Version:** 1.0.0  
**Status:** Ready for Production Deployment

---

## Executive Summary

This package contains a complete, production-ready serverless application that syncs Jira Cloud issues and comments to GitHub. The integration automatically creates GitHub issues from labeled Jira issues and syncs comments one-way (Jira → GitHub), with intelligent user mapping and duplicate prevention.

### Key Benefits
- ✅ **Automated Issue Sync:** Issues labeled in Jira automatically create GitHub issues
- ✅ **Comment Sync:** Jira comments automatically appear in GitHub (one-way)
- ✅ **User Attribution:** Maps Jira users to GitHub users for proper assignment
- ✅ **Zero Maintenance:** Serverless architecture with automatic scaling
- ✅ **Cost Effective:** ~$5-10/month for typical usage (1000+ syncs)
- ✅ **Secure:** Tokens stored in AWS Secrets Manager, no credentials in code

---

## What's Included

### Documentation (Complete Suite)
1. **INDEX.md** - Documentation navigation and overview
2. **QUICKSTART.md** - 5-minute deployment guide
3. **DEPLOYMENT_GUIDE.md** - Comprehensive 50-page reference manual
4. **TROUBLESHOOTING.md** - Complete troubleshooting guide with solutions
5. **CONFIGURATION_TEMPLATE.md** - Deployment documentation worksheet
6. **README.md** - Project overview and features

### Code & Configuration
- **template.yaml** - AWS SAM infrastructure template (configured)
- **template.yaml.example** - Clean template with detailed comments
- **samconfig.toml** - AWS SAM CLI configuration
- **jira_handler/app.py** - Lambda function (1845 lines, fully commented)
- **jira_handler/requirements.txt** - Python dependencies
- **events/event.json** - Sample webhook payload for testing

### Testing
- **tests/unit/** - Unit test suite
- **tests/integration/** - Integration test suite

---

## Important Client-Specific Configuration

### ⚠️ Critical: Custom Field Configuration

**The Acceptance Criteria field ID is unique to each Jira instance.** The default value (`customfield_10074`) is from the original Jira account and **will NOT work** on your Jira instance.

**You MUST configure your specific field ID:**

1. **Find your custom field ID:**
   ```bash
   curl -u "YOUR_JIRA_EMAIL:YOUR_TOKEN" \
     "https://YOUR_DOMAIN.atlassian.net/rest/api/3/field" \
     | jq '.[] | select(.custom==true) | {id, name}'
   ```

2. **Look for "Acceptance Criteria"** in the output and copy the `id` value

3. **Update template.yaml:**
   ```yaml
   ACCEPTANCE_CRITERIA_FIELD: "customfield_XXXXX"  # Your field ID here
   ```

4. **Redeploy:**
   ```bash
   sam build --use-container
   sam deploy
   ```

**Documentation:** See [CUSTOM_FIELD_SETUP.md](CUSTOM_FIELD_SETUP.md) for detailed instructions.

**Troubleshooting:** If Acceptance Criteria doesn't appear in GitHub issues, this is likely the cause. Check CloudWatch logs for messages about the configured field.

---

## Getting Started (3 Steps)

### Step 1: Prerequisites (30 minutes)
Install required tools and generate credentials:
- AWS CLI
- AWS SAM CLI  
- Docker Desktop
- GitHub Personal Access Token
- Jira API Token

**→ See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) Section 2 for detailed instructions**

### Step 2: Deploy (10 minutes)
```bash
# Configure
cp template.yaml.example template.yaml
# Edit template.yaml with your settings

# Create AWS secret
aws secretsmanager create-secret \
    --name jira-github-integration \
    --secret-string '{"github_token":"YOUR_TOKEN","jira_api_token":"YOUR_TOKEN"}'

# Deploy
sam build --use-container
sam deploy --guided
```

**→ See [QUICKSTART.md](QUICKSTART.md) for step-by-step guide**

### Step 3: Configure Webhooks (5 minutes)
- Copy webhook URL from deployment output
- Configure in Jira: Settings → System → WebHooks
- Test by creating a Jira issue with `sync-to-github` label

**→ See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) Section 7 for details**

---

## Architecture Overview

```
Jira Cloud → Webhook → API Gateway → Lambda → GitHub API
                                      ↓
                                  DynamoDB (state)
                                      ↓
                              Secrets Manager (tokens)
```

**Components:**
- **AWS Lambda:** Python 3.13 function (serverless compute)
- **API Gateway:** HTTPS endpoint for Jira webhooks
- **DynamoDB:** Sync state and comment mapping (pay-per-request)
- **Secrets Manager:** Secure token storage
- **CloudWatch:** Logs and monitoring

---

## Configuration Required

### AWS (Your Environment)
- AWS Region: `us-east-1` (or your choice)
- Stack Name: `jira-github-integration`

### GitHub (Your Repository)
- GitHub Owner/Org: `your-org`
- Repository Name: `your-repo`
- Token Scopes: `repo`, `write:discussion`

### Jira (Your Instance)
- Jira URL: `https://your-domain.atlassian.net`
- Jira Email: `your-email@example.com`
- Sync Label: `sync-to-github` (customizable)

### User Mapping (Optional but Recommended)
Map Jira users to GitHub usernames for assignee sync:
```yaml
USER_MAPPING: "jira.email@example.com:githubuser1,email2@example.com:githubuser2"
```

**→ See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) Section 1.2 for complete configuration**

---

## Key Features Explained

### 1. Issue Synchronization
- **Trigger:** Add `sync-to-github` label to Jira issue
- **Result:** GitHub issue created with:
  - Matching title and description
  - Link back to Jira
  - Assignee (if user mapping configured)
  - Labels
  - Acceptance criteria

### 2. Comment Synchronization
- **One-Way Sync:** Comments sync from Jira → GitHub only
- **Attribution:** Shows original Jira author with @mention (if mapped)
- **Duplicate Prevention:** Ensures comments aren't synced multiple times
- **Links:** Each comment includes link to original Jira comment

### 3. User Mapping
- **Email to GitHub Username:** Maps Jira users to GitHub collaborators
- **Verification:** Checks if user exists and has repository access
- **Fallback:** Shows name in description if user not found
- **Dynamic Lookup:** Can query Jira API for account IDs

### 4. Duplicate Prevention
- **DynamoDB State:** Tracks which issues have been synced
- **Comment Mapping:** Prevents duplicate comment creation
- **TTL:** Auto-expires old data after 90 days

---

## Cost Estimate

**Typical Monthly Costs (1000 syncs):**
| Service | Cost |
|---------|------|
| Lambda (1000 invocations, 3s avg) | $0.20 |
| API Gateway (1000 requests) | $3.50 |
| DynamoDB (on-demand) | $1.25 |
| Secrets Manager | $0.40 |
| CloudWatch Logs (1GB) | $0.50 |
| **Total** | **~$5.85/month** |

**Scaling:**
- Lambda: First 1M requests/month free
- Costs scale linearly with usage
- No fixed costs (100% pay-per-use)

**→ See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Cost Optimization for details**

---

## Security Features

### Token Security
- ✅ All tokens stored in AWS Secrets Manager (encrypted at rest)
- ✅ No credentials in code or configuration files
- ✅ Lambda uses IAM roles for AWS service access
- ✅ Tokens never logged or exposed

### Network Security
- ✅ HTTPS-only communication
- ✅ Webhook signature verification supported (optional)
- ✅ API Gateway rate limiting
- ✅ No inbound connections required

### Data Retention
- ✅ DynamoDB TTL: 90 days (auto-cleanup)
- ✅ CloudWatch Logs: Configurable retention
- ✅ No sensitive data stored (only issue keys and mappings)

**→ See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Security Best Practices**

---

## Testing Checklist

Use this checklist after deployment:

- [ ] **Test 1:** Jira issue with `sync-to-github` label creates GitHub issue
- [ ] **Test 2:** Jira comment appears in GitHub
- [ ] **Test 3:** User mapping works (assignee correctly set)
- [ ] **Test 4:** Duplicate issue not created when label re-applied
- [ ] **Test 5:** CloudWatch Logs show successful executions
- [ ] **Test 6:** DynamoDB contains sync state

**→ See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) Section 7 - Testing**

---

## Maintenance Requirements

### Regular Tasks
**Weekly:**
- Review CloudWatch Logs for errors
- Verify sync is working as expected

**Monthly:**
- Check AWS cost report
- Test integration end-to-end
- Review and update user mappings

**Quarterly:**
- Rotate GitHub and Jira tokens
- Review CloudWatch alarms
- Update documentation

### No Maintenance Required For:
- Lambda function (auto-scales, auto-patches)
- DynamoDB (auto-cleanup via TTL)
- API Gateway (fully managed)

**→ See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) Section 10 - Maintenance**

---

## Troubleshooting

### Most Common Issues & Quick Fixes

**Issue not syncing?**
```bash
# Check logs
sam logs --stack-name jira-github-integration --tail

# Common causes:
# 1. Wrong label name (check TARGET_LABEL in template.yaml)
# 2. Already synced (check DynamoDB)
# 3. Token expired (rotate in Secrets Manager)
```

**User not assigned?**
```bash
# Verify user is GitHub collaborator
curl -H "Authorization: token YOUR_TOKEN" \
     https://api.github.com/repos/OWNER/REPO/collaborators/USERNAME

# Update USER_MAPPING in template.yaml
```

**Comments not syncing?**
- Verify "Comment created" event enabled in Jira webhook
- Check CloudWatch Logs for errors
- Verify comment mapping in DynamoDB

**→ See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for complete guide with 50+ solutions**

---

## Support Resources

### Documentation
- **Quick Start:** [QUICKSTART.md](QUICKSTART.md)
- **Complete Guide:** [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **Troubleshooting:** [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Configuration:** [CONFIGURATION_TEMPLATE.md](CONFIGURATION_TEMPLATE.md)

### External Resources
- AWS SAM: https://docs.aws.amazon.com/serverless-application-model/
- GitHub API: https://docs.github.com/en/rest
- Jira API: https://developer.atlassian.com/cloud/jira/platform/rest/v3/
- Jira Webhooks: https://developer.atlassian.com/cloud/jira/platform/webhooks/

### Diagnostic Commands
```bash
# View logs
sam logs --stack-name jira-github-integration --tail

# Test GitHub connection
curl -H "Authorization: token YOUR_TOKEN" \
     https://api.github.com/repos/OWNER/REPO

# Test Jira connection
curl -u "EMAIL:TOKEN" \
     "https://YOUR_DOMAIN.atlassian.net/rest/api/3/myself"

# Check DynamoDB
aws dynamodb scan --table-name jira-github-sync-state
```

---

## Customization Options

### Easy Customizations (No Code Changes)
- Change sync label name (template.yaml: `TARGET_LABEL`)
- Add/update user mappings (template.yaml: `USER_MAPPING`)
- Change AWS region (samconfig.toml: `region`)
- Adjust Lambda timeout/memory (template.yaml: `Globals`)

### Advanced Customizations (Code Changes)
- Custom issue description format (app.py: `build_github_issue_body`)
- Additional label mappings (app.py: `map_jira_labels_to_github`)
- Custom webhook signature verification (app.py: `verify_webhook_signature`)
- Additional comment formatting (app.py: `build_github_comment_body`)

**Note:** Code is heavily commented (1845 lines with detailed explanations)

---

## Migration & Rollback

### Backup Before Changes
```bash
# Backup DynamoDB data
aws dynamodb scan --table-name jira-github-sync-state > backup.json

# Backup configuration
cp template.yaml template.yaml.backup
cp samconfig.toml samconfig.toml.backup
```

### Rollback Procedure
```bash
# 1. Remove Jira webhook
# (Navigate to Jira → Settings → System → WebHooks → Delete)

# 2. Delete CloudFormation stack
aws cloudformation delete-stack \
    --stack-name jira-github-integration \
    --region YOUR_REGION

# 3. Optional: Delete secrets
aws secretsmanager delete-secret \
    --secret-id jira-github-integration \
    --force-delete-without-recovery
```

---

## Production Readiness Checklist

Before deploying to production:

### Configuration
- [ ] All placeholder values in template.yaml replaced
- [ ] User mappings configured and tested
- [ ] AWS region selected and configured
- [ ] Secrets created in Secrets Manager
- [ ] Configuration documented in CONFIGURATION_TEMPLATE.md

### Security
- [ ] GitHub token has minimum required scopes
- [ ] Jira token has appropriate permissions
- [ ] AWS IAM roles follow least privilege
- [ ] Secrets Manager policies configured
- [ ] CloudWatch Logs retention set

### Testing
- [ ] Test deployment in non-production environment
- [ ] All test cases passed (see Testing Checklist above)
- [ ] User mapping verified
- [ ] Error handling tested
- [ ] Webhook connectivity tested

### Monitoring
- [ ] CloudWatch Logs reviewed
- [ ] CloudWatch alarms configured (optional)
- [ ] Cost monitoring enabled
- [ ] Dashboard created (optional)

### Documentation
- [ ] CONFIGURATION_TEMPLATE.md completed
- [ ] Support contacts documented
- [ ] Maintenance schedule defined
- [ ] Runbooks created for common issues

---

## Success Criteria

**Deployment is successful when:**
1. ✅ CloudFormation stack deploys without errors
2. ✅ Jira webhook shows successful deliveries
3. ✅ Test Jira issue creates GitHub issue
4. ✅ Jira comments appear in GitHub
5. ✅ Users are correctly assigned (if mapping configured)
6. ✅ No errors in CloudWatch Logs
7. ✅ DynamoDB contains sync state entries

---

## Next Steps

### Immediate (After Deployment)
1. Complete testing checklist
2. Document configuration in CONFIGURATION_TEMPLATE.md
3. Set up monitoring and alerts
4. Train team on how to use the integration
5. Create runbooks for common issues

### First Week
1. Monitor CloudWatch Logs daily
2. Verify all syncs are working correctly
3. Adjust user mappings as needed
4. Fine-tune configuration

### First Month
1. Review cost report
2. Optimize if needed (timeout, memory)
3. Document any custom issues/solutions
4. Schedule token rotation

### Ongoing
1. Follow maintenance schedule
2. Keep documentation updated
3. Monitor for new features/updates
4. Review security best practices

---

## File Structure Reference

```
📁 jira-github-integration/
│
├── 📄 INDEX.md                    ← START HERE (documentation index)
├── 📄 CLIENT_HANDOVER.md          ← This file
├── 📄 QUICKSTART.md               ← 5-minute setup
├── 📄 DEPLOYMENT_GUIDE.md         ← Complete reference (50 pages)
├── 📄 TROUBLESHOOTING.md          ← Problem solving
├── 📄 CONFIGURATION_TEMPLATE.md   ← Document your deployment
├── 📄 README.md                   ← Project overview
│
├── 📄 template.yaml               ← AWS infrastructure (YOUR CONFIG)
├── 📄 template.yaml.example       ← Clean template
├── 📄 samconfig.toml              ← SAM CLI settings
│
├── 📁 jira_handler/
│   ├── 📄 app.py                  ← Main code (1845 lines)
│   ├── 📄 requirements.txt        ← Dependencies
│   └── 📄 __init__.py
│
├── 📁 events/
│   └── 📄 event.json              ← Test payload
│
└── 📁 tests/
    ├── 📁 unit/                   ← Unit tests
    └── 📁 integration/            ← Integration tests
```

---

## Delivery Checklist

**This package includes:**
- [x] Complete source code (1845 lines, fully commented)
- [x] 6 comprehensive documentation files (100+ pages)
- [x] Configuration templates with examples
- [x] Test suite (unit + integration)
- [x] Sample webhook payload for testing
- [x] Deployment automation (AWS SAM)
- [x] Troubleshooting guide with 50+ solutions
- [x] Cost estimates and optimization guide
- [x] Security best practices
- [x] Maintenance procedures

**Ready for:**
- [x] Production deployment
- [x] Multi-environment setup (dev, staging, prod)
- [x] Team handover
- [x] Documentation and training
- [x] Long-term maintenance

---

## Contact & Support

### Getting Started
- **Start Here:** [INDEX.md](INDEX.md) - Complete documentation index
- **Quick Deploy:** [QUICKSTART.md](QUICKSTART.md) - 5 minutes to deployment
- **Need Help?** [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues and solutions

### Documentation Quality
All documentation has been written with:
- ✅ Step-by-step instructions
- ✅ Command examples (copy-paste ready)
- ✅ Troubleshooting for every common issue
- ✅ Screenshots and diagrams where helpful
- ✅ Real-world examples
- ✅ Links to official documentation
- ✅ FAQ sections

---

## Final Notes

### Code Quality
- **Well-commented:** Every function has docstrings and inline comments
- **Production-ready:** Error handling, logging, retry logic included
- **Maintainable:** Clear structure, modular functions
- **Tested:** Unit and integration tests included

### Documentation Quality
- **Comprehensive:** 100+ pages covering every aspect
- **Beginner-friendly:** Assumes no prior serverless experience
- **Copy-paste ready:** All commands can be copied directly
- **Troubleshooting:** Solutions for 50+ common issues

### Support
- All common issues documented with solutions
- Diagnostic commands provided for debugging
- External resource links for deeper learning
- Configuration templates for documentation

---

## Start Deploying!

**Ready to deploy?**

1. Read [INDEX.md](INDEX.md) for documentation overview
2. Follow [QUICKSTART.md](QUICKSTART.md) for fast deployment
3. Refer to [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for details
4. Use [TROUBLESHOOTING.md](TROUBLESHOOTING.md) if issues arise

**Have questions?** Everything is documented. Use INDEX.md to find what you need.

---

**Document Version:** 1.0.0  
**Last Updated:** January 20, 2026  
**Status:** ✅ Production Ready

---

**Thank you for using Jira-GitHub Integration!** 🚀
