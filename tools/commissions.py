"""
InsuranceOS v0.5 — Comissões
Calcula e rastreia comissões por ramo, corretor e período.
"""
import logging
from datetime import datetime, date
from typing import Optional

logger = logging.getLogger("insuranceos.commissions")

# Default commission rates by ramo (% over premio)
DEFAULT_RATES = {
    "auto":        0.10,
    "vida":        0.20,
    "saude":       0.08,
    "residencial": 0.15,
    "empresarial": 0.12,
    "outros":      0.10,
}


def calcular_comissao(
    premio: float,
    ramo: str,
    taxa_override: Optional[float] = None,
) -> dict:
    """Calculate commission for a single policy."""
    taxa = taxa_override or DEFAULT_RATES.get(ramo.lower(), 0.10)
    comissao = premio * taxa

    return {
        "ramo": ramo,
        "premio": premio,
        "taxa_comissao": taxa,
        "comissao_bruta": round(comissao, 2),
        "ir_retido": round(comissao * 0.115, 2),  # ~11.5% IRPF (simplified)
        "comissao_liquida": round(comissao * 0.885, 2),
    }


async def relatorio_comissoes(periodo_mes: Optional[str] = None) -> dict:
    """Generate commission report from Google Sheets apólices data."""
    try:
        from tools.crm_sheets import _get_sheet

        ws = _get_sheet("Apolices")
        apolices = ws.get_all_records()

        if periodo_mes:
            # Filter by month (formato: YYYY-MM)
            apolices = [
                a for a in apolices
                if str(a.get("criado_em", "")).startswith(periodo_mes)
            ]

        total_premio = 0
        total_comissao = 0
        por_ramo: dict[str, dict] = {}

        for a in apolices:
            premio = float(a.get("premio_total") or 0)
            ramo = a.get("ramo", "outros").lower()

            calc = calcular_comissao(premio, ramo)
            total_premio += premio
            total_comissao += calc["comissao_bruta"]

            if ramo not in por_ramo:
                por_ramo[ramo] = {"apolices": 0, "premio": 0, "comissao": 0}
            por_ramo[ramo]["apolices"] += 1
            por_ramo[ramo]["premio"] += premio
            por_ramo[ramo]["comissao"] += calc["comissao_bruta"]

        return {
            "periodo": periodo_mes or "geral",
            "total_apolices": len(apolices),
            "total_premio": round(total_premio, 2),
            "total_comissao_bruta": round(total_comissao, 2),
            "total_comissao_liquida": round(total_comissao * 0.885, 2),
            "por_ramo": {
                r: {k: round(v, 2) if isinstance(v, float) else v for k, v in d.items()}
                for r, d in por_ramo.items()
            },
        }

    except Exception as e:
        logger.error(f"Comissões report error: {e}")
        return {"erro": str(e)}


def formatar_comissoes_texto(dados: dict) -> str:
    if "erro" in dados:
        return f"Erro ao gerar relatório: {dados['erro']}"

    periodo = dados.get("periodo", "geral")
    lines = [
        f"*Relatório de Comissões* 💰",
        f"_Período: {periodo}_\n",
        f"Apólices: {dados['total_apolices']}",
        f"Prêmios totais: R$ {dados['total_premio']:,.2f}",
        f"Comissão bruta: R$ {dados['total_comissao_bruta']:,.2f}",
        f"Comissão líquida: R$ {dados['total_comissao_liquida']:,.2f}\n",
        "*Por ramo:*",
    ]

    for ramo, d in sorted(dados.get("por_ramo", {}).items(), key=lambda x: -x[1]["comissao"]):
        lines.append(
            f"• {ramo.title()}: {d['apolices']} apólices | "
            f"R$ {d['comissao']:,.2f} comissão"
        )

    return "\n".join(lines)
