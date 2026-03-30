# InsuranceOS

**Insurance Operating System — Operado por Inteligência Artificial**

InsuranceOS é uma plataforma de seguros 100% operada por agentes de IA — integrando atendimento via WhatsApp, cotação automatizada, gestão de apólices, sinistros e pipeline de vendas.

> **Missão:** Transformar corretoras e seguradoras com IA autônoma, reduzindo CAC e aumentando conversão.

---

## Arquitetura

```
insuranceOS/
├── insuranceos.py                    ← Entry point (menu interativo + CLI)
├── server.py                         ← Webhook WhatsApp (FastAPI)
│
├── orchestrator/
│   └── orchestrator.py               ← Orquestrador central + roteamento de agentes
│
├── modules/                          ← 8 módulos especializados
│   ├── quote/      agent.py          ← Cotação: auto, vida, saúde, residencial, empresarial
│   ├── policy/     agent.py          ← Apólices: emissão, renovação, vigência, endosso
│   ├── claim/      agent.py          ← Sinistros: registro, acompanhamento, regulação
│   ├── crm/        agent.py          ← Clientes: leads, histórico, segmentação
│   ├── sales/      agent.py          ← Vendas: pipeline, comissões, metas, follow-up
│   ├── compliance/ agent.py          ← SUSEP, regulatório, auditoria
│   ├── report/     agent.py          ← Dashboard, relatórios, KPIs
│   └── atendimento/agent.py          ← Bot WhatsApp: triagem, FAQ, humanização
│
├── tools/
│   ├── whatsapp.py                   ← Meta Cloud API / Twilio (envio/recebimento)
│   ├── susep.py                      ← API SUSEP: seguradoras, produtos, habilitação
│   ├── quote_engine.py               ← Motor de cotação multi-seguradora
│   ├── notifications.py              ← Telegram + WhatsApp (alertas internos)
│   ├── crm_sheets.py                 ← Google Sheets: leads, clientes, apólices
│   ├── pdf_tools.py                  ← Geração de propostas e apólices em PDF
│   └── rag.py                        ← RAG sobre manuais de produtos e regulamentos
│
├── autoresearch/
│   └── sales_loop.py                 ← AutoResearch: otimização de conversão
│
└── _insuranceos/
    ├── _memory/
    │   ├── company_profile.md        ← Perfil da corretora (configure aqui)
    │   └── products.json             ← Catálogo de produtos e seguradoras parceiras
    └── documentos/                   ← RAG: manuais, condições gerais, tabelas
```

---

## Módulos

| Módulo | Função | Status |
|--------|--------|--------|
| **Quote** | Cotação multi-ramo: auto, vida, saúde, residencial, empresarial | 🔨 v0.1 |
| **Policy** | Emissão, renovação, endosso, cancelamento de apólices | 🔨 v0.1 |
| **Claim** | Registro e acompanhamento de sinistros | 🔨 v0.1 |
| **CRM** | Gestão de leads, clientes, histórico e segmentação | 🔨 v0.1 |
| **Sales** | Pipeline, follow-up automático, comissões, metas | 🔨 v0.1 |
| **Compliance** | Conformidade SUSEP, auditoria, relatórios regulatórios | 🔨 v0.1 |
| **Report** | Dashboard KPIs: conversão, prêmios, sinistralidade | 🔨 v0.1 |
| **Atendimento** | Bot WhatsApp: triagem, cotação rápida, FAQ, escalada humana | 🔨 v0.1 |

---

## Stack Tecnológico

- **LLM**: Google Gemini (via ADK) ou multi-LLM (OpenAI, Anthropic, Ollama)
- **Framework de Agentes**: Google ADK (Python)
- **Mensageria**: WhatsApp (Meta Cloud API) + Telegram
- **Storage**: Google Sheets + SQLite (local) / PostgreSQL (produção)
- **PDF**: ReportLab / WeasyPrint
- **API SUSEP**: dados de seguradoras e produtos
- **Infra**: Docker + docker-compose (1 container por módulo)

---

## Configuração Rápida

```bash
cp .env.example .env
# Edite o .env com suas credenciais

pip install -r requirements.txt

python insuranceos.py
```

---

## Variáveis de Ambiente

```env
# LLM
GOOGLE_API_KEY=
GEMINI_MODEL=gemini-2.0-flash

# WhatsApp (Meta Cloud API)
WHATSAPP_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_VERIFY_TOKEN=

# Google Sheets (CRM)
GOOGLE_SHEETS_ID=
GOOGLE_SHEETS_CREDENTIALS_FILE=credentials.json

# Telegram (alertas internos)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Segurança
WEBHOOK_TOKEN=

# Servidor
PORT=8080
```

---

## Fluxo de Atendimento (WhatsApp)

```
Cliente envia mensagem
        ↓
   Webhook recebe
        ↓
 Atendimento/Agent
   (triagem NLP)
        ↓
┌───────┼───────────┬──────────────┐
│       │           │              │
Cotação  Sinistro  2ª via boleto  Falar com corretor
│       │           │              │
Quote   Claim     Policy        Escalada humana
Agent   Agent     Agent         (Telegram alert)
│       │           │
└───────┴───────────┘
        ↓
 Resposta WhatsApp
  + CRM atualizado
```
