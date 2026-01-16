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
    """Store bidirectional mapping between Jira and GitHub comments."""
    table_name = os.environ.get("DYNAMODB_TABLE", "jira-github-sync-state")
    table = dynamodb.Table(table_name)
    try:
        # Store both directions for easy lookup
        # comments.jira_to_github: jira_comment_id -> github_comment_id
        # comments.github_to_jira: github_comment_id -> jira_comment_id
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
        print(f"✓ Mapped Jira comment {jira_comment_id} <-> GitHub comment {github_comment_id}")
    except ClientError as e:
        print(f"DynamoDB update_item error: {e}")


def is_comment_already_synced(jira_key, jira_comment_id=None, github_comment_id=None):
    """Check if a comment has already been synced to prevent duplicates."""
    sync_item = get_sync_item(jira_key)
    if not sync_item:
        return False
    
    comments = sync_item.get("comments", {})
    
    # Check Jira -> GitHub direction
    if jira_comment_id:
        jira_to_github = comments.get("jira_to_github", {})
        if str(jira_comment_id) in jira_to_github:
            print(f"Comment already synced: Jira {jira_comment_id} -> GitHub {jira_to_github[str(jira_comment_id)]}")
            return True
    
    # Check GitHub -> Jira direction
    if github_comment_id:
        github_to_jira = comments.get("github_to_jira", {})
        if str(github_comment_id) in github_to_jira:
            print(f"Comment already synced: GitHub {github_comment_id} -> Jira {github_to_jira[str(github_comment_id)]}")
            return True
    
    return False


def extract_sync_marker(comment_body, source="jira"):
    """Extract sync marker from comment body to detect loops."""
    import re
    if source == "jira":
        # GitHub -> Jira marker format: <!-- jira-sync: jira_comment_id=12345 -->
        match = re.search(r'<!-- jira-sync: jira_comment_id=(\d+) -->', comment_body)
        return match.group(1) if match else None
    else:
        # Jira -> GitHub marker format: [//]: # (jira-sync: github_comment_id=12345)
        match = re.search(r'\[//\]: # \(jira-sync: github_comment_id=(\d+)\)', comment_body)
        return match.group(1) if match else None


def parse_jira_adf_to_text(adf_content, user_mapping=None):
    """Convert Jira ADF (Atlassian Document Format) or wiki markup to plain text with GitHub mentions."""
    if not adf_content:
        return ""
    
    # If it's already a string, it might be wiki markup - parse mentions
    if isinstance(adf_content, str):
        # Handle wiki markup mentions: [~accountid:712020:bb0cbe76-91d7-4797-bc17-cb969d3ddb7e]
        import re
        
        def replace_mention(match):
            account_id = match.group(1)  # e.g., "accountid:712020:bb0cbe76-91d7-4797-bc17-cb969d3ddb7e"
            
            # Remove "accountid:" prefix if present
            if account_id.startswith("accountid:"):
                account_id = account_id[10:]  # Remove "accountid:" (10 chars)
            
            # Try to map to GitHub username if user_mapping is provided
            if user_mapping and account_id:
                github_user = user_mapping.get('accountid', {}).get(account_id)
                if github_user:
                    return f"@{github_user}"
            
            # Fall back to a generic mention
            return f"@user"
        
        # Replace all [~accountid:...] or [~username] patterns
        text = re.sub(r'\[~([^\]]+)\]', replace_mention, adf_content)
        return text
    
    # If it's ADF format (dict with 'type' and 'content')
    if isinstance(adf_content, dict):
        text_parts = []
        
        def extract_text(node):
            if isinstance(node, dict):
                node_type = node.get("type")
                
                # Text node - extract the text
                if node_type == "text":
                    return node.get("text", "")
                
                # Nodes with content array
                if "content" in node:
                    return "".join(extract_text(child) for child in node["content"])
                
                # Mention node - convert Jira mention to GitHub mention
                if node_type == "mention":
                    attrs = node.get('attrs', {})
                    account_id = attrs.get('id', '')  # e.g., "712020:bb0cbe76-91d7-4797-bc17-cb969d3ddb7e"
                    display_text = attrs.get('text', 'user')
                    
                    # Try to map to GitHub username if user_mapping is provided
                    if user_mapping and account_id:
                        github_user = user_mapping.get('accountid', {}).get(account_id)
                        if github_user:
                            return f"@{github_user}"
                    
                    # Fall back to display text
                    return f"@{display_text}"
                
                # Hard break
                if node_type == "hardBreak":
                    return "\n"
                
            elif isinstance(node, list):
                return "".join(extract_text(item) for item in node)
            
            return ""
        
        result = extract_text(adf_content)
        return result.strip()
    
    return str(adf_content)


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
# User mapping helpers
# -------------------------------
def get_user_mapping():
    """
    Get user mapping from environment or use default mapping.
    Supports two formats:
    1. Email-based: JIRA_EMAIL:GITHUB_USERNAME
    2. AccountId-based: JIRA_ACCOUNTID:GITHUB_USERNAME
    Format: mapping1,mapping2,mapping3
    """
    mapping_str = os.environ.get("USER_MAPPING", "")
    email_map = {}
    accountid_map = {}
    
    if mapping_str:
        for pair in mapping_str.split(","):
            if ":" in pair:
                # Use rsplit to split from the right (last colon) to handle accountIds with colons
                # e.g., "712020:bb0cbe76-91d7-4797-bc17-cb969d3ddb7e:NuwanthaPiumal"
                jira_id, github_user = pair.strip().rsplit(":", 1)
                jira_id = jira_id.strip()
                github_user = github_user.strip()
                
                # Check if it's an accountId (contains ':' in the ID itself) or email
                if "@" in jira_id:
                    email_map[jira_id.lower()] = github_user
                else:
                    # Assume it's an accountId
                    accountid_map[jira_id] = github_user
    
    return {"email": email_map, "accountid": accountid_map}


def map_jira_user_to_github(jira_user_obj, user_mapping=None):
    """
    Map a Jira user to a GitHub username.
    Returns tuple: (github_username or None, display_name)
    """
    if not jira_user_obj:
        return None, "Unassigned"
    
    display_name = jira_user_obj.get("displayName") or jira_user_obj.get("name") or "Unknown User"
    
    if not user_mapping:
        return None, display_name
    
    # Try to map using accountId first (most reliable in Jira Cloud)
    jira_account_id = jira_user_obj.get("accountId", "")
    if jira_account_id and jira_account_id in user_mapping.get("accountid", {}):
        github_user = user_mapping["accountid"][jira_account_id]
        print(f"✓ Mapped via accountId: {jira_account_id} -> @{github_user}")
        return github_user, display_name
    
    # Fallback to email mapping (if available)
    email = jira_user_obj.get("emailAddress", "").lower()
    if email and email in user_mapping.get("email", {}):
        github_user = user_mapping["email"][email]
        print(f"✓ Mapped via email: {email} -> @{github_user}")
        return github_user, display_name
    
    # No mapping found
    return None, display_name


def verify_github_user_exists(username, token, owner, repo):
    """
    Verify if a GitHub user exists and has access to the repository.
    Returns True if user exists and can be assigned, False otherwise.
    """
    if not username:
        return False
    
    try:
        # Check if user is a collaborator or contributor
        url = f"https://api.github.com/repos/{owner}/{repo}/collaborators/{username}"
        resp = requests.get(
            url,
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json"
            },
            timeout=5
        )
        # 204 = user is a collaborator, 404 = not a collaborator
        return resp.status_code == 204
    except Exception as e:
        print(f"Error verifying GitHub user {username}: {e}")
        return False


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
        
        # Get user mapping for mention conversion
        user_mapping = get_user_mapping()
        
        # Extract comment body - Jira uses ADF (Atlassian Document Format)
        comment_body_raw = comment.get("body", "") or ""
        print(f"DEBUG: comment_body_raw type: {type(comment_body_raw)}")
        print(f"DEBUG: comment_body_raw: {str(comment_body_raw)[:500]}")
        comment_body = parse_jira_adf_to_text(comment_body_raw, user_mapping)
        
        print(f"Processing Jira comment {jira_comment_id}")
        print(f"Comment body preview: {comment_body[:100]}...")

        if not comment_body.strip():
            print("Empty Jira comment, skipping")
            return {"statusCode": 200, "body": json.dumps({"message": "Empty comment, skipping"})}

        # Loop prevention: Check if comment contains GitHub sync marker
        if "<!-- jira-sync:" in comment_body or "jira-sync: github_comment_id" in comment_body:
            print(f"Loop prevention: Jira comment {jira_comment_id} contains sync marker, skipping")
            return {"statusCode": 200, "body": json.dumps({"message": "Loop prevention - synced comment"})}

        # Check if this comment has already been synced
        if is_comment_already_synced(jira_key, jira_comment_id=jira_comment_id):
            print(f"Comment {jira_comment_id} already synced, skipping")
            return {"statusCode": 200, "body": json.dumps({"message": "Comment already synced"})}

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
        jira_author_obj = comment.get("author", {})
        jira_author_email = jira_author_obj.get("emailAddress", "")
        jira_author_name = jira_author_obj.get("displayName") or jira_author_obj.get("name") or "Jira user"
        
        # Try to map Jira user to GitHub user (user_mapping already fetched above)
        github_author = None
        if jira_author_email and user_mapping:
            github_author = user_mapping.get('email', {}).get(jira_author_email.lower())
        
        jira_base_url = os.environ.get("JIRA_BASE_URL", "")
        jira_url = f"{jira_base_url}/browse/{jira_key}"
        comment_created = comment.get("created", "")
        
        # Format timestamp if available
        timestamp_str = ""
        if comment_created:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(comment_created.replace('Z', '+00:00'))
                timestamp_str = f" at {dt.strftime('%Y-%m-%d %H:%M UTC')}"
            except:
                pass
        
        # Build author attribution
        if github_author:
            author_str = f"@{github_author} ({jira_author_name})"
        else:
            author_str = jira_author_name
        
        marker = f"<!-- jira-sync: jira_comment_id={jira_comment_id} -->"
        github_comment_body = f"""### 💬 Comment from Jira
**Author:** {author_str}{timestamp_str}

{comment_body}

---
*[View in Jira]({jira_url}?focusedCommentId={jira_comment_id})*
{marker}"""

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
    
    # ---- Step 3a: Check if already synced (handle updates if synced)
    sync_item = get_sync_item(jira_key)
    if sync_item:
        print(f"Issue {jira_key} already synced to GitHub - checking for updates")
        
        # Get webhook event type to determine if this is an update
        webhook_event = body.get("webhookEvent", "")
        changelog = body.get("changelog", {})
        
        # Check if description was updated
        if changelog:
            items = changelog.get("items", [])
            description_updated = any(item.get("field") == "description" for item in items)
            
            if description_updated:
                print(f"Description updated for {jira_key}, syncing to GitHub")
                
                # Get the updated description
                title = fields.get("summary", "No title provided")
                description = fields.get("description") or "_No description provided_"
                
                # Get GitHub issue number
                github_issue_number = sync_item.get("github_issue_number")
                if not github_issue_number and sync_item.get("github_issue_url"):
                    try:
                        github_issue_number = int(sync_item.get("github_issue_url").rstrip('/').split('/')[-1])
                    except Exception:
                        pass
                
                if github_issue_number:
                    try:
                        # Get GitHub credentials
                        token = get_github_token()
                        owner = os.environ["GITHUB_OWNER"]
                        repo = os.environ["GITHUB_REPO"]
                        
                        # Get current GitHub issue to preserve the existing body structure
                        url = f"https://api.github.com/repos/{owner}/{repo}/issues/{github_issue_number}"
                        headers = {
                            "Authorization": f"Bearer {token}",
                            "Accept": "application/vnd.github.v3+json",
                            "User-Agent": "jira-github-integration"
                        }
                        resp = requests.get(url, headers=headers, timeout=30)
                        
                        if resp.status_code == 200:
                            current_issue = resp.json()
                            current_body = current_issue.get("body", "")
                            
                            # Rebuild the body with updated description
                            jira_base_url = os.environ["JIRA_BASE_URL"]
                            jira_url = f"{jira_base_url}/browse/{jira_key}"
                            
                            # Parse description if it's ADF format
                            user_mapping = get_user_mapping()
                            description_text = parse_jira_adf_to_text(description, user_mapping)
                            
                            # Extract existing sections to preserve them
                            jira_details_section = ""
                            acceptance_criteria_section = ""
                            footer_section = ""
                            
                            # Extract Jira Details section (between Description and Acceptance Criteria or end)
                            if "### 📌 Jira Details" in current_body:
                                start_idx = current_body.index("### 📌 Jira Details")
                                # Find where it ends (either at next ## heading or end)
                                end_idx = len(current_body)
                                if "## 🎯 Acceptance Criteria" in current_body[start_idx:]:
                                    end_idx = start_idx + current_body[start_idx:].index("## 🎯 Acceptance Criteria")
                                jira_details_section = current_body[start_idx:end_idx].rstrip()
                            
                            # Extract Acceptance Criteria section
                            if "## 🎯 Acceptance Criteria" in current_body:
                                start_idx = current_body.index("## 🎯 Acceptance Criteria")
                                # Find where it ends (either at --- or end)
                                end_idx = len(current_body)
                                if "---\n*Synced from Jira:" in current_body[start_idx:]:
                                    end_idx = start_idx + current_body[start_idx:].index("---\n*Synced from Jira:")
                                acceptance_criteria_section = current_body[start_idx:end_idx].rstrip()
                            
                            # Extract footer
                            if "---\n*Synced from Jira:" in current_body:
                                footer_section = current_body[current_body.index("---\n*Synced from Jira:"):]
                            
                            # Rebuild body with updated description while preserving other sections
                            new_body = f"""## 📋 Description
{description_text}

"""
                            if jira_details_section:
                                new_body += jira_details_section + "\n\n"
                            
                            if acceptance_criteria_section:
                                new_body += acceptance_criteria_section + "\n\n"
                            
                            if footer_section:
                                new_body += footer_section
                            else:
                                new_body += f"""---
*Synced from Jira: [{jira_key}]({jira_url})*"""
                            
                            # Update GitHub issue
                            update_data = {"body": new_body}
                            resp = requests.patch(url, json=update_data, headers=headers, timeout=30)
                            
                            if resp.status_code == 200:
                                print(f"✓ Updated GitHub issue #{github_issue_number} description")
                                return {"statusCode": 200, "body": json.dumps({"message": "Description synced to GitHub"})}
                            else:
                                print(f"Failed to update GitHub issue: {resp.status_code} - {resp.text}")
                        else:
                            print(f"Failed to fetch GitHub issue: {resp.status_code}")
                            
                    except Exception as e:
                        print(f"Error updating GitHub issue description: {e}")
        
        # No updates to sync, skip
        print(f"⊘ No relevant updates for {jira_key}, skipping")
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Already synced, no updates",
                "jira_issue": jira_key
            })
        }
    
    title = fields.get("summary", "No title provided")
    description = fields.get("description") or "_No description provided_"
    print(f"Description preview: {description[:200]}...")  # Log description preview
    
    labels = fields.get("labels", [])
    priority_obj = fields.get("priority")
    priority = priority_obj.get("name") if priority_obj else "Medium"

    # Get reporter information
    reporter = fields.get("reporter")
    _, reporter_name = map_jira_user_to_github(reporter, get_user_mapping())
    
    # Get assignee information
    assignee = fields.get("assignee")
    user_mapping = get_user_mapping()
    github_assignee, assignee_name = map_jira_user_to_github(assignee, user_mapping)
    
    # Debug logging for assignee
    print(f"Assignee object: {assignee}")
    print(f"User mapping: {user_mapping}")
    print(f"Mapped GitHub assignee: {github_assignee}")
    print(f"Assignee name: {assignee_name}")
    
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

    # Build assignee section with note if user doesn't exist in GitHub
    assignee_section = f"**Assignee (Jira):** {assignee_name}"
    if github_assignee:
        assignee_section = f"**Assignee:** @{github_assignee} ({assignee_name})"

    github_body = f"""{description}

---

### Jira Details
- **Jira Issue**: [{jira_key}]({jira_url})
- **Reporter (Jira):** {reporter_name}
- {assignee_section}
- **Priority**: {priority}{ac_section}
"""

    github_labels = map_labels(labels)

    # ---- Step 6: Create GitHub issue
    try:
        token = get_github_token()
        owner = os.environ["GITHUB_OWNER"]
        repo = os.environ["GITHUB_REPO"]

        # Prepare issue data
        issue_data = {
            "title": title[:256],     # GitHub limit safety
            "body": github_body,
            "labels": github_labels[:20]
        }
        
        # Only assign if user exists in GitHub and is a collaborator
        if github_assignee:
            if verify_github_user_exists(github_assignee, token, owner, repo):
                issue_data["assignees"] = [github_assignee]
                print(f"✓ Will assign to GitHub user: @{github_assignee}")
            else:
                print(f"⚠ GitHub user @{github_assignee} not found or not a collaborator, skipping assignment")

        response = requests.post(
            f"https://api.github.com/repos/{owner}/{repo}/issues",
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json"
            },
            json=issue_data,
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
