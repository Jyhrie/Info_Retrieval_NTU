from __future__ import annotations

from utils import build_summary_table

import argparse
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from nltk.corpus import stopwords
import pandas as pd
from cardiff_classifier import CardiffClassifier 
BATCH_SIZE = 32
NEUTRAL_CONF_THRESHOLD = 0.60
NEUTRAL_MARGIN_THRESHOLD = 0.10

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Cardiff-only reference classification on input.csv")
    parser.add_argument("--input-csv", default="indexed.csv", help="Path to input.csv")
    parser.add_argument(
        "--output-root",
        default="outputs",
        help="Output root folder under classification/ (default: outputs)",
    )
    parser.add_argument(
        "--run-id",
        default="",
        help="Optional run id for output folder. Default uses timestamp.",
    )
    parser.add_argument(
        "--output-csv",
        default="",
        help="Optional legacy extra copy path for outputClassification.csv",
    )
    parser.add_argument("--batch-size", type=int, default=32, help="HuggingFace batch size")
    parser.add_argument(
        "--neutral-conf-threshold",
        type=float,
        default=NEUTRAL_CONF_THRESHOLD,
        help="Keep Neutral when top1_prob >= this threshold (default: 0.60)",
    )
    parser.add_argument(
        "--neutral-margin-threshold",
        type=float,
        default=NEUTRAL_MARGIN_THRESHOLD,
        help="Keep ambiguous Neutral when margin < this threshold (default: 0.10)",
    )
    return parser.parse_args()

def main() -> int:
    args = parse_args()
    here = Path(__file__).resolve().parent

    input_csv = Path(args.input_csv)
    if not input_csv.is_absolute():
        input_csv = (here / input_csv).resolve()

    if not input_csv.exists():
        print(f"Input file not found: {input_csv}")
        return 1

    df = pd.read_csv(input_csv)
    if "text_clean" not in df.columns:
        print("Input is missing required column: text_clean")
        return 1

    t0 = time.time()
    cardiff_classifier = CardiffClassifier(batch_size=BATCH_SIZE)
    out_df = cardiff_classifier.classify_dataframe(
        df,
        neutral_conf_threshold=float(args.neutral_conf_threshold),
        neutral_margin_threshold=float(args.neutral_margin_threshold),
    )
    summary_df = build_summary_table(out_df)
    elapsed = time.time() - t0

    run_id = str(args.run_id).strip() or datetime.now().strftime("%Y%m%d_%H%M%S")
    output_root = Path(args.output_root)
    if not output_root.is_absolute():
        output_root = (here / output_root).resolve()
    run_dir = output_root / f"run_{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)

    output_csv = run_dir / "outputClassification.csv"
    output_summary_csv = run_dir / "outputSummary.csv"

    out_df.to_csv(output_csv, index=False)
    summary_df.to_csv(output_summary_csv, index=False)

    if str(args.output_csv).strip():
        legacy_copy = Path(args.output_csv)
        if not legacy_copy.is_absolute():
            legacy_copy = (here / legacy_copy).resolve()
        legacy_copy.parent.mkdir(parents=True, exist_ok=True)
        out_df.to_csv(legacy_copy, index=False)
        print(f"Legacy extra copy written: {legacy_copy}")

    print("Classification complete")
    print(f"Input rows: {len(df)}")
    print(f"Run folder: {run_dir}")
    print(f"Output file: {output_csv}")
    print(f"Summary file: {output_summary_csv}")
    print(f"Elapsed seconds: {elapsed:.2f}")
    print("Predicted class counts:")
    print(out_df["sentiment"].value_counts().to_string())
    return 0

if __name__ == "__main__":
    sys.exit(main())