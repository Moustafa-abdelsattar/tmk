"""
Google Sheets service for logging webhook data
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

class GoogleSheetsService:
    """Google Sheets API service for logging webhook data"""
    
    # Google Sheets API scope for reading and writing
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    
    def __init__(self):
        self.service = None
        self.sheet_id = os.getenv('GOOGLE_SHEET_ID')
        self.sheet_name = os.getenv('GOOGLE_SHEET_NAME', 'TMK Webhooks')
        self.credentials_file = os.getenv('GOOGLE_SHEETS_CREDENTIALS_FILE', 'credentials.json')
        self.token_file = os.getenv('GOOGLE_SHEETS_TOKEN_FILE', 'sheets_token.json')
        
        if not self.sheet_id:
            raise ValueError("GOOGLE_SHEET_ID must be set in environment variables")
    
    def authenticate(self) -> bool:
        """Authenticate with Google Sheets API using OAuth2 or Service Account"""
        creds = None
        
        # Check if we have a service account key
        service_account_file = os.getenv('GOOGLE_SHEETS_SERVICE_ACCOUNT_FILE')
        if service_account_file and os.path.exists(service_account_file):
            logger.info("Using service account authentication for Google Sheets")
            try:
                creds = service_account.Credentials.from_service_account_file(
                    service_account_file, scopes=self.SCOPES
                )
            except Exception as e:
                logger.error("Service account authentication failed: %s", e)
                return False
        
        else:
            # Use OAuth2 flow
            logger.info("Using OAuth2 authentication for Google Sheets")
            
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
            self.service = build('sheets', 'v4', credentials=creds)
            logger.info("Google Sheets service authenticated successfully")
            return True
        except Exception as e:
            logger.error("Failed to build Google Sheets service: %s", e)
            return False
    
    def ensure_headers(self) -> bool:
        """Ensure the sheet has proper headers"""
        if not self.service:
            if not self.authenticate():
                return False
        
        try:
            # Define the headers matching your CSV structure
            headers = [
                'Received At',
                'Record ID', 
                'Submitted At',
                'SN',
                'TMK - CRM Account Name',
                'CC Email',
                'CC - CRM Account Name',
                'CC Whatsapp Number',
                'Submitted on',
                'Respondents',
                'Customer Name',
                'Customer ID',
                'Customer Contact',
                'Issue',
                'Raw JSON'
            ]
            
            # Check if headers exist
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.sheet_id,
                range=f'{self.sheet_name}!A1:O1'
            ).execute()
            
            values = result.get('values', [])
            
            if not values or len(values[0]) < len(headers):
                # Add or update headers
                logger.info("Adding/updating headers in Google Sheet")
                
                self.service.spreadsheets().values().update(
                    spreadsheetId=self.sheet_id,
                    range=f'{self.sheet_name}!A1:O1',
                    valueInputOption='RAW',
                    body={'values': [headers]}
                ).execute()
                
                logger.info("Headers added successfully to Google Sheet")
            
            return True
            
        except HttpError as e:
            logger.error("Error ensuring headers in Google Sheet: %s", e)
            return False
        except Exception as e:
            logger.error("Unexpected error ensuring headers: %s", e)
            return False
    
    def log_webhook_data(self, webhook_data: Dict[str, Any]) -> bool:
        """Log webhook data to Google Sheet"""
        
        if not self.service:
            if not self.authenticate():
                logger.error("Failed to authenticate with Google Sheets")
                return False
        
        # Ensure headers exist
        if not self.ensure_headers():
            logger.error("Failed to ensure headers in Google Sheet")
            return False
        
        try:
            fields = webhook_data.get('fields', {})
            
            # Prepare row data matching the CSV structure
            row_data = [
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # Received At
                webhook_data.get('record_id', ''),              # Record ID
                webhook_data.get('submitted_at', ''),           # Submitted At
                fields.get('SN', ''),                           # SN
                fields.get('TMK - CRM Account Name', ''),       # TMK - CRM Account Name
                fields.get('CC Email', ''),                     # CC Email
                fields.get('CC - CRM Account Name', ''),        # CC - CRM Account Name
                fields.get('CC Whatsapp Number', ''),           # CC Whatsapp Number
                fields.get('Submitted on', ''),                 # Submitted on
                fields.get('Respondents', ''),                  # Respondents
                fields.get('Customer Name', ''),                # Customer Name
                fields.get('Customer ID', ''),                  # Customer ID
                fields.get('Customer Contact', ''),             # Customer Contact
                fields.get('Issue', ''),                        # Issue
                str(webhook_data)                               # Raw JSON
            ]
            
            # Append the row to the sheet
            result = self.service.spreadsheets().values().append(
                spreadsheetId=self.sheet_id,
                range=f'{self.sheet_name}!A:O',
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body={'values': [row_data]}
            ).execute()
            
            logger.info("✅ Successfully logged webhook data to Google Sheet")
            logger.info("Updated range: %s", result.get('updates', {}).get('updatedRange', 'Unknown'))
            return True
            
        except HttpError as e:
            logger.error("❌ Google Sheets API error: %s", e)
            return False
        except Exception as e:
            logger.error("❌ Unexpected error logging to Google Sheet: %s", e)
            return False


# Singleton instance - initialized lazily
_sheets_service: Optional[GoogleSheetsService] = None

def get_sheets_service() -> GoogleSheetsService:
    """Get or create the Google Sheets service singleton"""
    global _sheets_service
    if _sheets_service is None:
        _sheets_service = GoogleSheetsService()
    return _sheets_service


async def log_to_google_sheet(webhook_data: Dict[str, Any]) -> bool:
    """
    Async wrapper to log webhook data to Google Sheet
    
    Args:
        webhook_data: The webhook payload data
        
    Returns:
        bool: True if logged successfully, False otherwise
    """
    try:
        sheets_service = get_sheets_service()
        return sheets_service.log_webhook_data(webhook_data)
    except Exception as e:
        logger.error("Error in log_to_google_sheet: %s", e)
        return False