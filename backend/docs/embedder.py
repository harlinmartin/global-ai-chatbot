"""
Embedding service — wraps sentence-transformers bge-small.
Interface: embed_texts(texts) -> list[list[float]]

The model and its heavy dependency (sentence_transformers / PyTorch) are
loaded lazily on the first call, not at import time. This keeps startup fast
and makes the module mockable in tests without triggering an ~11-second
PyTorch import.

Swapping to a hosted embedding API (e.g. OpenAI text-embedding-3-small)
later is a single-file change to this module.
"""

from __future__ import annotations
import asyncio
from config import settings

_model = None


def _get_model():
    """Lazy-load the sentence-transformer model on first call."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer  # heavy import
        _model = SentenceTransformer(settings.embedding_model)
    return _model


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Embed a list of text strings and return a list of float vectors.
    Runs the CPU-bound encode in a thread pool so it doesn't block the event loop.
    """
    loop = asyncio.get_event_loop()
    embeddings = await loop.run_in_executor(
        None,
        lambda: _get_model().encode(texts, normalize_embeddings=True).tolist()
    )
    return embeddings
