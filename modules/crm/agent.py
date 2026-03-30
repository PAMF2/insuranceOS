"""
InsuranceOS — Agente CRM
Gestão de leads, clientes, histórico e segmentação.
"""
import logging
import asyncio

logger = logging.getLogger("insuranceos.crm")


async def run_async(user_phone: str, text: str) -> str:
    from tools.crm_sheets import get_lead

    try:
        lead = get_lead(user_phone)
        if lead:
            return (
                f"*Cadastro encontrado* 📋\n"
                f"Nome: {lead.get('nome') or 'Não informado'}\n"
                f"Interesse: {lead.get('ramo_interesse') or 'Não informado'}\n"
                f"Status: {lead.get('status') or 'novo'}\n\n"
                "O que você gostaria de atualizar?"
            )
    except Exception as e:
        logger.error(f"CRM get_lead error: {e}")

    return (
        "Não encontrei seu cadastro. Vamos criá-lo!\n"
        "Qual é o seu nome completo?"
    )


def run(query: str = None):
    from rich.console import Console
    console = Console()
    console.print("[bold blue]CRM — InsuranceOS[/bold blue]\n")
    while True:
        text = query or input("Você: ").strip()
        if text.lower() in ("sair", "exit"):
            break
        response = asyncio.run(run_async("cli_user", text))
        console.print(f"[green]Agente:[/green] {response}\n")
        query = None
