"""Post enrichment - adds full details and comments to scraped posts."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List

from tqdm import tqdm

from .client import RedditClient


def enrich_posts(
    input_file: Path,
    output_file: Path | None = None,
    proxy_file: str | None = None,
    delay: float = 1.0,
    skip_existing: bool = True
) -> List[Dict[str, Any]]:
    """
    Enrich posts with full details and comments.
    
    Args:
        input_file: JSON file with posts (can be simple list or metadata format)
        output_file: Output file (defaults to input_file if None)
        proxy_file: Optional proxy file
        delay: Delay between requests
        skip_existing: Skip posts that already have details
        
    Returns:
        List of enriched posts
    """
    if output_file is None:
        output_file = input_file
    
    # Load posts
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Handle both formats: {metadata, posts} or just [posts]
    if isinstance(data, dict) and "posts" in data:
        posts = data["posts"]
        metadata = data.get("metadata", {})
    else:
        posts = data
        metadata = {}
    
    client = RedditClient(proxy_file=proxy_file)
    enriched = []
    
    for post in tqdm(posts, desc="Enriching posts", unit="post"):
        # Skip if already enriched
        if skip_existing and ("body" in post or "comments" in post):
            enriched.append(post)
            continue
        
        permalink = post.get("permalink")
        if not permalink:
            enriched.append(post)
            continue
        
        # Fetch details
        try:
            details = client.get_post_details(permalink)
            if details:
                post.update({
                    "body": details.get("body", ""),
                    "comments": details.get("comments", [])
                })
        except Exception as e:
            print(f"Failed to enrich {permalink}: {e}")
        
        enriched.append(post)
        time.sleep(delay)
    

    # Calculate enrichment stats
    total_comments = 0
    total_records = 0
    total_words = 0
    for post in enriched:
        # Count post title and body as records
        total_records += 1  # post itself
        title = post.get("title", "")
        body = post.get("body", "")
        # Only count words in title and all bodies (post + all comments)
        total_words += len(title.split())
        total_words += len(body.split())
        # Count comments recursively (body only)
        def count_comments_and_words(comments):
            nonlocal total_comments, total_records, total_words
            for c in comments:
                total_comments += 1
                total_records += 1
                comment_body = c.get("body", "")
                total_words += len(comment_body.split())
                if c.get("replies"):
                    count_comments_and_words(c["replies"])
        if post.get("comments"):
            count_comments_and_words(post["comments"])

    # Add to metadata
    metadata["total_comments"] = total_comments
    metadata["Total_records"] = total_records
    metadata["Total_words"] = total_words

    output_data = {
        "metadata": metadata,
        "posts": enriched
    } if metadata else enriched

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"✓ Enriched {len(enriched)} posts saved to {output_file}")
    print(f"  total_comments: {total_comments}")
    print(f"  Total_records: {total_records}")
    print(f"  Total_words: {total_words}")
    return enriched
