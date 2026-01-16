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


def get_jira_token():
    """
    Fetch Jira API token from AWS Secrets Manager
    """
    secrets = get_secrets()
    if "jira_api_token" not in secrets:
        raise Exception("'jira_api_token' not found in secret")
    return secrets["jira_api_token"]


# -------------------------------
# User Mapping with Dynamic AccountId Lookup
# -------------------------------
def get_accountid_from_email(email, jira_base_url, jira_credentials):
    """
    Query Jira API to get accountId from email address.
    Uses DynamoDB caching to minimize API calls.
    Cache TTL: 24 hours
    
    Args:
        email: Jira user email address
        jira_base_url: Jira instance URL
        jira_credentials: Dict with 'email' and 'token' for Basic auth
    
    Returns:
        accountId string or None if not found
    """
    table_name = os.environ.get("DYNAMODB_TABLE", "jira-github-sync-state")
    table = dynamodb.Table(table_name)
    cache_key = f"user_email_lookup#{email.lower()}"
    
    # Check cache first
    try:
        response = table.get_item(Key={"jira_issue_key": cache_key})
        if "Item" in response:
            item = response["Item"]
            # Check if cache is still valid (TTL not expired)
            if "ttl" in item and item["ttl"] > int(time.time()):
                account_id = item.get("accountId")
                if account_id:
                    print(f"✓ Cache hit: {email} -> {account_id}")
                    return account_id
    except ClientError as e:
        print(f"Cache lookup error: {e}")
    
    # Cache miss - query Jira API
    print(f"Cache miss - querying Jira API for: {email}")
    url = f"{jira_base_url}/rest/api/3/user/search"
    params = {"query": email}
    
    try:
        auth = (jira_credentials.get("email"), jira_credentials.get("token"))
        resp = requests.get(url, params=params, auth=auth, timeout=10)
        
        if resp.status_code == 200:
            users = resp.json()
            if users and len(users) > 0:
                # Find exact email match
                for user in users:
                    if user.get("emailAddress", "").lower() == email.lower():
                        account_id = user.get("accountId")
                        print(f"✓ Found accountId via API: {email} -> {account_id}")
                        
                        # Cache the result for 24 hours
                        try:
                            ttl = int(time.time()) + (24 * 60 * 60)
                            table.put_item(Item={
                                "jira_issue_key": cache_key,
                                "accountId": account_id,
                                "email": email.lower(),
                                "cached_at": datetime.utcnow().isoformat(),
                                "ttl": ttl
                            })
                            print(f"✓ Cached accountId for 24 hours")
                        except ClientError as e:
                            print(f"Cache write error: {e}")
                        
                        return account_id
                
                print(f"⚠ No exact email match found in API results for: {email}")
                return None
        else:
            print(f"⚠ Jira API error: {resp.status_code} - {resp.text[:200]}")
            return None
    except Exception as e:
        print(f"Error querying Jira API: {e}")
        return None


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


def parse_jira_adf_to_text(adf_content, user_mapping=None, jira_base_url=None, jira_attachments=None, jira_credentials=None):
    """Convert Jira ADF (Atlassian Document Format) or wiki markup to plain text with GitHub mentions and images.
    
    Args:
        jira_credentials: Dict with 'email' and 'token' for downloading images
    """
    if not adf_content:
        return ""
    
    # If it's already a string, it might be wiki markup - parse mentions and images
    if isinstance(adf_content, str):
        # Handle wiki markup mentions: [~accountid:712020:bb0cbe76-91d7-4797-bc17-cb969d3ddb7e]
        import re
        
        def replace_mention(match):
            account_id = match.group(1)  # e.g., "accountid:712020:bb0cbe76-91d7-4797-bc17-cb969d3ddb7e"
            
            # Remove "accountid:" prefix if present
            if account_id.startswith("accountid:"):
                account_id = account_id[10:]  # Remove "accountid:" (10 chars)
            
            # Try to map accountId to GitHub username using dynamic lookup
            if user_mapping and account_id and jira_base_url and jira_credentials:
                # Try each email in mapping to find which one matches this accountId
                for email, github_user in user_mapping.items():
                    lookup_account_id = get_accountid_from_email(email, jira_base_url, jira_credentials)
                    if lookup_account_id and lookup_account_id == account_id:
                        return f"@{github_user}"
            
            # Fall back to a generic mention
            return f"@user"
        
        # Replace all [~accountid:...] or [~username] patterns
        text = re.sub(r'\[~([^\]]+)\]', replace_mention, adf_content)
        
        # Handle wiki markup images: !image.png! or !image.png|width=494,alt="text"!
        if '!' in text:
            def replace_image(match):
                image_markup = match.group(1)  # e.g., "test-img.png|width=494,alt="test-img.png""
                
                # Parse image name and attributes
                parts = image_markup.split('|', 1)
                image_name = parts[0].strip()
                
                print(f"DEBUG: Parsing image: {image_name}")
                print(f"DEBUG: Available attachments: {[a.get('filename') for a in (jira_attachments or [])]}")
                
                # Parse attributes if present
                width = None
                alt = image_name
                if len(parts) > 1:
                    attrs = parts[1]
                    # Extract width
                    width_match = re.search(r'width=(\d+)', attrs)
                    if width_match:
                        width = width_match.group(1)
                    # Extract alt text
                    alt_match = re.search(r'alt="([^"]*)"', attrs)
                    if alt_match:
                        alt = alt_match.group(1)
                
                # Try to find attachment URL from jira_attachments list
                image_url = None
                if jira_attachments:
                    for attachment in jira_attachments:
                        if attachment.get('filename') == image_name:
                            image_url = attachment.get('content')
                            print(f"DEBUG: Found attachment URL: {image_url}")
                            break
                
                if not image_url:
                    print(f"DEBUG: No matching attachment found for {image_name}")
                
                # Download and upload image to GitHub repository
                if image_url and jira_credentials:
                    # Get GitHub credentials
                    github_token = jira_credentials.get('github_token')
                    github_owner = jira_credentials.get('github_owner')
                    github_repo = jira_credentials.get('github_repo')
                    
                    github_image_url = upload_image_to_github(
                        image_url, 
                        image_name,
                        jira_credentials.get('email'),
                        jira_credentials.get('token'),
                        github_token,
                        github_owner,
                        github_repo
                    )
                    
                    if github_image_url:
                        # Embed image using GitHub URL
                        if width:
                            return f'\n\n<img src="{github_image_url}" alt="{alt}" width="{width}" />\n\n'
                        else:
                            return f'\n\n![{alt}]({github_image_url})\n\n'
                
                # Fallback to link if download failed or no credentials
                if image_url:
                    if width:
                        return f'\n\n> 📷 **Image:** `{image_name}` (width: {width}px)\n> 🔗 [View in Jira]({image_url})\n\n'
                    else:
                        return f'\n\n> 📷 **Image:** `{image_name}`\n> 🔗 [View in Jira]({image_url})\n\n'
                else:
                    # Fallback if attachment not found
                    return f'\n\n> 📎 **Image:** {image_name}\n> ⚠️ *Attachment not found in issue data*\n\n'
            
            # Replace all !image! patterns
            text = re.sub(r'!([^!]+)!', replace_image, text)
        
        return text
    
    # If it's ADF format (dict with 'type' and 'content')
    if isinstance(adf_content, dict):
        text_parts = []
        
        def extract_text(node, depth=0):
            if isinstance(node, dict):
                node_type = node.get("type")
                
                # Text node - extract the text
                if node_type == "text":
                    return node.get("text", "")
                
                # Paragraph node - add newlines
                if node_type == "paragraph":
                    if "content" in node:
                        para_text = "".join(extract_text(child, depth+1) for child in node["content"])
                        return para_text + "\n\n"
                    return "\n\n"
                
                # Heading nodes
                if node_type == "heading":
                    level = node.get("attrs", {}).get("level", 1)
                    heading_prefix = "#" * level
                    if "content" in node:
                        heading_text = "".join(extract_text(child, depth+1) for child in node["content"])
                        return f"{heading_prefix} {heading_text}\n\n"
                    return ""
                
                # Media node - handle images, videos, GIFs
                if node_type == "media" or node_type == "mediaInline" or node_type == "mediaSingle":
                    attrs = node.get('attrs', {})
                    
                    # If it's a mediaSingle, look for media child
                    if node_type == "mediaSingle" and "content" in node:
                        for child in node["content"]:
                            if child.get("type") == "media":
                                return extract_text(child, depth+1)
                    
                    # Extract media attributes
                    media_id = attrs.get('id', '')
                    media_type = attrs.get('type', 'file')  # file, link, external
                    collection = attrs.get('collection', '')
                    alt_text = attrs.get('alt', 'image')
                    width = attrs.get('width')
                    height = attrs.get('height')
                    
                    # Build Jira media URL
                    if media_id and jira_base_url:
                        # Jira Cloud media URL format
                        media_url = f"{jira_base_url}/rest/api/3/attachment/content/{media_id}"
                        
                        # Generate markdown image
                        size_attr = ""
                        if width:
                            size_attr = f' width="{width}"'
                        
                        # Use HTML img tag for better control, or markdown
                        if size_attr:
                            return f'<img src="{media_url}" alt="{alt_text}"{size_attr} />\n\n'
                        else:
                            return f"![{alt_text}]({media_url})\n\n"
                    
                    return ""
                
                # Code block
                if node_type == "codeBlock":
                    language = node.get("attrs", {}).get("language", "")
                    if "content" in node:
                        code_text = "".join(extract_text(child, depth+1) for child in node["content"])
                        return f"```{language}\n{code_text}```\n\n"
                    return ""
                
                # Bullet list
                if node_type == "bulletList":
                    if "content" in node:
                        return "".join(extract_text(child, depth+1) for child in node["content"])
                    return ""
                
                # Ordered list
                if node_type == "orderedList":
                    if "content" in node:
                        return "".join(extract_text(child, depth+1) for child in node["content"])
                    return ""
                
                # List item
                if node_type == "listItem":
                    indent = "  " * depth
                    if "content" in node:
                        item_text = "".join(extract_text(child, depth+1) for child in node["content"]).strip()
                        return f"{indent}- {item_text}\n"
                    return ""
                
                # Nodes with content array (generic handler)
                if "content" in node:
                    return "".join(extract_text(child, depth) for child in node["content"])
                
                # Mention node - convert Jira mention to GitHub mention
                if node_type == "mention":
                    attrs = node.get('attrs', {})
                    account_id = attrs.get('id', '')  # e.g., "712020:bb0cbe76-91d7-4797-bc17-cb969d3ddb7e"
                    display_text = attrs.get('text', 'user')
                    
                    # Try to map accountId to GitHub username using dynamic lookup
                    if user_mapping and account_id and jira_base_url and jira_credentials:
                        # Try each email in mapping to find which one matches this accountId
                        for email, github_user in user_mapping.items():
                            lookup_account_id = get_accountid_from_email(email, jira_base_url, jira_credentials)
                            if lookup_account_id and lookup_account_id == account_id:
                                return f"@{github_user}"
                    
                    # Fall back to display text
                    return f"@{display_text}"
                
                # Hard break
                if node_type == "hardBreak":
                    return "\n"
                
            elif isinstance(node, list):
                return "".join(extract_text(item, depth) for item in node)
            
            return ""
        
        result = extract_text(adf_content)
        return result.strip()
    
    return str(adf_content)


def upload_image_to_github_repo(image_data, image_name, github_token, owner, repo):
    """Upload image to GitHub repository and return the URL."""
    try:
        import base64
        from datetime import datetime
        
        # Create a unique path for the image in the repo
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        safe_name = image_name.replace(' ', '_')
        file_path = f".jira-attachments/{timestamp}_{safe_name}"
        
        # Encode image data to base64
        content_b64 = base64.b64encode(image_data).decode('ascii')
        
        # Upload to GitHub repository using Contents API
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"
        
        payload = {
            "message": f"Upload Jira attachment: {image_name}",
            "content": content_b64,
            "branch": "main"  # or "master" depending on your default branch
        }
        
        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        print(f"Uploading image to GitHub repo: {file_path}")
        resp = requests.put(url, json=payload, headers=headers, timeout=30)
        
        if resp.status_code not in [200, 201]:
            print(f"Failed to upload to GitHub: {resp.status_code}")
            print(f"Response: {resp.text[:500]}")
            return None
        
        result = resp.json()
        # Get the raw content URL
        download_url = result.get('content', {}).get('download_url')
        
        print(f"Image uploaded successfully: {download_url}")
        return download_url
        
    except Exception as e:
        print(f"Error uploading image to GitHub: {e}")
        import traceback
        traceback.print_exc()
        return None


def upload_image_to_github(jira_image_url, image_name, jira_email, jira_token, github_token=None, github_owner=None, github_repo=None):
    """Download image from Jira and upload to GitHub repository."""
    try:
        # Download image from Jira with authentication
        import base64
        
        auth_str = f"{jira_email}:{jira_token}"
        auth_bytes = auth_str.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        print(f"Downloading image from Jira: {jira_image_url}")
        resp = requests.get(
            jira_image_url,
            headers={
                "Authorization": f"Basic {auth_b64}",
                "Accept": "*/*",
                "X-Atlassian-Token": "no-check"
            },
            timeout=30,
            allow_redirects=True
        )
        
        if resp.status_code != 200:
            print(f"Failed to download image: {resp.status_code}")
            print(f"Response headers: {resp.headers}")
            print(f"Response text: {resp.text[:200] if resp.text else 'No content'}")
            return None
        
        image_data = resp.content
        print(f"Downloaded {len(image_data)} bytes")
        
        # Upload to GitHub repository if credentials provided
        if github_token and github_owner and github_repo:
            return upload_image_to_github_repo(image_data, image_name, github_token, github_owner, github_repo)
        
        return None
        
    except Exception as e:
        print(f"Error processing image: {e}")
        import traceback
        traceback.print_exc()
        return None


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
    Get user mapping from environment.
    Format: email:github_username (comma-separated for multiple users)
    Example: "user1@example.com:githubuser1,user2@example.com:githubuser2"
    
    Note: AccountIds are now resolved dynamically via Jira API
    """
    mapping_str = os.environ.get("USER_MAPPING", "")
    email_map = {}
    
    if mapping_str:
        for pair in mapping_str.split(","):
            if ":" in pair:
                email, github_user = pair.strip().rsplit(":", 1)
                email = email.strip().lower()
                github_user = github_user.strip()
                email_map[email] = github_user
    
    return email_map


def map_jira_user_to_github(jira_user_obj, user_mapping=None, jira_base_url=None, jira_credentials=None):
    """
    Map a Jira user to a GitHub username using dynamic accountId lookup.
    
    Flow:
    1. Try to find email in user_mapping
    2. If found, dynamically lookup accountId from Jira API (cached in DynamoDB)
    3. Verify accountId matches the user object
    
    Returns tuple: (github_username or None, display_name)
    """
    if not jira_user_obj:
        return None, "Unassigned"
    
    display_name = jira_user_obj.get("displayName") or jira_user_obj.get("name") or "Unknown User"
    jira_account_id = jira_user_obj.get("accountId", "")
    
    if not user_mapping or not jira_base_url or not jira_credentials:
        return None, display_name
    
    # Try each email in the mapping to find which one matches this accountId
    for email, github_user in user_mapping.items():
        # Dynamically lookup accountId for this email
        lookup_account_id = get_accountid_from_email(email, jira_base_url, jira_credentials)
        
        if lookup_account_id and lookup_account_id == jira_account_id:
            print(f"✓ Mapped user: {email} ({jira_account_id}) -> @{github_user}")
            return github_user, display_name
    
    # No mapping found
    print(f"⚠ No mapping found for accountId: {jira_account_id} ({display_name})")
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
    
    # Extract attachments from the issue for image resolution
    jira_attachments = fields.get("attachment", [])

    # ---- Step 3: Extract fields safely
    jira_key = issue.get("key", "UNKNOWN")
    
    print(f"Jira Issue: {jira_key}")

    # ---- Comment handling: if this webhook contains a comment, mirror to GitHub
    if body.get("comment"):
        comment = body.get("comment")
        jira_comment_id = str(comment.get("id"))
        
        # Get user mapping for mention conversion
        user_mapping = get_user_mapping()
        jira_base_url = os.environ.get("JIRA_BASE_URL", "")
        
        # Extract comment body - Jira uses ADF (Atlassian Document Format)
        comment_body_raw = comment.get("body", "") or ""
        print(f"DEBUG: comment_body_raw type: {type(comment_body_raw)}")
        print(f"DEBUG: comment_body_raw: {str(comment_body_raw)[:500]}")
        
        # Prepare Jira credentials for image downloading
        secrets = get_secrets()
        jira_credentials = {
            'email': secrets.get('jira_email'),
            'token': secrets.get('jira_api_token'),
            'github_token': secrets.get('github_token'),
            'github_owner': os.environ.get('GITHUB_OWNER'),
            'github_repo': os.environ.get('GITHUB_REPO')
        }
        comment_body = parse_jira_adf_to_text(comment_body_raw, user_mapping, jira_base_url, jira_attachments, jira_credentials)
        
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
        jira_author_name = jira_author_obj.get("displayName") or jira_author_obj.get("name") or "Jira user"
        
        # Try to map Jira user to GitHub user using dynamic lookup
        jira_base_url = os.environ.get("JIRA_BASE_URL", "")
        github_author, _ = map_jira_user_to_github(jira_author_obj, user_mapping, jira_base_url, jira_credentials)
        
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
                            secrets = get_secrets()
                            jira_credentials = {
                                'email': secrets.get('jira_email'),
                                'token': secrets.get('jira_api_token'),
                                'github_token': secrets.get('github_token'),
                                'github_owner': os.environ.get('GITHUB_OWNER'),
                                'github_repo': os.environ.get('GITHUB_REPO')
                            }
                            description_text = parse_jira_adf_to_text(description, user_mapping, jira_base_url, jira_attachments, jira_credentials)
                            
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
                                # Find where it ends
                                end_idx = len(current_body)
                                acceptance_criteria_section = current_body[start_idx:end_idx].rstrip()
                            
                            # Rebuild body with updated description while preserving other sections
                            new_body = f"""## 📋 Description
{description_text}

"""
                            if jira_details_section:
                                new_body += jira_details_section + "\n\n"
                            
                            if acceptance_criteria_section:
                                new_body += acceptance_criteria_section
                            
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

    # Prepare credentials and base URL (used for both user mapping and image handling)
    jira_base_url = os.environ["JIRA_BASE_URL"]
    secrets = get_secrets()
    jira_credentials = {
        'email': secrets.get('jira_email'),
        'token': secrets.get('jira_api_token'),
        'github_token': secrets.get('github_token'),
        'github_owner': os.environ.get('GITHUB_OWNER'),
        'github_repo': os.environ.get('GITHUB_REPO')
    }
    user_mapping = get_user_mapping()

    # Get reporter information
    reporter = fields.get("reporter")
    _, reporter_name = map_jira_user_to_github(reporter, user_mapping, jira_base_url, jira_credentials)
    
    # Get assignee information
    assignee = fields.get("assignee")
    github_assignee, assignee_name = map_jira_user_to_github(assignee, user_mapping, jira_base_url, jira_credentials)
    
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
    jira_url = f"{jira_base_url}/browse/{jira_key}"
    
    # Parse description for ADF format, mentions, and images (reuse jira_credentials from above)
    description_text = parse_jira_adf_to_text(description, user_mapping, jira_base_url, jira_attachments, jira_credentials)

    # Build acceptance criteria section if available
    ac_section = ""
    if acceptance_criteria:
        ac_section = f"\n\n## 🎯 Acceptance Criteria\n{acceptance_criteria}"

    # Build assignee section with note if user doesn't exist in GitHub
    assignee_section = f"**Assignee (Jira):** {assignee_name}"
    if github_assignee:
        assignee_section = f"**Assignee:** @{github_assignee} ({assignee_name})"

    github_body = f"""## 📋 Description
{description_text}

### 📌 Jira Details
- **Issue**: [{jira_key}]({jira_url})
- **Reporter:** {reporter_name}
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
        
        # Assign to GitHub user if mapped
        if github_assignee:
            issue_data["assignees"] = [github_assignee]
            print(f"✓ Will assign to GitHub user: @{github_assignee}")

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
