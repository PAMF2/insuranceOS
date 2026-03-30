# InsuranceOS

**Insurance Operating System — Operado por Inteligência Artificial**

InsuranceOS é uma plataforma de seguros 100% operada por agentes de IA — integrando atendimento via WhatsApp, cotação automatizada, gestão de apólices, sinistros e pipeline de vendas.

> **Missão:** Transformar corretoras e seguradoras com IA autônoma, reduzindo CAC e aumentando conversão.

---

## Arquitetura (v0.5)

```
insuranceOS/
├── insuranceos.py                    ← Entry point (menu interativo + CLI)
├── server.py                         ← Webhook WhatsApp (FastAPI)
├── pico_monitor.py                   ← PicoClaw: renovações + follow-up + health
│
├── orchestrator/
│   └── orchestrator.py               ← Orquestrador central + multi-LLM + session
│
├── modules/                          ← 8 módulos especializados
│   ├── quote/      agent.py          ← Cotação: auto, vida, saúde, residencial, empresarial
│   ├── policy/     agent.py          ← Apólices: emissão, renovação, vigência, endosso
│   ├── claim/      agent.py          ← Sinistros: registro, acompanhamento, orientações
│   ├── crm/        agent.py          ← Clientes: leads, histórico, segmentação
│   ├── sales/      agent.py          ← Vendas: pipeline, follow-up automático, metas
│   ├── compliance/ agent.py          ← SUSEP, regulatório, auditoria
│   ├── report/     agent.py          ← Dashboard HTML + KPIs + relatório PDF
│   └── atendimento/agent.py          ← Sofia: bot WhatsApp com session memory
│
├── tools/
│   ├── whatsapp.py                   ← Meta Cloud API (texto, botões, listas, docs)
│   ├── susep.py                      ← SUSEP: seguradoras habilitadas, regulamentos (v0.3)
│   ├── rfb.py                        ← Receita Federal: CNPJ via BrasilAPI/ReceitaWS (v0.2)
│   ├── quote_engine.py               ← Motor de cotação multi-seguradora
│   ├── notifications.py              ← Telegram + WhatsApp (alertas internos)
│   ├── crm_sheets.py                 ← Google Sheets: leads, clientes, apólices, sinistros
│   ├── pdf_tools.py                  ← Propostas e relatórios em PDF (v0.3)
│   ├── rag.py                        ← RAG: condições gerais, manuais, circulares (v0.3)
│   ├── swarm.py                      ← Swarm de agentes para análise de cotações (v0.3)
│   ├── session.py                    ← Session memory por usuário (v0.4)
│   ├── llm.py                        ← Multi-LLM: Gemini, Claude, GPT-4o, Ollama (v0.2)
│   ├── ensemble.py                   ← Multi-LLM ensemble para decisões críticas (v0.5)
│   └── commissions.py                ← Calculadora e relatório de comissões (v0.5)
│
├── autoresearch/
│   └── sales_loop.py                 ← AutoResearch: otimização de conversão (v0.4)
│
└── _insuranceos/
    ├── _memory/
    │   ├── company_profile.md        ← Perfil da corretora (configure aqui)
    │   ├── products.json             ← Catálogo de produtos e seguradoras
    │   └── sales_strategy.json       ← Estratégia otimizada pelo AutoResearch
    ├── sessions/                     ← Session memory por usuário (v0.4)
    └── documentos/                   ← RAG: manuais, condições gerais, tabelas (v0.3)
```

---

## Módulos & Versões

| Módulo / Feature | Função | Status |
|------------------|--------|--------|
| **Atendimento** (Sofia) | Bot WhatsApp: triagem, FAQ, cotação rápida | ✅ v0.1 |
| **Quote** | Cotação multi-ramo e multi-seguradora | ✅ v0.1 |
| **Claim** | Sinistros: registro, protocolo, orientações | ✅ v0.1 |
| **Policy** | Apólices: 2ª via, renovação, endosso | ✅ v0.1 |
| **Sales** | Pipeline, follow-up, conversão | ✅ v0.1 |
| **CRM** | Leads e clientes via Google Sheets | ✅ v0.1 |
| **Compliance** | SUSEP, regulatório, auditoria | ✅ v0.1 |
| **Report** | KPIs em texto e dashboard HTML | ✅ v0.1 |
| **Multi-LLM** | Gemini, Claude, GPT-4o, Ollama | ✅ v0.2 |
| **RFB / CNPJ** | Consulta CNPJ via BrasilAPI | ✅ v0.2 |
| **PicoClaw Monitor** | Renovações + leads frios + health check | ✅ v0.2 |
| **SUSEP Tool** | Seguradoras habilitadas por ramo | ✅ v0.3 |
| **RAG Documentos** | Busca em condições gerais e manuais | ✅ v0.3 |
| **PDF Propostas** | Propostas e relatórios em PDF | ✅ v0.3 |
| **Swarm Análise** | Multi-agente paralelo para cotações | ✅ v0.3 |
| **Session Memory** | Contexto de conversa persistido por usuário | ✅ v0.4 |
| **Dashboard HTML** | Dashboard executivo com gráficos | ✅ v0.4 |
| **AutoResearch** | Sales loop: otimização de conversão por IA | ✅ v0.4 |
| **Ensemble LLM** | Multi-LLM consensus para decisões críticas | ✅ v0.5 |
| **Comissões** | Calculadora e relatório de comissões | ✅ v0.5 |
| **LLM Orchestration** | Roteamento com fallback LLM para intenções ambíguas | ✅ v0.5 |

---

## Provedores de LLM

Configure no `.env`:

```env
# Provedor padrão
INSURANCEOS_LLM_PROVIDER=gemini  # gemini | anthropic | openai | ollama

# Chaves (configure apenas o(s) que usar)
GOOGLE_API_KEY=...           # Gemini 2.0 Flash (padrão, mais rápido)
ANTHROPIC_API_KEY=...        # Claude Opus 4.6 (melhor raciocínio)
OPENAI_API_KEY=...           # GPT-4o (alternativa)
OLLAMA_BASE_URL=http://localhost:11434  # Ollama local (offline)
```

| Provedor | Modelo padrão | Ponto forte | Ideal para |
|----------|--------------|-------------|------------|
| **Gemini** | gemini-2.0-flash | Rápido, multimodal, gratuito | Atendimento, cotação |
| **Anthropic** | claude-opus-4-6 | Raciocínio, instrução longa | Sinistros complexos, compliance |
| **OpenAI** | gpt-4o | Coding, estruturado | AutoResearch, análises |
| **Ollama** | llama3.2 | Offline, privado | Dados sensíveis, local |

---

## Fluxo de Atendimento (WhatsApp)

```
Cliente envia mensagem
        ↓
   Webhook (FastAPI)
        ↓
 Session Memory carrega histórico
        ↓
 Orquestrador (regex + LLM fallback)
   classifica intenção
        ↓
┌───────┬──────────┬───────────┬──────────────┬─────┐
│       │          │           │              │     │
Cotação Sinistro  Apólice    Vendas        CNPJ  RAG
│       │          │           │
Quote   Claim    Policy     Sales
Agent   Agent    Agent      Agent
│       │
Swarm  Telegram
(v0.3)  alert
│
Ensemble
(v0.5)
        ↓
 Resposta WhatsApp
  + CRM atualizado
  + Session salva
```

---

## Setup Rápido

```bash
git clone https://github.com/PAMF2/insuranceOS
cd insuranceOS

pip install -r requirements.txt

cp .env.example .env
# Edite o .env com suas credenciais

# 1. Configure a corretora
nano _insuranceos/_memory/company_profile.md

# 2. Inicie o webhook
python insuranceos.py --server

# 3. (Opcional) PicoClaw Monitor em paralelo
python pico_monitor.py

# 4. (Opcional) AutoResearch sales loop
python autoresearch/sales_loop.py 5
```

---

## Docker

```bash
docker-compose up -d
```

---

## Comandos CLI

```bash
python insuranceos.py                  # Menu interativo
python insuranceos.py quote "auto"     # Cotação direta
python insuranceos.py report html      # Gerar dashboard HTML
python insuranceos.py --server         # Iniciar webhook WhatsApp
python pico_monitor.py                 # Monitor de renovações + follow-up
python autoresearch/sales_loop.py 5    # 5 iterações de otimização
```
