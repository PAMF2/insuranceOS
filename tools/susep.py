"""
InsuranceOS v0.3 — SUSEP Integration
Consulta seguradoras habilitadas, corretores registrados e normas vigentes.
"""
import re
import logging
import httpx

logger = logging.getLogger("insuranceos.susep")

# SUSEP Open Data base URL
SUSEP_BASE = "https://www.susep.gov.br"
OPEN_DATA  = "https://dados.susep.gov.br/api"

# Known regulamentos by ramo
REGULAMENTOS = {
    "auto":        "SUSEP Circular 621/2021",
    "vida":        "SUSEP Resolução CNSP 382/2020",
    "saude":       "ANS RN 465/2021",
    "residencial": "SUSEP Circular 306/2005",
    "empresarial": "SUSEP Circular 457/2012",
}

# Seguradoras top BR (static reference, updated manually)
SEGURADORAS_HABILITADAS = {
    "auto": [
        {"nome": "Porto Seguro",    "susep": "0635-2", "site": "portoseguro.com.br"},
        {"nome": "Tokio Marine",    "susep": "0662-0", "site": "tokiomarine.com.br"},
        {"nome": "Allianz",         "susep": "0633-6", "site": "allianz.com.br"},
        {"nome": "HDI Seguros",     "susep": "0638-7", "site": "hdi.com.br"},
        {"nome": "Bradesco Seguros","susep": "0635-2", "site": "bradescoseguros.com.br"},
        {"nome": "SulAmérica",      "susep": "0620-4", "site": "sulamerica.com.br"},
        {"nome": "Liberty Seguros", "susep": "0615-8", "site": "libertyseguros.com.br"},
        {"nome": "Mapfre",          "susep": "0626-3", "site": "mapfre.com.br"},
    ],
    "vida": [
        {"nome": "MetLife",         "susep": "0610-7", "site": "metlife.com.br"},
        {"nome": "Prudential",      "susep": "0611-5", "site": "prudential.com.br"},
        {"nome": "SulAmérica Vida", "susep": "0620-4", "site": "sulamerica.com.br"},
        {"nome": "Itaú Seguros",    "susep": "0609-3", "site": "itauseguros.com.br"},
    ],
    "residencial": [
        {"nome": "Porto Seguro",    "susep": "0635-2", "site": "portoseguro.com.br"},
        {"nome": "Allianz",         "susep": "0633-6", "site": "allianz.com.br"},
        {"nome": "Liberty",         "susep": "0615-8", "site": "libertyseguros.com.br"},
        {"nome": "Tokio Marine",    "susep": "0662-0", "site": "tokiomarine.com.br"},
    ],
    "empresarial": [
        {"nome": "Zurich",          "susep": "0645-0", "site": "zurich.com.br"},
        {"nome": "Mapfre",          "susep": "0626-3", "site": "mapfre.com.br"},
        {"nome": "Allianz",         "susep": "0633-6", "site": "allianz.com.br"},
        {"nome": "Sompo",           "susep": "0649-3", "site": "sompo.com.br"},
        {"nome": "AIG",             "susep": "0641-7", "site": "aig.com.br"},
    ],
}


async def consultar_seguradora(nome_ou_susep: str) -> dict:
    """Check if a seguradora is registered with SUSEP."""
    nome = nome_ou_susep.lower()
    all_segs = []
    for segs in SEGURADORAS_HABILITADAS.values():
        all_segs.extend(segs)

    for seg in all_segs:
        if (nome in seg["nome"].lower() or
                nome.replace("-", "") in seg["susep"].replace("-", "")):
            return {
                "encontrada": True,
                "nome": seg["nome"],
                "codigo_susep": seg["susep"],
                "site": seg["site"],
                "habilitada": True,
            }

    return {
        "encontrada": False,
        "message": f"'{nome_ou_susep}' não encontrada na base local. Verifique em susep.gov.br",
    }


def listar_seguradoras_por_ramo(ramo: str) -> list[dict]:
    """List authorized seguradoras for a given ramo."""
    ramo_key = ramo.lower().replace("ê", "e").replace("ú", "u")
    return SEGURADORAS_HABILITADAS.get(ramo_key, [])


def get_regulamento(ramo: str) -> str:
    """Return the main regulation for a ramo."""
    return REGULAMENTOS.get(ramo.lower(), "Consulte susep.gov.br para regulamentação específica")


async def check_corretor_habilitado(registro: str) -> dict:
    """
    Verify if a corretor/corretora is registered with SUSEP.
    Uses SUSEP public search (limited, may require CAPTCHA in production).
    Returns mock data structure — integrate with SUSEP portal in production.
    """
    return {
        "registro": registro,
        "status": "verificar_manualmente",
        "url": f"https://www2.susep.gov.br/safe/mainflow.do?cmd=c_pesquisa_corretores_cadastros",
        "message": "Verificação de corretor: acesse o portal SUSEP para consulta oficial.",
    }


def formatar_seguradoras_whatsapp(ramo: str) -> str:
    segs = listar_seguradoras_por_ramo(ramo)
    if not segs:
        return f"Não encontrei seguradoras cadastradas para o ramo {ramo}."

    lines = [f"*Seguradoras SUSEP — {ramo.title()}*\n"]
    for s in segs:
        lines.append(f"• {s['nome']} (SUSEP: {s['codigo_susep']})")

    lines.append(f"\n_Regulamento: {get_regulamento(ramo)}_")
    return "\n".join(lines)
