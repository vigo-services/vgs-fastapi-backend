import os
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Any, Dict, List
import httpx
import json
import logging
from datetime import datetime, timezone

# Configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("vgs-api")

WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v21.0")

app = FastAPI(
    title="VGS API",
    description="Backend FastAPI pour le traitement des webhooks WhatsApp",
    version="1.0.0",
)

class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: str

@app.get("/health")
async def health():
    return HealthResponse(
        status="healthy",
        service="vgs-api",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

@app.get("/")
async def root():
    return {"message": "VGS API is running", "docs": "/docs"}

@app.post("/webhook")
async def receive_webhook(
    request: Request,
    x_webhook_source: Optional[str] = Header(None),
    x_webhook_attempt: Optional[str] = Header(None),
):
    try:
        body = await request.json()
        logger.info(f"Webhook received (attempt {x_webhook_attempt})")
        logger.info(f"Payload: {json.dumps(body, indent=2)[:500]}")

        if body.get("object") == "whatsapp_business_account":
            entries = body.get("entry", [])
            for entry in entries:
                changes = entry.get("changes", [])
                for change in changes:
                    value = change.get("value", {})
                    messages = value.get("messages", [])
                    for message in messages:
                        await process_message(message)

            return JSONResponse(
                status_code=200,
                content={"status": "ok", "processed": True},
            )

        logger.warning("Webhook received but not a WhatsApp webhook")
        return JSONResponse(
            status_code=200,
            content={"status": "ok", "processed": False},
        )

    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_message(message: Dict[str, Any]):
    message_type = message.get("type", "unknown")
    from_number = message.get("from", "unknown")

    logger.info(f"Message from {from_number} — type: {message_type}")

    if message_type == "text":
        text_body = message.get("text", {}).get("body", "")
        logger.info(f"Text content: {text_body}")
        await send_whatsapp_message(
            to=from_number,
            text=f'✅ Message bien reçu ! Vous avez dit: "{text_body}"\n\n— VGS Bot',
        )
    else:
        logger.info(f"Message type '{message_type}' received (not processed yet)")

async def send_whatsapp_message(to: str, text: str):
    if not WHATSAPP_ACCESS_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        logger.warning("WhatsApp credentials not configured — skipping send")
        return

    url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                logger.info(f"Message sent to {to}")
            else:
                logger.error(f"Failed to send message: {response.status_code}")
    except Exception as e:
        logger.error(f"Error sending WhatsApp message: {e}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
