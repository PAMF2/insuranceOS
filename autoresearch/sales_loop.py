"""
InsuranceOS v0.4 — AutoResearch: Sales Conversion Loop
Otimiza automaticamente mensagens de follow-up, abordagens de cotação
e scripts de atendimento com base em dados reais de conversão.

Inspirado no invest_loop.py do FAMOS.
"""
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("insuranceos.autoresearch.sales")

OUTPUT_DIR = Path("output/autoresearch")
STRATEGY_FILE = Path("_insuranceos/_memory/sales_strategy.json")


def _ensure_dirs():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _load_strategy() -> dict:
    if STRATEGY_FILE.exists():
        with open(STRATEGY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return _default_strategy()


def _save_strategy(strategy: dict):
    STRATEGY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STRATEGY_FILE, "w", encoding="utf-8") as f:
        json.dump(strategy, f, ensure_ascii=False, indent=2)
    logger.info("Estratégia de vendas atualizada")


def _default_strategy() -> dict:
    return {
        "version": 0,
        "updated_at": datetime.now().isoformat(),
        "follow_up_timing": {
            "primeiro_contato_h": 1,
            "segundo_contato_dias": 3,
            "terceiro_contato_dias": 7,
        },
        "mensagens_teste": {
            "followup_a": "Oi {nome}! Ainda pensando no seguro {ramo}? Posso ajudar com dúvidas 😊",
            "followup_b": "Olá {nome}, sua cotação de {ramo} ainda está válida por {dias_restantes} dias. Quer fechar?",
        },
        "ramo_prioridade": ["auto", "vida", "saude", "residencial", "empresarial"],
        "score_threshold": 0.6,
        "conversion_rates": {},
        "best_hours_to_contact": [9, 10, 14, 15, 16],
        "insights": [],
    }


async def _fetch_conversion_data() -> dict:
    """Fetch real conversion data from Google Sheets."""
    try:
        from tools.crm_sheets import _get_sheet

        leads = _get_sheet("Leads").get_all_records()
        total = len(leads)
        convertidos = sum(1 for l in leads if l.get("status") == "convertido")
        por_ramo = {}

        for lead in leads:
            ramo = lead.get("ramo_interesse", "unknown")
            if ramo not in por_ramo:
                por_ramo[ramo] = {"total": 0, "convertidos": 0}
            por_ramo[ramo]["total"] += 1
            if lead.get("status") == "convertido":
                por_ramo[ramo]["convertidos"] += 1

        rates_by_ramo = {
            ramo: (v["convertidos"] / v["total"] if v["total"] else 0)
            for ramo, v in por_ramo.items()
        }

        return {
            "total_leads": total,
            "total_convertidos": convertidos,
            "taxa_global": convertidos / total if total else 0,
            "por_ramo": rates_by_ramo,
        }

    except Exception as e:
        logger.warning(f"Falha ao buscar dados de conversão: {e}")
        return {"total_leads": 0, "taxa_global": 0, "por_ramo": {}}


async def _generate_insights(dados: dict, strategy: dict) -> list[str]:
    """Use LLM to generate actionable sales insights."""
    from tools.llm import complete

    prompt = (
        f"Analise estes dados de conversão de uma corretora de seguros:\n\n"
        f"Total de leads: {dados.get('total_leads', 0)}\n"
        f"Taxa de conversão global: {dados.get('taxa_global', 0):.1%}\n"
        f"Por ramo: {json.dumps(dados.get('por_ramo', {}), ensure_ascii=False)}\n\n"
        f"Estratégia atual: {json.dumps(strategy.get('follow_up_timing', {}), ensure_ascii=False)}\n\n"
        f"Gere 3-5 insights acionáveis para melhorar a conversão. "
        f"Seja específico com números e ações concretas. Formato: lista com bullet points."
    )

    try:
        response = await complete(prompt, system="Você é um especialista em vendas de seguros.")
        return [line.strip() for line in response.split("\n") if line.strip() and line.strip()[0] in "•-*123456789"]
    except Exception as e:
        logger.error(f"Insights generation error: {e}")
        return []


async def _optimize_messages(dados: dict, strategy: dict) -> dict:
    """Use LLM to optimize follow-up message templates."""
    from tools.llm import complete

    melhor_ramo = max(dados.get("por_ramo", {"auto": 0}), key=lambda k: dados["por_ramo"].get(k, 0))

    prompt = (
        f"O ramo com melhor conversão é '{melhor_ramo}'. "
        f"Taxa de conversão global: {dados.get('taxa_global', 0):.1%}\n\n"
        f"Gere 2 versões otimizadas de mensagem de follow-up para WhatsApp (máx 2 linhas cada), "
        f"focando em urgência e valor. Use {'{nome}'}, {'{ramo}'} e {'{dias_restantes}'} como variáveis."
    )

    try:
        response = await complete(prompt, system="Você é copywriter especialista em vendas de seguros.")
        lines = [l.strip() for l in response.split("\n") if len(l.strip()) > 20]
        return {
            "followup_a": lines[0] if len(lines) > 0 else strategy["mensagens_teste"]["followup_a"],
            "followup_b": lines[1] if len(lines) > 1 else strategy["mensagens_teste"]["followup_b"],
        }
    except Exception as e:
        logger.error(f"Message optimization error: {e}")
        return strategy["mensagens_teste"]


async def run_iteration(iteration: int = 1) -> dict:
    """Run one AutoResearch iteration."""
    logger.info(f"AutoResearch Sales Loop — Iteração {iteration}")
    _ensure_dirs()

    strategy = _load_strategy()
    dados = await _fetch_conversion_data()

    logger.info(f"Dados: {dados['total_leads']} leads, taxa={dados['taxa_global']:.1%}")

    # Generate insights
    insights = await _generate_insights(dados, strategy)
    logger.info(f"Insights gerados: {len(insights)}")

    # Optimize messages if enough data
    if dados["total_leads"] >= 10:
        new_messages = await _optimize_messages(dados, strategy)
        strategy["mensagens_teste"] = new_messages
        logger.info("Mensagens de follow-up otimizadas")

    # Update strategy
    strategy["version"] = iteration
    strategy["updated_at"] = datetime.now().isoformat()
    strategy["conversion_rates"] = dados.get("por_ramo", {})
    strategy["insights"] = insights[-10:]  # Keep last 10 insights

    _save_strategy(strategy)

    # Save iteration report
    report = {
        "iteration": iteration,
        "timestamp": datetime.now().isoformat(),
        "dados": dados,
        "insights": insights,
        "strategy_updated": True,
    }

    report_path = OUTPUT_DIR / f"sales_loop_iter{iteration:03d}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    logger.info(f"Iteração {iteration} concluída. Relatório: {report_path}")
    return report


async def run_loop(n_iterations: int = 5, interval_hours: float = 24):
    """Run N iterations of the sales optimization loop."""
    from rich.console import Console
    console = Console()
    console.print(f"[bold blue]AutoResearch Sales Loop[/bold blue] — {n_iterations} iterações")

    for i in range(1, n_iterations + 1):
        console.print(f"\n[cyan]Iteração {i}/{n_iterations}[/cyan]")
        result = await run_iteration(i)

        console.print(f"  Leads: {result['dados']['total_leads']}")
        console.print(f"  Conversão: {result['dados']['taxa_global']:.1%}")
        console.print(f"  Insights:")
        for ins in result["insights"][:3]:
            console.print(f"    {ins}")

        if i < n_iterations:
            console.print(f"\n  Próxima iteração em {interval_hours}h...")
            await asyncio.sleep(interval_hours * 3600)

    console.print("\n[green]AutoResearch concluído![/green]")


if __name__ == "__main__":
    import sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    asyncio.run(run_loop(n))
