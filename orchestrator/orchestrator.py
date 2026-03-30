"""
InsuranceOS v0.5 — Orquestrador Central
Roteia intenções para agentes especializados.
Usa session memory, multi-LLM e ensemble para decisões críticas.
"""
import os
import re
import logging
from typing import Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("insuranceos.orchestrator")

# Intent → Module mapping (regex → module key)
INTENT_MAP = {
    r"(cot[aá]|quot|segur[ao] (de|para)|quanto (custa|fica)|preço|valor do seguro)": "quote",
    r"(sinistro|acident|baten|roub|furt|dano|acionar|abrir (sinistro|ocorr))":         "claim",
    r"(apólice|ap[oó]lice|vigência|vencimento|renovar|renovação|segunda via|2[aª] via|boleto|parcela)": "policy",
    r"(quero comprar|contratar|adquirir|fechar|proposta|me interessa)":                 "sales",
    r"(relatório|dashboard|kpi|performance|meta|resultado|estatísticas?)":              "report",
    r"(cliente|cadastro|histórico|contato|atualizar dados|meu perfil)":                 "crm",
    r"(cnpj|empresa|razão social|nome fantasia|sócios)":                                "rfb",
    r"(susep|regulament|norma|circular|habilitad|corretor registr)":                    "susep",
    r"(manual|condições gerais|cobertura (detalhe|completa)|cláusula|exclusão)":        "rag",
}

HUMAN_ESCALATION_PATTERNS = [
    r"falar com (corretor|humano|pessoa|atendente|gerente)",
    r"quero falar com alguém",
    r"preciso de ajuda humana",
    r"urgente|emergência|socorro",
]

RESET_PATTERNS = [
    r"novo atendimento|recomeçar|sair|voltar ao início",
]


def classify_intent(text: str) -> str:
    """Classify user message into a module intent."""
    if not text:
        return "atendimento"

    text_lower = text.lower()

    for pattern in HUMAN_ESCALATION_PATTERNS:
        if re.search(pattern, text_lower):
            return "human_escalation"

    for pattern, module in INTENT_MAP.items():
        if re.search(pattern, text_lower):
            return module

    return "atendimento"


async def classify_with_llm(text: str, history: str = "") -> str:
    """Use LLM for more nuanced intent classification when rule-based fails."""
    from tools.llm import complete

    prompt = (
        f"Histórico recente:\n{history}\n\n"
        f"Mensagem do cliente: {text}\n\n"
        f"Classifique a intenção em UMA palavra: "
        f"quote | claim | policy | sales | report | crm | atendimento | human_escalation\n\n"
        f"Responda apenas com a palavra, sem explicação."
    )
    try:
        result = await complete(prompt, system="Você é um classificador de intenções para seguros.", temperature=0)
        intent = result.strip().lower().split()[0]
        return intent if intent in ("quote", "claim", "policy", "sales", "report", "crm",
                                     "atendimento", "human_escalation") else "atendimento"
    except Exception as e:
        logger.warning(f"LLM classify error: {e}")
        return "atendimento"


async def route(
    user_phone: str,
    text: str,
    intent: Optional[str] = None,
    image_url: Optional[str] = None,
) -> str:
    """Route to the appropriate agent and return response."""
    from tools.session import add_message, get_history_text, set_context

    # Add message to session history
    add_message(user_phone, "user", text or "")

    if intent is None:
        intent = classify_intent(text or "")

        # Fallback to LLM if atendimento (ambiguous)
        if intent == "atendimento" and text and len(text) > 10:
            history = get_history_text(user_phone, last_n=4)
            intent = await classify_with_llm(text, history)

    logger.info(f"Routing {user_phone} → intent={intent}")

    if intent == "human_escalation":
        response = await escalate_to_human(user_phone, text)
    elif intent == "rfb":
        response = await route_rfb(user_phone, text)
    elif intent == "susep":
        response = await route_susep(user_phone, text)
    elif intent == "rag":
        response = await route_rag(user_phone, text)
    else:
        try:
            module_map = {
                "quote":      "modules.quote.agent",
                "claim":      "modules.claim.agent",
                "policy":     "modules.policy.agent",
                "sales":      "modules.sales.agent",
                "report":     "modules.report.agent",
                "crm":        "modules.crm.agent",
                "atendimento":"modules.atendimento.agent",
            }
            mod_path = module_map.get(intent, "modules.atendimento.agent")
            mod = __import__(mod_path, fromlist=["run_async"])
            response = await mod.run_async(user_phone, text)
        except ImportError as e:
            logger.error(f"Módulo não disponível: {e}")
            response = "Serviço temporariamente indisponível. Tente novamente em instantes."

    add_message(user_phone, "assistant", response)
    return response


async def route_rfb(user_phone: str, text: str) -> str:
    """Extract CNPJ from text and query RFB."""
    from tools.rfb import consultar_cnpj, formatar_resumo_cnpj, clean_cnpj
    import re

    match = re.search(r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}", text)
    if not match:
        return (
            "Para consultar um CNPJ, me informe o número no formato:\n"
            "12.345.678/0001-90"
        )

    dados = await consultar_cnpj(match.group(0))
    return formatar_resumo_cnpj(dados)


async def route_susep(user_phone: str, text: str) -> str:
    """Route SUSEP queries."""
    from tools.susep import formatar_seguradoras_whatsapp, get_regulamento

    text_lower = text.lower()
    ramo = None
    for r in ("auto", "vida", "saude", "saúde", "residencial", "empresarial"):
        if r in text_lower:
            ramo = r.replace("saúde", "saude")
            break

    if ramo:
        return formatar_seguradoras_whatsapp(ramo)

    return (
        "Posso te ajudar com informações SUSEP sobre:\n"
        "• Seguradoras habilitadas por ramo\n"
        "• Regulamentação vigente\n\n"
        "Qual ramo você quer consultar? (Auto, Vida, Saúde, Residencial, Empresarial)"
    )


async def route_rag(user_phone: str, text: str) -> str:
    """Route document queries to RAG."""
    from tools.rag import query_with_llm
    return await query_with_llm(text)


async def escalate_to_human(user_phone: str, text: str) -> str:
    """Escalate conversation to human agent via Telegram alert."""
    from tools.notifications import send_telegram_alert
    from tools.session import get_history_text

    history = get_history_text(user_phone, last_n=6)
    urgente = any(w in (text or "").lower() for w in ["urgente", "emergência", "socorro", "acidente"])

    alert = (
        f"{'🚨 *URGENTE*' if urgente else '*Escalada Humana*'} — InsuranceOS\n"
        f"Cliente: {user_phone}\n"
        f"Mensagem: {text}\n\n"
        f"Histórico recente:\n{history}"
    )

    try:
        await send_telegram_alert(alert)
    except Exception as e:
        logger.error(f"Falha ao enviar alerta Telegram: {e}")

    if urgente:
        return "Acionando corretor agora! 🚨 Você será contatado em instantes."

    return (
        "Entendido! Vou conectar você com um de nossos corretores. "
        "Em breve alguém entrará em contato. "
        "Horário de atendimento: segunda a sexta, das 8h às 18h."
    )
