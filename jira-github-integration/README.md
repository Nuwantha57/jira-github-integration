# Jira-GitHub Integration

Serverless integration that automatically syncs Jira issues and comments to GitHub using AWS Lambda, API Gateway, and DynamoDB.

**Sync Direction:** Jira → GitHub (one-way)

## 🚀 Quick Start

**New to this project?** Start here:
1. � **[INDEX.md](INDEX.md)** - Complete documentation index (START HERE!)
2. 📖 **[QUICKSTART.md](QUICKSTART.md)** - 5-minute setup guide
3. 📚 **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Complete 50-page reference
4. 🐛 **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Solutions to 50+ common issues
5. 📋 **[CONFIGURATION_TEMPLATE.md](CONFIGURATION_TEMPLATE.md)** - Document your deployment
6. 🎁 **[CLIENT_HANDOVER.md](CLIENT_HANDOVER.md)** - Executive summary & overview

**Total Documentation:** 100+ pages covering every aspect of deployment and operation.

## Features

- ✅ Sync Jira issues to GitHub issues with the `sync-to-github` label
- ✅ Sync Jira comments to GitHub (one-way)
- ✅ User mapping from Jira to GitHub
- ✅ DynamoDB-based duplicate prevention
- ✅ Acceptance Criteria support
- ✅ Label mapping
- ✅ ADF (Atlassian Document Format) parsing

## Architecture

- **JiraWebhookFunction**: Handles Jira webhooks for issue creation and comment sync to GitHub
- **DynamoDB**: Stores sync state and comment mappings
- **API Gateway**: Exposes webhook endpoint for Jira webhooks

## User Mapping

### Problem
Jira users (Assignee, Commenter, Reporter) might not exist as GitHub contributors.

### Solution
The integration handles missing users gracefully:

1. **User Mapping Configuration**: Map Jira email addresses to GitHub usernames via environment variable
2. **Verification**: Checks if GitHub users exist and are repository collaborators before assignment
3. **Fallback**: If no mapping or user doesn't exist, displays name only (no @mention/assignment)

### Configuration

Set the `USER_MAPPING` environment variable in [template.yaml](template.yaml):

```yaml
USER_MAPPING: "jira.user@example.com:githubuser1,another@example.com:githubuser2"
```

Format: `jira_email:github_username,jira_email2:github_username2`

### Behavior

**For Issue Assignment:**
- ✅ Mapped + Exists: Issue assigned to `@githubuser` in GitHub
- ⚠️ Mapped + Not Found: Shows "Assignee (Jira): Full Name" (no assignment)
- ⚠️ Not Mapped: Shows "Assignee (Jira): Full Name" (no assignment)

**For Comments:**
- ✅ Mapped + Exists: "Author: @githubuser (Full Name)"
- ⚠️ Mapped + Not Found: "Author: Full Name"
- ⚠️ Not Mapped: "Author: Full Name"

## 📦 Project Structure

```
jira-github-integration/
├── README.md                      # This file - project overview
├── QUICKSTART.md                  # 5-minute setup guide
├── DEPLOYMENT_GUIDE.md            # Complete deployment documentation
├── CONFIGURATION_TEMPLATE.md      # Configuration worksheet
├── template.yaml                  # AWS SAM template (your config)
├── template.yaml.example          # Template with instructions
├── samconfig.toml                 # SAM CLI configuration
├── events/
│   └── event.json                # Sample Jira webhook payload
├── jira_handler/
│   ├── app.py                    # Main Lambda function code
│   ├── requirements.txt          # Python dependencies
│   └── __init__.py
└── tests/
    ├── unit/                     # Unit tests
    └── integration/              # Integration tests
```

## 🔧 Setup & Deployment

### Prerequisites

- ✅ AWS CLI installed and configured
- ✅ AWS SAM CLI (v1.100.0+)
- ✅ Python 3.13
- ✅ Docker Desktop
- ✅ GitHub Personal Access Token (with `repo` scope)
- ✅ Jira API Token

### Quick Deployment

```bash
# 1. Copy and configure template
cp template.yaml.example template.yaml
# Edit template.yaml with your GitHub/Jira settings

# 2. Create AWS secret
aws secretsmanager create-secret \
    --name jira-github-integration \
    --secret-string '{"github_token":"YOUR_TOKEN","jira_api_token":"YOUR_TOKEN"}'

# 3. Build and deploy
sam build --use-container
sam deploy --guided
```

**For detailed step-by-step instructions, see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)**

## Use the SAM CLI to build and test locally

Build your application with the `sam build --use-container` command:

```bash
sam build --use-container
```

The SAM CLI installs dependencies defined in `hello_world/requirements.txt`, creates a deployment package, and saves it in the `.aws-sam/build` folder.

Test a single function by invoking it directly with a test event. An event is a JSON document that represents the input that the function receives from the event source. Test events are included in the `events` folder in this project.

Run functions locally and invoke them with the `sam local invoke` command.

```bash
jira-github-integration$ sam local invoke HelloWorldFunction --event events/event.json
```

The SAM CLI can also emulate your application's API. Use the `sam local start-api` to run the API locally on port 3000.

```bash
jira-github-integration$ sam local start-api
jira-github-integration$ curl http://localhost:3000/
```

The SAM CLI reads the application template to determine the API's routes and the functions that they invoke. The `Events` property on each function's definition includes the route and method for each path.

```yaml
      Events:
        HelloWorld:
          Type: Api
          Properties:
            Path: /hello
            Method: get
```

## Add a resource to your application
The application template uses AWS Serverless Application Model (AWS SAM) to define application resources. AWS SAM is an extension of AWS CloudFormation with a simpler syntax for configuring common serverless application resources such as functions, triggers, and APIs. For resources not included in [the SAM specification](https://github.com/awslabs/serverless-application-model/blob/master/versions/2016-10-31.md), you can use standard [AWS CloudFormation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-template-resource-type-ref.html) resource types.

## Fetch, tail, and filter Lambda function logs

To simplify troubleshooting, SAM CLI has a command called `sam logs`. `sam logs` lets you fetch logs generated by your deployed Lambda function from the command line. In addition to printing the logs on the terminal, this command has several nifty features to help you quickly find the bug.

`NOTE`: This command works for all AWS Lambda functions; not just the ones you deploy using SAM.

```bash
jira-github-integration$ sam logs -n HelloWorldFunction --stack-name "jira-github-integration" --tail
```

You can find more information and examples about filtering Lambda function logs in the [SAM CLI Documentation](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-logging.html).

## Tests

Tests are defined in the `tests` folder in this project. Use PIP to install the test dependencies and run tests.

```bash
jira-github-integration$ pip install -r tests/requirements.txt --user
# unit test
jira-github-integration$ python -m pytest tests/unit -v
# integration test, requiring deploying the stack first.
# Create the env variable AWS_SAM_STACK_NAME with the name of the stack we are testing
jira-github-integration$ AWS_SAM_STACK_NAME="jira-github-integration" python -m pytest tests/integration -v
```

## Cleanup

To delete the sample application that you created, use the AWS CLI. Assuming you used your project name for the stack name, you can run the following:

```bash
sam delete --stack-name "jira-github-integration"
```

## Resources

See the [AWS SAM developer guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html) for an introduction to SAM specification, the SAM CLI, and serverless application concepts.

Next, you can use AWS Serverless Application Repository to deploy ready to use Apps that go beyond hello world samples and learn how authors developed their applications: [AWS Serverless Application Repository main page](https://aws.amazon.com/serverless/serverlessrepo/)
