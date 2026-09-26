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
                content={"st
