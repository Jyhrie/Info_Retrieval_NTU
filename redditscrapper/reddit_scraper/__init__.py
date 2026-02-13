"""
Reddit Scraper Module

A standalone module for scraping Reddit posts and comments using the public JSON API.
Can be used independently in any project requiring Reddit data collection.

Usage:
    from reddit_scraper import RedditClient, Scraper
    
    client = RedditClient(proxy_file="proxies.txt")
    scraper = Scraper(client)
    posts = scraper.search("donald trump", limit=100)
"""

from .client import RedditClient
from .scraper import Scraper
from .async_client import AsyncRedditClient
from .async_scraper import AsyncScraper
from .enricher import enrich_posts

__all__ = ["RedditClient", "Scraper", "AsyncRedditClient", "AsyncScraper", "enrich_posts"]
__version__ = "1.0.0"
