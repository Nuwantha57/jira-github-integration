import json
import pytest
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../jira_handler'))

from jira_handler import app


@pytest.fixture()
def jira_webhook_event():
    """ Generates Jira Webhook Event"""

    return {
        "body": json.dumps({
            "webhookEvent": "jira:issue_created",
            "issue": {
                "key": "TEST-123",
                "fields": {
                    "summary": "Test Issue",
                    "description": "Test Description",
                    "labels": ["sync-to-github"],
                    "priority": {"name": "Medium"},
                    "reporter": {"displayName": "Test User", "emailAddress": "test@example.com"},
                    "assignee": None,
                    "attachment": []
                }
            }
        }),
        "resource": "/webhook",
        "requestContext": {
            "resourceId": "123456",
            "apiId": "1234567890",
            "resourcePath": "/webhook",
            "httpMethod": "POST",
            "requestId": "c6af9ac6-7b61-11e6-9a41-93e8deadbeef",
            "accountId": "123456789012",
            "identity": {
                "sourceIp": "127.0.0.1",
                "accountId": "",
            },
            "stage": "prod",
        },
        "queryStringParameters": None,
        "headers": {
            "Content-Type": "application/json",
            "User-Agent": "Atlassian-HttpClient/1.0 (test.atlassian.net)",
            "X-Atlassian-Webhook-Identifier": "test-webhook-123456789",
            "x-atlassian-webhook-identifier": "test-webhook-123456789",
            "Host": "test.execute-api.us-east-1.amazonaws.com",
        },
        "resource": "/{proxy+}",
        "requestContext": {
            "resourceId": "123456",
            "apiId": "1234567890",
            "resourcePath": "/{proxy+}",
            "httpMethod": "POST",
            "requestId": "c6af9ac6-7b61-11e6-9a41-93e8deadbeef",
            "accountId": "123456789012",
            "identity": {
                "apiKey": "",
                "userArn": "",
                "cognitoAuthenticationType": "",
                "caller": "",
                "userAgent": "Custom User Agent String",
                "user": "",
                "cognitoIdentityPoolId": "",
                "cognitoIdentityId": "",
                "cognitoAuthenticationProvider": "",
                "sourceIp": "127.0.0.1",
                "accountId": "",
            },
            "stage": "prod",
        },
        "queryStringParameters": {"foo": "bar"},
        "headers": {
            "Via": "1.1 08f323deadbeefa7af34d5feb414ce27.cloudfront.net (CloudFront)",
            "Accept-Language": "en-US,en;q=0.8",
            "CloudFront-Is-Desktop-Viewer": "true",
            "CloudFront-Is-SmartTV-Viewer": "false",
            "CloudFront-Is-Mobile-Viewer": "false",
            "X-Forwarded-For": "127.0.0.1, 127.0.0.2",
            "CloudFront-Viewer-Country": "US",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Upgrade-Insecure-Requests": "1",
            "X-Forwarded-Port": "443",
            "Host": "1234567890.execute-api.us-east-1.amazonaws.com",
            "X-Forwarded-Proto": "https",
            "X-Amz-Cf-Id": "aaaaaaaaaae3VYQb9jd-nvCd-de396Uhbp027Y2JvkCPNLmGJHqlaA==",
            "CloudFront-Is-Tablet-Viewer": "false",
            "Cache-Control": "max-age=0",
            "User-Agent": "Custom User Agent String",
            "CloudFront-Forwarded-Proto": "https",
            "Accept-Encoding": "gzip, deflate, sdch",
        },
        "pathParameters": None,
        "httpMethod": "POST",
        "stageVariables": None,
        "path": "/webhook",
    }


@patch.dict(os.environ, {
    "GITHUB_OWNER": "test-owner",
    "GITHUB_REPO": "test-repo",
    "JIRA_BASE_URL": "https://test.atlassian.net",
    "JIRA_EMAIL": "test@example.com",
    "TARGET_LABEL": "sync-to-github",
    "SECRET_NAME": "test-secret",
    "DYNAMODB_TABLE": "test-table"
})
@patch('jira_handler.app.get_secrets')
@patch('jira_handler.app.is_already_synced')
def test_lambda_handler_missing_body(mock_synced, mock_secrets, jira_webhook_event):
    """Test handler returns 400 for invalid JSON body"""
    jira_webhook_event["body"] = "{invalid json"
    
    ret = app.lambda_handler(jira_webhook_event, "")
    
    assert ret["statusCode"] == 400


@patch.dict(os.environ, {
    "GITHUB_OWNER": "test-owner",
    "GITHUB_REPO": "test-repo",
    "JIRA_BASE_URL": "https://test.atlassian.net",
    "JIRA_EMAIL": "test@example.com",
    "TARGET_LABEL": "sync-to-github",
    "SECRET_NAME": "test-secret",
    "DYNAMODB_TABLE": "test-table",
    "USER_MAPPING": "test@example.com:testuser"
})
@patch('jira_handler.app.requests.post')
@patch('jira_handler.app.mark_as_synced')
@patch('jira_handler.app.get_secrets')
@patch('jira_handler.app.is_already_synced')
def test_lambda_handler_valid_webhook(mock_synced, mock_secrets, mock_mark_synced, mock_post, jira_webhook_event):
    """Test handler processes valid webhook"""
    mock_secrets.return_value = {
        "github_token": "test_token",
        "jira_api_token": "test_jira_token",
        "jira_email": "test@example.com"
    }
    mock_synced.return_value = False
    mock_post.return_value = MagicMock(status_code=201, json=lambda: {"html_url": "https://github.com/test/issue/1"})
    
    ret = app.lambda_handler(jira_webhook_event, "")
    
    assert ret["statusCode"] == 200
    assert "message" in ret["body"]
