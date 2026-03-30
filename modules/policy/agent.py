"""
InsuranceOS — Agente de Apólices
2ª via, consulta de vigência, renovação, endosso.
"""
import logging
import asyncio

logger = logging.getLogger("insuranceos.policy")


async def run_async(user_phone: str, text: str) -> str:
    text_lower = text.lower()

    if any(w in text_lower for w in ["segunda via", "2ª via", "boleto", "pagamento"]):
        return (
            "Para emitir a 2ª via do boleto, preciso do:\n"
            "• Número da apólice *ou*\n"
            "• CPF/CNPJ cadastrado\n\n"
            "Pode me informar?"
        )

    if any(w in text_lower for w in ["renovar", "renovação", "vencer", "vencimento"]):
        return (
            "Vou verificar sua apólice para renovação. 📋\n"
            "Me informe o número da apólice ou seu CPF para eu localizar."
        )

    if any(w in text_lower for w in ["cancelar", "cancelamento"]):
        return (
            "Entendido. Para solicitar o cancelamento, precisamos:\n"
            "1. Número da apólice\n"
            "2. Motivo do cancelamento\n\n"
            "⚠️ O cancelamento pode gerar cobrança proporcional conforme condições gerais.\n"
            "Deseja continuar?"
        )

    return (
        "Posso te ajudar com sua apólice. O que você precisa?\n\n"
        "• 2ª via de boleto\n"
        "• Consultar vigência\n"
        "• Renovação\n"
        "• Endosso (alteração de dados)\n"
        "• Cancelamento"
    )


def run(query: str = None):
    from rich.console import Console
    console = Console()
    console.print("[bold blue]Agente de Apólices — InsuranceOS[/bold blue]\n")
    while True:
        text = query or input("Você: ").strip()
        if text.lower() in ("sair", "exit"):
            break
        response = asyncio.run(run_async("cli_user", text))
        console.print(f"[green]Agente:[/green] {response}\n")
        query = None
