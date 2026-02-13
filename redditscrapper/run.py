#!/usr/bin/env python3
"""
Reddit Scraper - Main Entry Point

A modular Reddit scraping tool with proxy rotation and enrichment support.

Usage:
    python run.py                    # Run with default config
    python run.py --enrich           # Run with enrichment enabled
    python run.py --queries "query1" "query2"  # Custom queries
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent))

from proxy_manager import ProxyRotator
from reddit_scraper import AsyncRedditClient, AsyncScraper, RedditClient, Scraper
from reddit_scraper.config import *
from reddit_scraper.enricher import enrich_posts
from shared import save_json


def prepare_proxies(proxy_file: str, target: int, fetch: int) -> int:
    """Prepare working proxies and save them to file."""
    # Always use proxy_manager/proxies.txt for proxy file
    proxy_path = Path(__file__).parent / "proxy_manager" / "proxies.txt"
    print(f"Preparing proxies into {proxy_path} (target={target}, fetch={fetch})")
    rotator = ProxyRotator(str(proxy_path))
    rotator.refresh(target=target, fetch=fetch)
    final_pool = rotator.load()
    print(f"✓ Ready: {len(final_pool)} working proxies in {proxy_path}")
    return len(final_pool)


def start_menu() -> None:
    """Simple interactive menu for common actions."""
    while True:
        print("\n" + "=" * 40)
        print("Reddit Scraper Menu")
        print("=" * 40)
        print("1) Fetch proxies")
        print("2) Run scraper")
        print("3) Exit")
        choice = input("Choose an option [1-3]: ").strip()

        if choice == "1":
            fetch_raw = input(f"How many proxies to fetch? [{HEALTHY_PROXY_FETCH}]: ").strip()
            fetch = int(fetch_raw) if fetch_raw else HEALTHY_PROXY_FETCH
            # Accept all working proxies found, no target limit
            prepare_proxies("proxy_manager/proxies.txt", target=fetch, fetch=fetch)
        elif choice == "2":
            run_scraper()
        elif choice == "3":
            print("Goodbye!")
            sys.exit(0)
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")


class Logger:
    """Tee-style logger that writes to both console and file."""
    
    def __init__(self, log_file: Path):
        self.terminal = sys.stdout
        self.log = open(log_file, 'w', encoding='utf-8')
    
    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.flush()
    
    def flush(self):
        self.terminal.flush()
        self.log.flush()
    
    def close(self):
        self.log.close()


def run_scraper(
    queries: list[str] | None = None,
    limit_per_query: int = DEFAULT_LIMIT_PER_QUERY,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    proxy_file: str = None,
    enable_enrichment: bool = ENABLE_ENRICHMENT,
    async_mode: bool = ASYNC_MODE,
    query_concurrency: int = ASYNC_QUERY_CONCURRENCY,
    verbose: bool = True
):
    """
    Main scraper pipeline.
    
    Args:
        queries: List of search queries (uses DEFAULT_QUERIES if None)
        limit_per_query: Max posts per query
        output_dir: Output directory
        proxy_file: Proxy file path
        enable_enrichment: Enable post enrichment with comments
        verbose: Print progress
    """
    if queries is None:
        queries = DEFAULT_QUERIES
    output_dir = Path(output_dir)
    first_query = queries[0]
    # Create output folder named after first query
    query_folder = output_dir / first_query
    query_folder.mkdir(parents=True, exist_ok=True)
    # Setup logging
    log_file = query_folder / f"console_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    logger = Logger(log_file)
    sys.stdout = logger
    sys.stderr = logger
    # Always use proxy_manager/proxies.txt
    proxy_path = Path(__file__).parent / "proxy_manager" / "proxies.txt"
    
    try:
        print(f"{'='*60}")
        print(f"Reddit Scraper - Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Output folder: {query_folder}")
        print(f"Queries: {queries}")
        print(f"{'='*60}\n")
        
        # Step 1: Use only proxies.txt, no refresh or testing
        print(f"STEP 1: Preparing proxy pool")
        print(f"{'='*60}")
        rotator = ProxyRotator(str(proxy_path))
        existing = rotator.load()
        if existing:
            print(f"✓ Using manual proxy list from {proxy_path} ({len(existing)} proxies)")
        else:
            print(f"❌ Proxy list is empty. Please add proxies to {proxy_path}.")
            return

        # Step 2: Run scraper
        print(f"\nSTEP 2: Running Reddit crawler")
        print(f"{'='*60}")
        
        if async_mode:
            print("Mode: ASYNC (aiohttp)")
            async def run_async() -> tuple[list[dict], dict[str, int]]:
                client = AsyncRedditClient(
                    proxy_file=str(proxy_path),
                    timeout=TIMEOUT,
                    proxy_retry_attempts=MAX_RETRIES,
                )
                scraper = AsyncScraper(client)
                try:
                    return await scraper.search_multi(
                        queries=queries,
                        limit_per_query=limit_per_query,
                        query_concurrency=query_concurrency,
                        batch_size=DEFAULT_BATCH_SIZE,
                        delay=DEFAULT_DELAY,
                        max_retries=MAX_RETRIES,
                        retry_backoff=RETRY_BACKOFF,
                        max_proxy_refreshes=MAX_PROXY_REFRESHES,
                        proxy_file=proxy_path,
                        verbose=verbose,
                    )
                finally:
                    await client.close()
            posts, query_stats = asyncio.run(run_async())
        else:
            print("Mode: SYNC (requests)")
            client = RedditClient(
                proxy_file=str(proxy_path),
                timeout=TIMEOUT,
                proxy_retry_attempts=MAX_RETRIES
            )
            scraper = Scraper(client)
            posts, query_stats = scraper.search_multi(
                queries=queries,
                limit_per_query=limit_per_query,
                batch_size=DEFAULT_BATCH_SIZE,
                delay=DEFAULT_DELAY,
                max_retries=MAX_RETRIES,
                retry_backoff=RETRY_BACKOFF,
                max_proxy_refreshes=MAX_PROXY_REFRESHES,
                proxy_file=proxy_path,
                verbose=verbose
            )
        
        # Save results with metadata
        output_file = query_folder / "results.json"
        metadata = {
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "total_posts": len(posts),
            "queries": [
                {
                    "query": q,
                    "posts_collected": stats["total"],
                    "unique_posts": stats["unique"]
                }
                for q, stats in query_stats.items()
            ]
        }
        
        save_json({"metadata": metadata, "posts": posts}, output_file)
        
        print(f"\n{'='*60}")
        print(f"✓ Scraping complete")
        print(f"  Total unique posts: {len(posts)}")
        for query, count in query_stats.items():
            print(f"    - '{query}': {count} posts")
        print(f"  Results saved to: {output_file}")
        print(f"{'='*60}\n")
        
        # Step 3: Optional enrichment
        if enable_enrichment:
            print(f"STEP 3: Enriching posts with details + comments")
            print(f"{'='*60}")
            
            from reddit_scraper.config import ENRICHED_OUTPUT_FILENAME
            enrich_posts(
                input_file=output_file,
                output_file=Path(output_file).parent / ENRICHED_OUTPUT_FILENAME,
                proxy_file=str(proxy_path),
                delay=ENRICHMENT_DELAY,
                skip_existing=True
            )
            
            print(f"\n{'='*60}")
            print("✓ Full scrape + enrichment complete!")
            print(f"{'='*60}\n")
        
        print(f"Log saved to: {log_file}")
        print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
    finally:
        sys.stdout = logger.terminal
        sys.stderr = logger.terminal
        logger.close()


if __name__ == "__main__":
    import argparse

    # If launched without CLI args, show interactive menu.
    if len(sys.argv) == 1:
        start_menu()
        raise SystemExit(0)
    
    parser = argparse.ArgumentParser(description="Reddit Scraper")
    parser.add_argument("--queries", nargs="+", help="Search queries")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT_PER_QUERY, help="Posts per query")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_DIR, help="Output directory")
    parser.add_argument("--proxies", default="proxy_manager/proxies.txt", help="Proxy file (always uses proxy_manager/proxies.txt)")
    parser.add_argument("--enrich", action="store_true", help="Enable enrichment")
    parser.add_argument("--sync", action="store_true", help="Force synchronous mode")
    parser.add_argument(
        "--query-concurrency",
        type=int,
        default=ASYNC_QUERY_CONCURRENCY,
        help="Number of queries to run concurrently in async mode",
    )
    parser.add_argument(
        "--prepare-proxies",
        action="store_true",
        help="Only prepare working proxies and save to proxies.txt, then exit",
    )
    parser.add_argument(
        "--prepare-target",
        type=int,
        default=HEALTHY_PROXY_TARGET,
        help="Target number of working proxies for --prepare-proxies",
    )
    parser.add_argument(
        "--prepare-fetch",
        type=int,
        default=HEALTHY_PROXY_FETCH,
        help="How many raw proxies to fetch for --prepare-proxies",
    )
    
    args = parser.parse_args()

    if args.prepare_proxies:
        prepare_proxies("proxy_manager/proxies.txt", args.prepare_target, args.prepare_fetch)
        raise SystemExit(0)
    run_scraper(
        queries=args.queries,
        limit_per_query=args.limit,
        output_dir=args.output,
        enable_enrichment=args.enrich,
        async_mode=not args.sync,
        query_concurrency=args.query_concurrency,
    )
