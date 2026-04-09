# MacroPulse

**Real-time macroeconomic intelligence platform for CFOs and finance teams.**

MacroPulse ingests central bank policy signals, FX markets, commodity prices, and inflation data to deliver AI-powered financial impact analysis. It monitors macro conditions, simulates stress scenarios, and provides natural language queries to quantify how macro shocks affect company P&L.

---

## Features

- **Real-Time Macro Monitoring** — Live ingestion from RBI policy rates, FX markets, WPI inflation, Brent crude across India, UAE, and Saudi Arabia
- **Scenario Simulation** — Model historical shocks (2008 crisis, COVID, oil crash) or custom scenarios to stress-test margins and quantify P&L exposure
- **AI Agent** — Natural language CFO assistant that answers macro questions, runs simulations, and generates financial briefs with confidence scoring
- **CFO Weekly Brief** — Deterministic pipeline generating macro environment, central bank watch, FX & currency risk, commodity & energy, and P&L sensitivity sections
- **Dashboard & Analytics** — KPI tiles, live alerts (P1/P2/P3), sensitivity matrix, and source freshness indicators
- **Human-in-the-Loop** — Low-confidence outputs auto-route to analyst review queue
- **Cost-Optimized AI** — LiteLLM integration for model selection based on query complexity with budget tracking

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | FastAPI, Python 3.10+, SQLAlchemy (async), PostgreSQL, Redis, Celery |
| **AI/LLM** | OpenAI GPT-4o, Pinecone (vector search), LiteLLM (cost routing) |
| **Frontend** | Next.js, React, TypeScript, Tailwind CSS |
| **Ingestion** | httpx (async), Playwright (browser), pdfplumber, BeautifulSoup, feedparser |
| **Infra** | Docker Compose, Alembic (migrations), Novu (notifications) |

---

## Data Sources

| Category | Source | Region |
|----------|--------|--------|
| Central Bank Policy | RBI API, ECB FX Feed | India, Global |
| FX Markets | AlphaVantage, OpenExchangeRates | IN, UAE, SA |
| Commodity Prices | EIA API (Brent Crude, WTI) | Global |
| Inflation | BLS CPI, MOSPI WPI, World Bank | US, India |
| News Signals | Newsdata.io, GNews, Gulf News RSS | Global |
| Treasury Yields | U.S. Treasury Data Center | US |

---

## Project Structure

```
backend/app/stream/macropulse/
├── router.py              # API endpoints
├── service.py             # Realtime snapshot logic
├── agent.py               # AI agent configuration
├── schemas.py             # Pydantic models
├── cfo_brief.py           # Weekly brief generation
├── cfo_brief_pipeline.py  # End-to-end brief pipeline
├── nl_query.py            # Natural language query parsing
├── auth_api.py            # User auth & tenant login
├── tenant_profile_api.py  # Company macro profile CRUD
├── anomaly.py             # Anomaly detection
├── confidence.py          # Confidence scoring
├── cost_routing.py        # LiteLLM cost optimization
├── event_publisher.py     # Pub/sub event system
├── ingestion/
│   ├── connectors/        # Data source connectors
│   │   ├── commodities.py # EIA Brent, MOSPI WPI
│   │   ├── fx.py          # AlphaVantage, OpenExchangeRates
│   │   ├── news.py        # Newsdata, GNews, RSS feeds
│   │   ├── gcc_central_banks.py
│   │   ├── rbi.py         # Reserve Bank of India
│   │   └── regional_stats.py
│   ├── etl/               # Transform & embed pipelines
│   ├── models/            # SQLAlchemy ORM models
│   ├── schemas/           # Request/response schemas
│   ├── tasks/             # Celery async tasks
│   ├── api/               # Ingestion API routes
│   │   ├── alert_engine.py
│   │   ├── guardrails.py
│   │   └── routes/
│   └── ops/               # Docker, env config
└── tools/                 # Agent tools
    ├── anomaly_detector.py
    ├── kpi_sql_tool.py
    ├── market_docs_retriever.py
    ├── scenario_sim_tool.py
    ├── time_series_tool.py
    └── report_export_tool.py

frontend/src/
├── app/stream/macropulse/
│   ├── page.tsx           # Main dashboard
│   ├── layout.tsx         # App layout
│   ├── agent/             # AI chat interface
│   ├── cfo-brief/         # Weekly brief viewer
│   ├── config/            # Tenant configuration
│   ├── datasources/       # Data source management
│   ├── financial/         # Financial impact analysis
│   ├── overview/          # Macro overview
│   ├── realtime/          # Live data feeds
│   ├── regional/          # Regional analysis
│   ├── risk/              # Risk dashboard
│   └── simulation/        # Scenario simulation
├── components/stream/macropulse/
│   ├── MacroPulseLayout.tsx
│   ├── MacroPulseSidebar.tsx
│   ├── ChatHistorySidebar.tsx
│   └── simulation/        # Simulation UI components
├── services/macropulse/   # API client services
├── hooks/macropulse/      # React hooks
├── types/macropulse/      # TypeScript types
├── lib/macropulse/        # Tenant store
└── utils/macropulse/      # Formatting utilities
```

---

## API Endpoints

**Base:** `/api/v1/macropulse`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/realtime` | Snapshot of live macro indicators |
| GET | `/sources` | Source catalog and metadata |
| POST | `/agent/query` | Natural language macro query |
| GET | `/dashboard/{tenant_id}` | Dashboard tiles, alerts, sensitivity matrix |
| POST | `/nl-query` | Parse natural language intent |
| POST | `/cfo-brief` | Generate weekly CFO brief |
| POST | `/cfo-brief/pipeline` | Run full brief pipeline |
| GET | `/cost-routing/status` | LiteLLM budget status |
| GET | `/metrics` | Latency and confidence metrics |
| GET | `/events/schemas` | Pub/sub event schemas |

**Auth:** `/api/v1/macropulse/auth`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/register` | User registration with tenant key |
| POST | `/login` | User authentication |
| GET | `/me` | Current user details |

**Tenant:** `/api/v1/macropulse/tenant`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/profile/{tenant_id}` | Create tenant profile |
| GET | `/profile/{tenant_id}` | Get tenant profile |
| PUT | `/profile/{tenant_id}` | Update tenant profile |
| GET | `/profile/{tenant_id}/sensitivity` | Get sensitivity matrix |

---

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL 15+
- Redis

### Environment Variables

Copy `.env.example` and configure:

```bash
cp backend/app/stream/macropulse/ingestion/ops/.env.example .env
```

| Variable | Description |
|----------|-------------|
| `POSTGRES_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `OPENAI_API_KEY` | OpenAI API key (GPT-4o) |
| `PINECONE_API_KEY` | Pinecone vector DB key |
| `ALPHAVANTAGE_API_KEY` | FX data provider |
| `OPEN_EXCHANGE_APP_ID` | OpenExchangeRates app ID |
| `EIA_API_KEY` | Energy Information Administration |
| `NEWSDATA_API_KEY` | Newsdata.io key |
| `GNEWS_KEY` | GNews API key |

### Run with Docker

```bash
cd backend/app/stream/macropulse/ingestion/ops
docker compose up -d
```

### Run Backend

```bash
cd backend
pip install -r app/stream/macropulse/ingestion/ops/requirements.txt
uvicorn app.main:app --reload
```

### Run Frontend

```bash
cd frontend
npm install
npm run dev
```

### Database Migrations

```bash
cd backend
alembic upgrade head
```

---

## Architecture

- **Multi-tenant** — Isolated profiles per tenant with region-specific currency, central bank sources, and macro variables
- **Confidence-driven** — Agent outputs below 85% threshold auto-route to HITL queue for analyst review
- **Fallback resilience** — Cached snapshots and sample data when external APIs are unavailable
- **Event-driven** — Realtime hub publishes snapshot updates via pub/sub event schemas
- **Deterministic pipelines** — CFO brief uses chained runnables for reproducible outputs

---

## Testing

```bash
cd backend
pytest tests/test_macropulse_api.py
pytest tests/stream/macropulse/
pytest app/stream/macropulse/ingestion/tests/
```

---

## License

Proprietary — Fidelis Technologies
