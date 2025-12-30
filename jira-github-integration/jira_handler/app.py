import json
import os
import hmac
import hashlib
import requests
import boto3
from botocore.exceptions import ClientError

# Create clients outside handler (reuse across invocations)
secrets_client = boto3.client("secretsmanager")

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
    title = fields.get("summary", "No title provided")
    description = fields.get("description") or "_No description provided_"
    labels = fields.get("labels", [])
    priority = fields.get("priority", {}).get("name", "Medium")

    assignee = fields.get("assignee")
    assignee_name = assignee.get("displayName") if assignee else "Unassigned"

    print(f"Jira Issue: {jira_key}")
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

    github_body = f"""{description}

---

### Jira Details
- **Jira Issue**: [{jira_key}]({jira_url})
- **Priority**: {priority}
- **Assignee**: {assignee_name}
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
    print(f"GitHub issue created: {github_issue['html_url']}")

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "GitHub issue created successfully",
            "jira_issue": jira_key,
            "github_issue_url": github_issue["html_url"]
        })
    }
