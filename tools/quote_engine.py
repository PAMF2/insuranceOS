"""
InsuranceOS — Motor de Cotação
Simula cotações multi-seguradora por ramo.
Em produção: integrar APIs das seguradoras parceiras.
"""
import random
from typing import Optional
from datetime import datetime, date


SEGURADORAS = {
    "auto": ["Porto Seguro", "Tokio Marine", "Allianz", "HDI", "Bradesco Seguros"],
    "vida": ["MetLife", "Prudential", "SulAmérica", "Itaú Seguros", "Porto Seguro"],
    "saude": ["Amil", "SulAmérica", "Bradesco Saúde", "Unimed", "NotreDame Intermédica"],
    "residencial": ["Porto Seguro", "Allianz", "Liberty", "Tokio Marine", "Mapfre"],
    "empresarial": ["Zurich", "Mapfre", "Allianz", "Sompo", "AIG"],
}

FRANQUIAS_AUTO = {
    "obrigatória": 0,
    "reduzida": 0.5,
    "normal": 1.0,
    "majorada": 1.5,
}


def cotar_auto(
    valor_veiculo: float,
    ano: int,
    cep: str,
    perfil_condutor: str = "30-40 anos, casado, garagem",
    cobertura: str = "compreensiva",
    franquia: str = "normal",
) -> list[dict]:
    """Gera cotações simuladas para seguro auto."""
    cotacoes = []
    base_rate = 0.028  # ~2.8% do valor do veículo ao ano

    # Ajustes por perfil simplificados
    age_factor = 1.0
    if "18-25" in perfil_condutor:
        age_factor = 1.4
    elif "25-30" in perfil_condutor:
        age_factor = 1.15
    elif "50+" in perfil_condutor:
        age_factor = 0.9

    ano_atual = datetime.now().year
    age_vehicle = ano_atual - ano
    vehicle_factor = 1.0 + (age_vehicle * 0.02)

    franquia_desconto = FRANQUIAS_AUTO.get(franquia, 1.0) * 0.05

    for seguradora in SEGURADORAS["auto"]:
        variation = random.uniform(-0.15, 0.15)
        rate = base_rate * age_factor * vehicle_factor * (1 + variation)
        premio_anual = valor_veiculo * rate * (1 - franquia_desconto)
        premio_mensal = premio_anual / 12

        cotacoes.append({
            "seguradora": seguradora,
            "ramo": "auto",
            "cobertura": cobertura,
            "franquia": franquia,
            "premio_anual": round(premio_anual, 2),
            "premio_mensal": round(premio_mensal, 2),
            "parcelamento": "12x sem juros no cartão",
            "validade": "7 dias",
            "diferenciais": _diferenciais_auto(seguradora),
        })

    return sorted(cotacoes, key=lambda x: x["premio_anual"])


def cotar_vida(
    idade: int,
    capital_segurado: float,
    fumante: bool = False,
    prazo_anos: int = 20,
) -> list[dict]:
    """Gera cotações simuladas para seguro de vida."""
    cotacoes = []
    base_rate = 0.001  # 0.1% do capital ao ano (base)

    # Ajuste por idade
    if idade < 30:
        age_factor = 0.6
    elif idade < 40:
        age_factor = 1.0
    elif idade < 50:
        age_factor = 1.8
    elif idade < 60:
        age_factor = 3.5
    else:
        age_factor = 6.0

    fumante_factor = 2.0 if fumante else 1.0

    for seguradora in SEGURADORAS["vida"]:
        variation = random.uniform(-0.1, 0.1)
        rate = base_rate * age_factor * fumante_factor * (1 + variation)
        premio_mensal = capital_segurado * rate / 12

        cotacoes.append({
            "seguradora": seguradora,
            "ramo": "vida",
            "capital_segurado": capital_segurado,
            "prazo_anos": prazo_anos,
            "cobertura": "morte + invalidez permanente",
            "premio_mensal": round(premio_mensal, 2),
            "premio_anual": round(premio_mensal * 12, 2),
            "validade": "30 dias",
            "carencia": "30 dias (acidente imediato)",
        })

    return sorted(cotacoes, key=lambda x: x["premio_mensal"])


def cotar_residencial(
    valor_imovel: float,
    tipo: str = "apartamento",
    cep: str = "",
) -> list[dict]:
    """Gera cotações para seguro residencial."""
    cotacoes = []
    base_rate = 0.0015  # 0.15% ao ano

    tipo_factor = 1.0
    if tipo == "casa":
        tipo_factor = 1.2
    elif tipo == "comercial":
        tipo_factor = 1.5

    for seguradora in SEGURADORAS["residencial"]:
        variation = random.uniform(-0.1, 0.1)
        rate = base_rate * tipo_factor * (1 + variation)
        premio_anual = valor_imovel * rate
        premio_mensal = premio_anual / 12

        cotacoes.append({
            "seguradora": seguradora,
            "ramo": "residencial",
            "tipo_imovel": tipo,
            "valor_imovel": valor_imovel,
            "coberturas": ["Incêndio", "Roubo", "Danos elétricos", "Vendaval", "Assistência 24h"],
            "premio_anual": round(premio_anual, 2),
            "premio_mensal": round(premio_mensal, 2),
            "validade": "15 dias",
        })

    return sorted(cotacoes, key=lambda x: x["premio_anual"])


def _diferenciais_auto(seguradora: str) -> list[str]:
    diferenciais = {
        "Porto Seguro": ["Carro reserva 30 dias", "Assistência 24h", "App Porto Seguro"],
        "Tokio Marine": ["Proteção de vidros", "Carro reserva 15 dias", "Rastreador incluso"],
        "Allianz": ["Cobertura continental", "Assistência premium", "Desconto na franquia"],
        "HDI": ["Melhor custo-benefício", "Cobertura para acessórios", "Pagamento mensal"],
        "Bradesco Seguros": ["Integração Bradesco", "Desconto cliente correntista", "App mobile"],
    }
    return diferenciais.get(seguradora, ["Assistência 24h"])


def formatar_cotacao_whatsapp(cotacoes: list[dict], top_n: int = 3) -> str:
    """Formata cotações para envio via WhatsApp."""
    if not cotacoes:
        return "Não foi possível gerar cotações no momento."

    ramo = cotacoes[0].get("ramo", "seguro").upper()
    lines = [f"*Cotações — {ramo}*\n"]

    for i, c in enumerate(cotacoes[:top_n], 1):
        lines.append(f"*{i}. {c['seguradora']}*")
        lines.append(f"   Mensal: R$ {c['premio_mensal']:.2f}")
        lines.append(f"   Anual: R$ {c['premio_anual']:.2f}")
        if "cobertura" in c:
            lines.append(f"   Cobertura: {c['cobertura']}")
        lines.append("")

    lines.append("_Válido por 7 dias. Valores aproximados, sujeitos a vistoria._")
    lines.append("\nDeseja contratar ou tirar dúvidas? Responda aqui!")
    return "\n".join(lines)
