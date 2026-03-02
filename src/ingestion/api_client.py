"""HTTP client for the oeffentlichevergabe.de notice export API."""

import logging
from datetime import date

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://www.oeffentlichevergabe.de"


class APIError(Exception):
    """Raised when the notice export API returns an error."""

    def __init__(self, status_code: int, url: str, message: str) -> None:
        self.status_code = status_code
        self.url = url
        super().__init__(f"API error {status_code} from {url}: {message}")


class TenderAPIClient:
    """Client for downloading bulk notice exports."""

    def __init__(self, base_url: str = BASE_URL) -> None:
        self.base_url = base_url

    async def fetch_day_export(
        self, pub_day: date, fmt: str = "csv.zip"
    ) -> bytes:
        """Download the notice export ZIP for a single day.

        Args:
            pub_day: Date to fetch notices for.
            fmt: Export format — 'csv.zip', 'ocds.zip', or 'eforms.zip'.

        Returns:
            Raw ZIP bytes.

        Raises:
            APIError: On HTTP errors after retries.
        """
        url = f"{self.base_url}/api/notice-exports"
        params = {"pubDay": pub_day.isoformat(), "format": fmt}

        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.get(
                        url, params=params, follow_redirects=True
                    )

                if resp.status_code == 404:
                    logger.debug("No data for %s (404)", pub_day)
                    return b""

                if resp.status_code == 200:
                    logger.info(
                        "Fetched %s: %d bytes", pub_day, len(resp.content)
                    )
                    return resp.content

                if resp.status_code in (429, 500, 502, 503):
                    wait = 2**attempt
                    logger.warning(
                        "API %d for %s, retry %d in %ds",
                        resp.status_code,
                        pub_day,
                        attempt + 1,
                        wait,
                    )
                    import asyncio

                    await asyncio.sleep(wait)
                    last_exc = APIError(resp.status_code, url, resp.text[:200])
                    continue

                raise APIError(resp.status_code, url, resp.text[:200])

            except httpx.TimeoutException as exc:
                wait = 2**attempt
                logger.warning(
                    "Timeout for %s, retry %d in %ds",
                    pub_day,
                    attempt + 1,
                    wait,
                )
                import asyncio

                await asyncio.sleep(wait)
                last_exc = exc

        raise APIError(0, url, f"Failed after 3 retries: {last_exc}")

    async def fetch_date_range(
        self, start: date, end: date, fmt: str = "csv.zip"
    ) -> list[tuple[date, bytes]]:
        """Download exports for each day in a date range.

        Args:
            start: First day (inclusive).
            end: Last day (inclusive).
            fmt: Export format.

        Returns:
            List of (date, zip_bytes) tuples. Days with no data are skipped.
        """
        from datetime import timedelta

        results: list[tuple[date, bytes]] = []
        current = start
        while current <= end:
            try:
                data = await self.fetch_day_export(current, fmt)
                if data:
                    results.append((current, data))
            except APIError as exc:
                logger.error("Failed to fetch %s: %s", current, exc)
            current += timedelta(days=1)
        return results
