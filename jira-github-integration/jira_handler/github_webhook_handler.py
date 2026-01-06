import os
import json
import boto3
import requests
from botocore.exceptions import ClientError

dynamodb = boto3.resource("dynamodb")

# --- Helpers ---
def get_sync_item_by_github_issue(github_issue_number):
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
    table_name = os.environ.get("DYNAMODB_TABLE", "jira-github-sync-state")
    table = dynamodb.Table(table_name)
    try:
        update_expr = "SET comments.#cid = :gid"
        expr_names = {"#cid": str(jira_comment_id)}
        expr_vals = {":gid": str(github_comment_id)}
        table.update_item(
            Key={"jira_issue_key": jira_key},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_vals
        )
    except ClientError as e:
        print(f"DynamoDB update_item error: {e}")

def post_jira_comment(jira_base_url, jira_key, jira_token, comment_body):
    url = f"{jira_base_url}/rest/api/3/issue/{jira_key}/comment"
    headers = {
        "Authorization": f"Basic {jira_token}",
        "Content-Type": "application/json"
    }
    data = {"body": comment_body}
    resp = requests.post(url, headers=headers, json=data, timeout=10)
    return resp

# --- Lambda handler ---
def lambda_handler(event, context):
    print("GitHub webhook received")
    try:
        body = json.loads(event.get("body", "{}"))
    except Exception:
        return {"statusCode": 400, "body": "Invalid JSON"}

    # Only handle issue_comment events
    if body.get("action") not in ("created",):
        return {"statusCode": 200, "body": "Not a comment creation event"}

    comment = body.get("comment", {})
    issue = body.get("issue", {})
    if not comment or not issue:
        return {"statusCode": 400, "body": "Missing comment or issue"}

    github_comment_id = comment.get("id")
    github_issue_number = issue.get("number")
    comment_body = comment.get("body", "")

    # Loop prevention: skip if marker is present
    if "jira-sync:" in comment_body:
        print("Loop prevention marker found, skipping")
        return {"statusCode": 200, "body": "Loop prevention"}

    # Find Jira mapping
    sync_item = get_sync_item_by_github_issue(github_issue_number)
    if not sync_item:
        print(f"No Jira mapping for GitHub issue {github_issue_number}")
        return {"statusCode": 200, "body": "No mapping"}

    jira_key = sync_item["jira_issue_key"]
    jira_base_url = os.environ["JIRA_BASE_URL"]
    jira_token = os.environ["JIRA_API_TOKEN"]  # Should be base64 encoded user:token

    # Build Jira comment with marker
    gh_author = comment.get("user", {}).get("login", "GitHub user")
    marker = f"[//]: # (jira-sync: github_comment_id={github_comment_id})"
    jira_comment_body = f"GitHub comment by {gh_author}:\n\n{comment_body}\n\n{marker}"

    resp = post_jira_comment(jira_base_url, jira_key, jira_token, jira_comment_body)
    if resp.status_code != 201:
        print(f"Failed to post Jira comment: {resp.status_code} {resp.text}")
        return {"statusCode": 502, "body": f"Failed to post Jira comment: {resp.text}"}

    jira_comment_id = resp.json().get("id")
    add_comment_mapping(jira_key, jira_comment_id, github_comment_id)
    return {"statusCode": 200, "body": json.dumps({"message": "Comment synced to Jira", "jira_comment_id": jira_comment_id})}
