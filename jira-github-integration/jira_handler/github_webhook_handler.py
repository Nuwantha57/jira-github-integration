import os
import json
import boto3
import requests
import base64
from botocore.exceptions import ClientError
from datetime import datetime

dynamodb = boto3.resource("dynamodb")
secrets_client = boto3.client("secretsmanager")

# --- Secrets Management ---
def get_jira_credentials():
    """Fetch Jira credentials from AWS Secrets Manager."""
    secret_name = os.environ.get("SECRET_NAME", "jira-github-integration")
    try:
        response = secrets_client.get_secret_value(SecretId=secret_name)
        secret = json.loads(response["SecretString"])
        
        # Get email and API token
        jira_email = secret.get("jira_email")
        jira_api_token = secret.get("jira_api_token")
        
        if not jira_email or not jira_api_token:
            raise Exception("jira_email or jira_api_token not found in secret")
        
        # Create base64 encoded auth token
        auth_string = f"{jira_email}:{jira_api_token}"
        jira_token = base64.b64encode(auth_string.encode()).decode()
        
        return jira_token
    except ClientError as e:
        print(f"Failed to retrieve Jira credentials: {e}")
        raise

# --- DynamoDB Helpers ---
def get_sync_item_by_github_issue(github_issue_number):
    """Find sync item by GitHub issue number."""
    table_name = os.environ.get("DYNAMODB_TABLE", "jira-github-sync-state")
    table = dynamodb.Table(table_name)
    # Scan for the item with this github_issue_number
    resp = table.scan(
        FilterExpression="github_issue_number = :num",
        ExpressionAttributeValues={":num": int(github_issue_number)}
    )
    items = resp.get("Items", [])
    return items[0] if items else None

def add_comment_mapping(jira_key, jira_comment_id, github_comment_id):
    """Store bidirectional mapping between Jira and GitHub comments."""
    table_name = os.environ.get("DYNAMODB_TABLE", "jira-github-sync-state")
    table = dynamodb.Table(table_name)
    try:
        # Store both directions for easy lookup
        update_expr = "SET comments.jira_to_github.#jid = :gid, comments.github_to_jira.#gid = :jid"
        expr_names = {
            "#jid": str(jira_comment_id),
            "#gid": str(github_comment_id)
        }
        expr_vals = {
            ":gid": str(github_comment_id),
            ":jid": str(jira_comment_id)
        }
        table.update_item(
            Key={"jira_issue_key": jira_key},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_vals
        )
        print(f"✓ Mapped GitHub comment {github_comment_id} <-> Jira comment {jira_comment_id}")
    except ClientError as e:
        print(f"DynamoDB update_item error: {e}")

def is_comment_already_synced(jira_key, github_comment_id):
    """Check if GitHub comment has already been synced to Jira."""
    table_name = os.environ.get("DYNAMODB_TABLE", "jira-github-sync-state")
    table = dynamodb.Table(table_name)
    try:
        response = table.get_item(Key={"jira_issue_key": jira_key})
        item = response.get("Item")
        if not item:
            return False
        
        comments = item.get("comments", {})
        github_to_jira = comments.get("github_to_jira", {})
        
        if str(github_comment_id) in github_to_jira:
            print(f"GitHub comment {github_comment_id} already synced to Jira")
            return True
        
        return False
    except ClientError as e:
        print(f"DynamoDB get_item error: {e}")
        return False

# --- Jira API ---
def post_jira_comment(jira_base_url, jira_key, jira_token, comment_body):
    """Post comment to Jira issue."""
    url = f"{jira_base_url}/rest/api/3/issue/{jira_key}/comment"
    headers = {
        "Authorization": f"Basic {jira_token}",
        "Content-Type": "application/json"
    }
    
    # Jira API v3 uses ADF (Atlassian Document Format) for rich text
    # Convert markdown-style body to ADF
    adf_body = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": comment_body
                    }
                ]
            }
        ]
    }
    
    data = {"body": adf_body}
    resp = requests.post(url, headers=headers, json=data, timeout=10)
    return resp

# --- Lambda handler ---
def lambda_handler(event, context):
    """Handle GitHub webhook events - specifically issue comments."""
    print("GitHub webhook received")
    
    try:
        body = json.loads(event.get("body", "{}"))
    except Exception as e:
        print(f"Invalid JSON: {e}")
        return {"statusCode": 400, "body": "Invalid JSON"}

    # Get event type from headers
    headers = event.get("headers", {})
    github_event = headers.get("X-GitHub-Event") or headers.get("x-github-event")
    print(f"GitHub Event: {github_event}")

    # Only handle issue_comment events
    action = body.get("action")
    if github_event != "issue_comment" or action not in ("created",):
        print(f"Not a comment creation event (event={github_event}, action={action})")
        return {"statusCode": 200, "body": "Event ignored"}

    comment = body.get("comment", {})
    issue = body.get("issue", {})
    
    if not comment or not issue:
        return {"statusCode": 400, "body": "Missing comment or issue"}

    github_comment_id = comment.get("id")
    github_issue_number = issue.get("number")
    comment_body = comment.get("body", "")
    comment_user = comment.get("user", {}).get("login", "GitHub user")
    comment_created = comment.get("created_at", "")

    print(f"GitHub comment {github_comment_id} on issue #{github_issue_number} by {comment_user}")

    # Loop prevention: skip if marker is present
    if "[//]: # (jira-sync:" in comment_body or "github_comment_id=" in comment_body:
        print("Loop prevention: GitHub comment contains sync marker, skipping")
        return {"statusCode": 200, "body": "Loop prevention - synced comment"}

    # Find Jira mapping
    sync_item = get_sync_item_by_github_issue(github_issue_number)
    if not sync_item:
        print(f"No Jira mapping for GitHub issue #{github_issue_number}")
        return {"statusCode": 200, "body": "No Jira mapping found"}

    jira_key = sync_item["jira_issue_key"]
    print(f"Found Jira mapping: {jira_key}")

    # Check if this comment has already been synced
    if is_comment_already_synced(jira_key, github_comment_id):
        print(f"GitHub comment {github_comment_id} already synced")
        return {"statusCode": 200, "body": "Comment already synced"}

    # Get Jira credentials
    jira_base_url = os.environ["JIRA_BASE_URL"]
    try:
        jira_token = get_jira_credentials()
    except Exception as e:
        print(f"Failed to get Jira credentials: {e}")
        return {"statusCode": 500, "body": "Failed to authenticate with Jira"}

    # Format timestamp
    timestamp_str = ""
    if comment_created:
        try:
            dt = datetime.fromisoformat(comment_created.replace('Z', '+00:00'))
            timestamp_str = f" at {dt.strftime('%Y-%m-%d %H:%M UTC')}"
        except:
            pass

    # Build Jira comment with loop prevention marker
    github_issue_url = issue.get("html_url", "")
    comment_url = comment.get("html_url", "")
    marker = f"[//]: # (jira-sync: github_comment_id={github_comment_id})"
    
    jira_comment_body = f"""🔗 Comment from GitHub
Author: {comment_user}{timestamp_str}

{comment_body}

---
View in GitHub: {comment_url}
{marker}"""

    # Post comment to Jira
    resp = post_jira_comment(jira_base_url, jira_key, jira_token, jira_comment_body)
    
    if resp.status_code != 201:
        print(f"Failed to post Jira comment: {resp.status_code} {resp.text}")
        return {
            "statusCode": 502, 
            "body": json.dumps({
                "error": "Failed to post Jira comment",
                "details": resp.text
            })
        }

    jira_comment_data = resp.json()
    jira_comment_id = jira_comment_data.get("id")
    print(f"✓ Created Jira comment {jira_comment_id}")
    
    # Store bidirectional mapping
    add_comment_mapping(jira_key, jira_comment_id, github_comment_id)
    
    return {
        "statusCode": 200, 
        "body": json.dumps({
            "message": "Comment synced to Jira successfully",
            "jira_key": jira_key,
            "jira_comment_id": jira_comment_id,
            "github_comment_id": github_comment_id
        })
    }

