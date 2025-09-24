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

# --- env & setup ---
load_dotenv()

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
LOG_FILE = os.getenv("LOG_FILE", "webhook.log")
CSV_FILE = os.getenv("CSV_FILE", "submissions.csv")
print(f"WEBHOOK_SECRET loaded: {'Yes' if WEBHOOK_SECRET else 'No'}")
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

# ensure CSV has a header
CSV_COLUMNS = [
    "received_at",
    "record_id",
    "submitted_at",
    "SN",
    "TMK Agent ID",
    "Submitted on",
    "Respondents",
    "Customer Name",
    "Customer ID",
    "Customer Contact",
    "Issue",
    "Date",
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
        "TMK Agent ID": "...",
        "Submitted on": "...",
        "Respondents": "...",
        "Customer Name": "...",
        "Customer ID": "...",
        "Customer Contact": "...",
        "Issue": "...",
        "Date": "..."
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
            
            # More comprehensive JSON fixing approach
            lines = body_str.split('\n')
            fixed_lines = []
            
            for line in lines:
                # Skip empty lines and braces
                if not line.strip() or line.strip() in ['{', '}']:
                    fixed_lines.append(line)
                    continue
                
                # Handle key-value pairs
                if ':' in line:
                    # Split on first colon to separate key and value
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        key_part = parts[0].strip()
                        value_part = parts[1].strip()
                        
                        # Remove trailing comma from value if present
                        has_comma = value_part.rstrip().endswith(',')
                        if has_comma:
                            value_part = value_part.rstrip(' ,')
                        
                        # Fix the value part - quote it if it's not already quoted and not a number/boolean
                        if (not value_part.startswith('"') and 
                            not value_part.startswith('{') and 
                            not value_part.replace('.', '').replace('-', '').isdigit() and
                            value_part not in ['true', 'false', 'null']):
                            value_part = f'"{value_part}"'
                        
                        # Reconstruct the line
                        fixed_line = f'  {key_part}: {value_part}'
                        if has_comma:
                            fixed_line += ','
                        
                        fixed_lines.append(fixed_line)
                    else:
                        fixed_lines.append(line)
                else:
                    fixed_lines.append(line)
            
            # Join back together
            fixed_json = '\n'.join(fixed_lines)
            logger.debug("Fixed JSON attempt: %s", fixed_json[:200])
            
            # Try parsing the fixed JSON
            payload = json.loads(fixed_json)
            logger.info("Successfully parsed JSON after fixing formatting issues")
            
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
        "TMK Agent ID": fields.get("TMK Agent ID", ""),
        "Submitted on": fields.get("Submitted on", ""),
        "Respondents": fields.get("Respondents", ""),
        "Customer Name": fields.get("Customer Name", ""),
        "Customer ID": fields.get("Customer ID", ""),
        "Customer Contact": fields.get("Customer Contact", ""),
        "Issue": fields.get("Issue", ""),
        "Date": fields.get("Date", ""),
        "_raw_json": json.dumps(payload, ensure_ascii=False),
    }
    write_csv_row(csv_row)

    # 6) Return a small OK JSON (Lark only needs a 2xx)
    return JSONResponse({"ok": True})
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)