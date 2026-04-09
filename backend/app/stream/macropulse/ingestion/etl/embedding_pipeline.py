"""
Embedding pipeline — OpenAI embeddings → Pinecone upsert.
"""
import os
from typing import Any

from sqlalchemy import select, update

from app.stream.macropulse.ingestion.db.session import AsyncSessionLocal
from app.stream.macropulse.ingestion.etl.normalize import tag_confidence_tier
from app.stream.macropulse.ingestion.models.news_articles import NewsArticle

PINECONE_INDEX = "macropulse-docs"
EMBED_MODEL = "text-embedding-ada-002"
CHUNK_SIZE = 2000   # ~500 tokens
CHUNK_OVERLAP = 200  # ~50 tokens
BATCH_SIZE = 100


# ---------------------------------------------------------------------------
# Region detection
# ---------------------------------------------------------------------------

def detect_region(tags: list[str]) -> str:
    if "RBI" in tags:
        return "IN"
    if "CBUAE" in tags:
        return "UAE"
    if "SAMA" in tags:
        return "SA"
    return "GLOBAL"


# ---------------------------------------------------------------------------
# Text chunker
# ---------------------------------------------------------------------------

def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks by character count."""
    if len(text) <= size:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start += size - overlap
    return chunks


# ---------------------------------------------------------------------------
# Pinecone + OpenAI clients (lazy init)
# ---------------------------------------------------------------------------

def _get_openai_client():
    import openai
    return openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))


def _get_pinecone_index():
    from pinecone import Pinecone
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY", ""))
    return pc.Index(PINECONE_INDEX)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

async def run_embedding_batch() -> dict[str, Any]:
    """
    1. Fetch unembedded articles (limit 100)
    2. Chunk + embed via OpenAI
    3. Upsert to Pinecone
    4. Mark articles as embedded
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(NewsArticle)
            .where(NewsArticle.embedded == False)  # noqa: E712
            .limit(BATCH_SIZE)
        )
        articles = result.scalars().all()

    if not articles:
        return {"embedded": 0, "vectors": 0}

    openai_client = _get_openai_client()
    pinecone_index = _get_pinecone_index()

    vectors: list[dict] = []
    processed_ids: list[int] = []

    for article in articles:
        chunk_input = f"{article.title}. {article.description or ''}"
        chunks = chunk_text(chunk_input)

        try:
            response = openai_client.embeddings.create(
                model=EMBED_MODEL,
                input=chunks,
            )
        except Exception:
            continue

        tags = article.tags or []
        for chunk_idx, embedding_obj in enumerate(response.data):
            vectors.append({
                "id": f"news_{article.id}_{chunk_idx}",
                "values": embedding_obj.embedding,
                "metadata": {
                    "source": article.source_name or "",
                    "region": detect_region(tags),
                    "date": article.published_at.isoformat() if article.published_at else "",
                    "tags": tags,
                    "confidence_tier": tag_confidence_tier(article.source_name or ""),
                    "url": article.url,
                },
            })
        processed_ids.append(article.id)

    # Upsert to Pinecone in batches of 100
    for i in range(0, len(vectors), BATCH_SIZE):
        pinecone_index.upsert(vectors=vectors[i : i + BATCH_SIZE])

    # Mark as embedded
    if processed_ids:
        async with AsyncSessionLocal() as session:
            await session.execute(
                update(NewsArticle)
                .where(NewsArticle.id.in_(processed_ids))
                .values(embedded=True)
            )
            await session.commit()

    return {"embedded": len(processed_ids), "vectors": len(vectors)}
