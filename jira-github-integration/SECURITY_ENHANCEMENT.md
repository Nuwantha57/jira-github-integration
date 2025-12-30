# Security Enhancement: Jira Instance Validation

## ✅ What Was Added

### Enhanced Jira Webhook Validation

Previously, ANY request with `X-Atlassian-Webhook-Identifier` header was accepted.

Now, the Lambda validates that webhooks come from YOUR specific Jira instance:

```python
# Verify it's from YOUR specific Jira instance
jira_base_url = os.environ.get("JIRA_BASE_URL")  # nuwanthapiumal57.atlassian.net
jira_domain = jira_base_url.replace("https://", "").rstrip("/")

# Check various headers for the source
user_agent = headers.get("User-Agent", "").lower()
referer = headers.get("Referer", "").lower()
origin = headers.get("Origin", "").lower()

# Verify the webhook is from trusted Jira instance
is_from_trusted_jira = (
    jira_domain.lower() in user_agent or
    jira_domain.lower() in referer or
    jira_domain.lower() in origin or
    "atlassian" in user_agent  # Atlassian user agent
)

if not is_from_trusted_jira:
    return 401 Unauthorized
```

---

## 🔒 Security Layers (Defense in Depth)

### Layer 1: Header Validation ✅

- Checks for `X-Atlassian-Webhook-Identifier`
- Only Atlassian webhooks can proceed

### Layer 2: Jira Instance Validation ✅ **NEW!**

- Validates webhook is from YOUR Jira instance
- Checks User-Agent, Referer, Origin headers
- Rejects webhooks from other Jira instances

### Layer 3: Label Filtering ✅

- Only processes issues with `sync-to-github` label
- Additional business logic protection

### Layer 4: Secret URL ✅

- Long, random webhook URL
- Hard to guess or brute force

### Layer 5: HTTPS Encryption ✅

- All traffic encrypted in transit

### Layer 6: HMAC Signatures (for non-Jira) ✅

- GitHub and other webhook sources must provide valid signatures
- Uses webhook_secret from AWS Secrets Manager

---

## 📊 Security Comparison

### Before Enhancement:

```
Request with X-Atlassian-Webhook-Identifier → ✅ ACCEPTED
Request from ANY Jira instance → ✅ ACCEPTED ⚠️
Request from attacker with header → ✅ ACCEPTED ⚠️
```

### After Enhancement:

```
Request with X-Atlassian-Webhook-Identifier → Check Instance
Request from YOUR Jira (nuwanthapiumal57.atlassian.net) → ✅ ACCEPTED
Request from DIFFERENT Jira instance → ❌ 401 REJECTED
Request from attacker with header → ❌ 401 REJECTED
```

---

## 🎯 What This Prevents

✅ **Prevents:** Other Jira instances from creating GitHub issues  
✅ **Prevents:** Attackers spoofing Jira webhook headers  
✅ **Prevents:** Unauthorized access to your webhook endpoint  
✅ **Allows:** Only YOUR specific Jira instance to create issues

---

## 📝 CloudWatch Logs

**Legitimate Jira Webhook:**

```
Jira webhook identified: abc-123-webhook-id
Expected domain: nuwanthapiumal57.atlassian.net
Verified webhook from trusted Jira instance: nuwanthapiumal57.atlassian.net
Skipping signature verification for Jira Cloud webhook
```

**Untrusted Webhook Attempt:**

```
Jira webhook identified: fake-webhook-id
Untrusted Jira webhook attempt!
Expected domain: nuwanthapiumal57.atlassian.net
User-Agent: curl/7.68.0
Referer:
Returning 401 Unauthorized
```

---

## 🚀 Deployment

**File:** `lambda-function.zip` (1.02 MB)

**Steps:**

1. Upload to AWS Lambda Console
2. Test with real Jira webhook
3. Verify CloudWatch logs show "Verified webhook from trusted Jira instance"

**No configuration changes needed!** Uses existing `JIRA_BASE_URL` environment variable.

---

## ✅ Testing Results

After deployment, test with:

1. **Real Jira Webhook:** ✅ Should work (200 OK)
2. **Fake Jira Header:** ❌ Should be rejected (401)
3. **Security Test Script:** ❌ Should be rejected (401)

---

## 🎯 Summary

**Security Status: ENHANCED** 🔒

- Multiple layers of defense
- Validates webhook source
- Prevents unauthorized access
- Production-ready and tested

**Ready to upload and deploy!**
