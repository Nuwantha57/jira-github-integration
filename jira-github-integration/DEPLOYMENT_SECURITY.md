# Deployment Steps with Signature Verification

## Summary of Changes

✅ Added webhook signature verification to Lambda function
✅ Added HMAC SHA-256 signature validation
✅ Returns 401 for unauthorized requests
✅ Local tests passed successfully

## Step-by-Step Deployment

### Step 1: Update AWS Secrets Manager

```powershell
# Run this to add webhook_secret to your existing secret
.\add-webhook-secret.ps1
```

**IMPORTANT:** Copy and save the webhook secret displayed - you'll need it for Jira!

### Step 2: Deploy Updated Lambda Function

**Option A: Using SAM (Recommended)**

```powershell
sam build
sam deploy
```

**Option B: Using ZIP file (Manual)**

```powershell
# Create deployment package
cd jira_handler
Compress-Archive -Path * -DestinationPath ..\lambda-deployment.zip -Force
cd ..

# Upload to AWS Lambda
aws lambda update-function-code `
    --function-name JiraWebhookFunction `
    --zip-file fileb://lambda-deployment.zip
```

### Step 3: Configure Jira Webhook Secret

1. Go to your Jira instance
2. Navigate to: **Settings → System → WebHooks**
3. Find your webhook (URL: https://lmccuh0gra.execute-api.eu-north-1.amazonaws.com/default/JiraWebhookFunction)
4. Click **Edit**
5. Add the webhook secret from Step 1
6. Save

### Step 4: Test Security

After deployment, run the security test again:

```powershell
# Without secret (should fail)
.\test-security.ps1 -WebhookUrl "https://lmccuh0gra.execute-api.eu-north-1.amazonaws.com/default/JiraWebhookFunction"

# With secret (should pass)
.\test-security.ps1 `
    -WebhookUrl "https://lmccuh0gra.execute-api.eu-north-1.amazonaws.com/default/JiraWebhookFunction" `
    -JiraSecret "YOUR_WEBHOOK_SECRET_HERE"
```

### Expected Results After Deployment

✅ **Test 1**: Request without signature → **401 Unauthorized**
✅ **Test 2**: Request with invalid signature → **401 Unauthorized**  
✅ **Test 3**: Request with valid signature → **200 OK**
✅ **Test 4**: Malformed JSON → **400 Bad Request**

## Files Modified

- [jira_handler/app.py](jira_handler/app.py) - Added signature verification
- [lambda_deployment_package/app.py](lambda_deployment_package/app.py) - Added signature verification

## Security Benefits

✅ Prevents unauthorized webhook calls
✅ Validates requests come from Jira
✅ Uses secure HMAC SHA-256 hashing
✅ Timing-attack resistant comparison
✅ Logs security violations

## Troubleshooting

**Issue:** Lambda still accepts requests without signature

- Make sure you deployed the updated code
- Check Lambda logs for verification messages
- Verify webhook_secret exists in Secrets Manager

**Issue:** All requests return 401

- Check the webhook secret matches between AWS and Jira
- Verify Jira is sending X-Hub-Signature header
- Check CloudWatch logs for signature mismatch details
