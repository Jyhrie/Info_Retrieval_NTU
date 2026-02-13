"""Proxy fetching, verification, and rotation."""

from __future__ import annotations


import sys
from pathlib import Path
from typing import List, Sequence
import json
import time

import requests

# Try to import rotating-free-proxies
try:
    from rotating_free_proxies.utils import fetch_new_proxies as rotating_fetch
except ImportError:
    rotating_fetch = None

DEFAULT_TEST_URL = "https://www.reddit.com/search.json?q=ping&limit=1&type=link"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def normalize_proxy(value: str) -> str:
    """Normalize proxy string to http:// format."""
    value = value.strip()
    if not value:
        return ""
    if value.startswith("http://") or value.startswith("https://"):
        return value
    return f"http://{value}"


def dedupe_preserve_order(items: List[str]) -> List[str]:
    """Remove duplicates while preserving first-seen order."""
    seen = set()
    out: List[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def fetch_proxies(count: int = 10, temp_path: Path | None = None) -> List[str]:
    """
    Fetch fresh proxies from multiple sources: rotating-free-proxies, proxybroker, proxyscrape.
    Args:
        count: Number of proxies to fetch (per source)
        temp_path: Optional temporary file path for rotating-free-proxies
    Returns:
        List of normalized proxy URLs
    """
    proxies = []
    # 1. Rotating-free-proxies
    if rotating_fetch:
        # Always use proxy_manager/temp_proxies.txt for temp files
        if temp_path is None:
            temp_path = Path(__file__).parent / "temp_proxies.txt"
        else:
            # If temp_path is not absolute, force it into proxy_manager
            temp_path = Path(temp_path)
            if not temp_path.is_absolute():
                temp_path = Path(__file__).parent / temp_path.name
        try:
            fetched = rotating_fetch(str(temp_path), count)
            proxies.extend(fetched)
        except Exception as e:
            print(f"[WARN] rotating-free-proxies failed: {e}")
        if temp_path.exists():
            temp_path.unlink()
    # 2. proxybroker
    try:
        import asyncio
        from proxybroker import Broker
        async def broker_fetch():
            broker = Broker()
            found = []
            async for proxy in broker.find(types=['HTTP', 'HTTPS'], limit=count):
                found.append(str(proxy))
            return found
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        broker_proxies = loop.run_until_complete(broker_fetch())
        proxies.extend(broker_proxies)
    except Exception as e:
        print(f"[WARN] proxybroker failed: {e}")
    # 3. proxyscrape (new API with API key)
    try:
        import requests as _requests
        api_key = "ee1ipf6zsci8zr52z6fy"
        url = f"https://api.proxyscrape.com/v3/proxy-list?token={api_key}&protocol=http&limit={count}&format=text"
        resp = _requests.get(url, timeout=15)
        if resp.status_code == 200:
            lines = [line.strip() for line in resp.text.splitlines() if line.strip()]
            proxies.extend(lines)
        else:
            print(f"[WARN] proxyscrape API error: {resp.status_code}")
    except Exception as e:
        print(f"[WARN] proxyscrape failed: {e}")
    # Normalize and dedupe
    return dedupe_preserve_order([normalize_proxy(proxy) for proxy in proxies])


def verify_proxies(
    proxies: List[str],
    test_url: str = DEFAULT_TEST_URL,
    timeout: float = 5.0,
    target: int | None = None,
    verbose: bool = True
) -> tuple[List[str], List[str]]:
    """
    Test proxies and return working and failed lists.
    
    Args:
        proxies: List of proxy URLs to test
        test_url: URL to use for testing
        timeout: Request timeout in seconds
        target: Stop after finding this many working proxies (optional)
        verbose: Print test results
        
    Returns:
        Tuple of (working_proxies, failed_proxies)
    """
    good: List[str] = []
    bad: List[str] = []
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    
    # For immediate save
    proxy_file = None
    proxy_path = None
    if hasattr(proxies, "_proxy_file"):
        proxy_path = getattr(proxies, "_proxy_file")
    # If not, try to guess from context (not always possible)
    if not proxy_path and hasattr(proxies, "proxy_file"):
        proxy_path = getattr(proxies, "proxy_file")
    # Fallback: look for proxies.txt in cwd
    if not proxy_path:
        proxy_path = Path("proxies.txt")
    else:
        proxy_path = Path(proxy_path)
    
    for proxy in proxies:
        if target and len(good) >= target:
            if verbose:
                print(f"[ STOP ] Found {target} working proxies, stopping early")
            break
        mapping = {"http": proxy, "https": proxy}
        try:
            response = session.get(test_url, proxies=mapping, timeout=timeout)
            response.raise_for_status()
            if verbose:
                print(f"[ OK ] {proxy}")
            good.append(proxy)
            # Immediately append to file, deduping
            try:
                if proxy_path:
                    # Read, dedupe, append
                    if proxy_path.exists():
                        lines = [x.strip() for x in proxy_path.read_text(encoding="utf-8").splitlines() if x.strip()]
                    else:
                        lines = []
                    if proxy not in lines:
                        lines.append(proxy)
                        proxy_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            except Exception as e:
                print(f"[WARN] Could not append proxy to file: {e}")
        except requests.RequestException as exc:
            if verbose:
                print(f"[FAIL] {proxy} -> {exc.__class__.__name__}")
            bad.append(proxy)
    
    return good, bad


class ProxyRotator:
    """Manages a pool of HTTP/HTTPS proxies with rotation and refresh capabilities."""

    def __init__(self, proxy_file: str = "proxies.txt", json_file: str = "proxies.json"):
        """
        Initialize proxy rotator.
        Args:
            proxy_file: Path to file containing proxy list (relative to this dir)
            json_file: Path to JSON file for proxy metadata (relative to this dir)
        """
        base_dir = Path(__file__).parent
        self.proxy_file = base_dir / proxy_file
        self.json_file = base_dir / json_file
        self.proxies: List[str] = []
        self.meta = {}  # {proxy: {last_ok, ok_streak, fail_streak}}
        if self.json_file.exists():
            self._load_json()
        elif self.proxy_file.exists():
            self.load()
            self._init_json_from_txt()
        else:
            self.proxies = []
            self.meta = {}

    def _load_json(self):
        try:
            with self.json_file.open("r", encoding="utf-8") as f:
                self.meta = json.load(f)
            self.proxies = list(self.meta.keys())
        except Exception as e:
            print(f"[WARN] Could not load proxies.json: {e}")
            self.meta = {}
            self.proxies = []

    def _save_json(self):
        try:
            with self.json_file.open("w", encoding="utf-8") as f:
                json.dump(self.meta, f, indent=2)
        except Exception as e:
            print(f"[WARN] Could not save proxies.json: {e}")

    def _init_json_from_txt(self):
        now = int(time.time())
        for proxy in self.proxies:
            self.meta[proxy] = {"last_ok": now, "ok_streak": 0, "fail_streak": 0}
        self._save_json()
    
    def load(self) -> List[str]:
        """Load proxies from file (txt)."""
        if not self.proxy_file.exists():
            return []
        with self.proxy_file.open("r", encoding="utf-8") as f:
            raw = [normalize_proxy(line) for line in f.read().splitlines() if line.strip()]
        self.proxies = dedupe_preserve_order(raw)
        return self.proxies
    
    def save(self, proxies: List[str] | None = None) -> None:
        """Save proxies to file (txt) and update JSON."""
        to_save = proxies if proxies is not None else self.proxies
        to_save = dedupe_preserve_order([normalize_proxy(p) for p in to_save])
        lines = "\n".join(to_save)
        self.proxy_file.write_text(lines + ("\n" if lines else ""), encoding="utf-8")
        # Also update JSON for new proxies
        now = int(time.time())
        for proxy in to_save:
            if proxy not in self.meta:
                self.meta[proxy] = {"last_ok": now, "ok_streak": 0, "fail_streak": 0}
        self._save_json()
    
    def refresh(
        self,
        target: int = 5,
        fetch: int = 10,
        test_url: str = DEFAULT_TEST_URL,
        timeout: float = 5.0
    ) -> List[str]:
        """
        Refresh proxy pool with fresh, tested proxies.
        
        Args:
            target: Target number of working proxies
            fetch: Number of proxies to fetch from source
            test_url: URL for testing proxies
            timeout: Test timeout in seconds
            
        Returns:
            List of working proxies
        """
        print(f"🔄 Refreshing proxy pool (target: {target})")
        print(f"   Step 1: Fetching {fetch} new proxies...")
        
        try:
            new_proxies = fetch_proxies(fetch, self.proxy_file.with_suffix(".tmp"))
            print(f"   ✓ Fetched {len(new_proxies)} proxies")
        except Exception as e:
            print(f"   ✗ Failed to fetch: {e}")
            return self.proxies
        
        print(f"   Step 2: Testing proxies (stop at {target} working)...")
        good, bad = verify_proxies(new_proxies, test_url, timeout, target=target)
        print(f"   ✓ Found {len(good)} working proxies")
        
        # Load existing and combine with new good ones
        existing = self.load()
        print(f"   Step 3: Current pool has {len(existing)} proxies")
        
        if not good:
            print(f"   ⚠️  No working proxies found, keeping existing pool")
            return existing
        
        # Strategy: Keep newest proxies, remove oldest
        final_pool = dedupe_preserve_order(good + existing)
        if len(final_pool) > target:
            final_pool = final_pool[:target]
        
        self.proxies = final_pool
        now = int(time.time())
        for proxy in final_pool:
            meta = self.meta.get(proxy, {"last_ok": now, "ok_streak": 0, "fail_streak": 0})
            meta["last_ok"] = now
            meta["ok_streak"] = meta.get("ok_streak", 0) + 1
            meta["fail_streak"] = 0
            self.meta[proxy] = meta
        # Remove proxies not in final_pool
        for proxy in list(self.meta.keys()):
            if proxy not in final_pool:
                del self.meta[proxy]
        self.save()
        self._save_json()
        print(f"   ✓ Final pool: {len(final_pool)} proxies")
        for i, proxy in enumerate(final_pool, 1):
            print(f"      {i}. {proxy}")
        return final_pool
    
    def get_proxies(self) -> List[str]:
        """Get current proxy list."""
        return self.proxies.copy()

    def record_proxy_use(self, proxy: str, ok: bool):
        now = int(time.time())
        meta = self.meta.get(proxy, {"last_ok": now, "ok_streak": 0, "fail_streak": 0})
        if ok:
            meta["last_ok"] = now
            meta["ok_streak"] = meta.get("ok_streak", 0) + 1
            meta["fail_streak"] = 0
        else:
            meta["fail_streak"] = meta.get("fail_streak", 0) + 1
        self.meta[proxy] = meta
        self._save_json()
