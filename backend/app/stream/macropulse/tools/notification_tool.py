from __future__ import annotations

from app.core.ai_orchestration.tools.registry import tool_registry
from app.core.notifications.engine import get_notification_engine
from app.core.notifications.models import (
    NotificationChannel,
    NotificationPriority,
    NotificationRecipient,
    NotificationRequest,
)
from app.stream.macropulse.tool_schemas import NOTIFICATION_TOOL_SCHEMA


SEVERITY_TO_PRIORITY = {
    "P1": NotificationPriority.URGENT,
    "P2": NotificationPriority.HIGH,
    "P3": NotificationPriority.NORMAL,
}

CHANNEL_MAP = {
    "teams": NotificationChannel.TEAMS,
    "slack": NotificationChannel.SLACK,
    "email": NotificationChannel.EMAIL,
    "webhook": NotificationChannel.WEBHOOK,
    "in_app": NotificationChannel.IN_APP,
}


@tool_registry.register(
    name="notification_tool",
    description="Dispatch MacroPulse alerts through the platform notification engine",
    parameters_schema=NOTIFICATION_TOOL_SCHEMA,
)
async def notification_tool(
    title: str,
    message: str,
    severity: str,
    channel: str = "teams",
) -> dict:
    engine = get_notification_engine()
    notification_channel = CHANNEL_MAP.get(channel.lower(), NotificationChannel.TEAMS)
    priority = SEVERITY_TO_PRIORITY.get(severity.upper(), NotificationPriority.NORMAL)

    request = NotificationRequest(
        channel=notification_channel,
        recipients=[NotificationRecipient(channel_address="macro-cfo-alerts", name="CFO Desk")],
        subject=title,
        body=message,
        priority=priority,
        metadata={"origin": "macropulse", "severity": severity.upper()},
    )
    records = await engine.send(request)
    return {
        "success": True,
        "dispatched": len(records),
        "channel": notification_channel.value,
        "priority": priority.value,
        "notification_ids": [record.id for record in records],
    }
