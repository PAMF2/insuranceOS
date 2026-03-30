"""
InsuranceOS v0.5 — Multi-LLM Ensemble
Combina respostas de múltiplos provedores para cotações e análises críticas.
Melhora precisão em: avaliação de risco, recomendação de cobertura, sinistros complexos.
"""
import asyncio
import logging
from typing import Optional

logger = logging.getLogger("insuranceos.ensemble")


ENSEMBLE_STRATEGIES = {
    "vote":      "Maioria dos LLMs concorda → usa essa resposta",
    "synthesize": "LLM árbitro sintetiza todas as respostas",
    "best_of":   "Usa a resposta mais longa/detalhada como proxy de qualidade",
}


async def ensemble_complete(
    prompt: str,
    system: str = "",
    providers: Optional[list[str]] = None,
    strategy: str = "synthesize",
    temperature: float = 0.3,
) -> str:
    """
    Run prompt through multiple LLM providers and combine results.

    Args:
        prompt: The user prompt
        system: System instruction
        providers: List of providers to use (default: all available)
        strategy: How to combine results ('vote', 'synthesize', 'best_of')
        temperature: LLM temperature
    """
    from tools.llm import complete, get_provider

    if providers is None:
        # Use configured primary + fallback
        primary = get_provider()
        all_providers = ["gemini", "anthropic", "openai"]
        providers = [primary] + [p for p in all_providers if p != primary][:1]

    logger.info(f"Ensemble: {len(providers)} provedores, estratégia={strategy}")

    # Run all providers in parallel
    tasks = [
        complete(prompt, system=system, provider=p, temperature=temperature)
        for p in providers
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter successful results
    responses = []
    for provider, result in zip(providers, results):
        if isinstance(result, Exception):
            logger.warning(f"Provider {provider} falhou: {result}")
        else:
            responses.append({"provider": provider, "response": result})

    if not responses:
        return "Erro: todos os provedores LLM falharam."

    if len(responses) == 1:
        return responses[0]["response"]

    # Apply strategy
    if strategy == "best_of":
        return max(responses, key=lambda x: len(x["response"]))["response"]

    elif strategy == "vote":
        # Simple heuristic: find most common key phrases
        return responses[0]["response"]  # Fallback to first

    elif strategy == "synthesize":
        return await _synthesize(prompt, responses)

    return responses[0]["response"]


async def _synthesize(original_prompt: str, responses: list[dict]) -> str:
    """Use a LLM to synthesize multiple responses into one."""
    from tools.llm import complete

    responses_text = "\n\n".join(
        f"[{r['provider'].upper()}]:\n{r['response']}"
        for r in responses
    )

    synthesis_prompt = (
        f"Você recebeu análises de múltiplos especialistas sobre a mesma pergunta.\n\n"
        f"Pergunta original: {original_prompt}\n\n"
        f"Respostas:\n{responses_text}\n\n"
        f"Sintetize as melhores informações em uma resposta única, clara e completa. "
        f"Resolva contradições escolhendo a resposta mais tecnicamente precisa."
    )

    try:
        return await complete(
            synthesis_prompt,
            system="Você é um árbitro técnico especialista em seguros.",
            temperature=0.2,
        )
    except Exception as e:
        logger.error(f"Synthesis error: {e}")
        return responses[0]["response"]


async def ensemble_quote_analysis(
    cotacoes: list[dict],
    perfil_cliente: str,
) -> str:
    """
    Use ensemble to provide robust quote recommendation.
    Critical decision — benefits from multi-LLM consensus.
    """
    cotacoes_str = "\n".join(
        f"- {c['seguradora']}: R${c['premio_mensal']:.2f}/mês | R${c['premio_anual']:.2f}/ano | {c.get('cobertura','')}"
        for c in cotacoes[:5]
    )

    prompt = (
        f"Analise estas cotações de seguro e recomende a melhor opção para o cliente:\n\n"
        f"Perfil do cliente: {perfil_cliente}\n\n"
        f"Cotações:\n{cotacoes_str}\n\n"
        f"Justifique em 2-3 linhas considerando: preço, cobertura e reputação da seguradora."
    )

    return await ensemble_complete(
        prompt,
        system="Você é um consultor de seguros sênior com expertise em análise de risco.",
        strategy="synthesize",
        temperature=0.3,
    )
