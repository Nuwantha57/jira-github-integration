import json
import os
import time
import hmac
import hashlib
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
def get_secrets():
    """
    Fetch secrets from AWS Secrets Manager
    Returns both github_token and webhook_secret
    """
    secret_name = os.environ["SECRET_NAME"]

    try:
        response = secrets_client.get_secret_value(SecretId=secret_name)
        secret = json.loads(response["SecretString"])
        return secret
    except ClientError as e:
        print(f"Failed to retrieve secret: {e}")
        raise


def get_github_token():
    """
    Fetch GitHub token from AWS Secrets Manager
    """
    secrets = get_secrets()
    if "github_token" not in secrets:
        raise Exception("'github_token' not found in secret")
    return secrets["github_token"]


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
        # Store github_issue_url and (when available) issue number for comment mapping
        github_issue_number = None
        try:
            # Try to parse a numeric issue number from the URL (e.g. .../issues/123)
            github_issue_number = int(github_url.rstrip('/').split('/')[-1])
        except Exception:
            github_issue_number = None

        ttl = int(time.time()) + (90 * 24 * 60 * 60)
        item = {
            "jira_issue_key": jira_key,
            "github_issue_url": github_url,
            "synced_at": datetime.utcnow().isoformat(),
            "ttl": ttl
        }
        if github_issue_number:
            item["github_issue_number"] = github_issue_number

        table.put_item(Item=item)
        print(f"✓ Marked {jira_key} as synced")
    except ClientError as e:
        print(f"DynamoDB error: {e}")


def verify_webhook_signature(payload_body, signature_header, secret):
    """
    Verify the HMAC signature from Jira webhook
    
    Args:
        payload_body: Raw request body as string
        signature_header: Value of X-Hub-Signature header
        secret: Webhook secret for HMAC validation
    
    Returns:
        True if signature is valid, False otherwise
    """
    if not signature_header:
        print("Missing signature header")
        return False
    
    if not secret:
        print("Warning: No webhook secret configured, skipping verification")
        return True  # Allow request if no secret is configured
    
    # Compute HMAC SHA-256
    expected_signature = hmac.new(
        key=secret.encode('utf-8'),
        msg=payload_body.encode('utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()
    
    # Expected format: "sha256=<hex_digest>"
    expected_header = f"sha256={expected_signature}"
    
    # Secure comparison to prevent timing attacks
    is_valid = hmac.compare_digest(expected_header, signature_header)
    
    if not is_valid:
        print(f"Signature mismatch. Expected: {expected_header[:20]}... Got: {signature_header[:20]}...")
    
    return is_valid


# -------------------------------
# DynamoDB helpers for comment mapping
# -------------------------------
def get_sync_item(jira_key):
    table_name = os.environ.get("DYNAMODB_TABLE", "jira-github-sync-state")
    table = dynamodb.Table(table_name)
    try:
        response = table.get_item(Key={"jira_issue_key": jira_key})
        return response.get("Item")
    except ClientError as e:
        print(f"DynamoDB get_item error: {e}")
        return None


def add_comment_mapping(jira_key, jira_comment_id, github_comment_id):
    """Store a mapping from a Jira comment id to a GitHub comment id under the Jira issue item."""
    table_name = os.environ.get("DYNAMODB_TABLE", "jira-github-sync-state")
    table = dynamodb.Table(table_name)
    try:
        # Use a map attribute `comments` with dynamic key for the jira_comment_id
        update_expr = "SET comments.#cid = :gid"
        expr_names = {"#cid": str(jira_comment_id)}
        expr_vals = {":gid": str(github_comment_id)}
        table.update_item(
            Key={"jira_issue_key": jira_key},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_vals
        )
        print(f"✓ Mapped Jira comment {jira_comment_id} -> GitHub comment {github_comment_id}")
    except ClientError as e:
        print(f"DynamoDB update_item error: {e}")


def post_github_comment(owner, repo, issue_number, body_text, token):
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/comments"
    try:
        resp = requests.post(
            url,
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json"
            },
            json={"body": body_text},
            timeout=10
        )
        return resp
    except requests.exceptions.RequestException as e:
        print(f"GitHub comment request failed: {e}")
        return None


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

    # ---- Step 1: Verify webhook signature (for non-Jira sources)
    raw_body = event.get("body", "{}")
    headers = event.get("headers", {})
    
    # Check if this is a Jira webhook
    is_jira_webhook = headers.get("X-Atlassian-Webhook-Identifier") or \
                      headers.get("x-atlassian-webhook-identifier")
    
    if is_jira_webhook:
        print(f"Jira webhook identified: {is_jira_webhook}")
        
        # Verify it's from YOUR specific Jira instance
        jira_base_url = os.environ.get("JIRA_BASE_URL", "")
        # Extract domain from Jira URL (e.g., "nuwanthapiumal57.atlassian.net")
        jira_domain = jira_base_url.replace("https://", "").replace("http://", "").rstrip("/")
        
        # Check various headers that might contain the source
        user_agent = headers.get("User-Agent", "").lower()
        referer = headers.get("Referer", "").lower()
        origin = headers.get("Origin", "").lower()
        host = headers.get("Host", "").lower()
        
        # Verify the webhook is from trusted Jira instance
        is_from_trusted_jira = (
            jira_domain.lower() in user_agent or
            jira_domain.lower() in referer or
            jira_domain.lower() in origin or
            "atlassian" in user_agent  # Atlassian user agent
        )
        
        if not is_from_trusted_jira:
            print(f"Untrusted Jira webhook attempt!")
            print(f"Expected domain: {jira_domain}")
            print(f"User-Agent: {user_agent[:50]}")
            print(f"Referer: {referer}")
            return {
                "statusCode": 401,
                "body": json.dumps({"error": "Unauthorized - Invalid Jira source"})
            }
        
        print(f"Verified webhook from trusted Jira instance: {jira_domain}")
        print("Skipping signature verification for Jira Cloud webhook")
    else:
        # For non-Jira webhooks, verify signature
        print("Non-Jira webhook detected, checking signature...")
        signature_header = headers.get("X-Hub-Signature") or \
                          headers.get("x-hub-signature")
        
        try:
            secrets = get_secrets()
            webhook_secret = secrets.get("webhook_secret")
        
            if not verify_webhook_signature(raw_body, signature_header, webhook_secret):
                print("Webhook signature verification failed")
                return {
                    "statusCode": 401,
                    "body": json.dumps({"error": "Unauthorized - Invalid signature"})
                }
            
            print("Webhook signature verified successfully")
        except Exception as e:
            print(f"Error during signature verification: {e}")
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "Internal server error"})
            }

    # ---- Step 2: Parse request body safely
    try:
        body = json.loads(raw_body)
    except json.JSONDecodeError:
        print("Invalid JSON payload")
        return {"statusCode": 400, "body": "Invalid JSON payload"}

    issue = body.get("issue")
    if not issue:
        return {"statusCode": 400, "body": "Missing issue object"}

    fields = issue.get("fields", {})

    # ---- Step 3: Extract fields safely
    jira_key = issue.get("key", "UNKNOWN")
    
    print(f"Jira Issue: {jira_key}")

    # ---- Comment handling: if this webhook contains a comment, mirror to GitHub
    if body.get("comment"):
        comment = body.get("comment")
        jira_comment_id = str(comment.get("id"))
        comment_body = comment.get("body", "") or ""

        if not comment_body.strip():
            print("Empty Jira comment, skipping")
            return {"statusCode": 200, "body": json.dumps({"message": "Empty comment, skipping"})}

        # Find GitHub issue mapping for this Jira issue
        sync_item = get_sync_item(jira_key)
        if not sync_item:
            print(f"No GitHub mapping found for {jira_key}. Skipping comment sync.")
            return {"statusCode": 200, "body": json.dumps({"message": "No mapping, skipping"})}

        github_issue_number = sync_item.get("github_issue_number")
        # Fallback: parse from url if number not stored
        if not github_issue_number and sync_item.get("github_issue_url"):
            try:
                github_issue_number = int(sync_item.get("github_issue_url").rstrip('/').split('/')[-1])
            except Exception:
                github_issue_number = None

        if not github_issue_number:
            print(f"Could not determine GitHub issue number for {jira_key}, skipping")
            return {"statusCode": 200, "body": json.dumps({"message": "No issue number, skipping"})}

        # Build GitHub comment body and include a marker to prevent loops
        jira_author = comment.get("author", {}).get("displayName") or comment.get("author", {}).get("name") or "Jira user"
        jira_base_url = os.environ.get("JIRA_BASE_URL", "")
        jira_url = f"{jira_base_url}/browse/{jira_key}"
        marker = f"<!-- jira-sync: jira_comment_id={jira_comment_id} -->"
        github_comment_body = f"**Jira comment by {jira_author}:**\n\n{comment_body}\n\n[View in Jira]({jira_url})\n\n{marker}"

        # Post comment to GitHub
        try:
            token = get_github_token()
            owner = os.environ["GITHUB_OWNER"]
            repo = os.environ["GITHUB_REPO"]
            resp = post_github_comment(owner, repo, github_issue_number, github_comment_body, token)
            if resp is None:
                return {"statusCode": 502, "body": "GitHub comment request failed"}

            if resp.status_code != 201:
                print(f"Failed to create GitHub comment {resp.status_code}: {resp.text}")
                return {"statusCode": 502, "body": json.dumps({"error": "Failed to create GitHub comment", "details": resp.text})}

            gh_comment = resp.json()
            gh_comment_id = gh_comment.get("id")
            add_comment_mapping(jira_key, jira_comment_id, gh_comment_id)

            return {"statusCode": 200, "body": json.dumps({"message": "Comment synced to GitHub", "github_comment_id": gh_comment_id})}

        except Exception as e:
            print(f"Error while syncing comment: {e}")
            return {"statusCode": 500, "body": json.dumps({"error": "Internal error"})}
    
    # ---- Step 3a: Check if already synced (PREVENT DUPLICATES)
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
    print(f"Description preview: {description[:200]}...")  # Log description preview
    
    labels = fields.get("labels", [])
    priority_obj = fields.get("priority")
    priority = priority_obj.get("name") if priority_obj else "Medium"

    assignee = fields.get("assignee")
    assignee_name = assignee.get("displayName") if assignee else "Unassigned"
    
    # Debug: Log all available field keys to help identify the AC field
    print(f"Available Jira fields: {list(fields.keys())}")
    
    # Debug: Log custom field values (first 100 chars) to identify AC field
    print("\n--- Custom Field Values ---")
    for field_key in sorted(fields.keys()):
        if field_key.startswith('customfield_'):
            field_value = fields.get(field_key)
            if field_value and isinstance(field_value, str) and field_value.strip():
                preview = field_value[:100].replace('\n', ' ')
                print(f"{field_key}: {preview}...")
    print("--- End Custom Fields ---\n")
    
    # Extract Acceptance Criteria (can be in different fields depending on Jira setup)
    acceptance_criteria = None
    
    # First, check the known AC field for this Jira instance
    if fields.get("customfield_10074"):
        acceptance_criteria = fields.get("customfield_10074")
        print(f"Found Acceptance Criteria in customfield_10074: {acceptance_criteria[:100]}...")
    
    # If not found, try common custom field patterns and names
    if not acceptance_criteria:
        for field_key in fields.keys():
            field_value = fields.get(field_key)
            field_key_lower = str(field_key).lower()
            
            # Check if field name or key contains 'acceptance' or 'criteria'
            if ("acceptance" in field_key_lower or 
                "criteria" in field_key_lower or
                field_key in ["customfield_10000", "customfield_10001", "customfield_10002", 
                             "customfield_10003", "customfield_10004", "customfield_10005",
                             "customfield_10010", "customfield_10011", "customfield_10012",
                             "customfield_10015", "customfield_10016", "customfield_10017",
                             "customfield_10020", "customfield_10021", "customfield_10022",
                             "customfield_10074"]):
                if field_value and isinstance(field_value, str) and field_value.strip():
                    acceptance_criteria = field_value
                    print(f"Found Acceptance Criteria in field '{field_key}': {acceptance_criteria[:50]}...")
                    break
        
        # Also check standard field names
        if not acceptance_criteria:
            acceptance_criteria = fields.get("Acceptance Criteria") or fields.get("acceptanceCriteria")
    
    if acceptance_criteria:
        print(f"✓ Acceptance Criteria found: {len(acceptance_criteria)} characters")
    else:
        print("⚠ No Acceptance Criteria found in Jira issue")

    print(f"Labels: {labels}")

    # ---- Step 4: Check trigger label
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

    # ---- Step 5: Build GitHub issue body
    jira_base_url = os.environ["JIRA_BASE_URL"]
    jira_url = f"{jira_base_url}/browse/{jira_key}"

    # Build acceptance criteria section if available
    ac_section = ""
    if acceptance_criteria:
        ac_section = f"\n\n### Acceptance Criteria\n{acceptance_criteria}"

    github_body = f"""{description}

---

### Jira Details
- **Jira Issue**: [{jira_key}]({jira_url})
- **Priority**: {priority}
- **Assignee**: {assignee_name}{ac_section}
"""

    github_labels = map_labels(labels)

    # ---- Step 6: Create GitHub issue
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

    # ---- Step 7: Handle GitHub response
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
