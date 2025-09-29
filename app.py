import csv
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# Import our services
from email_service import send_webhook_email, send_cc_agent_email
from sheets_service import log_to_google_sheet
from whatsapp_service import send_whatsapp_message

# --- env & setup ---
load_dotenv()

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
LOG_FILE = os.getenv("LOG_FILE", "webhook.log")
CSV_FILE = os.getenv("CSV_FILE", "submissions.csv")
EMAIL_ENABLED = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
SHEETS_ENABLED = os.getenv("GOOGLE_SHEETS_ENABLED", "false").lower() == "true"
WHATSAPP_ENABLED = os.getenv("WHATSAPP_ENABLED", "false").lower() == "true"

print(f"WEBHOOK_SECRET loaded: {'Yes' if WEBHOOK_SECRET else 'No'}")
print(f"EMAIL_ENABLED: {EMAIL_ENABLED}")
print(f"SHEETS_ENABLED: {SHEETS_ENABLED}")
print(f"WHATSAPP_ENABLED: {WHATSAPP_ENABLED}")
if not WEBHOOK_SECRET:
    raise RuntimeError("WEBHOOK_SECRET is not set. Put it in .env")

# logging
Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    filename=LOG_FILE,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("lark-webhook")

app = FastAPI(title="Lark → Python Webhook", version="1.0.0")

# --- WhatsApp Webhook Verification ---
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "51talk")

@app.get("/webhook")
async def verify_webhook(request: Request):
    """
    WhatsApp webhook verification endpoint
    Meta sends GET request to verify webhook URL with query parameters
    """
    # Get query parameters
    hub_mode = request.query_params.get("hub.mode")
    hub_verify_token = request.query_params.get("hub.verify_token") 
    hub_challenge = request.query_params.get("hub.challenge")
    
    logger.info(f"Webhook verification attempt - Mode: {hub_mode}, Token: {hub_verify_token}, Challenge: {hub_challenge}")
    
    # Verify the webhook
    if hub_mode == "subscribe" and hub_verify_token == WHATSAPP_VERIFY_TOKEN:
        logger.info("✅ WhatsApp webhook verified successfully!")
        # Must return the challenge as plain text (not JSON)
        return Response(content=hub_challenge, media_type="text/plain")
    else:
        logger.warning(f"❌ WhatsApp webhook verification failed. Expected token: {WHATSAPP_VERIFY_TOKEN}")
        raise HTTPException(status_code=403, detail="Verification failed")

@app.post("/webhook")
async def whatsapp_webhook(request: Request):
    """
    WhatsApp webhook for receiving message status updates
    This will help us track message delivery
    """
    try:
        payload = await request.json()
        logger.info(f"📱 WhatsApp webhook received: {json.dumps(payload, indent=2)}")
        
        # Process webhook data (message status, delivery confirmations, etc.)
        entry = payload.get("entry", [])
        for e in entry:
            changes = e.get("changes", [])
            for change in changes:
                value = change.get("value", {})
                
                # Handle message status updates
                statuses = value.get("statuses", [])
                for status in statuses:
                    message_id = status.get("id")
                    status_type = status.get("status")  # sent, delivered, read, failed
                    timestamp = status.get("timestamp")
                    
                    logger.info(f"📱 Message {message_id} status: {status_type} at {timestamp}")
                    
                    if status_type == "failed":
                        errors = status.get("errors", [])
                        for error in errors:
                            logger.error(f"❌ WhatsApp message failed: {error}")
                    elif status_type == "delivered":
                        logger.info(f"✅ WhatsApp message {message_id} delivered successfully!")
                    elif status_type == "read":
                        logger.info(f"📖 WhatsApp message {message_id} was read by recipient")
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"❌ Error processing WhatsApp webhook: {e}")
        return {"status": "error", "message": str(e)}

# ensure CSV has a header
CSV_COLUMNS = [
    "received_at",
    "record_id",
    "submitted_at",
    "SN",
    "TMK - CRM Account Name",
    "CC Email",
    "CC - CRM Account Name",
    "CC Whatsapp Number",
    "Submitted on",
    "Respondents",
    "Customer Name",
    "Customer ID",
    "Customer Contact",
    "Issue",
    "_raw_json",
]
if not Path(CSV_FILE).exists():
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()


def write_csv_row(row: Dict[str, Any]) -> None:
    """Append a row to the CSV; missing keys will be filled with ''."""
    out = {k: row.get(k, "") for k in CSV_COLUMNS}
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=CSV_COLUMNS).writerow(out)


@app.get("/healthz")
def healthz() -> Dict[str, str]:
    return {"status": "ok"}

@app.post("/webhook/lark")
async def lark_webhook(
    request: Request,
    x_webhook_secret: Optional[str] = Header(default=None, alias="X-Webhook-Secret"),
):
    """
    Receives JSON from Lark Base Automation HTTP Request:
    {
      "event": "lark_form_submission",
      "record_id": "...",
      "submitted_at": "...",
      "fields": {
        "SN": "...",
        "TMK - CRM Account Name": "...",
        "CC - CRM Account Name": "...",
        "CC Email": "...",
        "CC Whatsapp Number": "...",
        "Submitted on": "...",
        "Respondents": "...",
        "Customer Name": "...",
        "Customer ID": "...",
        "Customer Contact": "...",
        "Issue": "..."
      }
    }
    """

    # 1) Secret check (header name must match exactly in Lark)
    if not x_webhook_secret or x_webhook_secret != WEBHOOK_SECRET:
        logger.warning("Unauthorized request (bad or missing X-Webhook-Secret).")
        raise HTTPException(status_code=401, detail="invalid secret")

    # 2) Parse JSON safely with fallback for malformed JSON
    try:
        payload: Dict[str, Any] = await request.json()
    except Exception as e:
        body_text = await request.body()
        logger.error("Invalid JSON body: %s", body_text.decode('utf-8')[:500])
        
        # Try to fix common JSON formatting issues
        try:
            body_str = body_text.decode('utf-8')
            logger.debug("Attempting to fix malformed JSON: %s", body_str[:200])
            
            # ENHANCED JSON fixing with specific handling for CC Agent ID pattern
            lines = body_str.split('\n')
            fixed_lines = []
            i = 0
            
            while i < len(lines):
                line = lines[i]
                stripped = line.strip()
                
                # Skip empty lines and structural elements
                if not stripped or stripped in ['{', '}']:
                    fixed_lines.append(line)
                    i += 1
                    continue
                
                # Handle key-value pairs
                if ':' in stripped:
                    # Split on first colon
                    colon_pos = stripped.find(':')
                    key_part = stripped[:colon_pos].strip()
                    value_part = stripped[colon_pos + 1:].strip()
                    
                    # CRITICAL FIX: Handle the CC Agent ID pattern where value is on next line
                    if not value_part and i + 1 < len(lines):
                        # Look at the next line
                        next_line = lines[i + 1].strip()
                        if next_line and ':' not in next_line and next_line not in ['{', '}']:
                            # This is our value on the next line
                            has_trailing_comma = next_line.endswith(',')
                            actual_value = next_line.rstrip(',').strip()
                            
                            # Quote the value if it's not already quoted
                            if (actual_value and 
                                not actual_value.startswith('"') and 
                                not actual_value.replace('.', '').replace('-', '').isdigit() and
                                actual_value not in ['true', 'false', 'null']):
                                actual_value = f'"{actual_value}"'
                            elif not actual_value:
                                actual_value = '""'
                            
                            # Reconstruct as a single line with proper indentation
                            fixed_line = f'    {key_part}: {actual_value}'
                            if has_trailing_comma:
                                fixed_line += ','
                            
                            fixed_lines.append(fixed_line)
                            i += 2  # Skip both current and next line
                            continue
                    
                    # Handle normal case where value is on same line
                    has_trailing_comma = value_part.endswith(',')
                    if has_trailing_comma:
                        value_part = value_part.rstrip(',').strip()
                    
                    # Handle empty values
                    if not value_part:
                        value_part = '""'
                    # Quote unquoted string values
                    elif (not value_part.startswith('"') and 
                          not value_part.startswith('{') and 
                          not value_part.replace('.', '').replace('-', '').isdigit() and
                          value_part not in ['true', 'false', 'null']):
                        value_part = f'"{value_part}"'
                    
                    # Reconstruct the line with proper indentation
                    fixed_line = f'    {key_part}: {value_part}'
                    if has_trailing_comma:
                        fixed_line += ','
                    
                    fixed_lines.append(fixed_line)
                else:
                    # Non key-value line - keep as is
                    fixed_lines.append(line)
                
                i += 1
            
            # Join back together
            fixed_json = '\n'.join(fixed_lines)
            logger.debug("Enhanced fixed JSON: %s", fixed_json[:400])
            
            # Try parsing the fixed JSON
            payload = json.loads(fixed_json)
            logger.info("Successfully parsed JSON after enhanced fixing")
            
        except Exception as fix_error:
            logger.exception("Failed to fix JSON formatting: %s", fix_error)
            raise HTTPException(status_code=400, detail="invalid json format")

    # 3) Basic validation
    fields = payload.get("fields") or {}
    record_id = payload.get("record_id") or ""
    submitted_at = payload.get("submitted_at") or ""

    # 4) Log what we received
    logger.info("Received payload: %s", json.dumps(payload, ensure_ascii=False))
    print("=== WEBHOOK PAYLOAD RECEIVED ===")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print("=================================")
    # 5) Persist to CSV
    csv_row = {
        "received_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "record_id": record_id,
        "submitted_at": submitted_at,
        "SN": fields.get("SN", ""),
        "TMK - CRM Account Name": fields.get("TMK - CRM Account Name", ""),
        "CC Email": fields.get("CC Email", ""),
        "CC - CRM Account Name": fields.get("CC - CRM Account Name", ""),
        "CC Whatsapp Number": fields.get("CC Whatsapp Number", ""),
        "Submitted on": fields.get("Submitted on", ""),
        "Respondents": fields.get("Respondents", ""),
        "Customer Name": fields.get("Customer Name", ""),
        "Customer ID": fields.get("Customer ID", ""),
        "Customer Contact": fields.get("Customer Contact", ""),
        "Issue": fields.get("Issue", ""),
        "_raw_json": json.dumps(payload, ensure_ascii=False),
    }
    write_csv_row(csv_row)
    
    # 6) Log to Google Sheets (if enabled)
    print("\n" + "="*60)
    print("📊 GOOGLE SHEETS INTEGRATION")
    print("="*60)
    
    if SHEETS_ENABLED:
        print("✅ Google Sheets integration is ENABLED")
        try:
            print("🔄 Attempting to log data to Google Sheets...")
            sheets_success = await log_to_google_sheet(payload)
            if sheets_success:
                print("✅ SUCCESS: Data logged to Google Sheets successfully!")
                logger.info("✅ Successfully logged webhook data to Google Sheets")
            else:
                print("❌ FAILED: Could not log data to Google Sheets")
                logger.error("❌ Failed to log webhook data to Google Sheets")
        except Exception as e:
            print(f"❌ ERROR: Exception in Google Sheets integration: {e}")
            logger.error("Error logging to Google Sheets: %s", e)
    else:
        print("⚠️  Google Sheets integration is DISABLED")
        print("   Set GOOGLE_SHEETS_ENABLED=true in .env to enable")
    
    # 7) Send email notifications (if enabled)
    print("\n" + "="*60)
    print("📧 EMAIL NOTIFICATIONS")
    print("="*60)
    
    if EMAIL_ENABLED:
        print("✅ Email notifications are ENABLED")
        try:
            # Only send CC agent follow-up notification if CC Email is present
            cc_email = fields.get('CC Email', '').strip()
            print(f"🔍 Checking CC Email field: '{cc_email}'")
            
            if cc_email and '@' in cc_email:
                print(f"📧 Sending email notification to: {cc_email}")
                cc_success = await send_cc_agent_email(payload)
                if cc_success:
                    print(f"✅ SUCCESS: Email sent successfully to {cc_email}")
                    logger.info("CC agent notification sent successfully to %s", cc_email)
                else:
                    print(f"❌ FAILED: Could not send email to {cc_email}")
                    logger.error("Failed to send CC agent notification to %s", cc_email)
            else:
                print("⚠️  No valid CC Email provided - skipping email notifications")
                print("   Make sure CC Email field contains a valid email address")
                logger.info("No CC Email provided - no email notifications sent")
                
        except Exception as e:
            print(f"❌ ERROR: Exception in email service: {e}")
            logger.error("Error sending email notifications: %s", e)
    else:
        print("⚠️  Email notifications are DISABLED")
        print("   Set EMAIL_ENABLED=true in .env to enable")
    
    # 8) Send WhatsApp notifications (if enabled)
    print("\n" + "="*60)
    print("📱 WHATSAPP NOTIFICATIONS")
    print("="*60)
    
    if WHATSAPP_ENABLED:
        print("✅ WhatsApp notifications are ENABLED")
        try:
            # Send WhatsApp message to CC Whatsapp Number if provided
            cc_whatsapp = fields.get('CC Whatsapp Number', '').strip()
            print(f"🔍 Checking CC Whatsapp Number field: '{cc_whatsapp}'")
            
            if cc_whatsapp:
                print(f"📱 Sending WhatsApp template 'tmktocc' to: {cc_whatsapp}")
                whatsapp_success = await send_whatsapp_message(payload)
                if whatsapp_success:
                    print(f"✅ SUCCESS: WhatsApp message sent successfully to {cc_whatsapp}")
                    print("   📋 Template: tmktocc")
                    print("   ⏰ No 24-hour restriction (template message)")
                    logger.info("WhatsApp message sent successfully to %s", cc_whatsapp)
                else:
                    print(f"❌ FAILED: Could not send WhatsApp message to {cc_whatsapp}")
                    print("   Check WhatsApp API credentials and phone number format")
                    logger.error("Failed to send WhatsApp message to %s", cc_whatsapp)
            else:
                print("⚠️  No CC Whatsapp Number provided - skipping WhatsApp notifications")
                print("   Make sure CC Whatsapp Number field contains a valid phone number")
                logger.info("No CC Whatsapp Number provided - no WhatsApp messages sent")
                
        except Exception as e:
            print(f"❌ ERROR: Exception in WhatsApp service: {e}")
            logger.error("Error sending WhatsApp notifications: %s", e)
    else:
        print("⚠️  WhatsApp notifications are DISABLED")
        print("   Set WHATSAPP_ENABLED=true in .env to enable")
    
    print("\n" + "="*60)
    print("🎯 WEBHOOK PROCESSING COMPLETE")
    print("="*60)
    print("✅ Form submission processed successfully")
    print(f"📝 Record ID: {payload.get('record_id', 'N/A')}")
    print(f"👤 Customer: {fields.get('Customer Name', 'N/A')}")
    print(f"📞 Contact: {fields.get('Customer Contact', 'N/A')}")
    print("="*60)

    # 9) Return a small OK JSON (Lark only needs a 2xx)
    return JSONResponse({"ok": True})
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)