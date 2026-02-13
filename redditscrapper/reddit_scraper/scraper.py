"""Main Reddit scraper with deduplication and multi-query support."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from tqdm import tqdm

from .client import RedditClient


def refresh_proxies(proxy_file: Path, target: int = 5, fetch: int = 10) -> bool:
    """Refresh proxy pool using proxy_manager."""
    import sys
    sys.path.insert(0, str(proxy_file.parent.parent))
    
    from proxy_manager import ProxyRotator
    
    try:
        rotator = ProxyRotator(str(proxy_file))
        rotator.refresh(target=target, fetch=fetch)
        return True
    except Exception as e:
        print(f"Failed to refresh proxies: {e}")
        return False


class Scraper:
    """
    Reddit scraper with pagination, deduplication, and proxy management.
    
    Example:
        client = RedditClient(proxy_file="proxies.txt")
        scraper = Scraper(client)
        posts = scraper.search_multi(
            queries=["donald trump", "trump election"],
            limit_per_query=200
        )
    """
    
    def __init__(self, client: RedditClient):
        """
        Initialize scraper.
        
        Args:
            client: RedditClient instance
        """
        self.client = client
    
    def search(
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
        verbose: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search Reddit for a single query with pagination.
        
        Args:
            query: Search query
            limit: Max posts to collect
            batch_size: Posts per page (max 100)
            delay: Delay between requests in seconds
            max_retries: Retry attempts per request
            retry_backoff: Backoff multiplier for retries
            max_proxy_refreshes: Max proxy refresh attempts
            proxy_file: Path to proxy file for auto-refresh
            seen_ids: Optional set for deduplication across queries
            verbose: Show progress bar
            
        Returns:
            List of post dictionaries
        """
        if seen_ids is None:
            seen_ids = set()
        
        results = []
        remaining = limit
        batch_size = max(1, min(batch_size, 100))
        proxy_refresh_count = 0
        consecutive_errors = 0
        max_consecutive_errors = 10
        
        after = None
        empty_page_streak = 0
        
        pbar = tqdm(total=limit, desc=f"'{query}'", unit="post", disable=not verbose)
        
        try:
            while remaining > 0:
                page_size = min(remaining, batch_size)
                page = None
                after_token = None
                
                for attempt in range(max_retries):
                    try:
                        page, after_token = self.client.search(
                            query,
                            limit=page_size,
                            after=after
                        )
                        break
                    except Exception as e:
                        error_text = str(e)
                        if attempt < max_retries - 1:
                            time.sleep(retry_backoff)
                            continue
                        elif "Proxy pool exhausted" in error_text:
                            # Only refresh when current pool is exhausted
                            if proxy_file and proxy_refresh_count < max_proxy_refreshes:
                                pbar.write(f"🔄 Proxy pool exhausted - refreshing (attempt {proxy_refresh_count + 1}/{max_proxy_refreshes})...")
                                if refresh_proxies(proxy_file, target=5, fetch=10):
                                    proxy_refresh_count += 1
                                    self.client = RedditClient(
                                        proxy_file=str(proxy_file),
                                        timeout=self.client.timeout,
                                        proxy_retry_attempts=self.client.proxy_retry_attempts
                                    )
                                    try:
                                        page, after_token = self.client.search(query, limit=page_size, after=after)
                                        break
                                    except Exception:
                                        pass
                
                if page is None:
                    if proxy_refresh_count >= max_proxy_refreshes:
                        pbar.write("❌ Exhausted proxy refreshes. Stopping.")
                        break
                    pbar.write("❌ Request failed. Stopping.")
                    break
                
                after = after_token
                
                # Stop conditions
                if not after_token:
                    pbar.write("✓ Reached end (no pagination token)")
                    break
                
                if not page:
                    empty_page_streak += 1
                    if empty_page_streak >= 2:
                        pbar.write("✓ No more results (empty pages)")
                        break
                else:
                    empty_page_streak = 0
                
                # Deduplicate and add new posts
                new_posts = 0
                for post in page:
                    post_id = post.get("id") or post.get("permalink", "")
                    if post_id and post_id not in seen_ids:
                        seen_ids.add(post_id)
                        results.append(post)
                        new_posts += 1
                
                pbar.update(new_posts)
                remaining -= new_posts
                consecutive_errors = 0
                
                if new_posts == 0:
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        pbar.write("❌ Too many consecutive errors")
                        break
                
                time.sleep(delay)
        finally:
            pbar.close()
        
        return results
    
    def search_multi(
        self,
        queries: List[str],
        limit_per_query: int = 250,
        **kwargs
    ) -> tuple[List[Dict[str, Any]], Dict[str, int]]:
        """
        Search multiple queries with shared deduplication.
        
        Args:
            queries: List of search queries
            limit_per_query: Max posts per query
            **kwargs: Additional arguments passed to search()
            
        Returns:
            Tuple of (all_posts, query_stats)
        """
        shared_seen_ids: Set[str] = set()
        all_results = []
        query_stats = {}
        
        for i, query in enumerate(queries, 1):
            print(f"\n{'='*60}")
            print(f"Query {i}/{len(queries)}: '{query}'")
            print(f"{'='*60}")
            
            results = self.search(
                query,
                limit=limit_per_query,
                seen_ids=shared_seen_ids,
                **kwargs
            )
            
            all_results.extend(results)
            query_stats[query] = len(results)
            print(f"✓ '{query}': {len(results)} new posts (total: {len(all_results)})")
        
        return all_results, query_stats


def save_results(
    posts: List[Dict[str, Any]],
    output_file: Path,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Save posts to JSON file with optional metadata.
    
    Args:
        posts: List of post dictionaries
        output_file: Output file path
        metadata: Optional metadata dictionary
    """
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    data = {
        "metadata": metadata or {},
        "posts": posts
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
