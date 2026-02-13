"""
Proxy Manager Module

A standalone module for fetching, verifying, and rotating HTTP/HTTPS proxies.
Can be used independently in any project requiring proxy management.

Usage:
    from proxy_manager import ProxyRotator
    
    rotator = ProxyRotator(proxy_file="proxies.txt")
    rotator.refresh(target=5, fetch=10)
    proxies = rotator.get_proxies()
"""

from .rotator import ProxyRotator, fetch_proxies, verify_proxies

__all__ = ["ProxyRotator", "fetch_proxies", "verify_proxies"]
__version__ = "1.0.0"
