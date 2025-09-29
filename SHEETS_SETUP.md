# Google Sheets Integration Setup Guide

## Overview
Your TMK webhook system now logs data to both CSV files and Google Sheets automatically. This provides real-time visibility of webhook data in your Google Sheet.

## Google Sheet Details
- **Sheet URL**: https://docs.google.com/spreadsheets/d/1HBV0ixj-yKGEeChN_VWHhj3DFLe530HVdfzmBfcZue8/edit
- **Sheet ID**: `1HBV0ixj-yKGEeChN_VWHhj3DFLe530HVdfzmBfcZue8`
- **Sheet Name**: `TMK Webhooks` (configurable via `GOOGLE_SHEET_NAME` in .env)

## Authentication Setup

Since you already have Gmail API working, you can use the same `credentials.json` file for Google Sheets. The system will create a separate token file (`sheets_token.json`) for Sheets API access.

### Option 1: Use Existing Gmail Credentials (Recommended)
1. Your existing `credentials.json` file should work
2. The system will create `sheets_token.json` automatically
3. You'll need to grant Sheets API permissions when first running

### Option 2: Enable Google Sheets API in Google Cloud Console
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your existing project (or create new one)
3. Enable **Google Sheets API**
4. Your existing credentials should work for both Gmail and Sheets

## Configuration (.env file)

The following settings have been added to your `.env` file:

```env
# Google Sheets Configuration
GOOGLE_SHEET_ID=1HBV0ixj-yKGEeChN_VWHhj3DFLe530HVdfzmBfcZue8
GOOGLE_SHEET_NAME=TMK Webhooks
GOOGLE_SHEETS_ENABLED=true

# Google Sheets Authentication (uses same credentials as Gmail)
GOOGLE_SHEETS_CREDENTIALS_FILE=credentials.json
GOOGLE_SHEETS_TOKEN_FILE=sheets_token.json
```

## Data Structure

The system will automatically create headers in your Google Sheet with the following columns:

| Column | Description |
|--------|-------------|
| Received At | Timestamp when webhook was processed |
| Record ID | Unique record identifier from webhook |
| Submitted At | Original submission timestamp |
| SN | Serial number |
| TMK Agent ID | Agent identifier |
| CC Email | CC email address |
| CC Agent ID | CC agent identifier |
| Submitted on | Submission date |
| Respondents | User who submitted |
| Customer Name | Customer name |
| Customer ID | Customer identifier |
| Customer Contact | Customer contact information |
| Issue | Issue description |
| Date | Date field |
| Raw JSON | Complete webhook payload |

## Testing

Run the test script to verify everything works:

```bash
python test_sheets_integration.py
```

## How It Works

1. **Webhook Received** → TMK form submission arrives
2. **CSV Logging** → Data saved to local `submissions.csv` 
3. **Sheets Logging** → Data automatically logged to Google Sheet
4. **Email Notification** → CC agent receives email (if CC Email provided)

## Troubleshooting

### Authentication Issues
- Ensure `credentials.json` exists in project directory
- Make sure Google Sheets API is enabled in Google Cloud Console
- Check that your Google account has access to the sheet

### Permission Issues
- Verify the Google Sheet is accessible to your Google account
- Check that the sheet isn't protected or restricted

### API Errors
- Monitor the webhook logs in `webhook.log`
- Look for Google Sheets API error messages
- Ensure you haven't exceeded API quotas

## Benefits

✅ **Real-time Visibility**: See webhook data immediately in Google Sheets
✅ **Easy Sharing**: Share the Google Sheet with team members
✅ **Data Analysis**: Use Google Sheets features for filtering, charts, etc.
✅ **Backup**: Multiple storage locations (CSV + Google Sheets)
✅ **Collaboration**: Team can view and analyze data together

## Next Steps

1. Run the test script to verify setup
2. Submit a test webhook to see data appear in the sheet
3. Share the Google Sheet with relevant team members
4. Consider adding additional analysis or visualization features