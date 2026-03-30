"""
InsuranceOS — Agente de Sinistros
Registra, acompanha e orienta clientes em sinistros.
"""
import logging
import asyncio

logger = logging.getLogger("insuranceos.claim")

ORIENTACOES = {
    "colisao": [
        "Fotografe todos os danos no veículo e no local",
        "Solicite o Boletim de Ocorrência (BO) online ou na delegacia",
        "Anote dados do outro motorista (se houver): nome, placa, CNH, seguro",
        "NÃO assine nada nem faça acordos na hora",
        "Entre em contato com a seguradora em até 24h",
    ],
    "roubo": [
        "Registre o Boletim de Ocorrência imediatamente (BO online ou delegacia)",
        "Guarde o número do BO — é obrigatório para o sinistro",
        "Notifique a seguradora em até 24h após o BO",
        "Tenha em mãos: DUT, CRLV, CNH e documento pessoal",
    ],
    "incendio": [
        "Prioridade: segurança das pessoas — evacue o local",
        "Acione o Corpo de Bombeiros (193)",
        "Registre BO e informe à seguradora imediatamente",
        "Fotografe os danos antes de qualquer limpeza",
    ],
    "residencial": [
        "Fotografe todos os danos antes de qualquer reparo",
        "Guarde notas fiscais de itens danificados",
        "Não faça reparos estruturais antes da vistoria do perito",
        "Contate a assistência 24h da seguradora",
    ],
}


async def run_async(user_phone: str, text: str) -> str:
    """Handle claim registration and guidance."""
    from tools.crm_sheets import create_claim, get_lead
    from tools.notifications import alert_new_claim

    text_lower = text.lower()

    # Identify claim type
    tipo = _identify_claim_type(text_lower)

    # Build response
    response_lines = ["*Sinistro Registrado* ✅\n"]

    try:
        claim = create_claim(
            apolice_id="pendente",
            cliente_id=user_phone,
            tipo=tipo,
            data_ocorrencia="a confirmar",
            descricao=text[:500],
        )
        response_lines.append(f"Protocolo: *{claim.get('id', 'N/A')}*")
        response_lines.append(f"Tipo: {tipo.title()}\n")

        # Send alert to team
        asyncio.create_task(alert_new_claim(user_phone, tipo, text[:200]))

    except Exception as e:
        logger.error(f"Claim creation error: {e}")
        response_lines = ["Recebi sua solicitação de sinistro.\n"]

    # Add orientations
    orientacoes = _get_orientacoes(tipo)
    if orientacoes:
        response_lines.append("*O que fazer agora:*")
        for i, item in enumerate(orientacoes, 1):
            response_lines.append(f"{i}. {item}")

    response_lines.append("\nNossa equipe entrará em contato em até *2 horas* em dias úteis.")
    response_lines.append("Precisa de algo mais urgente? Digite *corretor* para falar com alguém agora.")

    return "\n".join(response_lines)


def run(query: str = None):
    """CLI mode."""
    from rich.console import Console
    console = Console()
    console.print("[bold blue]Agente de Sinistros — InsuranceOS[/bold blue]\n")
    while True:
        text = query or input("Você: ").strip()
        if text.lower() in ("sair", "exit"):
            break
        response = asyncio.run(run_async("cli_user", text))
        console.print(f"[green]Agente:[/green] {response}\n")
        query = None


def _identify_claim_type(text: str) -> str:
    if any(w in text for w in ["baten", "colisão", "colisao", "acidente", "batid"]):
        return "colisao"
    if any(w in text for w in ["roub", "furt", "levaram"]):
        return "roubo"
    if any(w in text for w in ["incêndio", "incendio", "fogo", "queimou"]):
        return "incendio"
    if any(w in text for w in ["casa", "resid", "apto", "apartamento", "imóvel"]):
        return "residencial"
    if any(w in text for w in ["vida", "morte", "falec", "invalidez"]):
        return "vida"
    return "outros"


def _get_orientacoes(tipo: str) -> list:
    return ORIENTACOES.get(tipo, ORIENTACOES.get("residencial", []))
