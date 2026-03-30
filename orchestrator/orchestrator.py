"""
InsuranceOS — Orquestrador Central
Roteia intenções para os agentes especializados.
"""
import os
import re
import logging
from typing import Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("insuranceos.orchestrator")

# Intent → Module mapping
INTENT_MAP = {
    # Cotação
    r"(cot[aá]|quot|segur[ao] (de|para)|quanto (custa|fica)|preço)": "quote",
    # Sinistro
    r"(sinistro|acidente|baten|roub|furt|dano|acionar|abrir (sinistro|ocorrência))": "claim",
    # Apólice / 2ª via
    r"(apólice|ap[oó]lice|vigência|vencimento|renovar|renovação|segunda via|2[aª] via|boleto)": "policy",
    # Vendas / Lead
    r"(quero comprar|contratar|adquirir|fechar|proposta|lead)": "sales",
    # Relatório
    r"(relatório|dashboard|kpi|performance|meta|resultado)": "report",
    # CRM
    r"(cliente|cadastro|histórico|contato|atualizar dados)": "crm",
}

HUMAN_ESCALATION_TRIGGERS = [
    "falar com (corretor|humano|pessoa|atendente)",
    "quero falar com alguém",
    "preciso de ajuda humana",
]


def classify_intent(text: str) -> str:
    """Classify user message into a module intent."""
    if not text:
        return "atendimento"

    text_lower = text.lower()

    # Check for human escalation first
    for pattern in HUMAN_ESCALATION_TRIGGERS:
        if re.search(pattern, text_lower):
            return "human_escalation"

    # Match against intent map
    for pattern, module in INTENT_MAP.items():
        if re.search(pattern, text_lower):
            return module

    return "atendimento"  # Default: general customer service


async def route(
    user_phone: str,
    text: str,
    intent: Optional[str] = None,
    image_url: Optional[str] = None,
) -> str:
    """Route to the appropriate agent and return response."""

    if intent is None:
        intent = classify_intent(text)

    logger.info(f"Routing {user_phone} → intent={intent}")

    if intent == "human_escalation":
        return await escalate_to_human(user_phone, text)

    try:
        if intent == "quote":
            from modules.quote.agent import run_async
            return await run_async(user_phone, text)
        elif intent == "claim":
            from modules.claim.agent import run_async
            return await run_async(user_phone, text)
        elif intent == "policy":
            from modules.policy.agent import run_async
            return await run_async(user_phone, text)
        elif intent == "sales":
            from modules.sales.agent import run_async
            return await run_async(user_phone, text)
        elif intent == "report":
            from modules.report.agent import run_async
            return await run_async(user_phone, text)
        elif intent == "crm":
            from modules.crm.agent import run_async
            return await run_async(user_phone, text)
        else:
            from modules.atendimento.agent import run_async
            return await run_async(user_phone, text)

    except ImportError as e:
        logger.error(f"Módulo não disponível: {e}")
        return "Serviço temporariamente indisponível. Tente novamente em instantes."


async def escalate_to_human(user_phone: str, text: str) -> str:
    """Escalate conversation to human agent via Telegram alert."""
    try:
        from tools.notifications import send_telegram_alert
        await send_telegram_alert(
            f"*Escalada Humana*\n"
            f"Cliente: {user_phone}\n"
            f"Mensagem: {text}"
        )
    except Exception as e:
        logger.error(f"Falha ao enviar alerta Telegram: {e}")

    return (
        "Entendido! Vou conectar você com um de nossos corretores. "
        "Em breve alguém entrará em contato. "
        "Horário de atendimento: segunda a sexta, das 8h às 18h."
    )
