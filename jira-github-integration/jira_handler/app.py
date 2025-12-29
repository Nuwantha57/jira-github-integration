import json
import os
import time
import requests
import boto3
from botocore.exceptions import ClientError
from datetime import datetime

# Create clients outside handler (reuse across invocations)
secrets_client = boto3.client("secretsmanager")
dynamodb = boto3.resource("dynamodb")

# -------------------------------
# Secrets
# -------------------------------
def get_github_token():
    """
    Fetch GitHub token from AWS Secrets Manager
    """
    secret_name = os.environ["SECRET_NAME"]

    try:
        response = secrets_client.get_secret_value(SecretId=secret_name)
        secret = json.loads(response["SecretString"])
        return secret["github_token"]
    except ClientError as e:
        print(f"Failed to retrieve secret: {e}")
        raise
    except KeyError:
        raise Exception("'github_token' not found in secret")

# -------------------------------
# DynamoDB State Management
# -------------------------------
def is_already_synced(jira_key):
    """Check if already synced to prevent duplicates"""
    table_name = os.environ.get("DYNAMODB_TABLE", "jira-github-sync-state")
    table = dynamodb.Table(table_name)
    
    try:
        response = table.get_item(Key={"jira_issue_key": jira_key})
        return "Item" in response
    except ClientError as e:
        print(f"DynamoDB error: {e}")
        return False


def mark_as_synced(jira_key, github_url):
    """Mark as synced in DynamoDB"""
    table_name = os.environ.get("DYNAMODB_TABLE", "jira-github-sync-state")
    table = dynamodb.Table(table_name)
    
    try:
        ttl = int(time.time()) + (90 * 24 * 60 * 60)
        table.put_item(
            Item={
                "jira_issue_key": jira_key,
                "github_issue_url": github_url,
                "synced_at": datetime.utcnow().isoformat(),
                "ttl": ttl
            }
        )
        print(f"✓ Marked {jira_key} as synced")
    except ClientError as e:
        print(f"DynamoDB error: {e}")


# -------------------------------
# Label mapping
# -------------------------------
def map_labels(jira_labels):
    """
    Map Jira labels to GitHub labels
    """
    mapping = {
        "bug": "type:bug",
        "feature": "type:feature",
        "backend": "component:backend",
        "frontend": "component:frontend",
        "high-priority": "priority:high",
        "medium-priority": "priority:medium",
        "low-priority": "priority:low"
    }

    mapped = []
    for label in jira_labels:
        if label == "sync-to-github":
            continue
        mapped.append(mapping.get(label, label))

    return mapped


# -------------------------------
# Lambda handler
# -------------------------------
def lambda_handler(event, context):
    print("Jira webhook received")

    # ---- Step 1: Parse request body safely
    try:
        body = json.loads(event.get("body", "{}"))
    except json.JSONDecodeError:
        print("Invalid JSON payload")
        return {"statusCode": 400, "body": "Invalid JSON payload"}

    issue = body.get("issue")
    if not issue:
        return {"statusCode": 400, "body": "Missing issue object"}

    fields = issue.get("fields", {})

    # ---- Step 2: Extract fields safely
    jira_key = issue.get("key", "UNKNOWN")
    
    print(f"Jira Issue: {jira_key}")
    
    # ---- Step 2a: Check if already synced (PREVENT DUPLICATES)
    if is_already_synced(jira_key):
        print(f"⊘ Skipping {jira_key} - already synced to GitHub")
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Already synced, skipping",
                "jira_issue": jira_key
            })
        }
    
    title = fields.get("summary", "No title provided")
    description = fields.get("description") or "_No description provided_"
    labels = fields.get("labels", [])
    priority_obj = fields.get("priority")
    priority = priority_obj.get("name") if priority_obj else "Medium"

    assignee = fields.get("assignee")
    assignee_name = assignee.get("displayName") if assignee else "Unassigned"

    print(f"Labels: {labels}")

    # ---- Step 3: Check trigger label
    target_label = os.environ.get("TARGET_LABEL", "sync-to-github")
    if target_label not in labels:
        print("Trigger label not found, skipping")
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Label not found, skipping",
                "jira_issue": jira_key
            })
        }

    # ---- Step 4: Build GitHub issue body
    jira_base_url = os.environ["JIRA_BASE_URL"]
    jira_url = f"{jira_base_url}/browse/{jira_key}"

    github_body = f"""{description}

---

### Jira Details
- **Jira Issue**: [{jira_key}]({jira_url})
- **Priority**: {priority}
- **Assignee**: {assignee_name}
"""

    github_labels = map_labels(labels)

    # ---- Step 5: Create GitHub issue
    try:
        token = get_github_token()
        owner = os.environ["GITHUB_OWNER"]
        repo = os.environ["GITHUB_REPO"]

        response = requests.post(
            f"https://api.github.com/repos/{owner}/{repo}/issues",
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json"
            },
            json={
                "title": title[:256],     # GitHub limit safety
                "body": github_body,
                "labels": github_labels[:20]
            },
            timeout=10
        )

    except requests.exceptions.RequestException as e:
        print(f"GitHub API request failed: {e}")
        return {"statusCode": 502, "body": "GitHub API request failed"}

    # ---- Step 6: Handle GitHub response
    if response.status_code != 201:
        print(f"GitHub API error {response.status_code}: {response.text}")
        return {
            "statusCode": 502,
            "body": json.dumps({
                "error": "Failed to create GitHub issue",
                "details": response.text
            })
        }

    github_issue = response.json()
    github_url = github_issue["html_url"]
    print(f"GitHub issue created: {github_url}")
    
    # ---- Step 7: Mark as synced in DynamoDB to prevent duplicates
    mark_as_synced(jira_key, github_url)

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "GitHub issue created successfully",
            "jira_issue": jira_key,
            "github_issue_url": github_url
        })
    }
