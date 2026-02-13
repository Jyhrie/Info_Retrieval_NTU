"""Async Reddit API client with proxy support using aiohttp."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

import aiohttp

from .client import ProxyRotator


class AsyncRedditClient:
    """Async HTTP client for Reddit public JSON API."""

    def __init__(
        self,
        proxy_file: Optional[str] = None,
        timeout: int = 16,
        proxy_retry_attempts: int = 1,
    ):
        self.timeout = timeout
        self.proxy_retry_attempts = max(1, proxy_retry_attempts)
        self.proxy_rotator = ProxyRotator(proxy_file) if proxy_file else None
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                },
            )
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        session = await self._get_session()
        last_error: Optional[Exception] = None
        last_proxy: Optional[str] = None

        if not self.proxy_rotator:
            async with session.get(url, params=params) as resp:
                resp.raise_for_status()
                return await resp.json()

        used_proxies = set()
        while True:
            proxy_mapping = self.proxy_rotator.get_requests_proxy()
            if not proxy_mapping:
                raise RuntimeError("Proxy pool exhausted")

            proxy = proxy_mapping["http"]
            last_proxy = proxy
            if proxy in used_proxies:
                # All proxies have been tried
                break
            used_proxies.add(proxy)
            for attempt in range(2):  # Try each proxy up to 2 times
                try:
                    async with session.get(url, params=params, proxy=proxy) as resp:
                        if resp.status >= 400:
                            failure_type = self.proxy_rotator.classify_failure(
                                Exception(f"HTTP {resp.status}"),
                                status_code=resp.status,
                            )
                            self.proxy_rotator.mark_failure(last_proxy, failure_type=failure_type)
                            resp.raise_for_status()
                        self.proxy_rotator.mark_success(last_proxy)
                        return await resp.json()
                except Exception as err:
                    last_error = err
                    failure_type = self.proxy_rotator.classify_failure(err)
                    self.proxy_rotator.mark_failure(last_proxy, failure_type=failure_type)
                    if attempt == 0:
                        continue  # Retry once
                    else:
                        break  # Move to next proxy

        if last_error:
            raise last_error
        raise RuntimeError("All proxies failed for this request.")

    async def search(
        self,
        query: str,
        limit: int = 100,
        after: Optional[str] = None,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> tuple[List[Dict[str, Any]], Optional[str]]:
        url = "https://www.reddit.com/search.json"
        params: Dict[str, Any] = {"q": query, "limit": limit, "sort": "relevance", "type": "link"}
        if after:
            params["after"] = after
        if extra_params:
            params.update(extra_params)

        data = await self._request(url, params=params)
        posts: List[Dict[str, Any]] = []

        for post in data["data"]["children"]:
            post_data = post["data"]
            permalink = post_data.get("permalink", "")
            posts.append(
                {
                    "id": post_data.get("id"),
                    "name": post_data.get("name"),
                    "title": post_data.get("title"),
                    "author": post_data.get("author"),
                    "subreddit": post_data.get("subreddit"),
                    "permalink": permalink,
                    "link": f"https://www.reddit.com{permalink}" if permalink else post_data.get("url", ""),
                    "description": (post_data.get("selftext") or "")[:269],
                    "created_utc": post_data.get("created_utc"),
                    "score": post_data.get("score"),
                    "num_comments": post_data.get("num_comments"),
                }
            )

        after_token = data.get("data", {}).get("after")
        return posts, after_token
