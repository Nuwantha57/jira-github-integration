# Documentation Index - Jira-GitHub Integration

Complete documentation suite for deploying, configuring, and maintaining the Jira-GitHub integration.

---

## 📚 Documentation Overview

This project includes comprehensive documentation to help you deploy and maintain the integration in your environment.

**Sync Direction:** Jira → GitHub (one-way sync only)

Start with the guide that matches your needs:

### 🚀 For New Users

**Start here if this is your first deployment:**

1. **[QUICKSTART.md](QUICKSTART.md)** - 5-minute setup guide
   - Prerequisites checklist
   - Minimal configuration steps
   - Quick deployment commands
   - Basic testing

2. **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Complete deployment documentation
   - Detailed prerequisites and tool installation
   - Step-by-step AWS configuration
   - GitHub and Jira token generation
   - Post-deployment configuration
   - Monitoring and maintenance

### 🔧 For Configuration & Customization

3. **[CUSTOM_FIELD_SETUP.md](CUSTOM_FIELD_SETUP.md)** - **CRITICAL: Custom field configuration**
   - Find your Jira Acceptance Criteria field ID
   - Three methods to detect custom fields
   - Field ID configuration guide
   - Testing and troubleshooting

4. **[CONFIGURATION_TEMPLATE.md](CONFIGURATION_TEMPLATE.md)** - Configuration worksheet
   - Document your deployment settings
   - Track user mappings
   - Testing checklist
   - Maintenance schedule
   - Support contacts

5. **[template.yaml.example](template.yaml.example)** - Configuration template
   - AWS SAM template with detailed comments
   - Environment variable descriptions
   - Deployment instructions

### 🐛 For Troubleshooting

6. **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Complete troubleshooting guide
   - Diagnostic tools
   - Common issues and solutions
   - Error message reference
   - Performance optimization
   - Advanced debugging techniques

### 📖 For Understanding the Project

7. **[README.md](README.md)** - Project overview
   - Feature summary
   - Architecture overview
   - User mapping explanation
   - Quick links to other docs

---

## 🎯 Quick Navigation by Task

### "I need to deploy this for the first time"
→ Start with [QUICKSTART.md](QUICKSTART.md)  
→ Then read [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) sections 1-7

### "Acceptance Criteria isn't syncing"
→ **[CUSTOM_FIELD_SETUP.md](CUSTOM_FIELD_SETUP.md)** - Find your field ID  
→ [TROUBLESHOOTING.md - Custom Fields](TROUBLESHOOTING.md)

### "I need to configure user mappings"
→ [DEPLOYMENT_GUIDE.md - User Mapping](DEPLOYMENT_GUIDE.md#user-mapping)  
→ [CONFIGURATION_TEMPLATE.md - User Mapping](CONFIGURATION_TEMPLATE.md#user-mapping)

### "Issues aren't syncing"
→ [TROUBLESHOOTING.md - GitHub Issue Not Created](TROUBLESHOOTING.md#issue-1-github-issue-not-created)

### "Comments aren't syncing"
→ [TROUBLESHOOTING.md - Comments Not Syncing](TROUBLESHOOTING.md#issue-2-comments-not-syncing)

### "Users aren't being assigned"
→ [TROUBLESHOOTING.md - User Not Assigned](TROUBLESHOOTING.md#issue-3-user-not-assigned-in-github)

### "I need to update tokens"
→ [DEPLOYMENT_GUIDE.md - Rotating Secrets](DEPLOYMENT_GUIDE.md#rotating-secrets)

### "I need to update the configuration"
→ [DEPLOYMENT_GUIDE.md - Updating the Application](DEPLOYMENT_GUIDE.md#updating-the-application)

### "I need to monitor costs"
→ [DEPLOYMENT_GUIDE.md - Cost Optimization](DEPLOYMENT_GUIDE.md#cost-optimization)

### "I need to delete everything"
→ [DEPLOYMENT_GUIDE.md - Cleanup](DEPLOYMENT_GUIDE.md#cleanup--uninstallation)

---

## 📋 Document Descriptions

### QUICKSTART.md
**Purpose:** Get up and running in 5 minutes  
**Length:** ~10 minutes to read and execute  
**Best for:** Users who want to deploy quickly and have the prerequisites ready

**Key Sections:**
- Prerequisites checklist
- 5-step deployment process
- Basic troubleshooting
- Command cheat sheet

---

### DEPLOYMENT_GUIDE.md
**Purpose:** Complete reference for deployment and operations  
**Length:** ~30 minutes to read fully  
**Best for:** First-time deployers, operations teams, documentation

**Key Sections:**
- Overview and architecture
- Prerequisites (with installation links)
- Pre-deployment setup (token generation)
- AWS configuration
- Step-by-step deployment
- Post-deployment configuration
- Testing procedures
- Troubleshooting basics
- Maintenance procedures
- Cost optimization
- Security best practices
- FAQ

---

### CONFIGURATION_TEMPLATE.md
**Purpose:** Document your specific deployment  
**Length:** Fill-in-the-blank form  
**Best for:** Operations teams, compliance, audit trails

**Key Sections:**
- Deployment information
- AWS resource details
- GitHub and Jira configuration
- User mapping table
- Testing checklist
- Monitoring configuration
- Maintenance schedule
- Support contacts
- Change history

---

### TROUBLESHOOTING.md
**Purpose:** Solve problems and debug issues  
**Length:** Reference document (use as needed)  
**Best for:** When things go wrong, performance tuning

**Key Sections:**
- Diagnostic tools
- Common issues (6 detailed scenarios)
- Error message reference
- Performance issues
- Data issues
- Advanced debugging
- Diagnostic checklist

---

### template.yaml.example
**Purpose:** Configuration template with inline documentation  
**Length:** AWS SAM template file  
**Best for:** Understanding configuration options, starting fresh deployment

**Key Sections:**
- Detailed comments for each configuration option
- Environment variable descriptions
- Resource definitions
- Deployment instructions
- Examples and best practices

---

### README.md
**Purpose:** Project overview and quick reference  
**Length:** ~5 minutes to read  
**Best for:** Understanding what the project does, quick links

**Key Sections:**
- Feature list
- Architecture diagram
- User mapping explanation
- Quick setup steps
- Links to detailed documentation

---

## 🔄 Typical User Journey

### First-Time Deployment

```
1. README.md
   └─> Understand what the project does

2. QUICKSTART.md
   └─> Quick overview of steps

3. DEPLOYMENT_GUIDE.md (Sections 1-4)
   └─> Install prerequisites
   └─> Generate tokens
   └─> Configure AWS

4. template.yaml.example
   └─> Copy to template.yaml
   └─> Fill in your configuration

5. DEPLOYMENT_GUIDE.md (Sections 5-7)
   └─> Deploy to AWS
   └─> Configure webhooks
   └─> Test integration

6. CONFIGURATION_TEMPLATE.md
   └─> Document your deployment

7. TROUBLESHOOTING.md (as needed)
   └─> Solve any issues
```

### Ongoing Operations

```
Weekly:
- Review CloudWatch Logs
- Check CONFIGURATION_TEMPLATE.md for scheduled maintenance

Monthly:
- Review costs (DEPLOYMENT_GUIDE.md - Cost Optimization)
- Test integration (DEPLOYMENT_GUIDE.md - Testing)
- Update CONFIGURATION_TEMPLATE.md change log

Quarterly:
- Rotate tokens (DEPLOYMENT_GUIDE.md - Rotating Secrets)
- Review and update user mappings
- Test disaster recovery

As Needed:
- TROUBLESHOOTING.md for issues
- DEPLOYMENT_GUIDE.md for updates
```

---

## 🛠️ Prerequisites Summary

All documentation assumes you have:

### Required Accounts
- ✅ AWS account with admin access
- ✅ GitHub account with repository admin access
- ✅ Jira Cloud account with project admin access

### Required Tools
- ✅ AWS CLI (v2.x+)
- ✅ AWS SAM CLI (v1.100.0+)
- ✅ Python 3.13
- ✅ Docker Desktop
- ✅ Git

### Required Credentials
- ✅ GitHub Personal Access Token (with `repo` scope)
- ✅ Jira API Token
- ✅ AWS credentials (Access Key ID & Secret)

---

## 📞 Getting Help

### Troubleshooting Steps
1. Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for your specific issue
2. Review CloudWatch Logs for error messages
3. Verify configuration in [template.yaml](template.yaml)
4. Test connections (GitHub, Jira, AWS)
5. Run diagnostic commands from TROUBLESHOOTING.md

### Common Resources
- **AWS SAM Documentation:** https://docs.aws.amazon.com/serverless-application-model/
- **GitHub REST API:** https://docs.github.com/en/rest
- **Jira REST API:** https://developer.atlassian.com/cloud/jira/platform/rest/v3/
- **Jira Webhooks:** https://developer.atlassian.com/cloud/jira/platform/webhooks/

---

## 📝 Contributing to Documentation

If you find issues or want to improve the documentation:

1. **Typos/Errors:** Fix directly in the markdown files
2. **Missing Information:** Add to relevant document
3. **New Issues:** Document solution in TROUBLESHOOTING.md
4. **Configuration Examples:** Add to CONFIGURATION_TEMPLATE.md

---

## 📊 Documentation Maintenance

### Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01-20 | Initial complete documentation suite |

### Review Schedule
- **Quarterly:** Review all documentation for accuracy
- **After Major Updates:** Update affected sections
- **After Common Issues:** Add to TROUBLESHOOTING.md

---

## ✅ Documentation Completeness Checklist

This documentation suite covers:

- [x] Installation prerequisites and setup
- [x] AWS account and IAM configuration
- [x] GitHub token generation and permissions
- [x] Jira token generation and permissions
- [x] Step-by-step deployment process
- [x] Webhook configuration
- [x] User mapping configuration
- [x] Testing procedures
- [x] Troubleshooting common issues
- [x] Error message reference
- [x] Performance optimization
- [x] Security best practices
- [x] Cost optimization
- [x] Monitoring and alerting
- [x] Maintenance procedures
- [x] Secret rotation
- [x] Cleanup/uninstallation
- [x] FAQ
- [x] Architecture explanation
- [x] Configuration templates
- [x] Command references

---

## 🎓 Learning Path

### Beginner (Never deployed serverless apps)
1. Read [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Prerequisites section
2. Install all required tools
3. Follow [QUICKSTART.md](QUICKSTART.md) step-by-step
4. Refer to [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for detailed explanations
5. Use [TROUBLESHOOTING.md](TROUBLESHOOTING.md) when stuck

### Intermediate (Familiar with AWS/Lambda)
1. Skim [README.md](README.md) for overview
2. Review [template.yaml.example](template.yaml.example)
3. Follow [QUICKSTART.md](QUICKSTART.md)
4. Customize configuration for your needs
5. Document in [CONFIGURATION_TEMPLATE.md](CONFIGURATION_TEMPLATE.md)

### Advanced (DevOps/SRE)
1. Review [template.yaml.example](template.yaml.example)
2. Customize [template.yaml](template.yaml) for your requirements
3. Deploy with `sam deploy`
4. Set up monitoring and alerts
5. Document runbooks in [CONFIGURATION_TEMPLATE.md](CONFIGURATION_TEMPLATE.md)

---

## 📦 Files Summary

```
Documentation Files:
├── INDEX.md                      # This file - documentation index
├── README.md                     # Project overview
├── QUICKSTART.md                 # 5-minute setup guide
├── DEPLOYMENT_GUIDE.md           # Complete deployment reference
├── TROUBLESHOOTING.md            # Troubleshooting guide
├── CONFIGURATION_TEMPLATE.md     # Configuration worksheet
└── template.yaml.example         # Configuration template

Code Files:
├── template.yaml                 # AWS SAM template (your config)
├── samconfig.toml               # SAM CLI configuration
├── jira_handler/
│   ├── app.py                   # Lambda function code
│   └── requirements.txt         # Python dependencies
└── tests/                       # Test files
```

---

## 🚀 Quick Start Command Summary

```bash
# 1. Configure
cp template.yaml.example template.yaml
# Edit template.yaml with your settings

# 2. Create secret
aws secretsmanager create-secret \
    --name jira-github-integration \
    --secret-string '{"github_token":"TOKEN","jira_api_token":"TOKEN"}'

# 3. Deploy
sam build --use-container && sam deploy --guided

# 4. Monitor
sam logs --stack-name jira-github-integration --tail

# 5. Troubleshoot (if needed)
# See TROUBLESHOOTING.md
```

---

**Ready to get started?** → [QUICKSTART.md](QUICKSTART.md) → [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)

**Having issues?** → [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

**Need to document your setup?** → [CONFIGURATION_TEMPLATE.md](CONFIGURATION_TEMPLATE.md)
