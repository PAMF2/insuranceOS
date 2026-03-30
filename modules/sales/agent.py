"""
InsuranceOS — Agente de Vendas
Pipeline, follow-up automático, conversão de leads.
"""
import logging
import asyncio
from datetime import datetime, timedelta

logger = logging.getLogger("insuranceos.sales")


FOLLOW_UP_TEMPLATES = {
    "cotacao_enviada": (
        "Oi {nome}! 👋 Tudo bem?\n"
        "Enviamos sua cotação de seguro {ramo} há alguns dias. "
        "Você teve a chance de analisar? Posso esclarecer alguma dúvida ou ajustar algo para você?"
    ),
    "sem_resposta_3d": (
        "Oi {nome}! Sou a Sofia da sua corretora de seguros. 😊\n"
        "Notei que você tinha interesse em seguro {ramo}. "
        "Posso te ajudar com uma cotação personalizada hoje?"
    ),
    "renovacao": (
        "Oi {nome}! Sua apólice de {ramo} vence em {dias} dias. 📅\n"
        "Já preparamos as melhores opções de renovação para você. "
        "Quer que eu envie as cotações?"
    ),
    "pos_venda": (
        "Oi {nome}! Tudo certo com seu seguro {ramo}? 🛡️\n"
        "Estou aqui se precisar de qualquer informação, "
        "quiser adicionar coberturas ou tiver alguma dúvida. "
        "Fique à vontade!"
    ),
}


async def run_async(user_phone: str, text: str) -> str:
    """Handle sales queries and lead conversion."""
    from tools.crm_sheets import get_lead, upsert_lead

    try:
        lead = get_lead(user_phone)
        if lead:
            upsert_lead(user_phone, status="qualificado")
    except Exception as e:
        logger.error(f"CRM error: {e}")

    return (
        "Ótimo! Vou te ajudar a encontrar o seguro ideal. 🎯\n\n"
        "Para montar a melhor proposta, me diga:\n"
        "1. Qual ramo de seguro você precisa? (Auto, Vida, Saúde, Residencial)\n"
        "2. Tem alguma seguradora de preferência?\n"
        "3. Qual sua principal prioridade: menor preço ou melhor cobertura?"
    )


async def send_follow_up(
    user_phone: str,
    template_key: str,
    context: dict,
) -> bool:
    """Send automated follow-up message via WhatsApp."""
    from tools.whatsapp import send_text

    template = FOLLOW_UP_TEMPLATES.get(template_key)
    if not template:
        logger.error(f"Template não encontrado: {template_key}")
        return False

    try:
        message = template.format(**context)
        await send_text(user_phone, message)
        logger.info(f"Follow-up '{template_key}' enviado para {user_phone}")
        return True
    except Exception as e:
        logger.error(f"Follow-up error: {e}")
        return False


def run(query: str = None):
    """CLI mode."""
    from rich.console import Console
    console = Console()
    console.print("[bold blue]Agente de Vendas — InsuranceOS[/bold blue]\n")
    while True:
        text = query or input("Você: ").strip()
        if text.lower() in ("sair", "exit"):
            break
        response = asyncio.run(run_async("cli_user", text))
        console.print(f"[green]Agente:[/green] {response}\n")
        query = None
