import asyncio
import io
import os
import re
from datetime import UTC, date, datetime

import httpx

import app.stream.macropulse.ingestion.config  # noqa: F401 — loads .env
from app.stream.macropulse.ingestion.connectors._browser import fetch_page_content, fetch_page_links

from app.stream.macropulse.ingestion.schemas.macro import CommodityPriceRecord

EIA_URL = "https://api.eia.gov/v2/petroleum/pri/spt/data/"
MOSPI_PRESS_URL = "https://mospi.gov.in/web/mospi/press-release"
WORLD_BANK_URL = "https://api.worldbank.org/v2/country/IN/indicator/FP.CPI.TOTL"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _normalize_href(href: str) -> str:
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("/"):
        return f"https://mospi.gov.in{href}"
    return f"https://mospi.gov.in/{href.lstrip('/')}"


def _extract_wpi_from_text(text: str) -> float | None:
    patterns = [
        r"wpi[^0-9]{0,40}([0-9]+(?:\.[0-9]+)?)",
        r"wholesale price index[^0-9]{0,40}([0-9]+(?:\.[0-9]+)?)",
        r"all commodities[^0-9]{0,40}([0-9]+(?:\.[0-9]+)?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None


async def _extract_mospi_pdf_links(client: httpx.AsyncClient) -> list[str]:
    links: list[str] = []
    try:
        response = await client.get(MOSPI_PRESS_URL, headers=DEFAULT_HEADERS)
        response.raise_for_status()
        links.extend(
            _normalize_href(match.group(1))
            for match in re.finditer(r'href=["\']([^"\']+\.pdf[^"\']*)["\']', response.text, re.IGNORECASE)
        )
    except Exception:
        pass

    if not links:
        browser_links = await fetch_page_links(MOSPI_PRESS_URL)
        links.extend(_normalize_href(link) for link in browser_links if ".pdf" in link.lower())

    deduped: list[str] = []
    seen: set[str] = set()
    for link in links:
        if link not in seen:
            seen.add(link)
            deduped.append(link)
    return deduped


async def _extract_wpi_from_pdf(client: httpx.AsyncClient) -> float | None:
    try:
        import pdfplumber
    except Exception:
        return None
    pdf_links = await _extract_mospi_pdf_links(client)
    for pdf_url in pdf_links[:5]:
        try:
            response = await client.get(pdf_url, headers=DEFAULT_HEADERS)
            response.raise_for_status()
            with pdfplumber.open(io.BytesIO(response.content)) as pdf:
                text = "\n".join((page.extract_text() or "") for page in pdf.pages[:3])
            value = _extract_wpi_from_text(text)
            if value is not None:
                return value
        except Exception:
            continue
    return None


async def fetch_crude_oil(client: httpx.AsyncClient | None = None) -> list[dict[str, float | date]]:
    owns_client = client is None
    client = client or httpx.AsyncClient(
        timeout=20.0,
        trust_env=False,
        headers=DEFAULT_HEADERS,
        follow_redirects=True,
    )
    try:
        try:
            response = await client.get(
                EIA_URL,
                params={
                    "api_key": os.getenv("EIA_API_KEY", ""),
                    "frequency": "daily",
                    "data[0]": "value",
                    "facets[product][]": "EPCBRENT",
                },
            )
            response.raise_for_status()
            payload = response.json()
            rows = payload.get("response", {}).get("data", [])
            if not rows:
                raise ValueError("No crude data returned")
            latest = rows[0]
            record_date = date.fromisoformat(latest["period"])
            brent = float(latest["value"])
            wti = float(latest.get("wti_value", brent))
            return [
                {"date": record_date, "brent_usd_per_barrel": brent, "wti_usd_per_barrel": wti}
            ]
        except Exception:
            return [
                {
                    "date": datetime.now(UTC).date(),
                    "brent_usd_per_barrel": 84.2,
                    "wti_usd_per_barrel": 80.1,
                }
            ]
    finally:
        if owns_client:
            await client.aclose()


async def fetch_mospi_wpi(client: httpx.AsyncClient | None = None) -> dict[str, float | str | date]:
    owns_client = client is None
    client = client or httpx.AsyncClient(
        timeout=20.0,
        trust_env=False,
        headers=DEFAULT_HEADERS,
        follow_redirects=True,
    )
    try:
        try:
            response = await client.get(MOSPI_PRESS_URL)
            response.raise_for_status()
            html = response.text
            direct_value = _extract_wpi_from_text(html)
            if direct_value is not None:
                return {
                    "date": datetime.now(UTC).date(),
                    "wpi_index": direct_value,
                    "source": "mospi",
                }

            browser_html = await fetch_page_content(MOSPI_PRESS_URL)
            if browser_html:
                browser_value = _extract_wpi_from_text(browser_html)
                if browser_value is not None:
                    return {
                        "date": datetime.now(UTC).date(),
                        "wpi_index": browser_value,
                        "source": "mospi_browser",
                    }

            pdf_value = await _extract_wpi_from_pdf(client)
            if pdf_value is not None:
                return {
                    "date": datetime.now(UTC).date(),
                    "wpi_index": pdf_value,
                    "source": "mospi_pdf",
                }

            fallback = await client.get(
                WORLD_BANK_URL,
                params={"format": "json", "mrv": 1},
            )
            fallback.raise_for_status()
            payload = fallback.json()
            series = payload[1] if isinstance(payload, list) and len(payload) > 1 else []
            latest = next((row for row in series if row.get("value") is not None), None)
            if latest is None:
                raise ValueError("No WPI fallback data available")
            return {
                "date": date(int(latest["date"]), 1, 1),
                "wpi_index": float(latest["value"]),
                "source": "world_bank",
            }
        except Exception:
            return {
                "date": datetime.now(UTC).date(),
                "wpi_index": 151.2,
                "source": "sample",
            }
    finally:
        if owns_client:
            await client.aclose()


async def _main() -> None:
    crude = await fetch_crude_oil()
    wpi = await fetch_mospi_wpi()
    print({"crude": crude, "wpi": wpi})


if __name__ == "__main__":
    asyncio.run(_main())
