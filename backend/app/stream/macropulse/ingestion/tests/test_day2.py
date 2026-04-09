"""
Day 2 tests — Celery tasks, ETL normalization, news connector, embedding pipeline.
Run: pytest backend/app/stream/macropulse/ingestion/tests/test_day2.py -v
"""
import asyncio
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.stream.macropulse.ingestion.connectors.news import strip_html, tag_entities
from app.stream.macropulse.ingestion.etl.normalize import (
    normalize_currency,
    normalize_timezone,
    normalize_units,
    tag_confidence_tier,
)

IST = timezone(timedelta(hours=5, minutes=30))


# ---------------------------------------------------------------------------
# 1. Celery fx task retries on failure
# ---------------------------------------------------------------------------

def test_celery_fx_task_retries_on_failure():
    from app.stream.macropulse.ingestion.tasks.ingestion_tasks import fetch_fx_task

    retry_count = {"n": 0}

    def fake_retry(exc):
        retry_count["n"] += 1
        if retry_count["n"] >= 3:
            raise fetch_fx_task.MaxRetriesExceededError()
        raise exc

    with patch(
        "app.stream.macropulse.ingestion.connectors.fx.fetch_fx_rates",
        side_effect=RuntimeError("API down"),
    ), patch.object(fetch_fx_task, "retry", side_effect=fake_retry), \
       patch("app.stream.macropulse.ingestion.tasks.ingestion_tasks._push_to_dlq"):
        with pytest.raises((RuntimeError, fetch_fx_task.MaxRetriesExceededError)):
            fetch_fx_task()

    assert retry_count["n"] >= 1


# ---------------------------------------------------------------------------
# 2. DLQ records failure
# ---------------------------------------------------------------------------

def test_dlq_records_failure():
    from app.stream.macropulse.ingestion.tasks.ingestion_tasks import (
        DLQ_KEY,
        _push_to_dlq,
        get_dlq_failures,
    )

    mock_redis = MagicMock()
    pushed: list[str] = []
    mock_redis.rpush = lambda key, val: pushed.append(val)
    mock_redis.lrange = lambda key, start, end: pushed

    with patch(
        "app.stream.macropulse.ingestion.tasks.ingestion_tasks.redis_lib.from_url",
        return_value=mock_redis,
    ):
        _push_to_dlq("fetch_fx_task", "API timeout")
        failures = get_dlq_failures()

    assert len(failures) >= 1
    assert failures[0]["task"] == "fetch_fx_task"
    assert "API timeout" in failures[0]["error"]
    assert "timestamp" in failures[0]


# ---------------------------------------------------------------------------
# 3. normalize_currency USD → INR
# ---------------------------------------------------------------------------

def test_normalize_currency_usd_to_inr():
    fx = {"USD_INR": 83.25, "AED_INR": 22.67, "SAR_INR": 22.20}
    result = normalize_currency(1.0, "USD", "INR", fx)
    assert abs(result - 83.25) < 0.01


# ---------------------------------------------------------------------------
# 4. normalize_units lakh → crore
# ---------------------------------------------------------------------------

def test_normalize_units_lakh_to_crore():
    value, unit = normalize_units(100, "lakh")
    assert abs(value - 1.0) < 0.0001
    assert unit == "Cr"


# ---------------------------------------------------------------------------
# 5. tag_entities RBI
# ---------------------------------------------------------------------------

def test_tag_entities_rbi():
    tags = tag_entities("RBI repo rate hike announced today")
    assert "RBI" in tags
    assert "interest_rate" in tags


# ---------------------------------------------------------------------------
# 6. strip_html
# ---------------------------------------------------------------------------

def test_strip_html():
    result = strip_html("<b>Hello</b> <i>world</i>")
    assert result == "Hello world"


def test_strip_html_entities():
    result = strip_html("Price &amp; Volume &lt;100&gt;")
    assert "&amp;" not in result
    assert "&lt;" not in result


# ---------------------------------------------------------------------------
# 7. Embedding pipeline marks articles as embedded
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_embedding_pipeline_marks_embedded():
    from app.stream.macropulse.ingestion.etl.embedding_pipeline import run_embedding_batch
    from app.stream.macropulse.ingestion.models.news_articles import NewsArticle

    # Mock article
    mock_article = MagicMock(spec=NewsArticle)
    mock_article.id = 1
    mock_article.title = "RBI hikes repo rate by 25bps"
    mock_article.description = "The RBI MPC voted to raise the repo rate."
    mock_article.url = "https://example.com/rbi-hike"
    mock_article.published_at = datetime(2026, 4, 2, tzinfo=timezone.utc)
    mock_article.source_name = "RBI"
    mock_article.tags = ["RBI", "interest_rate"]
    mock_article.embedded = False

    # Mock embedding response
    mock_embedding = MagicMock()
    mock_embedding.embedding = [0.1] * 1536
    mock_openai_resp = MagicMock()
    mock_openai_resp.data = [mock_embedding]

    mock_openai = MagicMock()
    mock_openai.embeddings.create.return_value = mock_openai_resp

    mock_index = MagicMock()
    mock_index.upsert = MagicMock()

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_article]
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()

    with patch(
        "app.stream.macropulse.ingestion.etl.embedding_pipeline.AsyncSessionLocal",
        return_value=mock_session,
    ), patch(
        "app.stream.macropulse.ingestion.etl.embedding_pipeline._get_openai_client",
        return_value=mock_openai,
    ), patch(
        "app.stream.macropulse.ingestion.etl.embedding_pipeline._get_pinecone_index",
        return_value=mock_index,
    ):
        result = await run_embedding_batch()

    assert result["embedded"] == 1
    assert result["vectors"] >= 1
    mock_index.upsert.assert_called_once()
