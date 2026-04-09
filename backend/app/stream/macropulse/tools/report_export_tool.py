"""
MacroPulse Report Export Tool — Day 5 (Pranisree)

Generates PDF/HTML weekly CFO briefs using reportlab + Jinja2.
Includes matplotlib charts: G-Sec yield trend, FX 7D movement, commodity MoM index.
Saves output to S3 / ADLS raw bucket.
"""
from __future__ import annotations

import base64
import io
import logging
from datetime import datetime, timezone
from typing import Any

import matplotlib

matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from jinja2 import Template
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.core.ai_orchestration.tools.registry import tool_registry
from app.core.data_infra.storage import get_storage_service, StorageError
from app.stream.macropulse.tool_schemas import REPORT_EXPORT_TOOL_SCHEMA

logger = logging.getLogger(__name__)

# ── Chart Generators ─────────────────────────────────────────

CHART_STYLE = {
    "figure.facecolor": "#ffffff",
    "axes.facecolor": "#f8f9fa",
    "axes.edgecolor": "#dee2e6",
    "axes.grid": True,
    "grid.color": "#e9ecef",
    "grid.linewidth": 0.5,
    "font.size": 9,
}


def _generate_gsec_yield_chart(data: list[dict]) -> bytes:
    """G-Sec 10Y yield trend chart (matplotlib → PNG bytes)."""
    with plt.rc_context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(6, 3), dpi=120)

        if data:
            dates = [d.get("date", f"D{i}") for i, d in enumerate(data)]
            values = [float(d.get("value", 0)) for d in data]
        else:
            # Demo data when no real data supplied
            dates = [f"W{i}" for i in range(1, 8)]
            values = [7.12, 7.08, 7.15, 7.22, 7.18, 7.25, 7.20]

        ax.plot(dates, values, color="#1a73e8", linewidth=2, marker="o", markersize=4)
        ax.fill_between(range(len(values)), values, alpha=0.08, color="#1a73e8")
        ax.set_title("G-Sec 10Y Yield Trend (%)", fontsize=11, fontweight="bold", pad=10)
        ax.set_ylabel("Yield %")
        ax.tick_params(axis="x", rotation=45)
        fig.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()


def _generate_fx_7d_chart(data: list[dict]) -> bytes:
    """FX 7-day movement bar chart."""
    with plt.rc_context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(6, 3), dpi=120)

        if data:
            pairs = [d.get("pair", f"P{i}") for i, d in enumerate(data)]
            changes = [float(d.get("change_pct", 0)) for d in data]
        else:
            pairs = ["USD/INR", "EUR/INR", "GBP/INR", "AED/INR", "SAR/INR"]
            changes = [0.35, -0.12, 0.48, 0.02, -0.05]

        bar_colors = ["#dc3545" if c > 0 else "#28a745" for c in changes]
        ax.bar(pairs, changes, color=bar_colors, edgecolor="white", linewidth=0.5)
        ax.axhline(0, color="#6c757d", linewidth=0.8)
        ax.set_title("FX 7-Day Movement (%)", fontsize=11, fontweight="bold", pad=10)
        ax.set_ylabel("Change %")
        fig.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()


def _generate_commodity_mom_chart(data: list[dict]) -> bytes:
    """Commodity month-over-month index chart."""
    with plt.rc_context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(6, 3), dpi=120)

        if data:
            commodities = [d.get("name", f"C{i}") for i, d in enumerate(data)]
            mom_changes = [float(d.get("mom_pct", 0)) for d in data]
        else:
            commodities = ["Brent Crude", "Gold", "Natural Gas", "Copper", "Palm Oil"]
            mom_changes = [3.2, -1.5, 5.8, 2.1, -0.7]

        bar_colors = ["#e74c3c" if c > 0 else "#27ae60" for c in mom_changes]
        bars = ax.barh(commodities, mom_changes, color=bar_colors, edgecolor="white", height=0.5)
        ax.axvline(0, color="#6c757d", linewidth=0.8)
        ax.set_title("Commodity MoM Index (%)", fontsize=11, fontweight="bold", pad=10)
        ax.set_xlabel("MoM Change %")

        for bar, val in zip(bars, mom_changes):
            ax.text(
                bar.get_width() + (0.1 if val >= 0 else -0.1),
                bar.get_y() + bar.get_height() / 2,
                f"{val:+.1f}%",
                ha="left" if val >= 0 else "right",
                va="center",
                fontsize=8,
            )
        fig.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()


# ── Jinja2 HTML Template ────────────────────────────────────

HTML_TEMPLATE = Template("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{{ title }}</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, sans-serif; margin: 0; padding: 20px; background: #fff; color: #333; }
        .header { background: linear-gradient(135deg, #1a237e, #283593); color: white; padding: 24px 32px; border-radius: 8px; margin-bottom: 24px; }
        .header h1 { margin: 0 0 8px 0; font-size: 24px; }
        .header .meta { opacity: 0.85; font-size: 13px; }
        .section { background: #f8f9fa; border-radius: 8px; padding: 20px; margin-bottom: 16px; border-left: 4px solid #1a73e8; }
        .section h2 { margin: 0 0 8px 0; font-size: 16px; color: #1a237e; }
        .section .signal { display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }
        .signal-positive { background: #d4edda; color: #155724; }
        .signal-negative { background: #f8d7da; color: #721c24; }
        .signal-neutral { background: #fff3cd; color: #856404; }
        .charts { display: grid; grid-template-columns: 1fr; gap: 16px; margin: 24px 0; }
        .chart-container { background: #fff; border: 1px solid #e9ecef; border-radius: 8px; padding: 12px; text-align: center; }
        .chart-container img { max-width: 100%; height: auto; }
        .actions { background: #e8f5e9; border-radius: 8px; padding: 16px 20px; }
        .actions h3 { margin: 0 0 8px 0; color: #2e7d32; }
        .actions ul { margin: 0; padding-left: 20px; }
        .footer { text-align: center; color: #999; font-size: 11px; margin-top: 24px; padding-top: 16px; border-top: 1px solid #eee; }
        .confidence-bar { height: 8px; border-radius: 4px; background: #e9ecef; margin: 8px 0; }
        .confidence-fill { height: 100%; border-radius: 4px; background: linear-gradient(90deg, #28a745, #1a73e8); }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ title }}</h1>
        <div class="meta">
            Week ending {{ week_ending }} &bull; Tenant: {{ tenant_id }} &bull; Generated {{ generated_at }}
        </div>
        <div class="meta" style="margin-top: 6px;">
            Overall Confidence: {{ "%.0f"|format(overall_confidence * 100) }}%
            <div class="confidence-bar"><div class="confidence-fill" style="width: {{ "%.0f"|format(overall_confidence * 100) }}%"></div></div>
        </div>
    </div>

    {% if headline %}
    <div class="section" style="border-left-color: #ff9800;">
        <h2>Headline</h2>
        <p>{{ headline }}</p>
    </div>
    {% endif %}

    {% for section in sections %}
    <div class="section">
        <h2>{{ section.title }} <span class="signal signal-{{ section.signal }}">{{ section.signal | upper }}</span></h2>
        <p>{{ section.summary }}</p>
        <div class="confidence-bar"><div class="confidence-fill" style="width: {{ "%.0f"|format(section.confidence * 100) }}%"></div></div>
        <small><strong>Action:</strong> {{ section.action }}</small>
    </div>
    {% endfor %}

    <div class="charts">
        {% if gsec_chart_b64 %}
        <div class="chart-container">
            <img src="data:image/png;base64,{{ gsec_chart_b64 }}" alt="G-Sec Yield Trend">
        </div>
        {% endif %}
        {% if fx_chart_b64 %}
        <div class="chart-container">
            <img src="data:image/png;base64,{{ fx_chart_b64 }}" alt="FX 7D Movement">
        </div>
        {% endif %}
        {% if commodity_chart_b64 %}
        <div class="chart-container">
            <img src="data:image/png;base64,{{ commodity_chart_b64 }}" alt="Commodity MoM Index">
        </div>
        {% endif %}
    </div>

    {% if cfo_actions %}
    <div class="actions">
        <h3>CFO Action Items</h3>
        <ul>
            {% for action in cfo_actions %}
            <li>{{ action }}</li>
            {% endfor %}
        </ul>
    </div>
    {% endif %}

    {% if top3_scenarios %}
    <div class="section">
        <h2>Top Scenarios</h2>
        <ol>
            {% for scenario in top3_scenarios %}
            <li>{{ scenario }}</li>
            {% endfor %}
        </ol>
    </div>
    {% endif %}

    <div class="footer">
        MacroPulse Weekly Brief &bull; Intelli Platform &bull; {{ generated_at }}
    </div>
</body>
</html>""")


# ── PDF Builder (reportlab) ──────────────────────────────────

def _build_pdf(
    title: str,
    brief_data: dict[str, Any],
    gsec_png: bytes,
    fx_png: bytes,
    commodity_png: bytes,
) -> bytes:
    """Build a PDF report using reportlab with embedded charts."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm)
    styles = getSampleStyleSheet()
    story: list = []

    # Custom styles
    title_style = ParagraphStyle(
        "BriefTitle", parent=styles["Title"], fontSize=20,
        textColor=colors.HexColor("#1a237e"), spaceAfter=6,
    )
    heading_style = ParagraphStyle(
        "BriefHeading", parent=styles["Heading2"], fontSize=13,
        textColor=colors.HexColor("#1a237e"), spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "BriefBody", parent=styles["Normal"], fontSize=10, spaceAfter=8, leading=14,
    )
    meta_style = ParagraphStyle(
        "Meta", parent=styles["Normal"], fontSize=9,
        textColor=colors.HexColor("#666666"), spaceAfter=12,
    )

    # Title & metadata
    story.append(Paragraph(title, title_style))
    story.append(Paragraph(
        f"Week ending {brief_data.get('week_ending', 'N/A')} &bull; "
        f"Tenant: {brief_data.get('tenant_id', 'N/A')} &bull; "
        f"Confidence: {brief_data.get('overall_confidence', 0):.0%}",
        meta_style,
    ))

    # Headline
    headline = brief_data.get("headline", "")
    if headline:
        story.append(Paragraph(f"<b>Headline:</b> {headline}", body_style))
        story.append(Spacer(1, 6))

    # Sections
    sections = brief_data.get("sections", [])
    for section in sections:
        s_title = section.get("title", "")
        signal = section.get("signal", "neutral").upper()
        signal_color = {"POSITIVE": "#28a745", "NEGATIVE": "#dc3545"}.get(signal, "#ffc107")
        story.append(Paragraph(
            f'{s_title} <font color="{signal_color}"><b>[{signal}]</b></font>',
            heading_style,
        ))
        story.append(Paragraph(section.get("summary", ""), body_style))
        story.append(Paragraph(
            f"<i>Action: {section.get('action', 'N/A')}</i>",
            body_style,
        ))
        story.append(Spacer(1, 4))

    # Charts
    for chart_bytes, chart_title in [
        (gsec_png, "G-Sec 10Y Yield Trend"),
        (fx_png, "FX 7-Day Movement"),
        (commodity_png, "Commodity MoM Index"),
    ]:
        story.append(Spacer(1, 8))
        story.append(Paragraph(chart_title, heading_style))
        img_buf = io.BytesIO(chart_bytes)
        story.append(Image(img_buf, width=5.5 * inch, height=2.5 * inch))
        story.append(Spacer(1, 6))

    # CFO Actions
    cfo_actions = brief_data.get("cfo_actions", [])
    if cfo_actions:
        story.append(Spacer(1, 8))
        story.append(Paragraph("CFO Action Items", heading_style))
        for i, action in enumerate(cfo_actions, 1):
            story.append(Paragraph(f"{i}. {action}", body_style))

    # Top scenarios
    scenarios = brief_data.get("top3_scenarios", [])
    if scenarios:
        story.append(Spacer(1, 8))
        story.append(Paragraph("Top Scenarios", heading_style))
        for i, s in enumerate(scenarios, 1):
            story.append(Paragraph(f"{i}. {s}", body_style))

    # Footer
    story.append(Spacer(1, 16))
    story.append(Paragraph(
        f"MacroPulse Weekly Brief &bull; Intelli Platform &bull; {brief_data.get('generated_at', '')}",
        meta_style,
    ))

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


# ── S3 Upload ────────────────────────────────────────────────

def _upload_to_s3(content: bytes, key: str, content_type: str) -> dict:
    """Upload report to S3 / ADLS raw bucket."""
    try:
        storage = get_storage_service()
        metadata = storage.upload_file(
            file_data=content,
            key=key,
            content_type=content_type,
            metadata={"origin": "macropulse", "type": "weekly_brief"},
        )
        return {"uploaded": True, "key": metadata.key, "bucket": metadata.bucket, "size": metadata.size}
    except (StorageError, Exception) as exc:
        logger.warning("S3 upload failed (non-blocking): %s", exc)
        return {"uploaded": False, "error": str(exc)}


# ── Main Tool ────────────────────────────────────────────────

@tool_registry.register(
    name="report_export_tool",
    description="Generate a presentation-ready MacroPulse weekly brief as PDF or HTML with charts",
    parameters_schema=REPORT_EXPORT_TOOL_SCHEMA,
)
def report_export_tool(
    title: str,
    summary: str,
    format: str = "html",
    brief_data: dict[str, Any] | None = None,
    gsec_data: list[dict] | None = None,
    fx_data: list[dict] | None = None,
    commodity_data: list[dict] | None = None,
    tenant_id: str | None = None,
    upload_to_s3: bool = True,
) -> dict:
    """
    Generate PDF/HTML weekly brief with embedded charts.

    Args:
        title: Report title.
        summary: Executive summary text.
        format: Output format — "html" or "pdf".
        brief_data: Full CFOBriefResponse as dict (sections, actions, etc.).
        gsec_data: G-Sec yield data points [{date, value}, ...].
        fx_data: FX movement data [{pair, change_pct}, ...].
        commodity_data: Commodity MoM data [{name, mom_pct}, ...].
        tenant_id: Tenant identifier.
        upload_to_s3: Whether to upload to S3/ADLS.
    """
    export_format = format.lower()
    now = datetime.now(timezone.utc)
    generated_at = now.isoformat()

    # Default brief_data structure
    if brief_data is None:
        brief_data = {
            "tenant_id": tenant_id or "default",
            "week_ending": now.strftime("%d %b %Y"),
            "headline": summary,
            "sections": [],
            "top3_scenarios": [],
            "cfo_actions": [],
            "overall_confidence": 0.85,
            "generated_at": generated_at,
        }
    else:
        brief_data.setdefault("generated_at", generated_at)
        brief_data.setdefault("tenant_id", tenant_id or "default")

    # Generate charts
    gsec_png = _generate_gsec_yield_chart(gsec_data or [])
    fx_png = _generate_fx_7d_chart(fx_data or [])
    commodity_png = _generate_commodity_mom_chart(commodity_data or [])

    # Base64 encode for HTML embedding
    gsec_b64 = base64.b64encode(gsec_png).decode()
    fx_b64 = base64.b64encode(fx_png).decode()
    commodity_b64 = base64.b64encode(commodity_png).decode()

    result: dict[str, Any] = {
        "success": export_format in {"html", "pdf"},
        "format": export_format,
        "title": title,
        "generated_at": generated_at,
    }

    if export_format == "html":
        rendered_html = HTML_TEMPLATE.render(
            title=title,
            tenant_id=brief_data.get("tenant_id", "default"),
            week_ending=brief_data.get("week_ending", ""),
            generated_at=generated_at,
            overall_confidence=brief_data.get("overall_confidence", 0.85),
            headline=brief_data.get("headline", summary),
            sections=brief_data.get("sections", []),
            cfo_actions=brief_data.get("cfo_actions", []),
            top3_scenarios=brief_data.get("top3_scenarios", []),
            gsec_chart_b64=gsec_b64,
            fx_chart_b64=fx_b64,
            commodity_chart_b64=commodity_b64,
        )
        result["rendered_html"] = rendered_html
        result["export_status"] = "ready"

        if upload_to_s3:
            s3_key = f"reports/macropulse/{brief_data['tenant_id']}/weekly_brief_{now.strftime('%Y%m%d_%H%M%S')}.html"
            result["s3"] = _upload_to_s3(rendered_html.encode(), s3_key, "text/html")

    elif export_format == "pdf":
        pdf_bytes = _build_pdf(title, brief_data, gsec_png, fx_png, commodity_png)
        result["pdf_base64"] = base64.b64encode(pdf_bytes).decode()
        result["pdf_size_bytes"] = len(pdf_bytes)
        result["export_status"] = "ready"

        if upload_to_s3:
            s3_key = f"reports/macropulse/{brief_data['tenant_id']}/weekly_brief_{now.strftime('%Y%m%d_%H%M%S')}.pdf"
            result["s3"] = _upload_to_s3(pdf_bytes, s3_key, "application/pdf")

    else:
        result["export_status"] = "unsupported_format"

    return result
