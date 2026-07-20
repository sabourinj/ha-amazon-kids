"""Async client for the (unofficial) Amazon Kids Parent Dashboard.

This talks to the private endpoints that parents.amazon.com uses. There is no
public API; these were identified by observing the dashboard's own network
traffic. They can change without notice.

Credentials are supplied by the caller (session cookies + CSRF token harvested
from a real browser login). This library never performs login itself and never
stores credentials.
"""

from __future__ import annotations

import logging
from typing import Iterable

import aiohttp

_LOGGER = logging.getLogger(__name__)

BASE = "https://parents.amazon.com"

# Sentinel meaning "clear the off-screen override / resume normal schedule".
RESUME_VALUE = -1


class AmazonKidsError(Exception):
    """Base error."""


class AmazonKidsAuthError(AmazonKidsError):
    """Raised when the session/CSRF token is rejected (401/403)."""


class AmazonKidsClient:
    """Minimal client for pausing/resuming Amazon Kids child profiles.

    Args:
        cookies: dict of cookie name -> value from a logged-in browser session.
        csrf_token: value of the ``x-amzn-csrf`` header from the same session.
        session: optional shared aiohttp session (recommended inside HA).
    """

    def __init__(
        self,
        cookies: dict[str, str],
        csrf_token: str,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self._cookies = cookies
        self._csrf = csrf_token
        self._session = session
        self._owns_session = session is None

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json;charset=UTF-8",
            "x-amzn-csrf": self._csrf,
            "Origin": BASE,
            "Referer": f"{BASE}/",
            # A realistic UA reduces the chance of being treated as a bot.
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
            ),
        }

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession(cookies=self._cookies)
            self._owns_session = True
        return self._session

    async def close(self) -> None:
        if self._session is not None and self._owns_session:
            await self._session.close()
            self._session = None

    async def __aenter__(self) -> "AmazonKidsClient":
        await self._get_session()
        return self

    async def __aexit__(self, *exc) -> None:
        await self.close()

    async def _post(self, path: str, payload: dict) -> dict:
        session = await self._get_session()
        try:
            async with session.post(
                f"{BASE}{path}",
                json=payload,
                headers=self._headers,
                cookies=self._cookies,
            ) as resp:
                if resp.status in (401, 403):
                    raise AmazonKidsAuthError(
                        f"Auth rejected ({resp.status}); cookie or CSRF token "
                        "is likely expired. Re-harvest from the browser."
                    )
                resp.raise_for_status()
                # Some endpoints return empty bodies on success.
                text = await resp.text()
                if not text:
                    return {}
                try:
                    return await resp.json(content_type=None)
                except Exception:  # noqa: BLE001 - non-JSON success body
                    return {"raw": text}
        except aiohttp.ClientResponseError as err:
            raise AmazonKidsError(f"HTTP error on {path}: {err}") from err

    async def set_offscreen_time(
        self, directed_ids: Iterable[str], seconds: int
    ) -> dict:
        """Set off-screen (paused) time for one or more children.

        ``seconds`` > 0 pauses for that many seconds. ``RESUME_VALUE`` (-1)
        clears the override. The endpoint accepts multiple IDs in one call,
        so pausing "all" children is a single request.
        """
        ids = list(directed_ids)
        if not ids:
            raise ValueError("directed_ids must not be empty")
        _LOGGER.debug("set-offscreen-time: %d child(ren), seconds=%s", len(ids), seconds)
        return await self._post(
            "/ajax/set-offscreen-time",
            {"directedIds": ids, "expirationTimeInSeconds": int(seconds)},
        )

    async def pause(self, directed_ids: Iterable[str], seconds: int) -> dict:
        """Pause children for ``seconds`` seconds."""
        if seconds <= 0:
            raise ValueError("pause seconds must be positive; use resume() to clear")
        return await self.set_offscreen_time(directed_ids, seconds)

    async def resume(self, directed_ids: Iterable[str]) -> dict:
        """Clear the off-screen override (resume normal schedule)."""
        return await self.set_offscreen_time(directed_ids, RESUME_VALUE)
