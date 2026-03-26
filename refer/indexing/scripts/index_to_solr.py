import pandas as pd
import numpy as np
import json

# Load the Excel file
df = pd.read_csv("../../scraper-new/results_no_emoji.csv")

# Just use the first 10 rows
#subset = df.head(10)

# Prepare the Solr-friendly JSON format
docs = []
for _, row in df.iterrows():
    if pd.isna(row['post_content']):
        row['post_content'] = "[No content written by the author]"
    
    originalDateTime = pd.to_datetime(row['created_iso'])
    #Convert to ISO 8601 format
    ISO_datetime = originalDateTime.strftime('%Y-%m-%dT%H:%M:%S.%SZ')

    doc = {
        "id": row['comment_id'],  # Unique ID for the comment
        "post_id": row['post_id'],  # Unique ID
        "subreddit": row['subreddit'],
        "title": row['title'],
        "url": row['post_url'],
        "post_content": row['post_content'],
        "comment_id": row['comment_id'],
        "comment_content": row['comment_body'],
        "comment_author": row['comment_author'],
        "score": row['comment_score'],
        "datetime": ISO_datetime,
    }
    docs.append(doc)

# Save to JSON
with open("../dataset/reddit_index.json", "w") as f:
    json.dump(docs, f, indent=2)

print(f"✅ reddit_index.json created with {len(docs)} documents.")
