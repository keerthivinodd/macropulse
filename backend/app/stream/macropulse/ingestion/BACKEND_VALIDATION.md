
# MacroPulse Backend Validation

Run these from `C:\Intelli\Intelli\backend` to validate backend work through Day 4.

## Tests

```powershell
python -m pytest app\stream\macropulse\ingestion\tests\test_day1_connectors.py app\stream\macropulse\ingestion\tests\test_day3.py app\stream\macropulse\ingestion\tests\test_day4.py -q
```

Expect:

- `25 passed`

## Day 4 guardrails

```powershell
@'
import asyncio
from app.stream.macropulse.ingestion.api.guardrails_runtime import validate_sources

async def main():
    source = "RBI Bulletin ? 2026-04-01T09:30:00+05:30"
    print(await validate_sources(
        tenant_id="tenant-test",
        title="Test alert",
        source_citation=source
    ))

asyncio.run(main())
'@ | python -
```

Expect:

- `True`

## Routes

```powershell
@'
from app.main import app
for path in sorted({route.path for route in app.routes if any(x in route.path for x in ["alerts", "hitl", "guardrails"])}):
    print(path)
'@ | python -
```

Expect:

- `/api/alerts/classify`
- `/api/hitl/pending`
- `/api/hitl/{alert_id}/approve`
- `/api/guardrails/violations/{tenant_id}`
- matching `/api/v1/macropulse/...` routes

## Database

```powershell
$env:PGPASSWORD='intelli'
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U intelli -h localhost -d intelli -c "SELECT version_num FROM alembic_version;"
```

Expect:

- `006_macropulse_day4`

```powershell
$env:PGPASSWORD='intelli'
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U intelli -h localhost -d intelli -P pager=off -c "\dt"
```

Expect MacroPulse tables:

- `macro_rates`
- `fx_rates`
- `commodity_prices`
- `news_articles`
- `tenant_profiles`
- `alerts`
- `hitl_queue`
- `guardrail_violations`
