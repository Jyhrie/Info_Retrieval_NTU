"""Merge sentiment labels from outputClassification.csv into indexed.csv.

Produces solr_ready.csv — the file intended for Solr ingestion.

Join key: (post_id, text_clean)
  - Rows that match get final_class, rank_score, polarity, subjectivity, sarcasm populated.
  - Unmatched rows get empty/zero defaults so the schema is always consistent.

Usage:
    python indexing/merge_sentiment.py \
        --sentiment redditscrapper/data/ai_coding_agents_1/outputClassification.csv

    # explicit paths:
    python indexing/merge_sentiment.py \
        --indexed   indexing/outputs/indexed.csv \
        --sentiment redditscrapper/data/ai_coding_agents_1/outputClassification.csv \
        --out       indexing/outputs/solr_ready.csv
"""

import argparse
import csv
from pathlib import Path

from common import (
    BASE_FIELDS,
    DERIVED_FIELDS,
    OUTPUT_DIR,
    PROJECT_ROOT,
    SENTIMENT_FIELDS,
    read_output_rows,
    write_csv,
)

DEFAULT_INDEXED_PATH = OUTPUT_DIR / "indexed.csv"
DEFAULT_SENTIMENT_PATH = (
    PROJECT_ROOT / "redditscrapper" / "data" / "ai_coding_agents_1" / "outputClassification.csv"
)
DEFAULT_OUT_PATH = OUTPUT_DIR / "solr_ready.csv"

_POLARITY_MAP = {
    "positive": 1,
    "negative": -1,
    "neutral": 0,
}

ALL_FIELDS = BASE_FIELDS + DERIVED_FIELDS + SENTIMENT_FIELDS


def _load_sentiment_lookup(sentiment_path: Path) -> dict:
    """Build a (post_id, text_clean) → sentiment dict from outputClassification.csv."""
    lookup = {}
    with sentiment_path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            post_id = (row.get("post_id") or "").strip()
            text_clean = (row.get("text_clean") or "").strip()
            if not post_id or not text_clean:
                continue
            key = (post_id, text_clean)
            lookup[key] = {
                "sentiment": (row.get("sentiment") or "").strip(),
                "confidence": (row.get("confidence") or "").strip(),
                "subjectivity": (row.get("subjectivity") or "").strip(),
                "sarcasm": (row.get("sarcasm") or "").strip(),
            }
    return lookup


def _sentiment_row(match: dict | None) -> dict:
    """Convert a lookup hit (or None) into the SENTIMENT_FIELDS dict."""
    if match is None:
        return {f: "" for f in SENTIMENT_FIELDS}

    sentiment = match["sentiment"]
    try:
        rank_score = float(match["confidence"])
    except (ValueError, TypeError):
        rank_score = 0.0

    polarity = _POLARITY_MAP.get(sentiment.lower(), 0)

    return {
        "final_class": sentiment,
        "rank_score": rank_score,
        "polarity": polarity,
        "subjectivity": match["subjectivity"],
        "sarcasm": match["sarcasm"],
    }


def merge(indexed_path: Path, sentiment_path: Path, out_path: Path) -> dict:
    lookup = _load_sentiment_lookup(sentiment_path)

    rows = []
    matched = 0

    for doc in read_output_rows(indexed_path, include_derived=True):
        post_id = (doc.get("post_id") or "").strip()
        text_clean = (doc.get("text_clean") or "").strip()
        key = (post_id, text_clean)

        hit = lookup.get(key)
        if hit:
            matched += 1

        sentiment_data = _sentiment_row(hit)

        # Re-serialise derived list fields back to pipe-separated strings for CSV
        row = {f: doc.get(f, "") for f in BASE_FIELDS}
        for f in DERIVED_FIELDS:
            val = doc.get(f, [])
            row[f] = "|".join(val) if isinstance(val, list) else (val or "")
        row.update(sentiment_data)
        rows.append(row)

    write_csv(out_path, rows, ALL_FIELDS)
    return {
        "total_rows": len(rows),
        "matched": matched,
        "unmatched": len(rows) - matched,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge sentiment into indexed.csv → solr_ready.csv")
    parser.add_argument("--indexed", default=str(DEFAULT_INDEXED_PATH), help="Path to indexed.csv")
    parser.add_argument(
        "--sentiment",
        default=str(DEFAULT_SENTIMENT_PATH),
        help="Path to outputClassification.csv",
    )
    parser.add_argument("--out", default=str(DEFAULT_OUT_PATH), help="Output path for solr_ready.csv")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    indexed_path = Path(args.indexed).resolve()
    sentiment_path = Path(args.sentiment).resolve()
    out_path = Path(args.out).resolve()

    for p, label in [(indexed_path, "--indexed"), (sentiment_path, "--sentiment")]:
        if not p.exists():
            print(f"Error: {label} file not found: {p}")
            return 1

    out_path.parent.mkdir(parents=True, exist_ok=True)

    stats = merge(indexed_path, sentiment_path, out_path)

    print("Merge complete")
    print(f"- indexed={indexed_path}")
    print(f"- sentiment={sentiment_path}")
    print(f"- out={out_path}")
    print(f"- total_rows={stats['total_rows']}")
    print(f"- sentiment_matched={stats['matched']}")
    print(f"- sentiment_unmatched={stats['unmatched']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
