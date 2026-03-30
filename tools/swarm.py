"""
InsuranceOS v0.3 — Swarm de Agentes
Análise paralela de cotações e cenários por múltiplos sub-agentes.
Inspirado no MiroFish Swarm do FAMOS.
"""
import asyncio
import logging
from typing import Optional

logger = logging.getLogger("insuranceos.swarm")


PERSONAS = [
    {
        "name":  "MaxCobertura",
        "role":  "Defende sempre a cobertura mais completa, independente do preço.",
        "focus": "coberturas máximas, sem franquia reduzida, garantias extras",
    },
    {
        "name":  "BestPriceBot",
        "role":  "Busca o menor prêmio para o cliente, mesmo com menos coberturas.",
        "focus": "menor prêmio mensal, franquia majorada, coberturas essenciais",
    },
    {
        "name":  "RiskAnalyst",
        "role":  "Avalia o risco real do cliente e sugere a cobertura adequada.",
        "focus": "perfil de risco, histórico, frequência de sinistros, zona de uso",
    },
    {
        "name":  "SalesAdvisor",
        "role":  "Foca em conversão — qual opção tem mais chance de fechar?",
        "focus": "gatilhos de decisão, parcelamento, ancoragem de preço",
    },
]


async def _agent_analysis(
    persona: dict,
    cotacoes: list[dict],
    contexto_cliente: str,
) -> dict:
    """Single swarm agent analysis."""
    from tools.llm import complete

    cotacoes_str = "\n".join(
        f"- {c['seguradora']}: R${c['premio_mensal']:.2f}/mês | {c.get('cobertura','')}"
        for c in cotacoes[:5]
    )

    prompt = (
        f"Você é {persona['name']}: {persona['role']}\n"
        f"Foco: {persona['focus']}\n\n"
        f"Contexto do cliente: {contexto_cliente}\n\n"
        f"Cotações disponíveis:\n{cotacoes_str}\n\n"
        f"Qual opção você recomenda e por quê? (máximo 3 linhas)"
    )

    try:
        response = await complete(prompt, system="Você é um consultor de seguros especialista.")
        return {"persona": persona["name"], "recommendation": response.strip()}
    except Exception as e:
        logger.error(f"Swarm agent {persona['name']} error: {e}")
        return {"persona": persona["name"], "recommendation": f"Erro: {e}"}


async def analyze_quotes_swarm(
    cotacoes: list[dict],
    contexto_cliente: str = "cliente padrão, sem informações específicas",
    personas: Optional[list] = None,
) -> dict:
    """
    Run multiple agent personas in parallel to analyze quotes.
    Returns consensus recommendation + individual opinions.
    """
    active_personas = personas or PERSONAS

    logger.info(f"Swarm iniciado: {len(active_personas)} agentes analisando {len(cotacoes)} cotações")

    # Parallel execution
    tasks = [
        _agent_analysis(p, cotacoes, contexto_cliente)
        for p in active_personas
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out exceptions
    opinions = [r for r in results if isinstance(r, dict)]

    # Generate consensus
    consensus = await _build_consensus(cotacoes, opinions, contexto_cliente)

    return {
        "total_agents": len(active_personas),
        "opinions": opinions,
        "consensus": consensus,
        "best_quote": cotacoes[0] if cotacoes else None,
    }


async def _build_consensus(
    cotacoes: list[dict],
    opinions: list[dict],
    contexto_cliente: str,
) -> str:
    from tools.llm import complete

    opinions_str = "\n".join(
        f"- {o['persona']}: {o['recommendation']}"
        for o in opinions
    )

    cotacoes_str = "\n".join(
        f"- {c['seguradora']}: R${c['premio_mensal']:.2f}/mês"
        for c in cotacoes[:3]
    )

    prompt = (
        f"Você é um gerente sênior de seguros. Analise as opiniões dos consultores:\n\n"
        f"{opinions_str}\n\n"
        f"Top 3 cotações:\n{cotacoes_str}\n\n"
        f"Cliente: {contexto_cliente}\n\n"
        f"Dê uma recomendação final clara e objetiva em 2-3 linhas, "
        f"mencionando qual seguradora recomendar e o motivo principal."
    )

    try:
        return await complete(prompt, system="Você é um gerente sênior de seguros com 20 anos de experiência.")
    except Exception as e:
        logger.error(f"Consensus error: {e}")
        return f"Recomendação: {cotacoes[0]['seguradora']} — melhor custo-benefício." if cotacoes else ""


def formatar_swarm_whatsapp(resultado: dict) -> str:
    """Format swarm result for WhatsApp."""
    lines = ["*Análise de Especialistas* 🤖\n"]

    for op in resultado.get("opinions", []):
        lines.append(f"*{op['persona']}:*")
        lines.append(op["recommendation"])
        lines.append("")

    lines.append("*Consenso:*")
    lines.append(resultado.get("consensus", "—"))

    return "\n".join(lines)
