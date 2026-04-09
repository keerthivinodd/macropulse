"""
MacroPulse — Pinecone index validation and seed document ingestion.
Run once at startup or via CLI to ensure macropulse_market_docs collection
is ready with real embedding-backed documents.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from app.core.ai_orchestration.rag.vector_store_contract import VectorDocument, get_vector_store
from app.core.data_infra.vector_db import get_embedding_service

logger = logging.getLogger(__name__)

COLLECTION = "macropulse_market_docs"

# Seed corpus — representative macro policy docs for retrieval quality
SEED_DOCUMENTS = [
    {
        "id": "rbi-mpc-2024-oct",
        "content": (
            "RBI Monetary Policy Committee October 2024: The MPC voted 5-1 to keep the repo rate "
            "unchanged at 6.50%. CPI inflation is projected at 4.5% for FY25. The committee noted "
            "elevated food prices and global commodity volatility as key risks."
        ),
        "metadata": {"source": "RBI", "region": "India", "category": "central_bank_policy", "date": "2024-10-09"},
    },
    {
        "id": "sama-monetary-2024-q3",
        "content": (
            "SAMA Monetary Policy Q3 2024: Saudi Arabia maintained its repo rate at 6.00% in line "
            "with the US Federal Reserve. Non-oil GDP growth is forecast at 3.8%. FX reserves remain "
            "robust at $450B. Inflation is contained at 1.7% YoY."
        ),
        "metadata": {"source": "SAMA", "region": "Saudi Arabia", "category": "central_bank_policy", "date": "2024-09-20"},
    },
    {
        "id": "cbuae-policy-2024-q3",
        "content": (
            "CBUAE Policy Statement Q3 2024: The Central Bank of UAE held its base rate at 5.40%. "
            "UAE CPI rose 2.3% YoY driven by housing and transport costs. Credit growth to the private "
            "sector expanded 8.2% YoY. The dirham peg to USD remains stable."
        ),
        "metadata": {"source": "CBUAE", "region": "UAE", "category": "central_bank_policy", "date": "2024-09-18"},
    },
    {
        "id": "fed-fomc-2024-sep",
        "content": (
            "US Federal Reserve FOMC September 2024: The Fed cut rates by 50bps to 4.75-5.00%, "
            "the first cut since 2020. Core PCE inflation at 2.6%. Labor market shows gradual cooling. "
            "Dot plot signals two more cuts in 2024."
        ),
        "metadata": {"source": "Federal Reserve", "region": "Global", "category": "central_bank_policy", "date": "2024-09-18"},
    },
    {
        "id": "brent-crude-outlook-2024",
        "content": (
            "Brent Crude Outlook Q4 2024: OPEC+ extended production cuts of 2.2M bpd through December. "
            "Brent is trading at $84/barrel. EIA forecasts average $85/barrel for Q4. "
            "Every $5/barrel increase in Brent correlates to a 0.8% rise in logistics costs for "
            "manufacturing firms with petroleum-linked supply chains."
        ),
        "metadata": {"source": "EIA", "region": "Global", "category": "commodity_prices", "date": "2024-10-01"},
    },
    {
        "id": "gcc-inflation-2024",
        "content": (
            "GCC Inflation Report 2024: Average core inflation across GCC states is running at 2.1%, "
            "0.3% above Q3 baseline. CBUAE and SAMA data show commodity pricing variance of 1.2%. "
            "Food inflation remains the primary driver at 3.4% YoY across the region."
        ),
        "metadata": {"source": "IMF", "region": "UAE", "category": "inflation_statistics", "date": "2024-10-05"},
    },
    {
        "id": "usd-inr-fx-2024",
        "content": (
            "USD/INR FX Analysis October 2024: The Indian rupee is trading at 83.8 against the USD, "
            "near its all-time low. RBI has been intervening to prevent sharp depreciation. "
            "A 1% depreciation in INR increases import costs by approximately Rs. 540 Cr for a "
            "company with $12M USD exposure and 45% hedge ratio."
        ),
        "metadata": {"source": "RBI", "region": "India", "category": "fx_market_data", "date": "2024-10-10"},
    },
    {
        "id": "india-cpi-sep-2024",
        "content": (
            "India CPI September 2024: Headline CPI rose to 5.49% YoY, above the RBI's 4% target. "
            "Food inflation surged to 9.24% driven by vegetable prices. Core CPI (ex-food and fuel) "
            "remained stable at 3.5%. The RBI is unlikely to cut rates before Q1 FY26."
        ),
        "metadata": {"source": "MOSPI", "region": "India", "category": "inflation_statistics", "date": "2024-10-14"},
    },
]


async def validate_and_seed_index() -> dict:
    """
    Validate the macropulse_market_docs collection exists and has documents.
    Seeds with representative macro documents if empty.
    Returns a status report.
    """
    store = get_vector_store()
    embedder = get_embedding_service()

    # Health check
    healthy = await store.health_check()
    if not healthy:
        logger.error("Vector store health check failed — cannot seed macropulse index")
        return {"status": "error", "message": "Vector store unreachable"}

    # Ensure collection exists
    try:
        await store.create_collection(COLLECTION, dimension=embedder.dimension)
    except Exception as e:
        logger.warning("Collection creation skipped (may already exist): %s", e)

    # Check if already seeded
    existing = await store.get([SEED_DOCUMENTS[0]["id"]], collection=COLLECTION)
    if existing:
        logger.info("macropulse_market_docs already seeded (%d seed docs)", len(SEED_DOCUMENTS))
        return {"status": "already_seeded", "collection": COLLECTION, "seed_count": len(SEED_DOCUMENTS)}

    # Embed and upsert seed documents
    texts = [doc["content"] for doc in SEED_DOCUMENTS]
    embeddings = await embedder.embed_texts(texts)

    docs = [
        VectorDocument(
            id=seed["id"],
            content=seed["content"],
            embedding=embeddings[i],
            metadata={**seed["metadata"], "seeded_at": datetime.now(UTC).isoformat()},
            collection=COLLECTION,
        )
        for i, seed in enumerate(SEED_DOCUMENTS)
    ]

    count = await store.upsert(docs, collection=COLLECTION)
    logger.info("Seeded %d documents into macropulse_market_docs", count)

    return {
        "status": "seeded",
        "collection": COLLECTION,
        "documents_upserted": count,
        "embedding_dim": embedder.dimension,
        "seeded_at": datetime.now(UTC).isoformat(),
    }


async def validate_retrieval_quality(query: str = "RBI repo rate inflation India") -> dict:
    """
    Run a test query against the collection and return top results with scores.
    Use this to verify embedding-backed retrieval is working correctly.
    """
    store = get_vector_store()
    embedder = get_embedding_service()

    embedding = await embedder.embed_query(query)
    results = await store.search(
        query_embedding=embedding,
        collection=COLLECTION,
        top_k=3,
    )

    return {
        "query": query,
        "top_results": [
            {
                "id": r.id,
                "score": round(r.score, 4),
                "source": r.metadata.get("source"),
                "region": r.metadata.get("region"),
                "preview": r.content[:120],
            }
            for r in results
        ],
        "retrieval_ok": len(results) > 0 and results[0].score > 0.3,
    }
