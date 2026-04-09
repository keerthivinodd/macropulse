from __future__ import annotations

import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Any

import httpx
from jinja2 import Environment, FileSystemLoader, select_autoescape

try:
    from novu import NovuConfig  # noqa: F401
except ImportError:  # pragma: no cover - optional dependency in local/container dev
    NovuConfig = None  # type: ignore[assignment]

from app.stream.macropulse.ingestion.models.alerts import Alert

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates"
JINJA_ENV = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


class NotificationTool:
    def __init__(self) -> None:
        self.novu_api_key = os.getenv("NOVU_API_KEY")

    def _render_email(self, alert: Alert) -> str:
        template = JINJA_ENV.get_template("alert_email.html")
        return template.render(alert=self._render_alert_card(alert))

    def _render_alert_card(self, alert: Alert) -> dict[str, Any]:
        impact_value = alert.financial_impact_cr or 0.0
        return {
            "title": alert.title,
            "tier": alert.tier,
            "confidence": f"{alert.confidence_score * 100:.0f}%",
            "financial_impact": f"₹{impact_value:.2f} Cr",
            "source": alert.source_citation,
            "actions": ["Run What-If", "View Analysis", "Schedule Report"],
            "body": alert.body,
        }

    async def _send_email(self, email: str, alert: Alert) -> dict[str, Any]:
        return {
            "channel": "email",
            "target": email,
            "subject": f"[{alert.tier}] MacroPulse Alert: {alert.title}",
            "html": self._render_email(alert),
            "provider": "novu",
        }

    async def _post_webhook(self, webhook: str, payload: dict[str, Any], channel: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=15.0, trust_env=False) as client:
            response = await client.post(webhook, json=payload)
            response.raise_for_status()
        return {"channel": channel, "status_code": response.status_code}

    async def _send_slack(self, webhook: str, alert: Alert) -> dict[str, Any]:
        card = self._render_alert_card(alert)
        payload = {
            "text": alert.title,
            "blocks": [
                {"type": "section", "text": {"type": "mrkdwn", "text": f"*{card['title']}*"}},
                {"type": "section", "text": {"type": "mrkdwn", "text": alert.body}},
                {"type": "context", "elements": [{"type": "mrkdwn", "text": f"{card['tier']} • {card['confidence']} • {card['source']}"}]},
            ],
        }
        return await self._post_webhook(webhook, payload, "slack")

    async def _send_teams(self, webhook: str, alert: Alert) -> dict[str, Any]:
        card = self._render_alert_card(alert)
        payload = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": [
                            {"type": "TextBlock", "weight": "Bolder", "size": "Medium", "text": card["title"]},
                            {"type": "TextBlock", "wrap": True, "text": alert.body},
                            {"type": "FactSet", "facts": [
                                {"title": "Tier", "value": card["tier"]},
                                {"title": "Confidence", "value": card["confidence"]},
                                {"title": "Financial impact", "value": card["financial_impact"]},
                                {"title": "Source", "value": card["source"]},
                            ]},
                        ],
                    },
                }
            ],
        }
        return await self._post_webhook(webhook, payload, "teams")

    async def _dispatch_now(self, alert: Alert, tenant_config: dict[str, Any]) -> dict[str, Any]:
        channels = tenant_config.get("channels", [])
        tasks = []
        if "email" in channels and tenant_config.get("email"):
            tasks.append(self._send_email(tenant_config["email"], alert))
        if "slack" in channels and tenant_config.get("slack_webhook"):
            tasks.append(self._send_slack(tenant_config["slack_webhook"], alert))
        if "teams" in channels and tenant_config.get("teams_webhook"):
            tasks.append(self._send_teams(tenant_config["teams_webhook"], alert))
        results = await asyncio.gather(*tasks, return_exceptions=True) if tasks else []
        return {"channels": channels, "results": results}

    async def dispatch(self, alert: Alert, tenant_config: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()

        if alert.tier == "P1":
            result = await self._dispatch_now(alert, tenant_config)
        elif alert.tier == "P2":
            from app.stream.macropulse.ingestion.tasks.ingestion_tasks import dispatch_p2_digest

            dispatch_p2_digest.apply_async(kwargs={"tenant_id": alert.tenant_id}, countdown=900)
            result = {"scheduled": "p2_digest"}
        else:
            from app.stream.macropulse.ingestion.tasks.ingestion_tasks import dispatch_p3_digest

            dispatch_p3_digest.apply_async(kwargs={"tenant_id": alert.tenant_id}, countdown=3600)
            result = {"scheduled": "p3_digest"}

        latency_ms = int((time.perf_counter() - started) * 1000)
        if alert.tier == "P1" and latency_ms > 60_000:
            logger.warning("P1 dispatch latency breached SLO: %sms for alert %s", latency_ms, alert.id)
        result["dispatch_latency_ms"] = latency_ms
        return result
