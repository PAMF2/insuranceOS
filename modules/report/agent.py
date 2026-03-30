"""
InsuranceOS — Agente de Relatórios / Dashboard
KPIs: leads, conversão, prêmios emitidos, sinistralidade.
"""
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger("insuranceos.report")


async def run_async(user_phone: str, text: str) -> str:
    return await generate_dashboard()


async def generate_dashboard() -> str:
    """Generate KPI summary from Google Sheets data."""
    try:
        from tools.crm_sheets import _get_sheet

        # Leads
        leads_ws = _get_sheet("Leads")
        leads = leads_ws.get_all_records()
        total_leads = len(leads)
        novos = sum(1 for l in leads if l.get("status") == "novo")
        qualificados = sum(1 for l in leads if l.get("status") == "qualificado")
        convertidos = sum(1 for l in leads if l.get("status") == "convertido")
        conversao = f"{(convertidos/total_leads*100):.1f}%" if total_leads else "0%"

        # Apólices
        apolices_ws = _get_sheet("Apolices")
        apolices = apolices_ws.get_all_records()
        total_apolices = len(apolices)
        premio_total = sum(float(a.get("premio_total", 0) or 0) for a in apolices)

        # Sinistros
        sinistros_ws = _get_sheet("Sinistros")
        sinistros = sinistros_ws.get_all_records()
        total_sinistros = len(sinistros)
        abertos = sum(1 for s in sinistros if s.get("status") == "aberto")

        return (
            f"*Dashboard InsuranceOS* 📊\n"
            f"_{datetime.now().strftime('%d/%m/%Y %H:%M')}_\n\n"
            f"*Leads*\n"
            f"• Total: {total_leads}\n"
            f"• Novos: {novos} | Qualificados: {qualificados} | Convertidos: {convertidos}\n"
            f"• Taxa de conversão: {conversao}\n\n"
            f"*Apólices*\n"
            f"• Total ativas: {total_apolices}\n"
            f"• Prêmios emitidos: R$ {premio_total:,.2f}\n\n"
            f"*Sinistros*\n"
            f"• Total: {total_sinistros} | Abertos: {abertos}\n"
        )

    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return (
            "*Dashboard InsuranceOS* 📊\n\n"
            "Não foi possível carregar os dados. "
            "Verifique as configurações do Google Sheets."
        )


def run(query: str = None):
    from rich.console import Console
    console = Console()
    console.print("[bold blue]Relatórios — InsuranceOS[/bold blue]\n")
    response = asyncio.run(generate_dashboard())
    console.print(response)
