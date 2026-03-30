"""
InsuranceOS — Atendimento Tools (ADK FunctionTools)
"""
import logging

logger = logging.getLogger("insuranceos.atendimento.tools")


def collect_lead_info(
    telefone: str,
    nome: str = None,
    email: str = None,
    ramo_interesse: str = None,
    observacoes: str = None,
) -> dict:
    """
    Registra ou atualiza as informações de um lead no CRM.
    Use quando o cliente fornecer nome, email ou interesse em algum ramo de seguro.

    Args:
        telefone: Número de telefone do cliente (com DDD)
        nome: Nome completo do cliente
        email: E-mail do cliente
        ramo_interesse: Ramo de interesse (auto, vida, saúde, residencial, empresarial)
        observacoes: Notas adicionais sobre o cliente ou conversa
    """
    from tools.crm_sheets import upsert_lead
    from tools.notifications import alert_new_lead
    import asyncio

    try:
        lead = upsert_lead(
            telefone=telefone,
            nome=nome,
            email=email,
            ramo_interesse=ramo_interesse,
            observacoes=observacoes,
        )

        if nome or ramo_interesse:
            asyncio.create_task(alert_new_lead(telefone, nome, ramo_interesse))

        return {"status": "success", "lead_id": lead.get("id"), "message": "Lead registrado com sucesso"}
    except Exception as e:
        logger.error(f"collect_lead_info error: {e}")
        return {"status": "error", "message": str(e)}


def get_client_info(telefone: str) -> dict:
    """
    Busca informações do cliente no CRM pelo telefone.

    Args:
        telefone: Número de telefone do cliente
    """
    from tools.crm_sheets import get_lead
    try:
        lead = get_lead(telefone)
        if lead:
            return {"status": "found", "client": lead}
        return {"status": "not_found", "message": "Cliente não cadastrado"}
    except Exception as e:
        logger.error(f"get_client_info error: {e}")
        return {"status": "error", "message": str(e)}


def transfer_to_quote(
    telefone: str,
    ramo: str,
    dados_coletados: str,
) -> dict:
    """
    Transfere o atendimento para o agente de cotação.

    Args:
        telefone: Telefone do cliente
        ramo: Ramo do seguro (auto, vida, saúde, residencial, empresarial)
        dados_coletados: Resumo dos dados já coletados na conversa
    """
    import asyncio
    from modules.quote.agent import run_async

    asyncio.create_task(run_async(telefone, f"cotacao {ramo}: {dados_coletados}"))
    return {
        "status": "transferred",
        "message": f"Transferindo para cotação de seguro {ramo}. Vou buscar as melhores opções para você!"
    }


def transfer_to_claim(
    telefone: str,
    tipo_sinistro: str,
    descricao: str,
    data_ocorrencia: str = None,
) -> dict:
    """
    Abre um sinistro e transfere para o agente de sinistros.

    Args:
        telefone: Telefone do cliente
        tipo_sinistro: Tipo do sinistro (colisão, roubo, incêndio, etc.)
        descricao: Descrição do ocorrido
        data_ocorrencia: Data do ocorrido (formato: DD/MM/AAAA)
    """
    from tools.crm_sheets import create_claim
    from tools.notifications import alert_new_claim
    import asyncio

    try:
        claim = create_claim(
            apolice_id="pendente",
            cliente_id=telefone,
            tipo=tipo_sinistro,
            data_ocorrencia=data_ocorrencia or "não informada",
            descricao=descricao,
        )
        asyncio.create_task(alert_new_claim(telefone, tipo_sinistro, descricao))
        return {
            "status": "success",
            "claim_id": claim.get("id"),
            "message": f"Sinistro registrado! Protocolo: {claim.get('id')}. Nossa equipe entrará em contato em até 24h."
        }
    except Exception as e:
        logger.error(f"transfer_to_claim error: {e}")
        return {"status": "error", "message": str(e)}


def transfer_to_policy(
    telefone: str,
    numero_apolice: str = None,
    tipo_solicitacao: str = "consulta",
) -> dict:
    """
    Transfere para o agente de apólices (2ª via, renovação, consulta).

    Args:
        telefone: Telefone do cliente
        numero_apolice: Número da apólice (se conhecido)
        tipo_solicitacao: Tipo: 'segunda_via', 'renovacao', 'consulta', 'cancelamento'
    """
    return {
        "status": "transferred",
        "tipo": tipo_solicitacao,
        "message": "Vou verificar sua apólice agora. Um momento..."
    }


def escalate_human(
    telefone: str,
    motivo: str,
    urgente: bool = False,
) -> dict:
    """
    Escala o atendimento para um corretor humano via Telegram.

    Args:
        telefone: Telefone do cliente
        motivo: Motivo da escalada
        urgente: Se é urgente (sinistro grave, cliente insatisfeito, etc.)
    """
    from tools.notifications import send_telegram_alert
    import asyncio

    urgencia = "URGENTE 🚨" if urgente else "Normal"
    msg = (
        f"*Escalada {urgencia} — InsuranceOS*\n"
        f"Cliente: {telefone}\n"
        f"Motivo: {motivo}"
    )
    asyncio.create_task(send_telegram_alert(msg))

    if urgente:
        response = "Entendido! Um corretor já foi acionado e entrará em contato em breve. 🚨"
    else:
        response = "Vou conectar você com um de nossos corretores. Retornaremos em breve no horário comercial (8h–18h)."

    return {"status": "escalated", "message": response}
