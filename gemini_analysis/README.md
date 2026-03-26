# TrendCatcher Analysis System

## 📚 Overview

The analysis system processes crawled social media posts using Google's Gemini AI to generate sentiment analysis, statistics, and narrative summaries.

## 🔄 Automated Pipeline Flow

```
1. User triggers crawl from frontend
   ↓
2. Crawler collects posts
   ↓
3. Save to: backend/data/{keyword}-MMDDYY-0-0/crawled_data.json
   ↓
4. AUTO-TRIGGER: Analysis pipeline starts
   ↓
5. Step 1: Gemini Analysis (run_analysis.py)
   - Analyzes each post for sentiment, relevance, geography
   - Outputs: analysis_results.csv
   ↓
6. Step 2: Post-Processing (run_post_processing.py)
   - Aggregates results
   - Outputs: stats.json, content.json, summary.json
   ↓
7. Dashboard updated - analysis ready to view!
```

## 📁 File Structure

```
backend/src/analysis/
├── analyzer_config.yaml      # Configuration for analysis behavior
├── run_analysis.py           # Main Gemini analysis script
├── run_post_processing.py    # Post-processor for dashboard files
├── run_pipeline.py          # (Optional) Full pipeline runner
└── utils/
    ├── config_loader.py      # Config and environment variable loader
    ├── gemini_analyzer.py    # Core Gemini API client
    └── post_processor.py     # Post-processing logic
```

## 🎯 Key Components

### 1. **run_analysis.py**
**Purpose**: Analyze each post using Gemini AI

**Input**: 
- `crawled_data.json` - Raw posts from crawler
```json
{
  "keyword": "NTU",
  "platform": "reddit",
  "total_posts": 42,
  "posts": [{"url": "...", "title": "...", ...}]
}
```

**Process**:
- Reads all posts from JSON
- For each post, sends to Gemini AI with structured prompt
- Gemini analyzes:
  - **Relevance**: Is it about the keyword? (0 or 1)
  - **Sentiment**: Positive (1), Neutral (0), Negative (-1)
  - **Geography**: Local vs International
  - **Summaries**: Positive and negative opinions
  - **Hotness**: Engagement score (0-100)

**Output**: `analysis_results.csv`
```csv
URL,Platform,Title,Summary,Sentiment_Score,Relevance_Score,...
https://reddit.com/...,reddit,Post about NTU,Summary text,1,1,...
```

**Features**:
- ✅ Incremental saving (every 25 posts)
- ✅ Parallel processing (4 workers)
- ✅ Resume support if interrupted
- ✅ Cost tracking (token usage)

**Command**:
```bash
python src/analysis/run_analysis.py \
  --web-scraper-data data/NTU-100225-0-0/crawled_data.json \
  --output-dir data/NTU-100225-0-0 \
  --config src/analysis/analyzer_config.yaml
```

### 2. **run_post_processing.py**
**Purpose**: Transform analysis into dashboard-ready JSON files

**Input**: `analysis_results.csv`

**Process**:
- Reads CSV with all analyzed posts
- Groups by sentiment and geography
- Generates statistics and summaries
- Uses Gemini AI to create narrative summaries for each category

**Output**: 3 JSON files

**A. stats.json** - Statistics for dashboard cards
```json
{
  "total_posts": 42,
  "platform": "reddit",
  "keyword": "NTU",
  "crawl_date": "2025-10-02T23:00:00",
  "sentiment_breakdown": {
    "positive": 15,
    "negative": 10,
    "neutral": 17
  }
}
```

**B. content.json** - Data for Content Overview table
```json
{
  "posts": [
    {
      "title": "Post title",
      "url": "https://...",
      "platform": "reddit",
      "sentiment": "positive",
      "region": "local",
      "hotness": 85
    }
  ],
  "total": 42
}
```

**C. summary.json** - AI narrative summaries
```json
{
  "version": "1.0.0",
  "generated_at": "2025-10-02T23:30:00",
  "international_positive": {
    "Theme 1": "Detailed explanation with citations...",
    "Theme 2": "Another insight..."
  },
  "international_negative": {...},
  "local_positive": {...},
  "local_negative": {...}
}
```

**Command**:
```bash
python src/analysis/run_post_processing.py \
  --csv-file data/NTU-100225-0-0/analysis_results.csv \
  --output-dir data/NTU-100225-0-0 \
  --config src/analysis/analyzer_config.yaml
```

### 3. **analyzer_config.yaml**
**Purpose**: Configure analysis behavior

**Key Settings**:

```yaml
api:
  gemini:
    api_key: GOOGLE_AI_API_KEY  # Loaded from .env
    model: "gemini-2.0-flash-exp"
    
    prompt:
      keyword: "General"  # Can be overridden dynamically
      geographic_labels:
        - "Singapore Local"
        - "International-China"
        # ... more regions
      
      template: |
        # Full prompt template for Gemini
        # Uses {keyword}, {url}, {title} placeholders

processing:
  analysis:
    batch_size: 50
    parallel_workers: 4
    auto_save_interval: 25  # Save every 25 posts
```

## 🔗 Integration with Crawler

### **In `server.py`**:

The `_run_automated_analysis()` function is called after crawl completes:

```python
async def _run_automated_analysis(self, dir_name: str, keyword: str):
    # 1. Send WebSocket message to show "Analysis in Progress"
    await websocket_manager.broadcast({
        "type": "analysis_started",
        "dir_name": dir_name
    })
    
    # 2. Run Gemini analysis script
    python src/analysis/run_analysis.py \
      --web-scraper-data data/{dir_name}/crawled_data.json \
      --output-dir data/{dir_name} \
      --config src/analysis/analyzer_config.yaml
    
    # 3. Run post-processing script
    python src/analysis/run_post_processing.py \
      --csv-file data/{dir_name}/analysis_results.csv \
      --output-dir data/{dir_name} \
      --config src/analysis/analyzer_config.yaml
    
    # 4. Notify completion
    await websocket_manager.send_status("🎉 Analysis complete!")
```

## 🎮 Frontend Integration

When analysis starts, the frontend (`session.html`):
1. Receives `analysis_started` WebSocket message
2. Immediately shows "Analysis in Progress" screen
3. Displays mini-game while user waits
4. Analysis runs in background
5. When complete, dashboard files are ready

## 🔑 Environment Variables

Required in `.env`:
```env
GOOGLE_AI_API_KEY=your_gemini_api_key_here
```

The config loader automatically replaces `GOOGLE_AI_API_KEY` placeholder with the actual value from `.env`.

## 📊 Data Flow Example

### Crawl: "NTU"
```
frontend/session.html
  → POST /crawl/start {keyword: "NTU", posts_to_collect: 20}
  → backend crawls Reddit
  → Finds 42 posts
  → Saves to: data/NTU-100225-0-0/crawled_data.json
  
  [AUTO-TRIGGER]
  → run_analysis.py analyzes 42 posts
  → Generates: analysis_results.csv (42 rows)
  → run_post_processing.py processes CSV
  → Generates: stats.json, content.json, summary.json
  
  [RESULT]
  → Dashboard shows "NTU - Created: Oct 2, 2025"
  → Click to view → analysis.html loads all 3 JSON files
  → Shows: sentiment cards, charts, content table, AI summaries
```

## 🛠️ Manual Usage

If you need to run analysis manually:

```bash
cd backend

# Step 1: Analyze posts
python src/analysis/run_analysis.py \
  --web-scraper-data data/NTU-100225-0-0/crawled_data.json \
  --output-dir data/NTU-100225-0-0 \
  --config src/analysis/analyzer_config.yaml

# Step 2: Generate dashboard files
python src/analysis/run_post_processing.py \
  --csv-file data/NTU-100225-0-0/analysis_results.csv \
  --output-dir data/NTU-100225-0-0 \
  --config src/analysis/analyzer_config.yaml
```

## 🎯 Evaluation Dataset Analysis (1000 Posts)

Use this when you have an evaluation CSV (for example `evaluation_dataset_1000.csv`) and want Gemini to:

1. Score each row with `neutral`, `positive`, `negative` probabilities
2. Predict one label (`predicted_label`)
3. Rank rows by confidence (`rank`)

Run:

```bash
python run_evaluation_analysis.py \
  --input-csv ../redditscrapper/data/ai_coding_agents_1/evaluation_dataset_1000.csv
```

Default output:

- `../redditscrapper/data/ai_coding_agents_1/evaluation_dataset_1000_ranked.csv`

Optional:

```bash
python run_evaluation_analysis.py \
  --input-csv ../redditscrapper/data/ai_coding_agents_1/evaluation_dataset_1000.csv \
  --output-csv ../redditscrapper/data/ai_coding_agents_1/evaluation_dataset_ranked_custom.csv \
  --model gemini-2.5-flash \
  --text-column text_clean
```

## ⚙️ Configuration Options

### Parallel Processing
```yaml
processing:
  analysis:
    parallel_workers: 4  # Analyze 4 posts simultaneously
```

### Auto-Save Frequency
```yaml
processing:
  analysis:
    auto_save_interval: 25  # Save progress every 25 posts
```

### Custom Keyword
Edit `analyzer_config.yaml` or pass dynamically:
```yaml
api:
  gemini:
    prompt:
      keyword: "Your keyword"
```

## 🐛 Troubleshooting

### "API key not found"
- Check `.env` file has `GOOGLE_AI_API_KEY=...`
- Verify it's in the backend root directory

### "Analysis script not found"
- Ensure scripts are in `backend/src/analysis/`
- Check file permissions (should be executable)

### "Import errors"
- All imports now use flexible try/except for both package and standalone usage
- Works whether called from root or from analysis directory

## 📈 Cost Tracking

The system tracks Gemini API usage:
- Input tokens
- Output tokens
- Estimated cost based on model pricing

Check terminal output after analysis completes for cost breakdown.

## 🎯 Next Steps

The system is now **fully automated**:
1. User runs crawl → Analysis happens automatically
2. No manual intervention needed
3. Results appear on dashboard when ready

Enjoy the automated sentiment analysis! 🚀

