"""
InsuranceOS v0.2 — Receita Federal (RFB)
Consulta CNPJ via API pública (ReceitaWS / BrasilAPI).
Usado pelo módulo empresarial para qualificar leads e cotar seguros.
"""
import re
import logging
import httpx

logger = logging.getLogger("insuranceos.rfb")

BRASILAPI = "https://brasilapi.com.br/api/cnpj/v1/{cnpj}"
RECEITAWS  = "https://www.receitaws.com.br/v1/cnpj/{cnpj}"


def clean_cnpj(cnpj: str) -> str:
    return re.sub(r"\D", "", cnpj)


async def consultar_cnpj(cnpj: str) -> dict:
    """
    Consulta dados de CNPJ na Receita Federal.
    Retorna: razao_social, nome_fantasia, situacao, atividade (CNAE), porte,
             capital_social, socios, endereco.
    """
    cnpj_clean = clean_cnpj(cnpj)
    if len(cnpj_clean) != 14:
        return {"erro": "CNPJ inválido — deve ter 14 dígitos"}

    # Try BrasilAPI first
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(BRASILAPI.format(cnpj=cnpj_clean))
            if r.status_code == 200:
                data = r.json()
                return _normalizar_brasilapi(data)
    except Exception as e:
        logger.warning(f"BrasilAPI falhou: {e}")

    # Fallback: ReceitaWS
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(RECEITAWS.format(cnpj=cnpj_clean))
            if r.status_code == 200:
                data = r.json()
                return _normalizar_receitaws(data)
    except Exception as e:
        logger.warning(f"ReceitaWS falhou: {e}")

    return {"erro": "Não foi possível consultar o CNPJ. Tente novamente."}


def _normalizar_brasilapi(data: dict) -> dict:
    return {
        "cnpj": data.get("cnpj"),
        "razao_social": data.get("razao_social"),
        "nome_fantasia": data.get("nome_fantasia"),
        "situacao": data.get("descricao_situacao_cadastral"),
        "ativo": data.get("descricao_situacao_cadastral", "").upper() == "ATIVA",
        "atividade_principal": (data.get("cnae_fiscal_descricao") or ""),
        "cnae_codigo": str(data.get("cnae_fiscal", "")),
        "porte": data.get("porte"),
        "capital_social": data.get("capital_social", 0),
        "natureza_juridica": data.get("natureza_juridica"),
        "data_abertura": data.get("data_inicio_atividade"),
        "socios": [
            {"nome": s.get("nome_socio"), "qualificacao": s.get("qualificacao_socio")}
            for s in (data.get("qsa") or [])
        ],
        "endereco": {
            "logradouro": data.get("logradouro"),
            "numero": data.get("numero"),
            "municipio": data.get("municipio"),
            "uf": data.get("uf"),
            "cep": data.get("cep"),
        },
        "fonte": "brasilapi",
    }


def _normalizar_receitaws(data: dict) -> dict:
    return {
        "cnpj": data.get("cnpj"),
        "razao_social": data.get("nome"),
        "nome_fantasia": data.get("fantasia"),
        "situacao": data.get("situacao"),
        "ativo": data.get("situacao", "").upper() == "ATIVA",
        "atividade_principal": (
            data.get("atividade_principal", [{}])[0].get("text", "")
            if data.get("atividade_principal") else ""
        ),
        "cnae_codigo": (
            data.get("atividade_principal", [{}])[0].get("code", "")
            if data.get("atividade_principal") else ""
        ),
        "porte": data.get("porte"),
        "capital_social": float(
            str(data.get("capital_social", "0")).replace(".", "").replace(",", ".") or 0
        ),
        "natureza_juridica": data.get("natureza_juridica"),
        "data_abertura": data.get("abertura"),
        "socios": [
            {"nome": s.get("nome"), "qualificacao": s.get("qual")}
            for s in (data.get("qsa") or [])
        ],
        "endereco": {
            "logradouro": data.get("logradouro"),
            "numero": data.get("numero"),
            "municipio": data.get("municipio"),
            "uf": data.get("uf"),
            "cep": data.get("cep"),
        },
        "fonte": "receitaws",
    }


def formatar_resumo_cnpj(dados: dict) -> str:
    """Formata dados CNPJ para envio via WhatsApp."""
    if "erro" in dados:
        return f"Erro na consulta: {dados['erro']}"

    status = "✅ Ativa" if dados.get("ativo") else "⚠️ Irregular"
    return (
        f"*Consulta CNPJ* 🏢\n\n"
        f"Razão Social: {dados.get('razao_social', 'N/A')}\n"
        f"Nome Fantasia: {dados.get('nome_fantasia') or '—'}\n"
        f"Situação: {status}\n"
        f"Atividade: {dados.get('atividade_principal', 'N/A')}\n"
        f"Porte: {dados.get('porte', 'N/A')}\n"
        f"Capital Social: R$ {float(dados.get('capital_social', 0)):,.2f}\n"
        f"Abertura: {dados.get('data_abertura', 'N/A')}\n"
        f"Cidade: {dados.get('endereco', {}).get('municipio', '')} / {dados.get('endereco', {}).get('uf', '')}"
    )
