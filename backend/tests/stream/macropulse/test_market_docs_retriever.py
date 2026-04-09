"""
Tests for market_docs_retriever — Day 1 Pranisree task.
Validates embedding-backed retrieval quality against the in-memory store.
"""
from __future__ import annotations

import pytest

from app.core.ai_orchestration.rag.vector_store_contract import (
    InMemoryVectorStore,
    VectorDocument,
    set_vector_store,
)
from app.core.data_infra.vector_db import EmbeddingService


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def use_in_memory_store():
    """Always use in-memory store for tests — no Pinecone needed."""
    store = InMemoryVectorStore()
    set_vector_store(store)
    return store


@pytest.fixture
def embedder():
    return EmbeddingService(model_name="all-MiniLM-L6-v2")


@pytest.fixture
async def seeded_store(use_in_memory_store, embedder):
    """Seed the in-memory store with representative macro docs."""
    docs_text = [
        "RBI repo rate held at 6.50% in October 2024. CPI inflation at 4.5%.",
        "SAMA monetary policy: Saudi Arabia repo rate 6.00%. Non-oil GDP growth 3.8%.",
        "CBUAE base rate 5.40%. UAE CPI rose 2.3% YoY. Dirham peg to USD stable.",
        "Brent crude at $84/barrel. OPEC+ extended production cuts through December.",
        "USD/INR at 83.8. RBI intervening to prevent sharp rupee depreciation.",
    ]
    embeddings = await embedder.embed_texts(docs_text)
    docs = [
        VectorDocument(
            id=f"seed-{i}",
            content=text,
            embedding=embeddings[i],
            metadata={"source": ["RBI", "SAMA", "CBUAE", "EIA", "RBI"][i], "region": ["India", "Saudi Arabia", "UAE", "Global", "India"][i]},
            collection="macropulse_market_docs",
        )
        for i, text in enumerate(docs_text)
    ]
    await use_in_memory_store.upsert(docs, collection="macropulse_market_docs")
    return use_in_memory_store


# ── Tests ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_retriever_returns_results(seeded_store, embedder):
    """market_docs_retriever should return results for a valid macro query."""
    from app.stream.macropulse.tools.market_docs_retriever import market_docs_retriever

    result = await market_docs_retriever(query="RBI repo rate India inflation")

    assert result["query"] == "RBI repo rate India inflation"
    assert len(result["matches"]) > 0


@pytest.mark.asyncio
async def test_retriever_top_k_respected(seeded_store, embedder):
    """top_k parameter should limit the number of results."""
    from app.stream.macropulse.tools.market_docs_retriever import market_docs_retriever

    result = await market_docs_retriever(query="central bank policy", top_k=2)

    assert len(result["matches"]) <= 2


@pytest.mark.asyncio
async def test_retriever_scores_present(seeded_store, embedder):
    """Each match should have a similarity score."""
    from app.stream.macropulse.tools.market_docs_retriever import market_docs_retriever

    result = await market_docs_retriever(query="Brent crude oil OPEC commodity")

    for match in result["matches"]:
        assert "score" in match
        assert 0.0 <= match["score"] <= 1.0


@pytest.mark.asyncio
async def test_retriever_relevant_result_ranks_first(seeded_store, embedder):
    """The most semantically relevant doc should rank highest."""
    from app.stream.macropulse.tools.market_docs_retriever import market_docs_retriever

    result = await market_docs_retriever(query="Brent crude oil barrel OPEC production")

    assert len(result["matches"]) > 0
    top = result["matches"][0]
    assert "crude" in top["content"].lower() or "brent" in top["content"].lower() or "opec" in top["content"].lower()


@pytest.mark.asyncio
async def test_retriever_independent_sources_count(seeded_store, embedder):
    """independent_sources should count unique source metadata values."""
    from app.stream.macropulse.tools.market_docs_retriever import market_docs_retriever

    result = await market_docs_retriever(query="inflation rate central bank", top_k=5)

    assert "independent_sources" in result
    assert result["independent_sources"] >= 1


@pytest.mark.asyncio
async def test_retriever_empty_collection_returns_empty():
    """Querying an empty collection should return empty matches gracefully."""
    from app.stream.macropulse.tools.market_docs_retriever import market_docs_retriever

    result = await market_docs_retriever(
        query="anything",
        collection="nonexistent_collection",
    )

    assert result["matches"] == []
