"""
InsuranceOS — Agente de Compliance
SUSEP, regulatório, auditoria.
"""
import logging
import asyncio

logger = logging.getLogger("insuranceos.compliance")

SUSEP_INFO = {
    "registro_corretor": "https://www2.susep.gov.br/safe/mainflow.do",
    "consulta_seguradora": "https://www2.susep.gov.br/safe/mainflow.do",
    "circular_vigente": "SUSEP Circular 621/2021 — Regulamentação de seguros",
}


async def run_async(user_phone: str, text: str) -> str:
    return (
        "*Compliance & Regulatório* ⚖️\n\n"
        "Módulo de conformidade SUSEP em desenvolvimento.\n\n"
        "Funcionalidades previstas:\n"
        "• Consulta de habilitação de seguradoras\n"
        "• Verificação de corretores habilitados\n"
        "• Monitoramento de circulares SUSEP\n"
        "• Relatórios regulatórios\n"
        "• Auditoria de processos"
    )


def run(query: str = None):
    from rich.console import Console
    console = Console()
    console.print("[bold blue]Compliance — InsuranceOS[/bold blue]\n")
    response = asyncio.run(run_async("cli_user", query or "status"))
    console.print(response)
