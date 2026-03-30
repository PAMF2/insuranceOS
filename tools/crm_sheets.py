"""
InsuranceOS — CRM via Google Sheets
Sheets: Leads | Clientes | Apolices | Sinistros | Interacoes
"""
import os
import logging
from datetime import datetime
from typing import Optional
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import json

load_dotenv()
logger = logging.getLogger("insuranceos.crm_sheets")

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

SHEET_HEADERS = {
    "Leads": [
        "id", "telefone", "nome", "email", "ramo_interesse",
        "origem", "status", "corretor", "criado_em", "atualizado_em", "observacoes"
    ],
    "Clientes": [
        "id", "telefone", "nome", "cpf_cnpj", "email", "endereco",
        "data_nascimento", "profissao", "criado_em", "atualizado_em"
    ],
    "Apolices": [
        "id", "cliente_id", "seguradora", "ramo", "numero_apolice",
        "inicio_vigencia", "fim_vigencia", "premio_total", "status",
        "criado_em", "atualizado_em"
    ],
    "Sinistros": [
        "id", "apolice_id", "cliente_id", "tipo", "data_ocorrencia",
        "descricao", "status", "valor_estimado", "criado_em", "atualizado_em"
    ],
    "Interacoes": [
        "id", "telefone", "canal", "direcao", "conteudo",
        "intencao", "modulo", "criado_em"
    ],
}


def _get_client():
    creds_file = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE")
    creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON")

    if creds_json:
        info = json.loads(creds_json)
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    elif creds_file:
        creds = Credentials.from_service_account_file(creds_file, scopes=SCOPES)
    else:
        raise ValueError("Credenciais do Google Sheets não configuradas")

    return gspread.authorize(creds)


def _get_sheet(sheet_name: str):
    client = _get_client()
    spreadsheet_id = os.getenv("GOOGLE_SHEETS_ID")
    if not spreadsheet_id:
        raise ValueError("GOOGLE_SHEETS_ID não configurado")

    wb = client.open_by_key(spreadsheet_id)
    try:
        ws = wb.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        ws = wb.add_worksheet(sheet_name, rows=1000, cols=20)
        ws.append_row(SHEET_HEADERS.get(sheet_name, []))
        logger.info(f"Aba '{sheet_name}' criada com cabeçalhos")
    return ws


def _new_id(prefix: str) -> str:
    ts = datetime.now().strftime("%Y%m%d%H%M%S%f")[:17]
    return f"{prefix}_{ts}"


# ── Leads ─────────────────────────────────────────────────────────────────────

def upsert_lead(
    telefone: str,
    nome: str = None,
    email: str = None,
    ramo_interesse: str = None,
    origem: str = "whatsapp",
    status: str = "novo",
    corretor: str = None,
    observacoes: str = None,
) -> dict:
    ws = _get_sheet("Leads")
    now = datetime.now().isoformat()

    # Check if lead exists by phone
    records = ws.get_all_records()
    for i, row in enumerate(records, start=2):
        if str(row.get("telefone")) == str(telefone):
            # Update existing
            updates = {"atualizado_em": now}
            if nome: updates["nome"] = nome
            if email: updates["email"] = email
            if ramo_interesse: updates["ramo_interesse"] = ramo_interesse
            if status: updates["status"] = status
            if corretor: updates["corretor"] = corretor
            if observacoes: updates["observacoes"] = observacoes

            headers = SHEET_HEADERS["Leads"]
            for col, val in updates.items():
                if col in headers:
                    ws.update_cell(i, headers.index(col) + 1, val)

            logger.info(f"Lead atualizado: {telefone}")
            return {**row, **updates}

    # Insert new lead
    lead_id = _new_id("lead")
    row = [
        lead_id, telefone, nome or "", email or "", ramo_interesse or "",
        origem, status, corretor or "", now, now, observacoes or ""
    ]
    ws.append_row(row)
    logger.info(f"Lead criado: {lead_id} — {telefone}")
    return dict(zip(SHEET_HEADERS["Leads"], row))


def get_lead(telefone: str) -> Optional[dict]:
    ws = _get_sheet("Leads")
    records = ws.get_all_records()
    for row in records:
        if str(row.get("telefone")) == str(telefone):
            return row
    return None


# ── Interações ────────────────────────────────────────────────────────────────

def log_interaction(
    telefone: str,
    conteudo: str,
    direcao: str = "inbound",
    canal: str = "whatsapp",
    intencao: str = None,
    modulo: str = None,
) -> dict:
    ws = _get_sheet("Interacoes")
    now = datetime.now().isoformat()
    row_id = _new_id("int")
    row = [row_id, telefone, canal, direcao, conteudo, intencao or "", modulo or "", now]
    ws.append_row(row)
    return dict(zip(SHEET_HEADERS["Interacoes"], row))


# ── Apólices ──────────────────────────────────────────────────────────────────

def create_policy(
    cliente_id: str,
    seguradora: str,
    ramo: str,
    numero_apolice: str,
    inicio_vigencia: str,
    fim_vigencia: str,
    premio_total: float,
    status: str = "ativa",
) -> dict:
    ws = _get_sheet("Apolices")
    now = datetime.now().isoformat()
    policy_id = _new_id("ap")
    row = [
        policy_id, cliente_id, seguradora, ramo, numero_apolice,
        inicio_vigencia, fim_vigencia, str(premio_total), status, now, now
    ]
    ws.append_row(row)
    logger.info(f"Apólice criada: {policy_id}")
    return dict(zip(SHEET_HEADERS["Apolices"], row))


# ── Sinistros ─────────────────────────────────────────────────────────────────

def create_claim(
    apolice_id: str,
    cliente_id: str,
    tipo: str,
    data_ocorrencia: str,
    descricao: str,
    valor_estimado: float = 0.0,
) -> dict:
    ws = _get_sheet("Sinistros")
    now = datetime.now().isoformat()
    claim_id = _new_id("sin")
    row = [
        claim_id, apolice_id, cliente_id, tipo, data_ocorrencia,
        descricao, "aberto", str(valor_estimado), now, now
    ]
    ws.append_row(row)
    logger.info(f"Sinistro criado: {claim_id}")
    return dict(zip(SHEET_HEADERS["Sinistros"], row))
