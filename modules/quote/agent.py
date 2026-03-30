"""
InsuranceOS — Agente de Cotação
Gera cotações multi-ramo e multi-seguradora.
"""
import os
import re
import logging
import asyncio
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("insuranceos.quote")

SYSTEM_PROMPT = """Você é o agente de cotação da InsuranceOS.
Sua função é coletar os dados necessários e gerar cotações precisas.

Fluxo por ramo:

AUTO: Precisa de: valor do veículo, ano/modelo, CEP do segurado, perfil do condutor principal (idade, estado civil, garagem)
VIDA: Precisa de: idade, capital segurado desejado, fumante (sim/não), prazo
SAÚDE: Precisa de: número de vidas, faixa etária, tipo de cobertura (ambulatorial, hospitalar, completo)
RESIDENCIAL: Precisa de: valor do imóvel, tipo (casa/apto), CEP
EMPRESARIAL: Precisa de: CNPJ/atividade, faturamento anual, tipo de cobertura

Instruções:
- Colete os dados de forma conversacional, um grupo por vez
- Ao ter todos os dados, gere a cotação e formate de forma clara
- Apresente as 3 melhores opções comparando preço e cobertura
- Ofereça enviar a proposta por e-mail ou PDF
- Sempre pergunte se o cliente quer fechar ou tem dúvidas
"""


async def run_async(user_phone: str, text: str) -> str:
    """Generate quote based on collected data."""
    from tools.quote_engine import (
        cotar_auto, cotar_vida, cotar_residencial, formatar_cotacao_whatsapp
    )
    from tools.crm_sheets import upsert_lead

    text_lower = text.lower()

    # Determine ramo
    ramo = _extract_ramo(text_lower)

    if not ramo:
        return (
            "Para gerar sua cotação, qual ramo de seguro você precisa?\n\n"
            "• *Auto* — para seu veículo\n"
            "• *Vida* — proteção para você e sua família\n"
            "• *Saúde* — plano de saúde\n"
            "• *Residencial* — sua casa ou apartamento\n"
            "• *Empresarial* — para seu negócio"
        )

    # Update lead with interest
    try:
        upsert_lead(user_phone, ramo_interesse=ramo, status="cotando")
    except Exception as e:
        logger.error(f"CRM update error: {e}")

    # Generate quote based on ramo
    try:
        if ramo == "auto":
            # Extract or use defaults for demo
            valor = _extract_valor(text) or 50000.0
            ano = _extract_ano(text) or 2020
            cotacoes = cotar_auto(valor_veiculo=valor, ano=ano, cep="01310-100")
            return formatar_cotacao_whatsapp(cotacoes)

        elif ramo == "vida":
            idade = _extract_idade(text) or 35
            capital = _extract_valor(text) or 300000.0
            cotacoes = cotar_vida(idade=idade, capital_segurado=capital)
            return formatar_cotacao_whatsapp(cotacoes)

        elif ramo == "residencial":
            valor = _extract_valor(text) or 400000.0
            cotacoes = cotar_residencial(valor_imovel=valor)
            return formatar_cotacao_whatsapp(cotacoes)

        elif ramo == "saude":
            return (
                "Para cotar plano de saúde, preciso saber:\n"
                "1. Quantas pessoas serão incluídas?\n"
                "2. Quais as idades?\n"
                "3. Prefere cobertura só hospitalar ou ambulatorial + hospitalar?"
            )

        elif ramo == "empresarial":
            return (
                "Para seguro empresarial, me informe:\n"
                "1. Qual o ramo de atividade da empresa?\n"
                "2. Qual o faturamento anual aproximado?\n"
                "3. Quais coberturas precisa? (incêndio, responsabilidade civil, equipamentos, etc.)"
            )

    except Exception as e:
        logger.error(f"Quote generation error: {e}")
        return "Tive um problema ao gerar a cotação. Pode repetir os dados? 🙏"

    return "Em que posso te ajudar com sua cotação?"


def run(query: str = None):
    """CLI mode."""
    from rich.console import Console
    console = Console()
    console.print("[bold blue]Agente de Cotação — InsuranceOS[/bold blue]\n")
    while True:
        text = query or input("Você: ").strip()
        if text.lower() in ("sair", "exit"):
            break
        response = asyncio.run(run_async("cli_user", text))
        console.print(f"[green]Agente:[/green] {response}\n")
        query = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_ramo(text: str) -> str:
    if re.search(r"(auto|carro|veículo|moto)", text):
        return "auto"
    if re.search(r"(vida|morte|invalidez|família)", text):
        return "vida"
    if re.search(r"(saúde|plano de saúde|médico|amil|unimed)", text):
        return "saude"
    if re.search(r"(resid|casa|apto|apartamento|imóvel)", text):
        return "residencial"
    if re.search(r"(empresa|negócio|comercial|cnpj)", text):
        return "empresarial"
    return None


def _extract_valor(text: str) -> float:
    match = re.search(r"r?\$?\s*([\d\.]+(?:,\d{2})?)", text)
    if match:
        val = match.group(1).replace(".", "").replace(",", ".")
        try:
            return float(val)
        except ValueError:
            pass
    return None


def _extract_ano(text: str) -> int:
    match = re.search(r"\b(19|20)\d{2}\b", text)
    if match:
        return int(match.group(0))
    return None


def _extract_idade(text: str) -> int:
    match = re.search(r"\b(\d{2})\s*anos?\b", text)
    if match:
        return int(match.group(1))
    return None
