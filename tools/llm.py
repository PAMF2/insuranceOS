"""
InsuranceOS v0.2 — Multi-LLM Provider
Suporta: Anthropic (Claude), OpenAI, Google Gemini, Ollama local.
"""
import os
import logging
from typing import Optional

logger = logging.getLogger("insuranceos.llm")

PROVIDER = os.getenv("INSURANCEOS_LLM_PROVIDER", "gemini")

MODELS = {
    "anthropic": os.getenv("ANTHROPIC_MODEL", "claude-opus-4-6"),
    "openai":    os.getenv("OPENAI_MODEL",    "gpt-4o"),
    "gemini":    os.getenv("GEMINI_MODEL",     "gemini-2.0-flash"),
    "ollama":    os.getenv("OLLAMA_MODEL",     "llama3.2"),
}


def get_provider() -> str:
    return os.getenv("INSURANCEOS_LLM_PROVIDER", PROVIDER)


async def complete(
    prompt: str,
    system: str = "",
    provider: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 1024,
) -> str:
    """Unified LLM call across providers."""
    p = (provider or get_provider()).lower()

    if p == "anthropic":
        return await _anthropic(prompt, system, temperature, max_tokens)
    elif p == "openai":
        return await _openai(prompt, system, temperature, max_tokens)
    elif p == "gemini":
        return await _gemini(prompt, system, temperature, max_tokens)
    elif p == "ollama":
        return await _ollama(prompt, system, temperature, max_tokens)
    else:
        logger.warning(f"Provider '{p}' desconhecido, usando gemini")
        return await _gemini(prompt, system, temperature, max_tokens)


async def _anthropic(prompt: str, system: str, temperature: float, max_tokens: int) -> str:
    import anthropic
    client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    msg = await client.messages.create(
        model=MODELS["anthropic"],
        max_tokens=max_tokens,
        temperature=temperature,
        system=system or "Você é um assistente especialista em seguros.",
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


async def _openai(prompt: str, system: str, temperature: float, max_tokens: int) -> str:
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    resp = await client.chat.completions.create(
        model=MODELS["openai"],
        temperature=temperature,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system or "Você é um assistente especialista em seguros."},
            {"role": "user", "content": prompt},
        ],
    )
    return resp.choices[0].message.content


async def _gemini(prompt: str, system: str, temperature: float, max_tokens: int) -> str:
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    model = genai.GenerativeModel(
        model_name=MODELS["gemini"],
        system_instruction=system or "Você é um assistente especialista em seguros.",
        generation_config=genai.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        ),
    )
    resp = await model.generate_content_async(prompt)
    return resp.text


async def _ollama(prompt: str, system: str, temperature: float, max_tokens: int) -> str:
    import httpx
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    payload = {
        "model": MODELS["ollama"],
        "prompt": f"{system}\n\n{prompt}" if system else prompt,
        "stream": False,
        "options": {"temperature": temperature, "num_predict": max_tokens},
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(f"{base}/api/generate", json=payload)
        r.raise_for_status()
        return r.json()["response"]
