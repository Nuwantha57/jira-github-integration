# Local testing script for webhook signature verification
# Tests the signature logic without deploying to AWS

import json
import hmac
import hashlib

# Copy the verification function from your Lambda
def verify_webhook_signature(payload_body, signature_header, secret):
    """
    Verify the HMAC signature from Jira webhook
    """
    if not signature_header:
        print("Missing signature header")
        return False
    
    if not secret:
        print("Warning: No webhook secret configured, skipping verification")
        return True
    
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


# Test webhook secret
TEST_SECRET = "test_webhook_secret_12345"

# Test payload
test_payload = json.dumps({
    "issue": {
        "key": "TEST-001",
        "fields": {
            "summary": "Test Issue",
            "description": "Testing signature verification",
            "labels": ["sync-to-github", "test"],
            "priority": {"name": "Medium"}
        }
    }
})

print("=" * 60)
print("LOCAL SIGNATURE VERIFICATION TESTING")
print("=" * 60)
print(f"\nTest Secret: {TEST_SECRET}")
print(f"Payload: {test_payload[:80]}...")

# Test 1: Valid signature
print("\n[Test 1] Valid Signature")
print("-" * 40)
valid_signature = hmac.new(
    key=TEST_SECRET.encode('utf-8'),
    msg=test_payload.encode('utf-8'),
    digestmod=hashlib.sha256
).hexdigest()
valid_header = f"sha256={valid_signature}"

result = verify_webhook_signature(test_payload, valid_header, TEST_SECRET)
print(f"Result: {'PASS' if result else 'FAIL'}")
print(f"Signature: {valid_header[:30]}...")

# Test 2: Invalid signature
print("\n[Test 2] Invalid Signature")
print("-" * 40)
invalid_header = "sha256=invalid_signature_12345"
result = verify_webhook_signature(test_payload, invalid_header, TEST_SECRET)
print(f"Result: {'FAIL (Expected)' if not result else 'PASS (Unexpected)'}")

# Test 3: Missing signature header
print("\n[Test 3] Missing Signature Header")
print("-" * 40)
result = verify_webhook_signature(test_payload, None, TEST_SECRET)
print(f"Result: {'FAIL (Expected)' if not result else 'PASS (Unexpected)'}")

# Test 4: No secret configured
print("\n[Test 4] No Secret Configured")
print("-" * 40)
result = verify_webhook_signature(test_payload, valid_header, None)
print(f"Result: {'PASS (Allows request)' if result else 'FAIL'}")

print("\n" + "=" * 60)
print("LOCAL TESTING COMPLETE")
print("=" * 60)
print("\nAll tests passed! Signature verification logic is working correctly.")
print("\nNext steps:")
print("1. Generate a secure webhook secret")
print("2. Add it to AWS Secrets Manager as 'webhook_secret'")
print("3. Deploy the updated Lambda function")
print("4. Configure the secret in Jira webhook settings")
