import json
import os
import requests
import boto3

secrets_client = boto3.client("secretsmanager")

def get_github_token():
    secret_name = os.environ["SECRET_NAME"]
    secret = secrets_client.get_secret_value(SecretId=secret_name)
    return json.loads(secret["SecretString"])["github_token"]

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
    return [mapping.get(label, label) for label in jira_labels if label != "sync-to-github"]

def lambda_handler(event, context):
    body = json.loads(event["body"])
    issue = body["issue"]
    fields = issue["fields"]

    labels = fields.get("labels", [])
    TARGET_LABEL = os.environ.get("TARGET_LABEL", "sync-to-github")

    if TARGET_LABEL not in labels:
        return {"statusCode": 200, "body": "Label not found, skipping"}

    title = fields["summary"]
    description = fields.get("description", "_No description provided_")
    priority = fields.get("priority", {}).get("name", "Medium")
    assignee = fields.get("assignee")
    assignee_name = assignee["displayName"] if assignee else "Unassigned"

    jira_key = issue["key"]
    jira_url = f"{os.environ['JIRA_BASE_URL']}/browse/{jira_key}"

    github_body = f"""{description}

---

### Jira Details
- **Issue**: [{jira_key}]({jira_url})
- **Priority**: {priority}
- **Assignee**: {assignee_name}
"""

    github_labels = map_labels(labels)
    token = get_github_token()

    response = requests.post(
        f"https://api.github.com/repos/{os.environ['GITHUB_OWNER']}/{os.environ['GITHUB_REPO']}/issues",
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        },
        json={
            "title": title,
            "body": github_body,
            "labels": github_labels
        },
        timeout=10
    )

    if response.status_code != 201:
        raise Exception(response.text)

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "GitHub issue created",
            "url": response.json()["html_url"]
        })
    }
