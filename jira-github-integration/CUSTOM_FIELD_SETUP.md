# Custom Field Configuration Guide

## Finding Your Jira Custom Field IDs

The Acceptance Criteria feature requires you to configure the correct custom field ID for your specific Jira instance. **Custom field IDs are unique to each Jira account** (e.g., `customfield_10074`, `customfield_10034`, etc.).

---

## Method 1: Using Jira REST API (Recommended)

### Step 1: List All Custom Fields

```bash
curl -u "YOUR_JIRA_EMAIL:YOUR_JIRA_API_TOKEN" \
  "https://YOUR_DOMAIN.atlassian.net/rest/api/3/field" | jq '.[] | select(.custom==true) | {id, name}'
```

**Example Output:**
```json
{
  "id": "customfield_10034",
  "name": "Acceptance Criteria"
}
{
  "id": "customfield_10035",
  "name": "Story Points"
}
```

### Step 2: Find Your Acceptance Criteria Field

Look for a field with name like:
- `Acceptance Criteria`
- `Acceptance Criteria (Paragraph)`
- `AC`
- Or any custom name you used

**Copy the `id` value** (e.g., `customfield_10034`)

---

## Method 2: Check a Jira Issue JSON

### Step 1: Open Any Jira Issue

1. Go to your Jira project
2. Open any issue that has Acceptance Criteria filled in
3. Get the issue key (e.g., `PROJ-123`)

### Step 2: Fetch Issue JSON

```bash
curl -u "YOUR_JIRA_EMAIL:YOUR_JIRA_API_TOKEN" \
  "https://YOUR_DOMAIN.atlassian.net/rest/api/3/issue/PROJ-123" \
  | jq '.fields | keys[] | select(startswith("customfield_"))'
```

This will list all custom fields in the issue. Look for the one containing your Acceptance Criteria data.

### Step 3: Inspect Field Contents

```bash
curl -u "YOUR_JIRA_EMAIL:YOUR_JIRA_API_TOKEN" \
  "https://YOUR_DOMAIN.atlassian.net/rest/api/3/issue/PROJ-123" \
  | jq '.fields.customfield_XXXXX'  # Replace XXXXX with field number
```

Check which field contains your Acceptance Criteria text.

---

## Method 3: Using Browser DevTools (Easiest)

### Step 1: Open Jira Issue with Acceptance Criteria

1. Open your browser (Chrome/Firefox)
2. Go to any Jira issue that has Acceptance Criteria filled in
3. Open DevTools (F12)

### Step 2: Inspect Network Requests

1. In DevTools, go to **Network** tab
2. Refresh the page (F5)
3. Filter by "issue" in the network requests
4. Find the REST API call to `/rest/api/3/issue/PROJ-XXX`
5. Click on it and go to **Response** tab
6. Search for your Acceptance Criteria text
7. Look at the JSON path - it will be something like `fields.customfield_10034`

**The number after `customfield_` is your field ID!**

---

## Configuring the Integration

Once you have your custom field ID, you need to configure it in two places:

### Option 1: Environment Variable (Recommended for Future)

⚠️ **Currently not implemented** - requires code update (see Implementation section below)

### Option 2: Update Code Directly (Current Method)

Edit [jira_handler/app.py](jira_handler/app.py) and replace all instances of `customfield_10074` with your field ID:

**Search for:** `customfield_10074`  
**Replace with:** Your field ID (e.g., `customfield_10034`)

**Lines to update:**
- Line ~1149: `ac_updated = any(item.get("field") == "customfield_10074" for item in items)`
- Line ~1525: `acceptance_criteria_raw = fields.get("customfield_10074")`
- Line ~1665: `if fields.get("customfield_10074"):`
- Line ~1666: `acceptance_criteria_raw = fields.get("customfield_10074")`
- Line ~1683: `print(f"DEBUG AC: customfield_10074 not found or empty")`
- Line ~1684: `print(f"DEBUG AC: customfield_10074 value: {fields.get('customfield_10074')}")`
- Line ~1697: `acceptance_criteria_raw = full_fields.get('customfield_10074')`
- Line ~1726: List of common custom fields

After updating, rebuild and redeploy:

```bash
sam build --use-container
sam deploy
```

---

## Testing the Configuration

### Step 1: Create Test Issue

1. Create a Jira issue with Acceptance Criteria filled in
2. Add the `sync-to-github` label

### Step 2: Check CloudWatch Logs

```bash
sam logs --stack-name jira-github-integration --tail
```

**Look for these log messages:**

✅ **Success:**
```
Found Acceptance Criteria in customfield_10034
✓ Acceptance Criteria found: 245 characters
```

❌ **Failure:**
```
DEBUG AC: customfield_10034 not found or empty
⚠ No Acceptance Criteria found in Jira issue
```

### Step 3: Verify GitHub Issue

Check the GitHub issue - it should have a section like:

```markdown
## 🎯 Acceptance Criteria

- Criteria 1
- Criteria 2
- Criteria 3
```

If this section is missing, your custom field ID is incorrect.

---

## Common Custom Field IDs by Jira Template

Different Jira project templates assign different field IDs:

| Template Type | Common AC Field IDs |
|---------------|-------------------|
| Scrum | `customfield_10034`, `customfield_10035` |
| Kanban | `customfield_10030`, `customfield_10031` |
| Bug Tracking | `customfield_10020`, `customfield_10021` |
| Company-Managed | `customfield_100XX` (varies widely) |
| Team-Managed | `customfield_100XX` (varies widely) |

⚠️ **These are examples only** - you must find your specific field ID using the methods above.

---

## Implementation: Add Environment Variable Support

To make this configurable without code changes, add this feature:

### Update template.yaml

```yaml
Environment:
  Variables:
    # ... existing variables ...
    ACCEPTANCE_CRITERIA_FIELD: "customfield_10074"  # Your custom field ID
```

### Update app.py

Replace hardcoded field IDs with:

```python
# At the top of the file
ACCEPTANCE_CRITERIA_FIELD = os.environ.get("ACCEPTANCE_CRITERIA_FIELD", "customfield_10074")

# Then replace all instances like:
if fields.get("customfield_10074"):
    # Change to:
if fields.get(ACCEPTANCE_CRITERIA_FIELD):
```

This allows clients to configure their field ID without modifying code.

---

## Troubleshooting

### Issue: Acceptance Criteria Not Syncing

**Symptom:** GitHub issue created but missing Acceptance Criteria section

**Checklist:**
- [ ] Confirmed custom field ID using one of the methods above
- [ ] Updated all instances of `customfield_10074` in app.py
- [ ] Rebuilt and redeployed: `sam build --use-container && sam deploy`
- [ ] Jira issue actually has Acceptance Criteria filled in
- [ ] Checked CloudWatch logs for field detection messages

### Issue: Wrong Field Being Used

**Symptom:** Wrong data appears in Acceptance Criteria section

**Solution:** You may have multiple fields with similar names. Use Method 2 or 3 to confirm the exact field that contains your Acceptance Criteria text.

### Issue: Field Format Not Recognized

**Symptom:** Acceptance Criteria appears as raw JSON or strange formatting

**Cause:** Jira uses different formats:
- **ADF (Atlassian Document Format):** Rich text in JSON structure
- **Plain Text:** Simple string
- **Wiki Markup:** Jira's markdown-like syntax

The code handles all three formats automatically. If you see issues, check CloudWatch logs for parsing errors.

---

## Need Help?

1. **Check CloudWatch Logs:** `sam logs --stack-name jira-github-integration --tail`
2. **Test REST API:** Use the curl commands above to verify field exists
3. **Verify Field Type:** Ensure it's a text field (paragraph or text field)
4. **Review [TROUBLESHOOTING.md](TROUBLESHOOTING.md):** For more solutions

---

## Quick Reference Commands

```bash
# Find all custom fields
curl -u "EMAIL:TOKEN" "https://DOMAIN.atlassian.net/rest/api/3/field" | jq '.[] | select(.custom==true) | {id, name}'

# Get specific issue fields
curl -u "EMAIL:TOKEN" "https://DOMAIN.atlassian.net/rest/api/3/issue/PROJ-123" | jq '.fields | keys[]'

# Test specific field
curl -u "EMAIL:TOKEN" "https://DOMAIN.atlassian.net/rest/api/3/issue/PROJ-123" | jq '.fields.customfield_XXXXX'

# Update code and redeploy
# 1. Edit jira_handler/app.py - replace customfield_10074
# 2. sam build --use-container
# 3. sam deploy

# Test integration
# 1. Create Jira issue with Acceptance Criteria
# 2. Add label: sync-to-github
# 3. Check GitHub Issues tab
# 4. Verify AC section appears
```
