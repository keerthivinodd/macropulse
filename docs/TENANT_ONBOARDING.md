# MacroPulse Tenant Onboarding

Use this flow when onboarding a new tenant into MacroPulse.

## Step 1: Create the Tenant Profile

Call:

- `POST /api/tenant/profile`

Include the full JSON payload with:

- tenant identity
- primary region and currency
- debt profile
- FX exposure
- COGS profile
- investment portfolio
- logistics profile
- notification configuration

## Step 2: Verify the Sensitivity Matrix

Call:

- `GET /api/tenant/profile/{tenant_id}/sensitivity`

Confirm the response includes:

- `REPO_RATE`
- `FX_USD_INR`
- `CRUDE_OIL`
- `WPI_INFLATION`
- `GSEC_YIELD`

## Step 3: Add Notification Channels

Store or update `notification_config` on the tenant profile with any of:

- `email`
- `teams_webhook`
- `slack_webhook`
- `channels`

Example:

```json
{
  "email": "cfo@company.com",
  "teams_webhook": "https://example.webhook.office.com/...",
  "slack_webhook": "https://hooks.slack.com/services/...",
  "channels": ["email", "teams", "slack"]
}
```

## Step 4: Open the Dashboard

Call:

- `GET /api/macropulse/dashboard/{tenant_id}`

Verify:

- KPI tiles are populated
- top live alerts are visible
- sensitivity matrix is included
- freshness timestamps are present

## Step 5: Validate Alert Routing

Use:

- `POST /api/alerts/classify`

Then verify:

- low-confidence alerts show up in `GET /api/hitl/pending`
- approved alerts move to dispatched
- unsourced alerts are blocked by guardrails

## Step 6: Confirm Residency Routing

For writes, supply the correct request header:

- `X-Write-Region: IN` for India tenants
- `X-Write-Region: UAE` for UAE and Saudi tenants

Cross-region writes are blocked and logged to `residency_violations`.
