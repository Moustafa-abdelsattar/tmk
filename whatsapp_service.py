"""
WhatsApp Business API service for sending template messages
"""

import os
import logging
import json
import requests
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class WhatsAppService:
    """WhatsApp Business API service for sending template messages"""
    
    def __init__(self):
        self.access_token = os.getenv('WHATSAPP_ACCESS_TOKEN')
        self.phone_number_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
        self.business_account_id = os.getenv('WHATSAPP_BUSINESS_ACCOUNT_ID')
        self.api_version = os.getenv('WHATSAPP_API_VERSION', 'v20.0')
        
        # Base URL for WhatsApp Business API
        self.base_url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}"
        
        if not self.access_token:
            raise ValueError("WHATSAPP_ACCESS_TOKEN must be set in environment variables")
        if not self.phone_number_id:
            raise ValueError("WHATSAPP_PHONE_NUMBER_ID must be set in environment variables")
    
    def format_phone_number(self, phone_number: str) -> str:
        """Format phone number for WhatsApp API (remove + and spaces)"""
        if not phone_number:
            return ""
        
        # Remove +, spaces, dashes, and other formatting
        formatted = phone_number.replace('+', '').replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        
        # Ensure it's all digits
        if not formatted.isdigit():
            logger.warning("Invalid phone number format: %s", phone_number)
            return ""
        
        logger.info("Formatted phone number: %s -> %s", phone_number, formatted)
        return formatted
    
    def send_template_message(self, to_number: str, template_name: str, template_params: Optional[Dict[str, Any]] = None, language_code: str = "en") -> bool:
        """
        Send a template message via WhatsApp Business API
        
        Args:
            to_number: Recipient phone number (will be formatted automatically)
            template_name: Name of the approved template
            template_params: Parameters for the template (if any)
            language_code: Language code for template (default: "en")
            
        Returns:
            bool: True if message sent successfully, False otherwise
        """
        
        # Format phone number
        formatted_number = self.format_phone_number(to_number)
        if not formatted_number:
            logger.error("Invalid phone number: %s", to_number)
            return False
        
        # Try multiple language codes if the first one fails
        language_codes_to_try = [language_code, "en", "en_US", "en_GB"]
        
        for lang_code in language_codes_to_try:
            # Prepare the message payload
            message_data = {
                "messaging_product": "whatsapp",
                "to": formatted_number,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {
                        "code": lang_code
                    }
                }
            }
            
            # Add template parameters if provided
            if template_params:
                message_data["template"]["components"] = []
                
                # Add header parameters if provided
                if "header" in template_params:
                    message_data["template"]["components"].append({
                        "type": "header",
                        "parameters": template_params["header"]
                    })
                
                # Add body parameters if provided
                if "body" in template_params:
                    message_data["template"]["components"].append({
                        "type": "body",
                        "parameters": template_params["body"]
                    })
            
            # Prepare headers for API request
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            url = f"{self.base_url}/messages"
            
            try:
                print(f"🔄 WhatsApp API: Making request to Meta Business API")
                print(f"   📍 URL: {url}")
                print(f"   📋 Template: {template_name}")
                print(f"   📱 Number: {formatted_number}")
                print(f"   🌐 Language: {lang_code}")
                
                logger.info("📱 Sending WhatsApp message to %s with template %s (lang: %s)", formatted_number, template_name, lang_code)
                
                response = requests.post(url, headers=headers, json=message_data, timeout=10)
                
                print(f"📊 WhatsApp API Response: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    message_id = result.get('messages', [{}])[0].get('id', 'Unknown')
                    print(f"✅ WhatsApp API Success: Message sent!")
                    print(f"   📝 Message ID: {message_id}")
                    print(f"   🌐 Language used: {lang_code}")
                    logger.info("✅ WhatsApp message sent successfully! Message ID: %s (lang: %s)", message_id, lang_code)
                    return True
                else:
                    print(f"❌ WhatsApp API Error: {response.status_code}")
                    print(f"   📄 Response: {response.text[:200]}{'...' if len(response.text) > 200 else ''}")
                    logger.warning("❌ WhatsApp API error with lang %s: %s - %s", lang_code, response.status_code, response.text)
                    # If it's a template language error, try next language code
                    if "does not exist" in response.text and len(language_codes_to_try) > 1:
                        print(f"🔄 Trying next language code...")
                        continue
                    else:
                        return False
                        
            except requests.exceptions.Timeout:
                print("❌ WhatsApp API Error: Request timeout")
                logger.error("❌ WhatsApp API request timeout")
                return False
            except requests.exceptions.RequestException as e:
                print(f"❌ WhatsApp API Error: Request exception - {e}")
                logger.error("❌ WhatsApp API request failed: %s", e)
                return False
            except Exception as e:
                print(f"❌ WhatsApp API Error: Unexpected error - {e}")
                logger.error("❌ Unexpected error sending WhatsApp message: %s", e)
                return False
        
        logger.error("❌ Failed to send WhatsApp message with any language code tried: %s", language_codes_to_try)
        return False
    
    def send_tmktocc_template(self, webhook_data: Dict[str, Any]) -> bool:
        """
        Send the tmktocc template message to CC agent - TEMPLATE ONLY (no parameters)
        This bypasses the 24-hour rule as templates can be sent anytime.
        
        Args:
            webhook_data: The webhook payload data
            
        Returns:
            bool: True if message sent successfully, False otherwise
        """
        fields = webhook_data.get('fields', {})
        
        # Get CC Whatsapp Number from webhook data
        cc_whatsapp = fields.get('CC Whatsapp Number', '').strip()
        
        if not cc_whatsapp:
            print("❌ WhatsApp Error: No CC Whatsapp Number provided in webhook data")
            logger.warning("❌ No CC Whatsapp Number provided in webhook data")
            return False
        
        print(f"📱 WhatsApp Service: Preparing to send 'tmktocc' template")
        print(f"   📞 Target number: {cc_whatsapp}")
        print(f"   📋 Template: tmktocc (no parameters)")
        print(f"   🌐 Language: en")
        logger.info("📱 Sending 'tmktocc' template to CC agent at %s", cc_whatsapp)
        
        # Use template without parameters (this always works)
        result = self.send_template_message(
            to_number=cc_whatsapp,
            template_name="tmktocc",
            template_params=None,  # No parameters - just the template
            language_code="en"
        )
        
        if result:
            print(f"✅ WhatsApp Success: tmktocc template sent to {cc_whatsapp}")
            logger.info("✅ tmktocc template sent successfully to %s", cc_whatsapp)
        else:
            print(f"❌ WhatsApp Failed: Could not send tmktocc template to {cc_whatsapp}")
            logger.error("❌ Failed to send tmktocc template to %s", cc_whatsapp)
        
        return result


# Singleton instance - initialized lazily
_whatsapp_service: Optional[WhatsAppService] = None

def get_whatsapp_service() -> WhatsAppService:
    """Get or create the WhatsApp service singleton"""
    global _whatsapp_service
    if _whatsapp_service is None:
        _whatsapp_service = WhatsAppService()
    return _whatsapp_service


async def send_whatsapp_message(webhook_data: Dict[str, Any]) -> bool:
    """
    Async wrapper to send WhatsApp template message
    
    Args:
        webhook_data: The webhook payload data
        
    Returns:
        bool: True if message sent successfully, False otherwise
    """
    try:
        whatsapp_service = get_whatsapp_service()
        return whatsapp_service.send_tmktocc_template(webhook_data)
    except Exception as e:
        logger.error("Error in send_whatsapp_message: %s", e)
        return False