# MacroPulse Connector Configuration

This document summarizes the required environment variables, expected cadence, and fallback behavior for the current MacroPulse connectors.

## RBI

- File: `backend/app/stream/macropulse/ingestion/connectors/rbi.py`
- Required env vars:
  - none for the current official-first path
- Primary source:
  - RBI public website snapshot
- Fallback sources:
  - FRED and World Bank
- Celery cadence:
  - hourly via `fetch_macro_rates_task`
- Notes:
  - Upserts into `macro_rates`
  - Used for repo rate, 10Y G-Sec, CPI, and WPI fallback values

## FX

- File: `backend/app/stream/macropulse/ingestion/connectors/fx.py`
- Required env vars:
  - `ALPHAVANTAGE_API_KEY`
  - `OPEN_EXCHANGE_APP_ID`
- Primary sources:
  - Alpha Vantage
  - Open Exchange Rates
- Fallback:
  - built-in sample row if live requests fail
- Celery cadence:
  - every 5 minutes via `fetch_fx_task`
- Notes:
  - Market-hours helper supports India and GCC windows

## Commodities

- File: `backend/app/stream/macropulse/ingestion/connectors/commodities.py`
- Required env vars:
  - `EIA_API_KEY`
- Primary sources:
  - EIA for Brent/WTI
  - MOSPI press-release page and PDF extraction for WPI
- Fallback:
  - World Bank WPI fallback
- Celery cadence:
  - daily via `fetch_commodities_task`

## News

- File: `backend/app/stream/macropulse/ingestion/connectors/news.py`
- Required env vars:
  - `NEWSDATA_API_KEY`
  - `GNEWS_KEY`
- Primary sources:
  - Newsdata
  - GNews
  - Gulf News RSS
- Fallback:
  - best-effort empty set if no source responds
- Celery cadence:
  - hourly via `fetch_news_task`
  - embeddings every 2 hours via `embed_news_task`

## GCC Central Banks

- File: `backend/app/stream/macropulse/ingestion/connectors/gcc_central_banks.py`
- Required env vars:
  - none mandatory for the current public-source path
- Primary sources:
  - official public SAMA / CBUAE reachable endpoints where available
- Fallback:
  - stable public secondary sources when official pages are challenge-protected
- Celery cadence:
  - daily 08:00 IST via `fetch_sama_task` and `fetch_cbuae_task`

## Regional Statistics

- File: `backend/app/stream/macropulse/ingestion/connectors/regional_stats.py`
- Required env vars:
  - none mandatory
- Sources:
  - GASTAT
  - FCSA
  - IMF
  - World Bank
- Fallback:
  - World Bank proxies when official/statistical endpoints are blocked
- Celery cadence:
  - daily via `fetch_regional_stats_task`

## Shared Runtime Variables

- `POSTGRES_URL`
- `REDIS_URL`
- `INDIA_DB_URL`
- `GCC_DB_URL`
- `OPENAI_API_KEY`
- `PINECONE_API_KEY`
- `ENABLE_BROWSER_FETCH`
- `BROWSER_CHANNEL`
- `BROWSER_HEADLESS`
- `BROWSER_USER_DATA_DIR`
