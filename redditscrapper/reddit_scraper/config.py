"""Reddit scraper configuration."""

# Scraping settings
DEFAULT_QUERIES = [
    "ai coding agents",
    "github copilot",
    "openai codex",
    "claude code",
    "gemini code assist",
    "coding agents weakness",
    "coding agents strength",
    "best ai coding agents",
    "ai agents review",
]


DEFAULT_LIMIT_PER_QUERY = 100
DEFAULT_BATCH_SIZE = 100
DEFAULT_DELAY = 0.5
ASYNC_MODE = True
ASYNC_QUERY_CONCURRENCY = 1

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

# Post-processing settings
ENABLE_POSTPROCESSING = True
CLEANED_OUTPUT_FILENAME = "results_no_emoji.csv"
REFINED_OUTPUT_FILENAME = "refined_dataset.csv"
ANALYSIS_OUTPUT_FILENAME = "corpus_analysis.json"
ANALYSIS_TOP_WORDS = 20
