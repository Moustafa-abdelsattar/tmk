"""
Fixed Email service for sending formatted webhook notifications via Gmail API
"""

import base64
import os
import json
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
import logging

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Load environment variables here
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

class GmailService:
    """Gmail API service for sending formatted emails"""
    
    # Gmail API scope for sending emails
    SCOPES = ['https://www.googleapis.com/auth/gmail.send']
    
    def __init__(self):
        self.service = None
        self.sender_email = os.getenv('GMAIL_SENDER_EMAIL')
        self.form_owner_email = os.getenv('FORM_OWNER_EMAIL')
        self.credentials_file = os.getenv('GMAIL_CREDENTIALS_FILE', 'credentials.json')
        self.token_file = os.getenv('GMAIL_TOKEN_FILE', 'token.json')
        
        if not self.sender_email:
            raise ValueError("GMAIL_SENDER_EMAIL must be set in environment variables")
        
        # Form owner email is optional - only used for general webhook notifications
        if not self.form_owner_email:
            logger.warning("FORM_OWNER_EMAIL not set - form owner notifications disabled")
    
    def authenticate(self) -> bool:
        """Authenticate with Gmail API using OAuth2 or Service Account"""
        creds = None
        
        # Check if we have a service account key
        service_account_file = os.getenv('GMAIL_SERVICE_ACCOUNT_FILE')
        if service_account_file and os.path.exists(service_account_file):
            logger.info("Using service account authentication")
            try:
                creds = service_account.Credentials.from_service_account_file(
                    service_account_file, scopes=self.SCOPES
                )
                # For service accounts, we need to delegate to the sender email
                creds = creds.with_subject(self.sender_email)
            except Exception as e:
                logger.error("Service account authentication failed: %s", e)
                return False
        
        else:
            # Use OAuth2 flow
            logger.info("Using OAuth2 authentication")
            
            # Load existing token
            if os.path.exists(self.token_file):
                creds = Credentials.from_authorized_user_file(self.token_file, self.SCOPES)
            
            # If there are no (valid) credentials available, let the user log in
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                    except Exception as e:
                        logger.error("Token refresh failed: %s", e)
                        creds = None
                
                if not creds:
                    if not os.path.exists(self.credentials_file):
                        logger.error("Credentials file not found: %s", self.credentials_file)
                        return False
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, self.SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                
                # Save the credentials for the next run
                with open(self.token_file, 'w') as token:
                    token.write(creds.to_json())
        
        try:
            self.service = build('gmail', 'v1', credentials=creds)
            logger.info("Gmail service authenticated successfully")
            return True
        except Exception as e:
            logger.error("Failed to build Gmail service: %s", e)
            return False
    
    def create_html_email(self, webhook_data: Dict[str, Any]) -> str:
        """Create a beautifully formatted HTML email from webhook data"""
        
        # Extract data
        event = webhook_data.get('event', 'Unknown Event')
        record_id = webhook_data.get('record_id', 'N/A')
        submitted_at = webhook_data.get('submitted_at', 'N/A')
        fields = webhook_data.get('fields', {})
        
        # Format submission time
        try:
            if submitted_at != 'N/A' and submitted_at:
                # Try to parse and format the date
                formatted_time = submitted_at
        except:
            formatted_time = submitted_at
        
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    background-color: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 20px;
                    border-radius: 8px;
                    margin-bottom: 20px;
                    text-align: center;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 24px;
                }}
                .meta-info {{
                    background-color: #f8f9fa;
                    padding: 15px;
                    border-radius: 5px;
                    margin-bottom: 20px;
                    border-left: 4px solid #667eea;
                }}
                .meta-info p {{
                    margin: 5px 0;
                    font-size: 14px;
                }}
                .fields-container {{
                    margin-top: 20px;
                }}
                .field {{
                    background-color: #ffffff;
                    border: 1px solid #e9ecef;
                    border-radius: 5px;
                    padding: 12px 15px;
                    margin-bottom: 10px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}
                .field:nth-child(even) {{
                    background-color: #f8f9fa;
                }}
                .field-label {{
                    font-weight: 600;
                    color: #495057;
                    min-width: 150px;
                }}
                .field-value {{
                    color: #212529;
                    font-weight: 400;
                    flex: 1;
                    text-align: right;
                }}
                .priority {{
                    color: #dc3545;
                    font-weight: bold;
                }}
                .footer {{
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 2px solid #e9ecef;
                    text-align: center;
                    color: #6c757d;
                    font-size: 12px;
                }}
                .timestamp {{
                    color: #28a745;
                    font-weight: bold;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚨 New TMK Form Submission</h1>
                </div>
                
                <div class="meta-info">
                    <p><strong>Event:</strong> {event}</p>
                    <p><strong>Record ID:</strong> {record_id}</p>
                    <p><strong>Submitted At:</strong> <span class="timestamp">{formatted_time}</span></p>
                    <p><strong>Received At:</strong> <span class="timestamp">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span></p>
                </div>
                
                <div class="fields-container">
                    <h2>📋 Submission Details</h2>
        """
        
        # Add fields dynamically
        for field_name, field_value in fields.items():
            # Highlight important fields
            value_class = "priority" if field_name.lower() in ['issue', 'priority', 'urgency'] else ""
            
            html_template += f"""
                    <div class="field">
                        <span class="field-label">{field_name}:</span>
                        <span class="field-value {value_class}">{field_value}</span>
                    </div>
            """
        
        html_template += """
                </div>
                
                <div class="footer">
                    <p>This email was automatically generated by the TMK Webhook System</p>
                    <p>Generated on """ + datetime.now().strftime('%Y-%m-%d at %H:%M:%S') + """</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_template
    
    def create_cc_agent_email(self, webhook_data: Dict[str, Any]) -> str:
        """
        Create clean HTML email content for CC agents with all field details
        """
        fields = webhook_data.get('fields', {})
        record_id = webhook_data.get('record_id', 'N/A')
        submitted_at = webhook_data.get('submitted_at', 'N/A')
        
        # Extract all field information
        sn = fields.get('SN', 'N/A')
        tmk_crm_account = fields.get('TMK - CRM Account Name', 'N/A')
        cc_email = fields.get('CC Email', 'N/A')
        cc_crm_account = fields.get('CC - CRM Account Name', 'N/A')
        cc_whatsapp = fields.get('CC Whatsapp Number', 'N/A')
        submitted_on = fields.get('Submitted on', 'N/A')
        respondents = fields.get('Respondents', 'N/A')
        customer_name = fields.get('Customer Name', 'N/A')
        customer_id = fields.get('Customer ID', 'N/A')
        customer_contact = fields.get('Customer Contact', 'N/A')
        issue = fields.get('Issue', 'N/A')

        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>TMK Case Assignment - {customer_name}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    background-color: #f4f4f4;
                    margin: 0;
                    padding: 20px;
                }}
                .container {{
                    max-width: 800px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    overflow: hidden;
                }}
                .header {{
                    background: #2c3e50;
                    color: white;
                    padding: 20px;
                    text-align: center;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 24px;
                }}
                .content {{
                    padding: 30px;
                }}
                .field-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }}
                .field-table th,
                .field-table td {{
                    border: 1px solid #ddd;
                    padding: 12px;
                    text-align: left;
                }}
                .field-table th {{
                    background-color: #f8f9fa;
                    font-weight: bold;
                    color: #495057;
                }}
                .field-table tr:nth-child(even) {{
                    background-color: #f8f9fa;
                }}
                .issue-section {{
                    background: #fff3cd;
                    border: 2px solid #ffc107;
                    border-radius: 8px;
                    padding: 25px;
                    margin: 25px 0;
                }}
                .issue-section h3 {{
                    margin: 0 0 15px 0;
                    color: #856404;
                    font-size: 20px;
                    font-weight: bold;
                }}
                .issue-section p {{
                    font-size: 18px;
                    font-weight: 500;
                    line-height: 1.6;
                    color: #333;
                    margin: 0;
                }}
                .footer {{
                    background: #6c757d;
                    color: white;
                    padding: 15px;
                    text-align: center;
                    font-size: 14px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>TMK Case Assignment</h1>
                    <p>Customer Follow-Up Required</p>
                </div>
                
                <div class="content">
                    <p><strong>Hello CC Agent,</strong></p>
                    <p>You have been assigned to follow up with a customer. Please review all the details below:</p>
                    
                    <table class="field-table">
                        <tr>
                            <th>Field</th>
                            <th>Value</th>
                        </tr>
                        <tr>
                            <td><strong>Customer Name</strong></td>
                            <td>{customer_name}</td>
                        </tr>
                        <tr>
                            <td><strong>Customer ID</strong></td>
                            <td>{customer_id}</td>
                        </tr>
                        <tr>
                            <td><strong>Customer Contact</strong></td>
                            <td>{customer_contact}</td>
                        </tr>
                    </table>
                    
                    <div class="issue-section">
                        <h3>Issue Details</h3>
                        <p>{issue}</p>
                    </div>
                </div>
                
                <div class="footer">
                    <p><strong>TMK Customer Management System</strong></p>
                    <p>Generated on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_template
    
    def get_recipient_email(self, webhook_data: Dict[str, Any]) -> Optional[str]:
        """
        Determine recipient email from webhook payload or use default
        
        Priority:
        1. Direct recipient field in payload
        2. Agent-specific email mapping
        3. Default recipient from environment
        """
        fields = webhook_data.get('fields', {})
        
        # Option 1: Direct recipient email field
        recipient = fields.get('Recipient Email') or fields.get('recipient_email')
        if recipient and '@' in recipient:
            logger.info("Using recipient email from payload: %s", recipient)
            return recipient
        
        # Option 2: Map TMK CRM Account to specific emails
        agent_id = fields.get('TMK - CRM Account Name') or fields.get('tmk_crm_account_name')
        if agent_id:
            # Agent email mapping from environment variables
            agent_email = os.getenv(f'AGENT_EMAIL_{agent_id.upper().replace(" ", "_")}')
            if agent_email:
                logger.info("Using agent-specific email for %s: %s", agent_id, agent_email)
                return agent_email
        
        # Option 3: Use form owner email
        if self.form_owner_email:
            logger.info("Using form owner email: %s", self.form_owner_email)
            return self.form_owner_email
        
        logger.error("No recipient email found in payload or environment variables")
        return None

    def send_cc_agent_notification(self, webhook_data: Dict[str, Any]) -> bool:
        """Send a follow-up notification email directly to the CC Email address from webhook payload"""
        
        print("📧 Email Service: Starting CC agent notification process")
        
        if not self.service:
            print("🔐 Email Service: Gmail service not authenticated, attempting authentication...")
            if not self.authenticate():
                print("❌ Email Service: Gmail authentication FAILED")
                logger.error("Failed to authenticate with Gmail")
                return False
            else:
                print("✅ Email Service: Gmail authentication successful")
        
        # Get CC Email from webhook payload
        fields = webhook_data.get('fields', {})
        cc_email = fields.get('CC Email', '').strip()
        
        print(f"🔍 Email Service: Checking CC Email field: '{cc_email}'")
        
        if not cc_email or '@' not in cc_email:
            print(f"❌ Email Service: Invalid CC Email address: '{cc_email}'")
            logger.warning("No valid CC Email found in webhook payload: %s", cc_email)
            return False
        
        print(f"📧 Email Service: Preparing to send email to: {cc_email}")
        logger.info("🎯 Sending CC Agent notification to: %s", cc_email)
        
        try:
            print("🔄 Email Service: Creating email content...")
            # Create specialized CC agent email content
            html_content = self.create_cc_agent_email(webhook_data)
            
            # Create subject line with customer info
            customer_name = fields.get('Customer Name', 'Unknown Customer')
            issue_preview = fields.get('Issue', 'New Issue')[:50] + ('...' if len(fields.get('Issue', '')) > 50 else '')
            subject = f"Customer Follow-Up Required: {customer_name} - {issue_preview}"
            
            print(f"📝 Email Service: Subject: {subject}")
            print(f"👤 Email Service: Customer: {customer_name}")
            
            # Create plain text version (fallback)
            plain_text = f"""
Customer Follow-Up Required

Hello CC Agent,

You have been assigned to follow up with the following customer:

Customer Details:
- Name: {customer_name}
- ID: {fields.get('Customer ID', 'N/A')}
- Contact: {fields.get('Customer Contact', 'N/A')}
- Issue: {fields.get('Issue', 'No issue specified')}

Original TMK CRM Account: {fields.get('TMK - CRM Account Name', 'N/A')}
Assigned CC CRM Account: {fields.get('CC - CRM Account Name', 'N/A')}
CC Whatsapp Number: {fields.get('CC Whatsapp Number', 'N/A')}
Record ID: {webhook_data.get('record_id', 'N/A')}
Submission Date: {webhook_data.get('submitted_at', 'N/A')}

This email was automatically generated by the TMK Customer Management System.
            """
            
            # Create message
            print("📧 Email Service: Creating MIME message...")
            message = MIMEMultipart('alternative')
            message['To'] = cc_email
            message['From'] = self.sender_email
            message['Subject'] = subject
            message['Message-ID'] = f"<tmk-cc-{webhook_data.get('record_id', 'unknown')}-{datetime.now().strftime('%Y%m%d%H%M%S')}@tmk-system>"
            
            print(f"📧 Email Service: Message details:")
            print(f"   📧 To: {message['To']}")
            print(f"   📧 From: {message['From']}")
            print(f"   📝 Subject: {subject}")
            
            logger.info("📧 CC EMAIL DEBUG:")
            logger.info("   To: %s", message['To'])
            logger.info("   From: %s", message['From'])
            logger.info("   Subject: %s", subject)
            
            # Attach both plain text and HTML versions
            print("📧 Email Service: Attaching content (HTML and plain text)...")
            text_part = MIMEText(plain_text, 'plain', 'utf-8')
            html_part = MIMEText(html_content, 'html', 'utf-8')
            message.attach(text_part)
            message.attach(html_part)
            
            # Send the email
            print("🔄 Email Service: Sending via Gmail API...")
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            send_message = {'raw': raw_message}
            
            result = self.service.users().messages().send(userId='me', body=send_message).execute()
            
            print(f"✅ Email Service: SUCCESS! Email sent to {cc_email}")
            print(f"   📝 Gmail Message ID: {result.get('id')}")
            
            logger.info("✅ CC agent notification sent successfully to %s, Message ID: %s", cc_email, result.get('id'))
            return True
            
        except HttpError as e:
            print(f"❌ Email Service: Gmail API error - {e}")
            logger.error("Gmail API error sending CC notification: %s", e)
            return False
        except Exception as e:
            print(f"❌ Email Service: Unexpected error - {e}")
            logger.error("Unexpected error sending CC notification: %s", e)
            return False

    def send_webhook_notification(self, webhook_data: Dict[str, Any], recipient_email: Optional[str] = None) -> bool:
        """Send a formatted email notification for webhook data"""
        
        if not self.service:
            if not self.authenticate():
                logger.error("Failed to authenticate with Gmail")
                return False
        
        # Determine recipient email
        if not recipient_email:
            recipient_email = self.get_recipient_email(webhook_data)
        
        logger.info("🎯 RECIPIENT DEBUG:")
        logger.info("   Parameter recipient_email: %s", recipient_email)
        logger.info("   Sender email: %s", self.sender_email)
        logger.info("   Default recipient: %s", self.default_recipient_email)
        
        if not recipient_email:
            logger.error("No valid recipient email available")
            return False
        
        try:
            # Create the email content
            html_content = self.create_html_email(webhook_data)
            
            # Create subject line FIRST
            fields = webhook_data.get('fields', {})
            customer_name = fields.get('Customer Name', 'Unknown Customer')
            issue = fields.get('Issue', 'New Issue')
            subject = f"🚨 TMK Alert: {customer_name} - {issue}"
            
            # Create plain text version (fallback)
            plain_text = f"""
New TMK Form Submission

Event: {webhook_data.get('event', 'Unknown')}
Record ID: {webhook_data.get('record_id', 'N/A')}
Submitted At: {webhook_data.get('submitted_at', 'N/A')}

Details:
"""
            for field_name, field_value in fields.items():
                plain_text += f"{field_name}: {field_value}\n"
            
            plain_text += f"\nReceived at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # Create message using a cleaner approach
            message = MIMEMultipart('alternative')
            
            # CRITICAL FIX: Set headers in the right order and format
            message['To'] = recipient_email
            message['From'] = self.sender_email
            message['Subject'] = subject
            
            # Add message ID for tracking
            message['Message-ID'] = f"<tmk-webhook-{webhook_data.get('record_id', 'unknown')}-{datetime.now().strftime('%Y%m%d%H%M%S')}@tmk-system>"
            
            logger.info("📧 EMAIL MESSAGE DEBUG:")
            logger.info("   To: %s", message['To'])
            logger.info("   From: %s", message['From'])
            logger.info("   Subject: %s", subject)
            
            # Attach both plain text and HTML versions
            text_part = MIMEText(plain_text, 'plain', 'utf-8')
            html_part = MIMEText(html_content, 'html', 'utf-8')
            
            message.attach(text_part)
            message.attach(html_part)
            
            # CRITICAL FIX: Use proper encoding
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            send_message = {'raw': raw_message}
            
            # Send the email
            result = self.service.users().messages().send(
                userId='me', 
                body=send_message
            ).execute()
            
            logger.info("✅ Email sent successfully. Message ID: %s", result.get('id'))
            return True
            
        except HttpError as error:
            logger.error("Gmail API error: %s", error)
            return False
        except Exception as error:
            logger.error("Failed to send email: %s", error)
            import traceback
            traceback.print_exc()
            return False


# Singleton instance - initialized lazily
_gmail_service: Optional[GmailService] = None

def get_gmail_service() -> GmailService:
    """Get or create the Gmail service singleton"""
    global _gmail_service
    if _gmail_service is None:
        _gmail_service = GmailService()
    return _gmail_service


async def send_webhook_email(webhook_data: Dict[str, Any], recipient_email: Optional[str] = None) -> bool:
    """
    Async wrapper to send webhook email notification
    
    Args:
        webhook_data: The webhook payload data
        recipient_email: Optional specific recipient email (overrides automatic detection)
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        gmail_service = get_gmail_service()
        return gmail_service.send_webhook_notification(webhook_data, recipient_email)
    except Exception as e:
        logger.error("Error in send_webhook_email: %s", e)
        return False


async def send_cc_agent_email(webhook_data: Dict[str, Any]) -> bool:
    """
    Async wrapper to send CC agent follow-up notification
    
    Args:
        webhook_data: The webhook payload data (must contain CC Email field)
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        gmail_service = get_gmail_service()
        return gmail_service.send_cc_agent_notification(webhook_data)
    except Exception as e:
        logger.error("Error in send_cc_agent_email: %s", e)
        return False