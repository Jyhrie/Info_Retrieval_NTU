"""Reddit API client with proxy support."""

from __future__ import annotations

import sys
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import HTTPError
from requests.exceptions import ProxyError, SSLError
from requests.exceptions import RequestException
from urllib3.util.retry import Retry

# Add parent directory to path for imports
current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir.parent))

from proxy_manager import ProxyRotator as ExternalProxyRotator

logger = logging.getLogger(__name__)


class ProxyRotator:
    """Gold-list proxy rotator with cooldown and dead-proxy handling."""
    
    def __init__(self, proxy_file: str, shuffle: bool = True):
        self.external_rotator = ExternalProxyRotator(proxy_file)
        self.external_rotator.load()
        # Good list (active)
        self._proxies = self.external_rotator.get_proxies()
        # Cooldown list: proxy -> unix timestamp when it can return to good list
        self._cooldown: Dict[str, float] = {}
        # Dead list (hard removed)
        self._dead: set[str] = set()
        self._current_proxy: Optional[str] = None
        self._failures: Dict[str, int] = {}
        self._failure_threshold = 3
        self._cooldown_seconds = 300  # 5 minutes default
        self._max_failures_before_dead = 7
        self._retest_every_n_requests = 30
        self._request_counter = 0
        self._index = 0
        
        if shuffle:
            import random
            random.shuffle(self._proxies)
    
    def get_requests_proxy(self) -> Optional[Dict[str, str]]:
        """Get current proxy mapping for requests."""
        self._request_counter += 1
        if self._request_counter % self._retest_every_n_requests == 0:
            self._promote_cooled_down()

        if self._current_proxy:
            return {"http": self._current_proxy, "https": self._current_proxy}
        
        if not self._proxies:
            return None

        if self._index >= len(self._proxies):
            self._index = 0
        self._current_proxy = self._proxies[self._index]
        return {"http": self._current_proxy, "https": self._current_proxy}

    def _promote_cooled_down(self) -> None:
        """Move proxies from cooldown back to good list when cooldown expires."""
        now = time.time()
        ready = [proxy for proxy, ready_at in self._cooldown.items() if ready_at <= now]
        for proxy in ready:
            self._cooldown.pop(proxy, None)
            if proxy not in self._dead and proxy not in self._proxies:
                self._proxies.append(proxy)
                logger.info("Proxy promoted from cooldown: %s", proxy)

    def classify_failure(self, error: Exception, status_code: Optional[int] = None) -> str:
        """Classify failure as temporary or dead."""
        temporary_statuses = {408, 429, 500, 502, 503, 504, 520, 522, 524}
        dead_statuses = {400, 401, 403, 404, 407, 410}

        if status_code is not None:
            if status_code in dead_statuses:
                return "dead"
            if status_code in temporary_statuses:
                return "temporary"
            return "temporary" if status_code >= 500 else "dead"

        if isinstance(error, (RequestsConnectionError, SSLError, ProxyError)):
            return "temporary"
        return "temporary"

    def mark_success(self, proxy_str: str) -> None:
        """Reset failure count on success and keep proxy in good list."""
        self._failures[proxy_str] = 0
        self._cooldown.pop(proxy_str, None)

    def mark_failure(self, proxy_str: str, failure_type: str = "temporary") -> bool:
        """Mark failure and move proxy to cooldown/dead list. Returns True when removed from good list."""
        self._failures[proxy_str] = self._failures.get(proxy_str, 0) + 1

        if proxy_str == self._current_proxy:
            self._current_proxy = None

        # Hard-dead condition
        if failure_type == "dead" or self._failures[proxy_str] >= self._max_failures_before_dead:
            self._dead.add(proxy_str)
            self.remove_proxy(proxy_str)
            self._cooldown.pop(proxy_str, None)
            return True

        # Temporary condition -> cooldown
        backoff_factor = min(self._failures[proxy_str], 6)
        ready_at = time.time() + (self._cooldown_seconds * backoff_factor)
        self._cooldown[proxy_str] = ready_at
        self.remove_proxy(proxy_str)
        return True
    
    def mark_failed(self, proxy_str: str) -> bool:
        """Backward-compatible alias for temporary failures."""
        return self.mark_failure(proxy_str, failure_type="temporary")
    
    def remove_proxy(self, proxy_str: str):
        """Remove proxy from pool."""
        if proxy_str in self._proxies:
            self._proxies.remove(proxy_str)
            if self._index >= len(self._proxies):
                self._index = 0

    def has_proxies(self) -> bool:
        """Return True if there are proxies left in the pool."""
        return len(self._proxies) > 0

    def stats(self) -> Dict[str, int]:
        """Proxy pool stats for logs/debugging."""
        return {
            "good": len(self._proxies),
            "cooldown": len(self._cooldown),
            "dead": len(self._dead),
        }


class RedditClient:
    """HTTP client for Reddit's public JSON API with proxy rotation."""
    
    def __init__(
        self,
        proxy_file: Optional[str] = None,
        timeout: int = 16,
        proxy_retry_attempts: int = 1,
        log_proxies: bool = False
    ):
        """
        Initialize Reddit API client.
        
        Args:
            proxy_file: Path to proxy file (optional)
            timeout: Request timeout in seconds
            proxy_retry_attempts: Number of retries per request
            log_proxies: Log proxy usage
        """
        self.timeout = timeout
        self.proxy_retry_attempts = max(1, proxy_retry_attempts)
        self.log_proxies = log_proxies
        
        # Setup session with retries
        self.session = requests.Session()
        retries = Retry(
            total=5,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retries))
        
        # Random user agent
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        
        # Setup proxy rotation
        self.proxy_rotator = None
        if proxy_file:
            self.proxy_rotator = ProxyRotator(proxy_file)
    
    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make HTTP request with proxy rotation and retry logic."""
        kwargs.setdefault("timeout", self.timeout)
        request_callable = getattr(self.session, method)
        
        if not self.proxy_rotator:
            return request_callable(url, **kwargs)
        
        last_error = None
        last_proxy = None
        
        for _ in range(self.proxy_retry_attempts):
            proxy_mapping = self.proxy_rotator.get_requests_proxy()
            if not proxy_mapping:
                raise RuntimeError("Proxy pool exhausted")
            last_proxy = proxy_mapping["http"] if proxy_mapping else None
            
            if proxy_mapping:
                if self.log_proxies:
                    logger.info(f"Using proxy: {last_proxy}")
                kwargs["proxies"] = proxy_mapping
            
            try:
                response = request_callable(url, **kwargs)
                if response.status_code >= 400:
                    status_code = response.status_code
                    if last_proxy:
                        failure_type = self.proxy_rotator.classify_failure(
                            HTTPError(f"HTTP {status_code}"),
                            status_code=status_code,
                        )
                        self.proxy_rotator.mark_failure(last_proxy, failure_type=failure_type)
                        logger.warning(
                            "Proxy %s marked %s after HTTP %s (stats=%s)",
                            last_proxy,
                            failure_type,
                            status_code,
                            self.proxy_rotator.stats(),
                        )
                    response.raise_for_status()
                if last_proxy:
                    self.proxy_rotator.mark_success(last_proxy)
                return response
            except (ProxyError, SSLError, RequestsConnectionError, RequestException) as err:
                last_error = err
                if last_proxy:
                    failure_type = self.proxy_rotator.classify_failure(err)
                    self.proxy_rotator.mark_failure(last_proxy, failure_type=failure_type)
                    logger.warning(
                        "Proxy %s moved to %s after %s (stats=%s)",
                        last_proxy,
                        failure_type,
                        err.__class__.__name__,
                        self.proxy_rotator.stats(),
                    )
                continue
        
        if last_error:
            raise last_error
        
        return request_callable(url, **kwargs)
    
    def search(
        self,
        query: str,
        limit: int = 100,
        after: Optional[str] = None,
        extra_params: Optional[Dict] = None
    ) -> tuple[List[Dict[str, Any]], Optional[str]]:
        """
        Search Reddit and return posts with pagination token.
        
        Args:
            query: Search query
            limit: Max results per page
            after: Pagination token
            extra_params: Additional URL parameters
            
        Returns:
            Tuple of (posts, next_page_token)
        """
        url = "https://www.reddit.com/search.json"
        params = {"q": query, "limit": limit, "sort": "relevance", "type": "link"}
        
        if after:
            params["after"] = after
        if extra_params:
            params.update(extra_params)
        
        response = self._request("get", url, params=params)
        response.raise_for_status()
        
        data = response.json()
        posts = []
        
        for post in data["data"]["children"]:
            post_data = post["data"]
            permalink = post_data.get("permalink", "")
            
            posts.append({
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
            })
        
        after_token = data.get("data", {}).get("after")
        return posts, after_token
    
    def get_post_details(self, permalink: str) -> Optional[Dict[str, Any]]:
        """
        Fetch full post details including comments.
        
        Args:
            permalink: Reddit permalink (e.g., /r/subreddit/comments/abc123/title/)
            
        Returns:
            Dict with title, body, and comments
        """
        url = f"https://www.reddit.com{permalink}.json"
        
        try:
            response = self._request("get", url)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to fetch post details: {e}")
            return None
        
        post_data = response.json()
        if not isinstance(post_data, list) or len(post_data) < 2:
            return None
        
        main_post = post_data[0]["data"]["children"][0]["data"]
        comments = self._extract_comments(post_data[1]["data"]["children"])
        
        return {
            "title": main_post["title"],
            "body": main_post.get("selftext", ""),
            "comments": comments
        }
    
    def _extract_comments(self, comment_list: List) -> List[Dict]:
        """Recursively extract comments and replies."""
        extracted = []
        
        for comment in comment_list:
            if isinstance(comment, dict) and comment.get("kind") == "t1":
                comment_data = comment.get("data", {})
                extracted_comment = {
                    "author": comment_data.get("author", ""),
                    "body": comment_data.get("body", ""),
                    "score": comment_data.get("score", ""),
                    "replies": [],
                }
                
                replies = comment_data.get("replies", "")
                if isinstance(replies, dict):
                    extracted_comment["replies"] = self._extract_comments(
                        replies.get("data", {}).get("children", [])
                    )
                
                extracted.append(extracted_comment)
        
        return extracted
