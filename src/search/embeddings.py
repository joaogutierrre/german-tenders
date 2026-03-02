"""Sentence-transformers wrapper for embedding generation."""

import logging

from sentence_transformers import SentenceTransformer

from src.config import settings
from src.db.repositories import TenderRepository
from src.db.session import get_session

logger = logging.getLogger(__name__)

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    """Get the singleton SentenceTransformer model instance."""
    global _model
    if _model is None:
        logger.info("Loading embedding model: %s", settings.embedding_model)
        _model = SentenceTransformer(settings.embedding_model)
    return _model


def encode_text(text: str) -> list[float]:
    """Encode a single text into a normalized embedding vector."""
    model = get_model()
    return model.encode(text, normalize_embeddings=True).tolist()


def encode_batch(texts: list[str]) -> list[list[float]]:
    """Encode multiple texts into normalized embedding vectors."""
    model = get_model()
    return model.encode(texts, normalize_embeddings=True, batch_size=64).tolist()


async def generate_tender_embeddings(limit: int = 100) -> int:
    """Generate embeddings for tenders that have searchable text but no embedding.

    Returns:
        Number of tenders embedded.
    """
    count = 0

    async with get_session() as session:
        repo = TenderRepository(session)
        tenders = await repo.find_unembedded(limit=limit)

        if not tenders:
            logger.info("No tenders need embeddings")
            return 0

        logger.info("Generating embeddings for %d tenders", len(tenders))

        texts = [t.ai_searchable_text for t in tenders]
        embeddings = encode_batch(texts)

        for tender, embedding in zip(tenders, embeddings):
            await repo.update_embedding(tender.id, embedding)
            count += 1

        await session.commit()

    logger.info("Generated %d embeddings", count)
    return count
