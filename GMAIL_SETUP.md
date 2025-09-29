# Gmail API Setup Instructions

## Overview

This guide will walk you through setting up Gmail API access for sending email notifications from your webhook.

## Option 1: Personal Gmail Account (OAuth2) - Recommended for Personal Use

### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Note your project ID

### 2. Enable Gmail API

1. In Google Cloud Console, go to "APIs & Services" > "Library"
2. Search for "Gmail API"
3. Click on "Gmail API" and click "Enable"

### 3. Create OAuth2 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. If prompted, configure the OAuth consent screen:
   - Choose "External" for user type
   - Fill in required fields (app name, user support email, developer contact)
   - Add your email as a test user
4. For application type, choose "Desktop application"
5. Name it something like "TMK Webhook Email Service"
6. Download the JSON file and save it as `credentials.json` in your project directory

### 4. Configure Environment Variables

1. Copy `.env.example` to `.env`
2. Update the following variables:
   ```
   GMAIL_SENDER_EMAIL=your-email@gmail.com
   GMAIL_RECIPIENT_EMAIL=recipient@gmail.com
   EMAIL_ENABLED=true
   ```

### 5. First Time Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Run your application
3. The first time you send an email, a browser will open asking you to authorize the application
4. Grant permissions
5. A `token.json` file will be created automatically

## Option 2: G Workspace/Business Account (Service Account) - For Business Use

### 1. Create Service Account

1. In Google Cloud Console, go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "Service Account"
3. Fill in service account details
4. Grant roles: "Service Account User"
5. Create and download the JSON key file

### 2. Enable Domain-Wide Delegation

1. Go to "APIs & Services" > "Credentials"
2. Find your service account and click "Edit"
3. Check "Enable G Suite Domain-wide Delegation"
4. Note the Client ID

### 3. Configure G Workspace Admin

1. Go to [G Workspace Admin Console](https://admin.google.com/)
2. Go to Security > API Controls > Domain-wide Delegation
3. Add your service account Client ID
4. Add scope: `https://www.googleapis.com/auth/gmail.send`

### 4. Configure Environment Variables

```
GMAIL_SENDER_EMAIL=your-business-email@yourcompany.com
GMAIL_RECIPIENT_EMAIL=recipient@yourcompany.com
GMAIL_SERVICE_ACCOUNT_FILE=service-account.json
EMAIL_ENABLED=true
```

## Dynamic Recipient Configuration

The email service supports multiple ways to determine the recipient email:

### 1. Payload-Based Recipients

Add a `Recipient Email` or `recipient_email` field to your webhook payload:

```json
{
  "event": "lark_form_submission",
  "fields": {
    "Recipient Email": "manager@company.com",
    "Customer Name": "John Doe",
    "Issue": "Urgent issue"
  }
}
```

### 2. Agent-Based Email Routing

Set up agent-specific email routing in your `.env` file:

```bash
# Agent email mapping
AGENT_EMAIL_JOHN_DOE=john.doe@company.com
AGENT_EMAIL_AGENT001=agent001@company.com
AGENT_EMAIL_SUPPORT_TEAM=support@company.com
```

Then your payload can specify the agent:

```json
{
  "event": "lark_form_submission",
  "fields": {
    "TMK Agent ID": "JOHN_DOE",
    "Customer Name": "Jane Smith"
  }
}
```

### 3. Default Recipient Fallback

If no specific recipient is found, it falls back to `GMAIL_RECIPIENT_EMAIL` from your environment.

### Priority Order

1. **Direct recipient field** in payload (`Recipient Email` or `recipient_email`)
2. **Agent-specific mapping** based on `TMK Agent ID`
3. **Default recipient** from `GMAIL_RECIPIENT_EMAIL`

## Testing the Setup

### 1. Test Email Function

Create a test script:

```python
import asyncio
from email_service import send_webhook_email

async def test_email():
    test_data = {
        "event": "test_submission",
        "record_id": "test123",
        "submitted_at": "2025-09-25 10:00:00",
        "fields": {
            "SN": "1",
            "TMK Agent ID": "TEST001",
            "Customer Name": "Test Customer",
            "Customer ID": "CUST001",
            "Issue": "Test Issue",
            "Date": "2025-09-25"
        }
    }
    
    success = await send_webhook_email(test_data)
    print(f"Email sent: {success}")

if __name__ == "__main__":
    asyncio.run(test_email())
```

### 2. Run the Test

```bash
python test_email.py
```

## Troubleshooting

### Common Issues

1. **"The file credentials.json was not found"**
   - Make sure you downloaded the credentials file from Google Cloud Console
   - Ensure it's named exactly `credentials.json` and in the project root

2. **"Access blocked: This app's request is invalid"**
   - Make sure you added your email as a test user in OAuth consent screen
   - Verify the OAuth scopes are correct

3. **"insufficient authentication scopes"**
   - Check that you're using the correct scope: `https://www.googleapis.com/auth/gmail.send`

4. **Service Account Issues**
   - Ensure domain-wide delegation is enabled
   - Verify the service account has the right permissions
   - Check that the sender email domain matches your G Workspace domain

### Security Notes

- Keep your `credentials.json` and `token.json` files secure
- Add them to `.gitignore` to prevent committing to version control
- For production, consider using Google Cloud Secret Manager
- Regularly rotate service account keys

### Rate Limits

- Gmail API has quotas (250 quota units per user per second)
- Each send email request uses 25 quota units
- Monitor usage in Google Cloud Console

## Email Features

The email service includes:

- ✅ Beautiful HTML formatting with CSS styling
- ✅ Responsive design that works on mobile and desktop
- ✅ Automatic fallback to plain text
- ✅ Customer information highlighting
- ✅ Timestamp tracking
- ✅ Issue priority highlighting
- ✅ Professional branding
- ✅ Error handling and logging

## Customization

You can customize the email template by editing `email_service.py`:

- Modify the HTML template in `create_html_email()`
- Change colors, fonts, and styling in the CSS section
- Add custom fields or conditional formatting
- Modify subject line format