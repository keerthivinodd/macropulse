from __future__ import annotations

from app.core.ai_orchestration.tools.registry import tool_registry
from app.core.ai_orchestration.rag.vector_store_contract import get_vector_store
from app.core.data_infra.vector_db import get_embedding_service
from app.stream.macropulse.tool_schemas import MARKET_DOCS_RETRIEVER_SCHEMA


@tool_registry.register(
    name="market_docs_retriever",
    description="Semantic retrieval over macro policy documents, analyst notes, and regional market news",
    parameters_schema=MARKET_DOCS_RETRIEVER_SCHEMA,
)
async def market_docs_retriever(
    query: str,
    region: str | None = None,
    top_k: int = 5,
    collection: str = "macropulse_market_docs",
) -> dict:
    store = get_vector_store()
    embedder = get_embedding_service()
    embedding = (await embedder.embed_texts([query]))[0]

    # Build metadata filter using Keerthi's schema fields
    filter_metadata = None
    if region:
        region_code_map = {"India": "IN", "UAE": "UAE", "Saudi Arabia": "SA", "Global": "GLOBAL"}
        region_code = region_code_map.get(region, region)
        filter_metadata = {"region": region_code}

    results = await store.search(embedding, top_k=top_k, collection=collection, filter_metadata=filter_metadata)
    return {
        "query": query,
        "region": region,
        "collection": collection,
        "matches": [
            {
                "id": result.id,
                "score": round(result.score, 4),
                "content": result.content,
                "metadata": result.metadata,
            }
            for result in results
        ],
        "independent_sources": len({result.metadata.get("source", result.id) for result in results}),
    }
