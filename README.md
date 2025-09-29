# TMK Webhook System

A production-ready webhook system for processing Lark form submissions with multi-channel notifications.

## Features

- 📝 **CSV Logging** - Automatic data logging to CSV files
- 📊 **Google Sheets Integration** - Real-time data logging with OAuth authentication
- 📧 **Email Notifications** - Automatic email alerts to TMK agents
- 📱 **WhatsApp Business Integration** - Template-based notifications via WhatsApp Business API

## Production Files

### Core Application
- `app.py` - Main FastAPI webhook server
- `email_service.py` - Gmail API integration for email notifications
- `sheets_service.py` - Google Sheets API integration
- `whatsapp_service.py` - WhatsApp Business API integration

### Configuration
- `.env` - Environment variables (not in git)
- `.env.example` - Environment template
- `requirements.txt` - Python dependencies

### Setup Documentation
- `GMAIL_SETUP.md` - Gmail API configuration guide
- `SHEETS_SETUP.md` - Google Sheets API configuration guide

### Data Files
- `submissions.csv` - CSV data storage
- `webhook.log` - Application logs

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

3. **Run the server:**
   ```bash
   python app.py
   ```

The server will run on `http://0.0.0.0:5000` with endpoints:
- `POST /webhook/lark` - Lark form submissions
- `GET /webhook` - WhatsApp webhook verification
- `POST /webhook` - WhatsApp delivery status updates

## WhatsApp Integration

The system uses **template-only messaging** which bypasses WhatsApp's 24-hour rule:
- ✅ Templates can be sent anytime
- ✅ Professional, consistent messaging  
- ✅ Higher delivery rates
- ✅ Meta-approved content

## Environment Variables

Key variables required in `.env`:
- `WEBHOOK_SECRET` - Lark webhook authentication
- `WHATSAPP_ACCESS_TOKEN` - WhatsApp Business API token
- `WHATSAPP_PHONE_NUMBER_ID` - WhatsApp Business phone number
- `WHATSAPP_VERIFY_TOKEN` - Webhook verification token
- `GMAIL_SENDER_EMAIL` - Gmail sender address
- `GOOGLE_SHEET_ID` - Target Google Sheet ID

## Production Deployment

For production deployment:
1. Use a proper WSGI server (gunicorn, uvicorn)
2. Set up SSL/TLS certificates
3. Configure firewall rules
4. Set up log rotation
5. Monitor webhook endpoints

## Support

The system provides comprehensive logging and error handling. Check `webhook.log` for troubleshooting.