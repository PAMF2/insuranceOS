"""
InsuranceOS — Agente de Atendimento (WhatsApp)
Ponto de entrada para todos os clientes. Faz triagem e roteia para os módulos.
"""
import os
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("insuranceos.atendimento")

SYSTEM_PROMPT = """Você é a Sofia, assistente virtual da corretora de seguros.
Você atende clientes pelo WhatsApp com simpatia, clareza e objetividade.

Suas responsabilidades:
- Receber clientes e entender o que precisam
- Coletar informações necessárias para cotações (ramo, dados básicos)
- Informar sobre coberturas, franquias e condições de forma simples
- Registrar sinistros coletando: data, tipo, descrição
- Emitir 2ª via de boleto / consultar vigência de apólice
- Escalar para corretor humano quando necessário

Regras:
- Responda SEMPRE em português brasileiro, de forma amigável mas profissional
- Mensagens curtas e diretas (máximo 3-4 parágrafos por resposta)
- Use emojis com moderação
- Nunca prometa valores exatos sem gerar uma cotação formal
- Se não souber algo, diga "vou verificar com nossa equipe"
- Ao coletar dados sensíveis (CPF, dados bancários), avise que a conversa é segura

Ramos disponíveis: Auto, Vida, Saúde, Residencial, Empresarial
"""


def _build_agent():
    try:
        import google.generativeai as genai
        from google.adk.agents import Agent
        from google.adk.tools import FunctionTool

        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

        # Import tools
        from modules.atendimento.tools import (
            collect_lead_info,
            get_client_info,
            transfer_to_quote,
            transfer_to_claim,
            transfer_to_policy,
            escalate_human,
        )

        agent = Agent(
            model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
            name="sofia_atendimento",
            instruction=SYSTEM_PROMPT,
            tools=[
                FunctionTool(collect_lead_info),
                FunctionTool(get_client_info),
                FunctionTool(transfer_to_quote),
                FunctionTool(transfer_to_claim),
                FunctionTool(transfer_to_policy),
                FunctionTool(escalate_human),
            ],
        )
        return agent
    except ImportError:
        logger.warning("Google ADK não disponível — usando modo fallback")
        return None


# Session memory (in-memory, per process)
_sessions: dict[str, list] = {}

agent = _build_agent()


async def handle_message(user_phone: str, text: str, image_url: str = None, audio_url: str = None):
    """Main entry point called by webhook server."""
    from tools.whatsapp import send_text
    from tools.crm_sheets import log_interaction, upsert_lead
    from orchestrator.orchestrator import classify_intent, route

    # Log interaction
    try:
        log_interaction(user_phone, text or "[mídia]", "inbound", "whatsapp")
        upsert_lead(user_phone, origem="whatsapp")
    except Exception as e:
        logger.error(f"CRM log error: {e}")

    # Classify intent and route
    intent = classify_intent(text or "")
    response = await route(user_phone, text, intent)

    # Send response
    await send_text(user_phone, response)

    # Log outbound
    try:
        log_interaction(user_phone, response, "outbound", "whatsapp", intent, "atendimento")
    except Exception as e:
        logger.error(f"CRM outbound log error: {e}")


async def run_async(user_phone: str, text: str) -> str:
    """Called by orchestrator for general queries."""
    if agent is None:
        return _fallback_response(text)

    # Use ADK agent for response
    try:
        import asyncio
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService

        session_service = InMemorySessionService()
        runner = Runner(agent=agent, app_name="insurance_atendimento", session_service=session_service)

        session_id = f"whatsapp_{user_phone}"
        session = await session_service.get_session(
            app_name="insurance_atendimento", user_id=user_phone, session_id=session_id
        )
        if not session:
            session = await session_service.create_session(
                app_name="insurance_atendimento", user_id=user_phone, session_id=session_id
            )

        from google.genai.types import Content, Part
        content = Content(role="user", parts=[Part(text=text)])

        response_text = ""
        async for event in runner.run_async(
            user_id=user_phone, session_id=session_id, new_message=content
        ):
            if event.is_final_response() and event.content:
                response_text = event.content.parts[0].text
                break

        return response_text or _fallback_response(text)

    except Exception as e:
        logger.error(f"ADK agent error: {e}")
        return _fallback_response(text)


def run(query: str = None):
    """CLI mode — interactive terminal session."""
    import asyncio
    from rich.console import Console

    console = Console()
    console.print("[bold blue]Sofia — Atendimento InsuranceOS[/bold blue]")
    console.print("Digite 'sair' para encerrar\n")

    user_id = "cli_user"

    while True:
        text = input("Você: ").strip()
        if text.lower() in ("sair", "exit", "quit"):
            break

        import asyncio
        response = asyncio.run(run_async(user_id, text))
        console.print(f"[green]Sofia:[/green] {response}\n")


def _fallback_response(text: str) -> str:
    text_lower = (text or "").lower()
    if any(w in text_lower for w in ["cot", "quot", "segur", "preço", "valor"]):
        return (
            "Olá! Posso te ajudar com uma cotação de seguro. "
            "Qual ramo você precisa? Auto, Vida, Saúde, Residencial ou Empresarial?"
        )
    if any(w in text_lower for w in ["sinistro", "acident", "baten"]):
        return (
            "Sinto muito pelo ocorrido. Para registrar seu sinistro, preciso de algumas informações. "
            "Qual foi a data do ocorrido e o que aconteceu?"
        )
    return (
        "Olá! Sou a Sofia, sua assistente de seguros. 😊 "
        "Posso te ajudar com:\n"
        "• Cotação de seguros (Auto, Vida, Saúde, Residencial)\n"
        "• Registro de sinistros\n"
        "• Consulta de apólices\n"
        "• 2ª via de boleto\n\n"
        "Como posso te ajudar hoje?"
    )
