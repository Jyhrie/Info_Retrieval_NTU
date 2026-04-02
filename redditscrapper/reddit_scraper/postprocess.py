"""Post-processing utilities: cleaning and corpus analysis."""

from __future__ import annotations

import argparse
import csv
import html
import json
import random
import re
from collections import Counter
from pathlib import Path
from typing import Any


EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "]+",
    flags=re.UNICODE,
)

WORD_PATTERN = re.compile(r"\b\w+\b", flags=re.UNICODE)
URL_RE = re.compile(r"https?://\S+|www\.\S+", flags=re.IGNORECASE)
MENTION_RE = re.compile(r"\b[ur]/[A-Za-z0-9_]+\b", flags=re.IGNORECASE)
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\([^\)]+\)")
MARKDOWN_STYLE_RE = re.compile(r"[*_`~]+")
QUOTE_PREFIX_RE = re.compile(r"^>+", flags=re.MULTILINE)
SPACE_RE = re.compile(r"\s+")


def remove_emojis(text: Any) -> str:
    """Remove emojis from text while preserving non-emoji characters."""
    return EMOJI_PATTERN.sub("", str(text or ""))


def normalize_text(text: Any) -> str:
    """Normalize social text for cleaner indexing-friendly output."""
    s = html.unescape(str(text or ""))
    s = URL_RE.sub(" ", s)
    s = MENTION_RE.sub(" ", s)
    s = MARKDOWN_LINK_RE.sub(r"\1", s)
    s = MARKDOWN_STYLE_RE.sub(" ", s)
    s = QUOTE_PREFIX_RE.sub(" ", s)
    s = remove_emojis(s)
    s = SPACE_RE.sub(" ", s).strip()
    return s


def _load_posts(input_file: Path) -> list[dict[str, Any]]:
    with open(input_file, "r", encoding="utf-8") as f:
        payload = json.load(f)

    if isinstance(payload, dict) and "posts" in payload:
        return payload.get("posts", [])
    if isinstance(payload, list):
        return payload
    return []


def _load_records_from_csv(input_file: Path) -> list[dict[str, str]]:
    """Load flat records from CSV input (for indexed/refined/evaluation datasets)."""
    records: list[dict[str, str]] = []

    with open(input_file, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []

        if "text_clean" not in fieldnames:
            raise ValueError("CSV input must contain a 'text_clean' column")

        for row_idx, row in enumerate(reader, start=1):
            text_clean = str(row.get("text_clean", "") or "").strip()
            source_id = str(row.get("source_id", "") or "").strip()
            date_val = str(
                row.get("date")
                or row.get("created_utc")
                or row.get("created_at")
                or row.get("timestamp")
                or ""
            ).strip()
            if not source_id:
                id_fallback = str(row.get("id", "") or "").strip()
                source_id = id_fallback if id_fallback else f"row:{row_idx}"

            records.append(
                {
                    "source_id": source_id,
                    "record_type": str(row.get("record_type", "") or "").strip(),
                    "text_part": str(row.get("text_part", "") or "").strip(),
                    "post_id": str(row.get("post_id", "") or "").strip(),
                    "date": date_val,
                    # For CSV mode, raw text is not available, so we mirror text_clean.
                    "text": text_clean,
                    "text_clean": text_clean,
                }
            )

    # Backfill missing dates using post-level rows with the same post_id.
    # Preference order: post_title -> post_body -> any row with date under same post_id.
    post_date_by_post_id: dict[str, str] = {}

    for rec in records:
        post_id = str(rec.get("post_id", "") or "").strip()
        rec_date = str(rec.get("date", "") or "").strip()
        if not post_id or not rec_date:
            continue

        if rec.get("record_type") == "post" and rec.get("text_part") == "post_title":
            post_date_by_post_id[post_id] = rec_date

    for rec in records:
        post_id = str(rec.get("post_id", "") or "").strip()
        rec_date = str(rec.get("date", "") or "").strip()
        if not post_id or not rec_date or post_id in post_date_by_post_id:
            continue

        if rec.get("record_type") == "post" and rec.get("text_part") == "post_body":
            post_date_by_post_id[post_id] = rec_date

    for rec in records:
        post_id = str(rec.get("post_id", "") or "").strip()
        rec_date = str(rec.get("date", "") or "").strip()
        if not post_id or not rec_date or post_id in post_date_by_post_id:
            continue
        post_date_by_post_id[post_id] = rec_date

    for rec in records:
        if str(rec.get("date", "") or "").strip():
            continue
        post_id = str(rec.get("post_id", "") or "").strip()
        if post_id and post_id in post_date_by_post_id:
            rec["date"] = post_date_by_post_id[post_id]

    return records


def _extract_records(posts: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Extract textual records from posts and nested comments."""
    records: list[dict[str, str]] = []

    def walk_comments(
        comments: list[dict[str, Any]],
        post_id: str,
        post_date: str = "",
        path_prefix: str = "",
    ) -> None:
        for idx, c in enumerate(comments or []):
            body = str(c.get("body", "") or "")
            comment_id = str(c.get("id", "") or "")
            comment_date = str(c.get("created_utc") or c.get("date") or post_date or "")
            path_id = f"{path_prefix}{idx}"
            source_id = f"comment:{comment_id}" if comment_id else f"comment:{post_id}:{path_id}"
            records.append(
                {
                    "source_id": source_id,
                    "record_type": "comment",
                    "text_part": "comment_body",
                    "post_id": post_id,
                    "date": comment_date,
                    "text": body,
                }
            )
            walk_comments(c.get("replies", []) or [], post_id, post_date, path_prefix=f"{path_id}.")

    for post in posts:
        post_id = str(post.get("id", "") or "")
        title = str(post.get("title", "") or "")
        body = str(post.get("body", "") or "")
        description = str(post.get("description", "") or "")
        post_date = str(post.get("created_utc") or post.get("date") or "")

        records.append(
            {
                "source_id": f"post:{post_id}:title",
                "record_type": "post",
                "text_part": "post_title",
                "post_id": post_id,
                "date": post_date,
                "text": title,
            }
        )

        records.append(
            {
                "source_id": f"post:{post_id}:body",
                "record_type": "post",
                "text_part": "post_body",
                "post_id": post_id,
                "date": post_date,
                "text": body if body else description,
            }
        )

        walk_comments(post.get("comments", []) or [], post_id, post_date)

    return records


def _analyze_records(cleaned_records: list[dict[str, str]], top_n: int) -> dict[str, Any]:
    all_tokens: list[str] = []
    for rec in cleaned_records:
        all_tokens.extend([t.lower() for t in WORD_PATTERN.findall(rec["text_clean"])])

    total_records = len(cleaned_records)
    total_words = len(all_tokens)
    unique_types = len(set(all_tokens))
    top_words = Counter(all_tokens).most_common(max(1, top_n))

    return {
        "Total_records": total_records,
        "Total_words": total_words,
        "Total_types": unique_types,
        "top_words": [{"word": w, "count": c} for w, c in top_words],
    }


def _write_evaluation_sample_csv(
    cleaned_records: list[dict[str, str]],
    eval_csv_file: Path,
    sample_size: int,
    seed: int = 8888,
) -> int:
    """Write a separate evaluation sample CSV with sentiment label columns."""
    valid_records = [r for r in cleaned_records if str(r.get("text_clean", "")).strip()]
    n = min(max(1, int(sample_size)), len(valid_records)) if valid_records else 0

    sampled: list[dict[str, str]] = []
    if n > 0:
        rng = random.Random(seed)
        sampled = rng.sample(valid_records, n)

    eval_csv_file.parent.mkdir(parents=True, exist_ok=True)
    with open(eval_csv_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "source_id",
                "record_type",
                "text_part",
                "post_id",
                "date",
                "text_clean",
                "neutral",
                "positive",
                "negative",
            ],
        )
        writer.writeheader()
        for row in sampled:
            writer.writerow(
                {
                    "source_id": row.get("source_id", ""),
                    "record_type": row.get("record_type", ""),
                    "text_part": row.get("text_part", ""),
                    "post_id": row.get("post_id", ""),
                    "date": row.get("date", ""),
                    "text_clean": row.get("text_clean", ""),
                    "neutral": "",
                    "positive": "",
                    "negative": "",
                }
            )

    return len(sampled)


def _write_refined_dataset_csv(cleaned_records: list[dict[str, str]], refined_csv_file: Path) -> int:
    """Write refined dataset without raw text column (keeps text_clean)."""
    refined_csv_file.parent.mkdir(parents=True, exist_ok=True)
    with open(refined_csv_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["source_id", "record_type", "text_part", "post_id", "date", "text_clean"],
        )
        writer.writeheader()
        for row in cleaned_records:
            writer.writerow(
                {
                    "source_id": row.get("source_id", ""),
                    "record_type": row.get("record_type", ""),
                    "text_part": row.get("text_part", ""),
                    "post_id": row.get("post_id", ""),
                    "date": row.get("date", ""),
                    "text_clean": row.get("text_clean", ""),
                }
            )
    return len(cleaned_records)


def _build_cleaned_records(input_file: Path) -> list[dict[str, str]]:
    """Build normalized records from JSON/CSV input while preserving metadata."""
    cleaned_records: list[dict[str, str]] = []

    if input_file.suffix.lower() == ".csv":
        csv_records = _load_records_from_csv(input_file)
        for rec in csv_records:
            cleaned_records.append(
                {
                    **rec,
                    "text_clean": str(rec.get("text_clean", "") or "").strip(),
                }
            )
    else:
        posts = _load_posts(input_file)
        raw_records = _extract_records(posts)
        for rec in raw_records:
            cleaned_records.append(
                {
                    **rec,
                    "text_clean": normalize_text(rec["text"]),
                }
            )

    return cleaned_records


def process_scraped_output(
    input_file: Path,
    cleaned_csv_file: Path,
    refined_csv_file: Path,
    analysis_json_file: Path,
    top_n: int = 20,
    eval_csv_file: Path | None = None,
    eval_sample_size: int = 1000,
    eval_seed: int = 8888,
) -> dict[str, Any]:
    """Generate cleaned CSV and corpus analysis JSON from scraped JSON or CSV input."""
    cleaned_records = _build_cleaned_records(input_file)

    cleaned_csv_file.parent.mkdir(parents=True, exist_ok=True)
    with open(cleaned_csv_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["source_id", "record_type", "text_part", "post_id", "date", "text", "text_clean"],
        )
        writer.writeheader()
        writer.writerows(cleaned_records)

    refined_rows = _write_refined_dataset_csv(cleaned_records=cleaned_records, refined_csv_file=refined_csv_file)

    analysis = _analyze_records(cleaned_records, top_n=top_n)
    analysis_json_file.parent.mkdir(parents=True, exist_ok=True)
    with open(analysis_json_file, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)

    if eval_csv_file is None:
        eval_csv_file = input_file.parent / "evaluation_dataset_1000.csv"
    sampled_count = _write_evaluation_sample_csv(
        cleaned_records=cleaned_records,
        eval_csv_file=eval_csv_file,
        sample_size=eval_sample_size,
        seed=eval_seed,
    )

    return {
        "cleaned_csv_file": str(cleaned_csv_file),
        "refined_csv_file": str(refined_csv_file),
        "refined_rows": refined_rows,
        "analysis_json_file": str(analysis_json_file),
        "evaluation_csv_file": str(eval_csv_file),
        "evaluation_rows": sampled_count,
        **analysis,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run post-processing (emoji cleaning + corpus analysis) on Reddit JSON output"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to input JSON (results.json/enriched_results.json) or CSV (indexed/refined/evaluation)",
    )
    parser.add_argument(
        "--cleaned-csv",
        default="",
        help="Output cleaned CSV path (default: <input_dir>/results_no_emoji.csv)",
    )
    parser.add_argument(
        "--refined-csv",
        default="",
        help="Output refined CSV path without raw text column (default: <input_dir>/refined_dataset.csv)",
    )
    parser.add_argument(
        "--analysis-json",
        default="",
        help="Output corpus analysis JSON path (default: <input_dir>/corpus_analysis.json)",
    )
    parser.add_argument(
        "--eval-csv",
        default="",
        help="Output evaluation CSV path (default: <input_dir>/evaluation_dataset_1000.csv)",
    )
    parser.add_argument(
        "--eval-size",
        type=int,
        default=1000,
        help="Number of rows to sample for evaluation CSV",
    )
    parser.add_argument(
        "--eval-seed",
        type=int,
        default=8888,
        help="Random seed for deterministic evaluation sampling",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=20,
        help="Top N words to include in analysis output",
    )
    parser.add_argument(
        "--only-refined",
        action="store_true",
        help="Generate only refined_dataset.csv and skip other outputs",
    )
    args = parser.parse_args()

    input_file = Path(args.input)
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    cleaned_csv = Path(args.cleaned_csv) if args.cleaned_csv else (input_file.parent / "results_no_emoji.csv")
    refined_csv = Path(args.refined_csv) if args.refined_csv else (input_file.parent / "refined_dataset.csv")
    analysis_json = Path(args.analysis_json) if args.analysis_json else (input_file.parent / "corpus_analysis.json")
    eval_csv = Path(args.eval_csv) if args.eval_csv else (input_file.parent / "evaluation_dataset_1000.csv")

    if args.only_refined:
        cleaned_records = _build_cleaned_records(input_file)
        refined_rows = _write_refined_dataset_csv(cleaned_records=cleaned_records, refined_csv_file=refined_csv)
        print("✓ Post-processing complete (only refined mode)")
        print(f"  Input: {input_file}")
        print(f"  Refined CSV: {refined_csv} ({refined_rows} rows)")
        return

    result = process_scraped_output(
        input_file=input_file,
        cleaned_csv_file=cleaned_csv,
        refined_csv_file=refined_csv,
        analysis_json_file=analysis_json,
        top_n=max(1, int(args.top_n)),
        eval_csv_file=eval_csv,
        eval_sample_size=max(1, int(args.eval_size)),
        eval_seed=int(args.eval_seed),
    )

    print("✓ Post-processing complete")
    print(f"  Input: {input_file}")
    print(f"  Cleaned CSV: {result['cleaned_csv_file']}")
    print(f"  Refined CSV: {result['refined_csv_file']} ({result['refined_rows']} rows)")
    print(f"  Analysis JSON: {result['analysis_json_file']}")
    print(f"  Evaluation CSV: {result['evaluation_csv_file']} ({result['evaluation_rows']} rows)")
    print(
        f"  Corpus stats -> records={result['Total_records']}, words={result['Total_words']}, types={result['Total_types']}"
    )


if __name__ == "__main__":
    main()
