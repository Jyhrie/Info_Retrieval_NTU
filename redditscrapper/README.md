# Architecture Overview

```
redditscrapper/
├── proxy_manager/          # Proxy rotation and health tracking
│   ├── __init__.py
│   ├── rotator.py         # Fetch, verify, rotate proxies
│   └── config.py          # Proxy settings
│
├── reddit_scraper/         # Reddit scraping and enrichment
│   ├── __init__.py
│   ├── client.py          # Reddit API HTTP client
│   ├── scraper.py         # Main scraper with pagination & dedup
│   ├── enricher.py        # Post detail enrichment
│   └── config.py          # Scraper settings
│
├── shared/                 # Shared utilities
│   ├── __init__.py
│   └── utils.py           # JSON helpers, file management
│
├── run.py                  # Main entry point (menu & CLI)
├── data/                   # Output directory for results
└── proxy_manager/proxies.txt # Proxy list (auto-managed)
```

---

details = client.get_post_details(permalink)
enrich_posts(input_file, output_file, proxy_file, delay=1.0)

# Reddit Scraper - Step-by-Step Guide

This toolkit lets you scrape Reddit posts at scale, with robust proxy rotation and enrichment (fetching comments and full post text). Below is a step-by-step guide for setup, running, and understanding how everything works.

---

### 1.1. Install Python Requirements (including Proxy Rotation)
```bash
pip install -r requirements.txt
cd yars/rotating-free-proxies-master
pip install -e .
```
This installs all required dependencies: `requests`, `tqdm`, and `rotating-free-proxies` for automatic proxy fetching and rotation.

---

## 2. How the System Works

### 2.1. Proxy Manager
- **proxy_manager/proxies.txt**: List of working proxies (auto-managed, do not edit by hand)
- **proxy_manager/proxies.json**: Tracks proxy health, last success, and failure streaks
- **What happens when a proxy fails?**
  - The system tries the next proxy in the list
  - If all proxies fail, it fetches new ones and updates proxies.txt/json
- **How to refresh proxies manually?**
  - Run: `python run.py` and choose option 1 (Fetch proxies)

### 2.2. Reddit Scraper
- Scrapes Reddit posts for your queries using the proxies
- Handles pagination, deduplication, and saves results to `data/<query>/results.json`
- **Enrichment**: After scraping, can fetch full post text and comments for each post

---


## 3. Configuring Queries, Limits, and Enrichment

Before running the scraper, you can set your default queries, how many posts to collect per query, and whether enrichment is enabled by default:

- Open `reddit_scraper/config.py` and edit the following options:
  ```python
  # List of queries to search
  DEFAULT_QUERIES = ["your", "queries", "here"]  # Each string is a search term. The scraper will run once for each query and combine results, removing duplicates.

  # Number of posts per query
  DEFAULT_LIMIT_PER_QUERY = 250  # How many posts to collect for each query. Reddit may cap results per query, so use multiple queries for more data.

  # Enable or disable enrichment (fetch comments/full text)
  ENABLE_ENRICHMENT = False  # If True, after scraping post metadata, the tool will fetch full post text and all comments for each post (slower, more complete data).
  ```

**What these options do:**
- `DEFAULT_QUERIES`: Controls what topics or keywords you collect Reddit posts for.
- `DEFAULT_LIMIT_PER_QUERY`: Sets the maximum number of posts to collect for each query.
- `ENABLE_ENRICHMENT`: If True, the scraper will fetch extra details (full post text and comments) after collecting the basic post info. This makes the output richer but takes longer.

You can override these defaults at runtime using command-line options (see below).

---

## 4. Running the Scraper

### 4.1. Main Options

# Run with default settings (see reddit_scraper/config.py)
python run.py

If you run `python run.py` with no arguments, you'll see a menu:
1. Fetch proxies (refreshes proxy pool)
2. Run scraper (scrapes Reddit)
3. Exit

---

## 5. How Proxy Rotation & Failure Handling Works

- The scraper always uses proxies from `proxy_manager/proxies.txt`
- If a proxy fails (connection error, timeout, etc.), it is marked as failed and the next proxy is tried
- After 3 failures, a proxy is removed from the pool
- If all proxies fail, the system fetches new proxies and retries
- Proxy health and last success are tracked in `proxies.json`

---

## 6. Scraping & Enrichment Workflow
1. **Normal Data Collection**: Scraper collects post metadata (title, author, subreddit, etc.) for each query
2. **Enrichment (Optional)**: If `--enrich` is used, the scraper fetches full post text and all comments for each post, and saves them in the output JSON
3. **Output**: Results are saved in `data/<query>/results.json` with a summary at the top

---

## 9. Summary Table

| File/Module                  | Purpose/Behavior                                                                 |
|------------------------------|---------------------------------------------------------------------------------|
| proxy_manager/proxies.txt    | List of working proxies (auto-managed)                                           |
| proxy_manager/proxies.json   | Tracks proxy health, last success, failure streaks                               |
| reddit_scraper/              | Main scraping logic, enrichment, config                                          |
| run.py                       | Main entry point, menu, CLI options                                             |
| data/<query>/results.json    | Scraped posts and metadata                                                       |
| data/<query>/console_log_*.txt | Log of each run                                                                |

---

**Made with ❤️ for modular, production-ready data collection**
