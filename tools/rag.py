"""
InsuranceOS v0.3 — RAG (Retrieval-Augmented Generation)
Busca semântica em documentos de seguros:
- Condições Gerais de apólices
- Manuais de produtos
- Tabelas de coberturas
- Circulares SUSEP

Coloque PDFs/DOCX/TXT em: _insuranceos/documentos/
"""
import os
import hashlib
import logging
import json
from pathlib import Path
from typing import Optional

logger = logging.getLogger("insuranceos.rag")

DOCS_DIR  = Path("_insuranceos/documentos")
INDEX_DIR = Path("_insuranceos/.rag_index")

# Simple in-memory chunk store (upgrade to ChromaDB/FAISS in production)
_index: list[dict] = []
_index_loaded = False


def _ensure_dirs():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_DIR.mkdir(parents=True, exist_ok=True)


def _file_hash(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def _chunk_text(text: str, chunk_size: int = 600, overlap: int = 100) -> list[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def _extract_text(path: Path) -> str:
    """Extract text from PDF, DOCX or TXT."""
    suffix = path.suffix.lower()

    if suffix == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore")

    elif suffix == ".pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(str(path))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except ImportError:
            logger.warning("pypdf não instalado — instale com: pip install pypdf")
            return ""

    elif suffix in (".docx", ".doc"):
        try:
            import docx
            doc = docx.Document(str(path))
            return "\n".join(p.text for p in doc.paragraphs)
        except ImportError:
            logger.warning("python-docx não instalado — instale com: pip install python-docx")
            return ""

    return ""


def build_index(force: bool = False):
    """Index all documents in _insuranceos/documentos/."""
    global _index, _index_loaded
    _ensure_dirs()

    index_file = INDEX_DIR / "chunks.json"

    if not force and index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            _index = json.load(f)
        _index_loaded = True
        logger.info(f"RAG: {len(_index)} chunks carregados do índice")
        return

    _index = []
    docs = list(DOCS_DIR.glob("**/*"))
    docs = [d for d in docs if d.is_file() and d.suffix.lower() in (".pdf", ".docx", ".txt")]

    logger.info(f"RAG: indexando {len(docs)} documentos...")

    for doc_path in docs:
        try:
            text = _extract_text(doc_path)
            if not text.strip():
                continue

            chunks = _chunk_text(text)
            for i, chunk in enumerate(chunks):
                _index.append({
                    "doc": doc_path.name,
                    "chunk_id": i,
                    "text": chunk,
                    "hash": _file_hash(doc_path),
                })

            logger.info(f"  {doc_path.name}: {len(chunks)} chunks")
        except Exception as e:
            logger.error(f"Erro ao indexar {doc_path}: {e}")

    with open(index_file, "w", encoding="utf-8") as f:
        json.dump(_index, f, ensure_ascii=False)

    _index_loaded = True
    logger.info(f"RAG: índice construído com {len(_index)} chunks")


def search(query: str, top_k: int = 5) -> list[dict]:
    """
    Simple keyword search over indexed chunks.
    In production: replace with embedding-based vector search (ChromaDB, FAISS, etc.)
    """
    global _index_loaded
    if not _index_loaded:
        build_index()

    if not _index:
        return []

    query_words = set(query.lower().split())

    scored = []
    for chunk in _index:
        text_lower = chunk["text"].lower()
        score = sum(1 for w in query_words if w in text_lower)
        if score > 0:
            scored.append((score, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:top_k]]


async def query_with_llm(question: str, top_k: int = 5) -> str:
    """RAG: retrieve chunks + generate answer with LLM."""
    chunks = search(question, top_k=top_k)

    if not chunks:
        return (
            "Não encontrei documentos relevantes na base de conhecimento. "
            "Adicione documentos em _insuranceos/documentos/ e reindexe."
        )

    context = "\n\n---\n\n".join(
        f"[{c['doc']}, trecho {c['chunk_id']}]\n{c['text']}"
        for c in chunks
    )

    prompt = (
        f"Com base nos seguintes trechos de documentos de seguros:\n\n"
        f"{context}\n\n"
        f"Responda a pergunta: {question}\n\n"
        f"Se a informação não estiver nos documentos, diga que não encontrou."
    )

    from tools.llm import complete
    return await complete(prompt, system="Você é especialista em seguros e condições contratuais.")


def get_status() -> dict:
    global _index
    return {
        "total_chunks": len(_index),
        "documentos": list({c["doc"] for c in _index}),
        "docs_dir": str(DOCS_DIR.absolute()),
    }
