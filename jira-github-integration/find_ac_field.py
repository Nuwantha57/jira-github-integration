"""
Script to help identify which Jira field contains Acceptance Criteria
Run this after triggering a webhook to see all field values
"""

# Paste the fields list from your CloudWatch logs here
fields_list = ['statuscategorychangedate', 'issuetype', 'timespent', 'customfield_10074', 
               'customfield_10030', 'customfield_10031', 'project', 'customfield_10032', 
               'fixVersions', 'customfield_10033', 'statusCategory', 'aggregatetimespent', 
               'resolution', 'customfield_10035', 'customfield_10036', 'customfield_10037', 
               'customfield_10027', 'customfield_10028', 'customfield_10029', 'resolutiondate', 
               'workratio', 'lastViewed', 'watches', 'created', 'customfield_10020', 
               'customfield_10021', 'customfield_10022', 'priority', 'customfield_10023', 
               'customfield_10024', 'customfield_10025', 'labels', 'customfield_10026', 
               'customfield_10016', 'customfield_10017', 'customfield_10019', 'timeestimate', 
               'aggregatetimeoriginalestimate', 'versions', 'issuelinks', 'assignee', 
               'updated', 'status', 'components', 'timeoriginalestimate', 'description', 
               'customfield_10010', 'customfield_10014', 'timetracking', 'customfield_10015', 
               'customfield_10005', 'customfield_10006', 'security', 'customfield_10007', 
               'customfield_10008', 'customfield_10009', 'aggregatetimeestimate', 'attachment', 
               'summary', 'creator', 'subtasks', 'customfield_10040', 'reporter', 
               'aggregateprogress', 'customfield_10001', 'customfield_10002', 'customfield_10003', 
               'customfield_10004', 'customfield_10039', 'environment', 'duedate', 'progress', 'votes']

print("Custom fields found in your Jira instance:")
print("=" * 60)
custom_fields = [f for f in fields_list if f.startswith('customfield_')]
for i, field in enumerate(sorted(custom_fields), 1):
    print(f"{i}. {field}")

print("\n" + "=" * 60)
print(f"\nTotal custom fields: {len(custom_fields)}")
print("\nTo find your Acceptance Criteria field:")
print("1. Go to Jira Settings → Issues → Custom fields")
print("2. Find 'Acceptance Criteria' in the list")
print("3. Click on it to see its details")
print("4. Look for the field ID (e.g., customfield_10050)")
print("5. Tell me the field ID so I can update the code")
