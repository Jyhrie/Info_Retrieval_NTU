"""Reddit scraper configuration."""

# Scraping settings
DEFAULT_QUERIES = [
    "cryptocurrency",
    # "bitcoin",
    # "bitcoin price",
    # "bitcoin 2026"
]

DEFAULT_LIMIT_PER_QUERY = 100
DEFAULT_BATCH_SIZE = 100
DEFAULT_DELAY = 0.5
ASYNC_MODE = True
ASYNC_QUERY_CONCURRENCY = 4

# Proxy settings
DEFAULT_PROXY_FILE = "proxies.txt"
MAX_RETRIES = 1
RETRY_BACKOFF = 1.0
MAX_PROXY_REFRESHES = 3
TIMEOUT = 16
REFRESH_TARGET = 5
REFRESH_FETCH = 10
REFRESH_ON_START_IF_EMPTY = True

# Manual proxy preparation (recommended healthy pool for free proxies)
HEALTHY_PROXY_TARGET = 20
HEALTHY_PROXY_FETCH = 400  # Free proxies have ~1-5% success rate

# Output settings
DEFAULT_OUTPUT_DIR = "data"

 # Enrichment settings
ENABLE_ENRICHMENT = True
ENRICHMENT_DELAY = 1.5
ENRICHED_OUTPUT_FILENAME = "enriched_results.json"
