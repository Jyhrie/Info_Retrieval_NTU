"""Async scraper orchestration for multi-query crawling."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from tqdm import tqdm

from .async_client import AsyncRedditClient
from .scraper import refresh_proxies


class AsyncScraper:
    """Async multi-query scraper (query-level concurrency)."""

    def __init__(self, client: AsyncRedditClient):
        self.client = client

    async def search(
        self,
        query: str,
        limit: int = 300,
        batch_size: int = 100,
        delay: float = 0.5,
        max_retries: int = 1,
        retry_backoff: float = 1.0,
        max_proxy_refreshes: int = 3,
        proxy_file: Optional[Path] = None,
        seen_ids: Optional[Set[str]] = None,
        verbose: bool = True,
    ) -> List[Dict[str, Any]]:
        if seen_ids is None:
            seen_ids = set()

        results: List[Dict[str, Any]] = []
        remaining = limit
        batch_size = max(1, min(batch_size, 100))
        proxy_refresh_count = 0
        after = None

        pbar = tqdm(total=limit, desc=f"'{query}'", unit="post", disable=not verbose)
        try:
            while remaining > 0:
                page_size = min(remaining, batch_size)
                page = None
                after_token = None

                for attempt in range(max_retries):
                    try:
                        page, after_token = await self.client.search(query, limit=page_size, after=after)
                        break
                    except Exception as e:
                        if attempt < max_retries - 1:
                            await asyncio.sleep(retry_backoff)
                            continue
                        if "Proxy pool exhausted" in str(e):
                            if proxy_file and proxy_refresh_count < max_proxy_refreshes:
                                pbar.write(f"🔄 Proxy pool exhausted - refreshing (attempt {proxy_refresh_count + 1}/{max_proxy_refreshes})...")
                                if refresh_proxies(proxy_file, target=5, fetch=10):
                                    proxy_refresh_count += 1
                                    self.client = AsyncRedditClient(
                                        proxy_file=str(proxy_file),
                                        timeout=self.client.timeout,
                                        proxy_retry_attempts=self.client.proxy_retry_attempts,
                                    )
                                    try:
                                        page, after_token = await self.client.search(query, limit=page_size, after=after)
                                        break
                                    except Exception:
                                        pass

                if page is None:
                    break

                after = after_token
                if not page or not after_token:
                    if page:
                        new_posts = 0
                        for post in page:
                            post_id = post.get("id") or post.get("permalink", "")
                            if post_id and post_id not in seen_ids:
                                seen_ids.add(post_id)
                                results.append(post)
                                new_posts += 1
                        pbar.update(new_posts)
                    break

                new_posts = 0
                for post in page:
                    post_id = post.get("id") or post.get("permalink", "")
                    if post_id and post_id not in seen_ids:
                        seen_ids.add(post_id)
                        results.append(post)
                        new_posts += 1

                pbar.update(new_posts)
                remaining -= new_posts
                await asyncio.sleep(delay)
        finally:
            pbar.close()

        return results

    async def search_multi(
        self,
        queries: List[str],
        limit_per_query: int = 250,
        query_concurrency: int = 4,
        **kwargs,
    ) -> tuple[List[Dict[str, Any]], Dict[str, dict]]:
        # query_stats: {query: {"total": int, "unique": int}}
        query_stats: Dict[str, dict] = {}
        sem = asyncio.Semaphore(max(1, query_concurrency))

        # To track unique IDs per query and globally
        per_query_ids = {}
        all_results: List[Dict[str, Any]] = []
        all_ids: Set[str] = set()

        async def run_query(idx: int, query: str) -> List[Dict[str, Any]]:
            async with sem:
                print(f"\n{'='*60}")
                print(f"Query {idx + 1}/{len(queries)}: '{query}'")
                print(f"{'='*60}")
                results = await self.search(
                    query=query,
                    limit=limit_per_query,
                    seen_ids=None,
                    **kwargs,
                )
                # Track all IDs for this query
                ids = set()
                for post in results:
                    post_id = post.get("id") or post.get("permalink", "")
                    if post_id:
                        ids.add(post_id)
                per_query_ids[query] = ids
                query_stats[query] = {"total": len(results), "unique": 0}  # unique will be filled later
                print(f"✓ '{query}': {len(results)} posts fetched")
                return results

        tasks = [asyncio.create_task(run_query(i, q)) for i, q in enumerate(queries)]
        nested_results = await asyncio.gather(*tasks)

        for chunk in nested_results:
            all_results.extend(chunk)

        # Global deduplication across all queries
        unique_results: List[Dict[str, Any]] = []
        seen_ids: Set[str] = set()
        for post in all_results:
            post_id = post.get("id") or post.get("permalink", "")
            if post_id and post_id not in seen_ids:
                seen_ids.add(post_id)
                unique_results.append(post)

        # Now compute unique per query (not in any other query)
        for query in queries:
            other_ids = set()
            for q2 in queries:
                if q2 != query:
                    other_ids.update(per_query_ids.get(q2, set()))
            unique_only = per_query_ids[query] - other_ids
            query_stats[query]["unique"] = len(unique_only)

        return unique_results, query_stats
