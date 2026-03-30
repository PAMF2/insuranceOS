"""
InsuranceOS — Webhook Server (WhatsApp via Meta Cloud API)
"""
import os
import asyncio
import logging
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("insuranceos.server")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

app = FastAPI(title="InsuranceOS Webhook", version="0.1.0")

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "insuranceos_verify")
WEBHOOK_TOKEN = os.getenv("WEBHOOK_TOKEN", "")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "InsuranceOS"}


# ── WhatsApp webhook verification (GET) ──────────────────────────────────────
@app.get("/webhook/whatsapp")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        logger.info("Webhook verificado com sucesso")
        return PlainTextResponse(hub_challenge)
    raise HTTPException(status_code=403, detail="Token de verificação inválido")


# ── WhatsApp webhook receiver (POST) ─────────────────────────────────────────
@app.post("/webhook/whatsapp")
async def receive_message(request: Request):
    # Validate internal token if configured
    if WEBHOOK_TOKEN:
        token = request.headers.get("x-webhook-token", "")
        if token != WEBHOOK_TOKEN:
            raise HTTPException(status_code=401, detail="Não autorizado")

    body = await request.json()

    try:
        entry = body["entry"][0]
        changes = entry["changes"][0]["value"]
        messages = changes.get("messages", [])

        if not messages:
            return {"status": "no_message"}

        message = messages[0]
        user_phone = message["from"]
        msg_type = message.get("type", "text")

        # Extract content
        text = None
        image_url = None
        audio_url = None

        if msg_type == "text":
            text = message["text"]["body"]
        elif msg_type == "image":
            image_url = message["image"].get("id")
            text = message["image"].get("caption", "")
        elif msg_type == "audio":
            audio_url = message["audio"].get("id")
        elif msg_type == "interactive":
            # Button reply
            if "button_reply" in message.get("interactive", {}):
                text = message["interactive"]["button_reply"]["id"]
            elif "list_reply" in message.get("interactive", {}):
                text = message["interactive"]["list_reply"]["id"]

        logger.info(f"Mensagem de {user_phone}: type={msg_type} text={text!r}")

        # Route to atendimento agent (async, non-blocking)
        asyncio.create_task(
            route_message(user_phone, text, image_url, audio_url)
        )

        return {"status": "received"}

    except (KeyError, IndexError) as e:
        logger.warning(f"Payload inesperado: {e}")
        return {"status": "ignored"}


async def route_message(user_phone: str, text: str, image_url: str, audio_url: str):
    """Route incoming message to appropriate agent."""
    from modules.atendimento.agent import handle_message
    try:
        await handle_message(user_phone, text, image_url, audio_url)
    except Exception as e:
        logger.error(f"Erro ao processar mensagem de {user_phone}: {e}")
        # Send fallback message
        from tools.whatsapp import send_text
        await send_text(
            user_phone,
            "Desculpe, tive um problema interno. Por favor, tente novamente em instantes."
        )


# ── Internal webhook (for agent-to-agent calls) ──────────────────────────────
@app.post("/webhook/internal")
async def internal_trigger(request: Request):
    if WEBHOOK_TOKEN:
        token = request.headers.get("x-webhook-token", "")
        if token != WEBHOOK_TOKEN:
            raise HTTPException(status_code=401, detail="Não autorizado")

    body = await request.json()
    module = body.get("module")
    action = body.get("action")
    payload = body.get("payload", {})

    logger.info(f"Trigger interno: module={module} action={action}")
    # TODO: route to specific module action
    return {"status": "ok", "module": module, "action": action}
