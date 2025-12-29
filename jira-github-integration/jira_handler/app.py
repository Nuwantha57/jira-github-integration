import json
import os
import time
import requests
import boto3
from botocore.exceptions import ClientError
from requests.auth import HTTPBasicAuth

# Create clients outside handler (reuse across invocations)
secrets_client = boto3.client("secretsmanager")
dynamodb = boto3.resource("dynamodb")

# ================================
# Secrets Management
# ================================
def get_secrets():
    """
    Fetch GitHub token and Jira credentials from AWS Secrets Manager
    
    Returns:
        dict: Contains 'github_token', 'jira_email', 'jira_api_token'
    """
    secret_name = os.environ["SECRET_NAME"]

    try:
        response = secrets_client.get_secret_value(SecretId=secret_name)
        secret = json.loads(response["SecretString"])
        return secret
    except ClientError as e:
        print(f"Failed to retrieve secrets: {e}")
        raise
    except KeyError as e:
        raise Exception(f"Missing required secret key: {e}")


# ================================
# Jira API - Poll for Issues
# ================================
def get_jira_issues_to_sync():
    """
    Query Jira REST API for issues with the target label
    Uses JQL (Jira Query Language) to filter issues
    
    Returns:
        list: List of Jira issues matching the sync criteria
    """
    secrets = get_secrets()
    jira_base_url = os.environ["JIRA_BASE_URL"]
    project_key = os.environ["JIRA_PROJECT_KEY"]
    target_label = os.environ.get("TARGET_LABEL", "sync-to-github")
    
    # JQL query to find issues with the sync label
    jql = f'project = {project_key} AND labels = "{target_label}" ORDER BY created DESC'
    
    print(f"Querying Jira with JQL: {jql}")
    
    try:
        response = requests.get(
            f"{jira_base_url}/rest/api/3/search/jql",
            auth=HTTPBasicAuth(secrets["jira_email"], secrets["jira_api_token"]),
            params={
                "jql": jql,
                "maxResults": 100,
                "fields": "summary,description,labels,priority,assignee,status"
            },
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"Jira API error {response.status_code}: {response.text}")
            raise Exception(f"Jira query failed: {response.text}")
        
        data = response.json()
        issues = data.get("issues", [])
        
        print(f"Found {len(issues)} Jira issues with label '{target_label}'")
        return issues
        
    except requests.exceptions.RequestException as e:
        print(f"Jira API request failed: {e}")
        raise


# ================================
# DynamoDB State Management
# ================================
def is_already_synced(jira_key):
    """
    Check if a Jira issue has already been synced to GitHub
    
    Args:
        jira_key (str): Jira issue key (e.g., "PROJ-123")
        
    Returns:
        bool: True if already synced, False otherwise
    """
    table_name = os.environ["DYNAMODB_TABLE"]
    table = dynamodb.Table(table_name)
    
    try:
        response = table.get_item(Key={"jira_issue_key": jira_key})
        return "Item" in response
    except ClientError as e:
        print(f"DynamoDB error checking sync state for {jira_key}: {e}")
        return False


def mark_as_synced(jira_key, github_url):
    """
    Record in DynamoDB that a Jira issue has been synced to GitHub
    
    Args:
        jira_key (str): Jira issue key
        github_url (str): URL of the created GitHub issue
    """
    from datetime import datetime
    
    table_name = os.environ["DYNAMODB_TABLE"]
    table = dynamodb.Table(table_name)
    
    try:
        # TTL set to 90 days from now (optional)
        ttl = int(time.time()) + (90 * 24 * 60 * 60)
        
        table.put_item(
            Item={
                "jira_issue_key": jira_key,
                "github_issue_url": github_url,
                "synced_at": datetime.utcnow().isoformat(),
                "ttl": ttl
            }
        )
        print(f"✓ Marked {jira_key} as synced in DynamoDB")
    except ClientError as e:
        print(f"DynamoDB error marking {jira_key} as synced: {e}")
        raise


# ================================
# Label Mapping
# ================================
def map_labels(jira_labels):
    """
    Map Jira labels to GitHub labels
    
    Args:
        jira_labels (list): List of label strings from Jira
        
    Returns:
        list: Mapped GitHub labels
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
        # Skip the sync trigger label
        if label == "sync-to-github":
            continue
        mapped.append(mapping.get(label, label))

    return mapped


# ================================
# GitHub Issue Creation
# ================================
def create_github_issue(issue, github_token):
    """
    Create a GitHub issue from a Jira issue
    
    Args:
        issue (dict): Jira issue data from API
        github_token (str): GitHub authentication token
        
    Returns:
        str: URL of the created GitHub issue
    """
    fields = issue["fields"]
    jira_key = issue["key"]
    
    # Extract fields with fallback values
    title = fields.get("summary", "No title provided")
    description = fields.get("description") or "_No description provided_"
    priority_obj = fields.get("priority")
    priority = priority_obj.get("name") if priority_obj else "Medium"
    assignee = fields.get("assignee")
    assignee_name = assignee.get("displayName") if assignee else "Unassigned"
    labels = fields.get("labels", [])
    
    # Build Jira issue URL for reference
    jira_base_url = os.environ["JIRA_BASE_URL"]
    jira_url = f"{jira_base_url}/browse/{jira_key}"
    
    # Construct GitHub issue body with Jira context
    github_body = f"""{description}

---

### Jira Details
- **Jira Issue**: [{jira_key}]({jira_url})
- **Priority**: {priority}
- **Assignee**: {assignee_name}
"""
    
    # Map Jira labels to GitHub labels
    github_labels = map_labels(labels)
    
    print(f"Creating GitHub issue for {jira_key}...")
    
    try:
        owner = os.environ["GITHUB_OWNER"]
        repo = os.environ["GITHUB_REPO"]
        
        response = requests.post(
            f"https://api.github.com/repos/{owner}/{repo}/issues",
            headers={
                "Authorization": f"token {github_token}",
                "Accept": "application/vnd.github.v3+json"
            },
            json={
                "title": title[:256],      # GitHub limit safety
                "body": github_body,
                "labels": github_labels[:20]
            },
            timeout=10
        )
        
        if response.status_code != 201:
            print(f"GitHub API error {response.status_code}: {response.text}")
            raise Exception(f"GitHub creation failed: {response.text}")
        
        github_url = response.json()["html_url"]
        print(f"✓ Created GitHub issue: {github_url}")
        return github_url
        
    except requests.exceptions.RequestException as e:
        print(f"GitHub API request failed: {e}")
        raise


# ================================
# Main Lambda Handler (Scheduled)
# ================================
def lambda_handler(event, context):
    """
    Scheduled handler - runs every 30 minutes
    
    Process:
    1. Query Jira for issues with target label
    2. Check DynamoDB to see which issues are already synced
    3. Create GitHub issue for new Jira issues
    4. Mark as synced in DynamoDB to prevent duplicates
    
    Args:
        event (dict): EventBridge schedule event (not used)
        context (object): Lambda context object
        
    Returns:
        dict: Summary of sync operation
    """
    print("=== Starting scheduled Jira sync ===")
    
    try:
        # Step 1: Get credentials from Secrets Manager
        secrets = get_secrets()
        github_token = secrets["github_token"]
        
        # Step 2: Query Jira for issues to sync
        jira_issues = get_jira_issues_to_sync()
        
        # Step 3: Process each Jira issue
        synced_count = 0
        skipped_count = 0
        errors = []
        
        for issue in jira_issues:
            jira_key = issue["key"]
            
            try:
                # Skip if already synced to GitHub
                if is_already_synced(jira_key):
                    print(f"⊘ Skipping {jira_key} - already synced")
                    skipped_count += 1
                    continue
                
                # Create GitHub issue
                github_url = create_github_issue(issue, github_token)
                
                # Mark as synced in DynamoDB
                mark_as_synced(jira_key, github_url)
                
                synced_count += 1
                
            except Exception as e:
                error_msg = f"Error processing {jira_key}: {str(e)}"
                print(f"✗ {error_msg}")
                errors.append(error_msg)
        
        # Step 4: Return summary
        summary = {
            "status": "completed",
            "synced": synced_count,
            "skipped": skipped_count,
            "errors": len(errors),
            "error_details": errors,
            "total_processed": len(jira_issues)
        }
        
        print(f"=== Sync completed: {synced_count} synced, {skipped_count} skipped, {len(errors)} errors ===")
        
        return {
            "statusCode": 200,
            "body": json.dumps(summary)
        }
        
    except Exception as e:
        print(f"✗ Sync failed: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "status": "failed",
                "error": str(e)
            })
        }
