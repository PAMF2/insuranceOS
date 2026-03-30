"""
InsuranceOS — Notificações (Telegram + WhatsApp interno)
"""
import os
import logging
import httpx

logger = logging.getLogger("insuranceos.notifications")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


async def send_telegram_alert(message: str, parse_mode: str = "Markdown") -> bool:
    """Send alert to internal Telegram chat (for escalations and ops)."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram não configurado")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": parse_mode,
    }

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Telegram error: {e}")
            return False


async def alert_new_lead(telefone: str, nome: str, ramo: str, corretor: str = None):
    msg = (
        f"*Novo Lead InsuranceOS*\n"
        f"Telefone: {telefone}\n"
        f"Nome: {nome or 'Não informado'}\n"
        f"Interesse: {ramo or 'Não informado'}\n"
        f"Corretor: {corretor or 'A definir'}"
    )
    await send_telegram_alert(msg)


async def alert_new_claim(telefone: str, tipo: str, descricao: str):
    msg = (
        f"*Sinistro Aberto — InsuranceOS*\n"
        f"Cliente: {telefone}\n"
        f"Tipo: {tipo}\n"
        f"Descrição: {descricao[:200]}"
    )
    await send_telegram_alert(msg)


async def alert_policy_renewal(telefone: str, apolice: str, vencimento: str):
    msg = (
        f"*Renovação Pendente — InsuranceOS*\n"
        f"Cliente: {telefone}\n"
        f"Apólice: {apolice}\n"
        f"Vencimento: {vencimento}"
    )
    await send_telegram_alert(msg)
