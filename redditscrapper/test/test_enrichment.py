# To run this test, use:
# python -m test.test_enrichment
# (Run this command from the redditscrapper directory)
import os
import json

# Import enrich_posts from the main enricher module
from reddit_scraper.enricher import enrich_posts

# Paths
SAMPLE_INPUT = os.path.join(os.path.dirname(__file__), 'database', 'sample_posts.json')
SAMPLE_OUTPUT = os.path.join(os.path.dirname(__file__), 'database', 'sample_enriched.json')

if __name__ == "__main__":
    # Run enrichment and load results
    enrich_posts(SAMPLE_INPUT, SAMPLE_OUTPUT)

    # Load input and output for summary
    with open(SAMPLE_INPUT, 'r') as f:
        input_data = json.load(f)
    with open(SAMPLE_OUTPUT, 'r') as f:
        output_data = json.load(f)

    input_posts = input_data["posts"] if isinstance(input_data, dict) and "posts" in input_data else input_data
    output_posts = output_data["posts"] if isinstance(output_data, dict) and "posts" in output_data else output_data

    total = len(input_posts)
    success = 0
    failed = 0
    failed_ids = []
    for post in output_posts:
        # Consider enriched if it has 'body' or 'comments' (may adjust as needed)
        if (post.get("body") or post.get("comments")) and not (isinstance(post.get("comments"), list) and len(post.get("comments")) == 0 and not post.get("body")):
            success += 1
        else:
            failed += 1
            failed_ids.append(post.get("id", "unknown"))

    # Move summary to the top of the output JSON
    summary = {
        "enrichment_summary": {
            "total": total,
            "success": success,
            "failed": failed,
            "failed_ids": failed_ids
        }
    }
    # If output_data is a dict with metadata and posts, preserve order: summary, metadata, posts
    if isinstance(output_data, dict) and "posts" in output_data:
        new_output = {**summary}
        # Add metadata if present
        if "metadata" in output_data:
            new_output["metadata"] = output_data["metadata"]
        new_output["posts"] = output_data["posts"]
    else:
        # If output is just a list, put summary and then posts
        new_output = {**summary, "posts": output_data}

    with open(SAMPLE_OUTPUT, 'w') as f:
        json.dump(new_output, f, indent=2)
    print(f"Enrichment complete. Output written to {SAMPLE_OUTPUT}")
    print(f"Summary: total={total}, success={success}, failed={failed}, failed_ids={failed_ids}")
