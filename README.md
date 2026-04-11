# SC4021 - Information Retrieval Project
## Project Overview
* Introduction
* Crawling
* Index and Querying
* Classification
* Innovation on Classification


## Introduction 
In the last two years, amidst the broader artificial intelligence boom, AI-powered coding assistants have moved from novelty to mainstream developmental tools. Tools like Github Copilot, OpenAI Codex, Claude Code, Cursor, Gemini, Replit, Windsurf all compete for developer adoption. While each tool offers similar capabilities such as code generation, autocomplete and debugging speedups, they differ significantly in their strengths, weaknesses and suitability for specific development workflows. Developers seeking to adopt or switch between these tools often face a problem of incredible information overload; with thousands of opinions scattered across different sites, there is no structured way to compare tools along similar lines. 
We aim to address this gap in a new way: instead of asking “which coding AI tool is the best?”, we ask the question of which tool to use for which task and under which circumstances. To answer this, we built an end-to-end opinion search engine that crawls Reddit, indexes them with a task-aware schema, classifies sentiment and presents the results through a Solr search interface.

## Crawling
To construct our corpus, we crawled Reddit using public JSON search and permalink endpoints, selecting this platform for its rich, experience-based discussions on AI coding assistants. Our strategy was query-driven, targeting 800 initial posts across eight specific categories—including GitHub Copilot, Claude Code, and Gemini Code Assist—to ensure a balanced, tool-focused dataset. To maintain crawler stability, we implemented rotating proxies with health tracking and retry logic.

During the enrichment phase, we expanded these initial posts by retrieving their full recursive comment threads, which were then flattened into analysis-ready records. Our preprocessing pipeline standardized the data by removing non-linguistic noise such as URLs, Reddit mentions, markdown formatting, and placeholders like "[deleted]". We also performed deduplication and normalized the text through lowercasing and punctuation stripping, while intentionally avoiding lemmatization to preserve original sentiment cues. While we began with 800 posts, this recursive enrichment process significantly increased the final dataset size due to the depth of the nested comment threads. By storing the results in a structured JSON format containing titles, bodies, and comments, we produced a clean, comprehensive corpus ready for high-fidelity sentiment classification.
to start solr

## Index and Querying
The final stage of the pipeline invovles ingesting the enriched and classified data into a Solr search index. Using merge_sentiment.py, the system performs a relational join between the structured reddit data, and classification outputs. Categorical metadata, such as tools, reasons and workflows are also serialized into pipe separated strings.

For the user interface, we developed a simple django web application for the user to perform queries on. The web application interfaces to the Solr serach index via the pysolr library. When a user enters a search term, their query is first split, then stopwords are removed, then lemmatized before targeting the text_index field, applying logical AND operator between every token, along with a ~1 fuzzy search factor to account for minor character variations. 

For sidebar filters, the application passes paramters to pysolr using filter queries. These filters include date range, categorical metadata, sentiment, comment body or post and prediction confidence.
Results are returned as a ranked list based on a combination of TF-IDF relevance on the text_index and the rank_score.

## Classification
For our classification, we developed a sentiment classification pipeline to process our Reddit corpus, focusing on balancing high accuracy with structural interpretability. The workflow began with extensive data preprocessing to minimize noise, including the removal of URLs, Reddit-specific mentions, and markdown formatting, while preserving emotional punctuation like exclamation marks and question marks. We employed a hybrid methodology utilizing SenticNet as a lightweight subjectivity gate to filter opinionated content before applying transformer-based models like Cardiff RoBERTa and RoBERTa-MNLI. Our benchmarking on a manually labeled 1,000-record ground truth dataset revealed that the Cardiff-only configuration was the superior performer, achieving a macro-F1 score of 0.7808 and an accuracy of 0.7780. To confirm the system’s real-world reliability, we conducted a random accuracy test on the remaining 53,485 records, which demonstrated stable behavior and practical efficiency beyond the initial evaluation set.

## Innovation on Classification
Our ablation study systematically evaluated several targeted innovations designed to address complex linguistic challenges such as sarcasm and neutral ambiguity. 
These improvements included a:
* Cardiff-dominant decision policy
* Neutral suppression with margin logic
* Guarded sarcasm enhancement
* WSD and NER contextual enrichment
Incremental testing against the Cardiff-only baseline showed that while these decision rules slightly decreased predictive performance—with accuracy dropping from 0.7780 to 0.7490—they significantly enhanced system interpretability and control. We also explored contextual enrichment through Word Sense Disambiguation (WSD) and Named Entity Recognition (NER); however, these provided limited aggregate gains in this specific dataset, with NER resulting in a minor accuracy decline of 0.004. Ultimately, the study confirmed that the baseline Cardiff model remained exceptionally robust, while our innovations established a clear roadmap for handling more entity-sensitive sentiment patterns in the future

## Solr instructions
to start solr
```bash
docker compose up --build 
```

get container name/id
```bash
docker ps 
```

create solr core
```bash
docker exec -it <container_id> solr create_core -c info_retrieval
```

copy file into docker container
```bash
docker cp your_file.csv <container_id>:/data/your_file.csv

```

upload file into solr core
```bash
docker exec -it <container_id> bin/solr post -c info_retrieval /data/your_file.csv
```
