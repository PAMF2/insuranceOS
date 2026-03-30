"""
InsuranceOS v0.4 — Session Memory
Persiste contexto de conversa por usuário (em memória + JSON dump).
Permite que os agentes "lembrem" o que foi coletado em mensagens anteriores.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("insuranceos.session")

SESSION_DIR = Path("_insuranceos/sessions")
SESSION_TTL_HOURS = 24  # Sessions expire after 24h of inactivity

# In-memory store
_sessions: dict[str, dict] = {}


def _ensure_dir():
    SESSION_DIR.mkdir(parents=True, exist_ok=True)


def _session_path(user_id: str) -> Path:
    safe_id = user_id.replace("+", "").replace(" ", "_")
    return SESSION_DIR / f"{safe_id}.json"


def get_session(user_id: str) -> dict:
    """Get or create session for user."""
    if user_id in _sessions:
        s = _sessions[user_id]
        # Check TTL
        last_active = datetime.fromisoformat(s.get("last_active", datetime.now().isoformat()))
        hours_inactive = (datetime.now() - last_active).total_seconds() / 3600
        if hours_inactive > SESSION_TTL_HOURS:
            _sessions[user_id] = _new_session(user_id)
        return _sessions[user_id]

    # Try loading from disk
    path = _session_path(user_id)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                s = json.load(f)
            # Check TTL
            last_active = datetime.fromisoformat(s.get("last_active", "2000-01-01"))
            hours_inactive = (datetime.now() - last_active).total_seconds() / 3600
            if hours_inactive <= SESSION_TTL_HOURS:
                _sessions[user_id] = s
                return s
        except Exception as e:
            logger.warning(f"Erro ao carregar sessão {user_id}: {e}")

    s = _new_session(user_id)
    _sessions[user_id] = s
    return s


def set_context(user_id: str, key: str, value: Any):
    """Store a piece of context for the user's session."""
    s = get_session(user_id)
    s["context"][key] = value
    s["last_active"] = datetime.now().isoformat()
    _sessions[user_id] = s
    _persist(user_id)


def get_context(user_id: str, key: str, default: Any = None) -> Any:
    """Retrieve a piece of context from the session."""
    s = get_session(user_id)
    return s["context"].get(key, default)


def add_message(user_id: str, role: str, content: str):
    """Add message to session history (last 20 messages)."""
    s = get_session(user_id)
    s["history"].append({
        "role": role,
        "content": content,
        "ts": datetime.now().isoformat(),
    })
    s["history"] = s["history"][-20:]  # Keep last 20
    s["last_active"] = datetime.now().isoformat()
    _sessions[user_id] = s
    _persist(user_id)


def get_history(user_id: str, last_n: int = 10) -> list[dict]:
    """Get recent conversation history."""
    s = get_session(user_id)
    return s["history"][-last_n:]


def get_history_text(user_id: str, last_n: int = 6) -> str:
    """Get history as formatted string for prompt context."""
    history = get_history(user_id, last_n)
    lines = []
    for m in history:
        role = "Cliente" if m["role"] == "user" else "Sofia"
        lines.append(f"{role}: {m['content']}")
    return "\n".join(lines)


def clear_session(user_id: str):
    """Clear session (e.g., user said 'sair' or 'novo atendimento')."""
    _sessions[user_id] = _new_session(user_id)
    path = _session_path(user_id)
    if path.exists():
        path.unlink()


def _new_session(user_id: str) -> dict:
    return {
        "user_id": user_id,
        "created_at": datetime.now().isoformat(),
        "last_active": datetime.now().isoformat(),
        "context": {},   # Collected data (nome, ramo, veiculo, etc.)
        "history": [],   # Message history
        "stage": "greeting",  # Conversation stage
    }


def _persist(user_id: str):
    """Persist session to disk."""
    _ensure_dir()
    path = _session_path(user_id)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(_sessions[user_id], f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Falha ao persistir sessão {user_id}: {e}")
