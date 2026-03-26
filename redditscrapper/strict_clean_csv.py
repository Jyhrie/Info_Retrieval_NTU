#!/usr/bin/env python3
"""Strict cleanup for flattened Reddit CSV and duplicate removal."""

from __future__ import annotations

import argparse
import csv
import html
import re
from pathlib import Path


URL_RE = re.compile(r"https?://\S+|www\.\S+", flags=re.IGNORECASE)
MENTION_RE = re.compile(r"\b[ur]/[A-Za-z0-9_]+\b", flags=re.IGNORECASE)
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\([^\)]+\)")
MARKDOWN_FORMAT_RE = re.compile(r"[*_`~]+")
QUOTE_PREFIX_RE = re.compile(r"^>+", flags=re.MULTILINE)
NON_WORD_RE = re.compile(r"[^\w\s]", flags=re.UNICODE)
SPACE_RE = re.compile(r"\s+")
NUM_ONLY_RE = re.compile(r"^\d+$")
PLACEHOLDERS = {"[deleted]", "[removed]", "deleted", "removed", "na", "n/a", "none"}


def strict_normalize(text: str) -> str:
    """Aggressive normalization for indexing text."""
    s = html.unescape(str(text or ""))
    s = URL_RE.sub(" ", s)
    s = MENTION_RE.sub(" ", s)
    s = MARKDOWN_LINK_RE.sub(r"\1", s)
    s = MARKDOWN_FORMAT_RE.sub(" ", s)
    s = QUOTE_PREFIX_RE.sub(" ", s)
    s = s.lower()
    s = NON_WORD_RE.sub(" ", s)
    s = SPACE_RE.sub(" ", s).strip()

    if s in PLACEHOLDERS:
        return ""

    tokens = [t for t in s.split() if len(t) > 1 and not NUM_ONLY_RE.match(t)]
    return " ".join(tokens)


def clean_and_dedupe(
    input_csv: Path,
    output_csv: Path,
    dedupe: bool = True,
    include_empty: bool = False,
) -> tuple[int, int, int]:
    """Clean a flattened CSV and optionally remove duplicates.

    Returns: (input_rows, output_rows, duplicates_removed)
    """
    with open(input_csv, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        with open(output_csv, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["strict_text"])
            writer.writeheader()
        return (0, 0, 0)

    fieldnames = list(rows[0].keys())
    if "strict_text" not in fieldnames:
        fieldnames.append("strict_text")

    seen: set[tuple[str, str]] = set()
    out_rows: list[dict[str, str]] = []
    dup_removed = 0

    for row in rows:
        source_text = row.get("text_clean") or row.get("text") or ""
        strict_text = strict_normalize(source_text)
        row["strict_text"] = strict_text

        if not include_empty and not strict_text:
            continue

        key = ((row.get("record_type") or "").strip().lower(), strict_text)
        if dedupe:
            if key in seen:
                dup_removed += 1
                continue
            seen.add(key)

        out_rows.append(row)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(output_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)

    return (len(rows), len(out_rows), dup_removed)


def main() -> None:
    parser = argparse.ArgumentParser(description="Strict clean + dedupe flattened Reddit CSV")
    parser.add_argument("--input", required=True, help="Input CSV path (e.g. results_no_emoji.csv)")
    parser.add_argument(
        "--output",
        default="",
        help="Output CSV path (default: <input_stem>_strict_dedup.csv)",
    )
    parser.add_argument("--no-dedupe", action="store_true", help="Disable duplicate removal")
    parser.add_argument("--include-empty", action="store_true", help="Keep rows with empty strict_text")
    args = parser.parse_args()

    input_csv = Path(args.input)
    if not input_csv.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_csv}")

    output_csv = (
        Path(args.output)
        if args.output
        else input_csv.with_name(f"{input_csv.stem}_strict_dedup.csv")
    )

    in_rows, out_rows, dup_removed = clean_and_dedupe(
        input_csv=input_csv,
        output_csv=output_csv,
        dedupe=not args.no_dedupe,
        include_empty=args.include_empty,
    )

    print(f"✓ Input rows: {in_rows}")
    print(f"✓ Output rows: {out_rows}")
    print(f"✓ Duplicates removed: {dup_removed}")
    print(f"✓ Saved: {output_csv}")


if __name__ == "__main__":
    main()
