# MacroPulse API Reference

This document lists the MacroPulse backend routes owned in the Day 1 to Day 5 sprint, with emphasis on the Day 5 handoff surface.

## Dashboard

- `GET /api/macropulse/dashboard/{tenant_id}`
  - Returns KPI tiles, live alerts, sensitivity matrix, and freshness timestamps.

## Tenant Profile

- `POST /api/tenant/profile`
  - Create or upsert a tenant financial profile.
- `GET /api/tenant/profile/{tenant_id}`
  - Retrieve the stored tenant profile.
- `PUT /api/tenant/profile/{tenant_id}`
  - Update the tenant profile and recalculate the sensitivity matrix.
- `DELETE /api/tenant/profile/{tenant_id}`
  - Soft delete the tenant profile.
- `GET /api/tenant/profile/{tenant_id}/sensitivity`
  - Return the cached or freshly calculated sensitivity matrix.

## Alerts

- `POST /api/alerts/classify`
  - Classify agent output into `P1`, `P2`, or `P3`, apply guardrails, store the alert, and route it to dispatch or HITL.
- `GET /api/alerts/{alert_id}`
  - Retrieve a stored alert by ID.

## HITL Queue

- `GET /api/hitl/pending`
  - List all alerts waiting for analyst review.
- `GET /api/hitl/pending/{tenant_id}`
  - List pending analyst-review alerts for a single tenant.
- `POST /api/hitl/{alert_id}/approve`
  - Approve a queued alert and dispatch it.
- `POST /api/hitl/{alert_id}/reject`
  - Reject a queued alert and persist reviewer notes.

## Guardrails

- `GET /api/guardrails/violations/{tenant_id}`
  - Return the audit trail for blocked or malformed alerts.

## Alternate Mounts

The main backend also exposes the tenant, alert, HITL, and guardrail routes under:

- `/api/v1/macropulse/...`

The dashboard route is mounted on the main API path:

- `/api/macropulse/dashboard/{tenant_id}`

## Day 5 Validation Shortcuts

- Run dashboard and residency tests:
  - `python -m pytest app\stream\macropulse\ingestion\tests\test_residency.py app\stream\macropulse\ingestion\tests\test_integration.py -q`
- Inspect generated OpenAPI docs:
  - `http://localhost:8000/docs`
