import csv
import json
import logging
import os
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
    x_webhook_secret: Optional[str] = Header(default=None, convert_underscores=False),
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

    # 2) Parse JSON safely
    try:
        payload: Dict[str, Any] = await request.json()
    except Exception:
        body_text = await request.body()
        logger.exception("Invalid JSON body: %s", body_text[:500])
        raise HTTPException(status_code=400, detail="invalid json")

    # 3) Basic validation
    fields = payload.get("fields") or {}
    record_id = payload.get("record_id") or ""
    submitted_at = payload.get("submitted_at") or ""

    # 4) Log what we received
    logger.info("Received payload: %s", json.dumps(payload, ensure_ascii=False))

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
