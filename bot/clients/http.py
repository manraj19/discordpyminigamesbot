"""Shared async HTTP client. One aiohttp session is reused for the whole
process (cheap, connection-pooled, and never blocks the event loop), replacing
the old synchronous ``requests.get`` calls."""

import asyncio

import aiohttp


class HttpClient:
    def __init__(self):
        self._session = None

    async def _get_session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def fetch_json(self, url):
        """GET ``url`` and return ``(status, parsed_json_or_None)``.

        On any network/timeout/decoding error returns ``(None, None)`` so
        callers can handle failure with a simple falsy check."""
        session = await self._get_session()
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    return response.status, None
                return response.status, await response.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
            return None, None

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
