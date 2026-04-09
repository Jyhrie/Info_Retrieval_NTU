#!/usr/bin/env python3
"""Cardiff-only production classifier for CSV inputs.

Input must follow indexed.csv-style headers and include at least `text_clean`.
Outputs a report-friendly schema with a single sentiment field, confidence,
subjectivity score, sarcasm placeholder, and topic metadata.
"""

# How to run:
# python classification/run_classification.py \
#   --input-csv redditscrapper/data/ai_coding_agents_1/evaluation_dataset_1000.csv
#
# python classification/run_classification.py
#
# Input/output path settings:
# - Input file path: --input-csv <path-to-input.csv>
# - Output root folder: --output-root <folder> (default: classification/outputs)
# - Run folder name: --run-id <name> (default: timestamp, e.g. run_20260402_153000)
# - Optional extra copy of classification CSV: --output-csv <path-to-outputClassification.csv>
#
# Example with explicit input + output folder:
# python classification/run_classification.py \
#   --input-csv redditscrapper/data/ai_coding_agents_1/evaluation_dataset_1000.csv \
#   --output-root classification/outputs \
#   --run-id my_run_01

from __future__ import annotations

import argparse
import re
import sys
import time
import warnings
from datetime import datetime
from pathlib import Path
from nltk.corpus import stopwords

import pandas as pd


CARDIFF_MODEL_ID = "cardiffnlp/twitter-roberta-base-sentiment-latest"
NEUTRAL_CONF_THRESHOLD = 0.60
NEUTRAL_MARGIN_THRESHOLD = 0.10

WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_']+")
FALLBACK_STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "to",
    "of",
    "for",
    "in",
    "on",
    "at",
    "is",
    "it",
    "this",
    "that",
    "with",
    "as",
    "are",
    "be",
    "was",
    "were",
    "i",
    "you",
    "we",
    "they",
    "my",
    "your",
    "our",
    "their",
    "from",
    "have",
    "has",
    "had",
    "but",
    "not",
    "so",
    "if",
    "just",
    "can",
    "will",
    "would",
    "should",
    "do",
    "does",
    "did",
    "about",
    "what",
    "how",
    "when",
    "where",
    "who",
    "why",
}


def _load_stopwords() -> set[str]:
    try:
        return set(stopwords.words("english"))
    except LookupError:
        warnings.warn(
            "NLTK stopwords corpus is missing; using a built-in fallback stopword list.",
            RuntimeWarning,
            stacklevel=2,
        )
        return set(FALLBACK_STOPWORDS)


STOPWORDS = _load_stopwords()


def _resolve_existing_input_path(path_value: str, script_dir: Path) -> Path:
    """Resolve an input path from CWD first, then script dir for compatibility."""
    raw = Path(path_value)
    if raw.is_absolute():
        return raw.resolve()

    cwd_candidate = (Path.cwd() / raw).resolve()
    if cwd_candidate.exists():
        return cwd_candidate

    return (script_dir / raw).resolve()


def _resolve_output_path(path_value: str, script_dir: Path, *, prefer_script_for_simple: bool = False) -> Path:
    """Resolve output paths to support both repo-root and script-relative usage."""
    raw = Path(path_value)
    if raw.is_absolute():
        return raw.resolve()

    cwd_candidate = (Path.cwd() / raw).resolve()
    script_candidate = (script_dir / raw).resolve()

    if prefer_script_for_simple and len(raw.parts) == 1:
        return script_candidate

    cwd_parent_exists = cwd_candidate.parent.exists()
    script_parent_exists = script_candidate.parent.exists()
    if cwd_parent_exists and not script_parent_exists:
        return cwd_candidate
    if script_parent_exists and not cwd_parent_exists:
        return script_candidate

    return cwd_candidate


def _normalize_hf_label(raw_label: str) -> str:
    label = str(raw_label or "").strip().upper()
    alias = {
        "POS": "POS",
        "POSITIVE": "POS",
        "VERY POSITIVE": "POS",
        "NEG": "NEG",
        "NEGATIVE": "NEG",
        "VERY NEGATIVE": "NEG",
        "NEU": "NEU",
        "NEUTRAL": "NEU",
        "LABEL_0": "NEG",
        "LABEL_1": "NEU",
        "LABEL_2": "POS",
    }
    if label in alias:
        return alias[label]
    if "POS" in label:
        return "POS"
    if "NEG" in label:
        return "NEG"
    if "NEU" in label:
        return "NEU"
    return "NEU"


def _build_category_value(row: pd.Series) -> str:
    merged = []
    for col in ["tool", "reason", "workflow", "trust"]:
        raw = str(row.get(col, "") or "").strip()
        if raw == "":
            continue
        parts = [p.strip() for p in raw.split("|") if p.strip()]
        for p in parts:
            if p not in merged:
                merged.append(p)
    return "|".join(merged)


def _topic_key(text: str, top_k: int = 3) -> str:
    # Build a compact topic key from the first few meaningful words.
    # This lets similar comments cluster together even when full text differs.
    tokens = [
        t.lower()
        for t in WORD_RE.findall(str(text or ""))
        if len(t) >= 3 and t.lower() not in STOPWORDS
    ]
    if not tokens:
        return "misc"

    # Keep stable order by first appearance while removing duplicates.
    seen = []
    for tok in tokens:
        if tok not in seen:
            seen.append(tok)
        if len(seen) >= top_k:
            break
    return "|".join(seen) if seen else "misc"


def _top_repeated_opinions(df: pd.DataFrame, sentiment_value: str, top_n: int = 5) -> pd.DataFrame:
    filtered = df[df["sentiment"] == sentiment_value].copy()
    if filtered.empty:
        return pd.DataFrame(columns=["rank", "text_clean", "mean_confidence", "topic_key"])

    filtered["topic_key"] = filtered["text_clean"].apply(_topic_key)

    # Group by topic key instead of exact text so paraphrases are counted together.
    grouped = (
        filtered.groupby("topic_key", as_index=False)
        .agg(count=("text_clean", "size"), mean_confidence=("confidence", "mean"))
        .sort_values(["count", "mean_confidence"], ascending=[False, False])
        .head(top_n)
        .reset_index(drop=True)
    )

    # Attach one representative text for each topic key.
    reps = (
        filtered.groupby("topic_key", as_index=False)
        .agg(text_clean=("text_clean", "first"))
    )

    grouped = grouped.merge(reps, on="topic_key", how="left")

    # Final ranking is by grouped frequency, with confidence as tie-breaker.
    grouped.insert(0, "rank", grouped.index + 1)
    grouped["mean_confidence"] = grouped["mean_confidence"].round(4)
    return grouped[["rank", "topic_key", "text_clean", "mean_confidence"]]


def build_summary_table(df: pd.DataFrame) -> pd.DataFrame:
    # Totals are direct sentiment counts from outputClassification.csv.
    pos_total = int((df["sentiment"] == "Positive").sum())
    neg_total = int((df["sentiment"] == "Negative").sum())
    neu_total = int((df["sentiment"] == "Neutral").sum())

    totals = pd.DataFrame(
        [
            {"section": "totals", "metric": "total_rows", "value": int(len(df))},
            {"section": "totals", "metric": "positive_total", "value": pos_total},
            {"section": "totals", "metric": "negative_total", "value": neg_total},
            {"section": "totals", "metric": "neutral_total", "value": neu_total},
        ]
    )

    top_pos = _top_repeated_opinions(df, sentiment_value="Positive", top_n=5)
    if not top_pos.empty:
        top_pos = top_pos.assign(section="top_positive_repeated", metric="text_clean", value="")

    top_neg = _top_repeated_opinions(df, sentiment_value="Negative", top_n=5)
    if not top_neg.empty:
        top_neg = top_neg.assign(section="top_negative_repeated", metric="text_clean", value="")

    sections = [totals]
    if not top_pos.empty:
        sections.append(top_pos)
    if not top_neg.empty:
        sections.append(top_neg)

    summary = pd.concat(sections, ignore_index=True)
    expected_cols = ["section", "metric", "value", "rank", "topic_key", "text_clean", "mean_confidence"]
    for col in expected_cols:
        if col not in summary.columns:
            summary[col] = ""
    return summary[expected_cols]


class CardiffOnlyClassifier:
    def __init__(self, batch_size: int = 32) -> None:
        self.batch_size = max(1, int(batch_size))
        self._hf_pipeline = self._import_hf_pipeline()
        self.hf = self._load_hf()

    @staticmethod
    def _import_hf_pipeline():
        try:
            from transformers import pipeline as hf_pipeline

            return hf_pipeline
        except Exception as exc:  # pragma: no cover
            raise ImportError(
                "Missing dependency: transformers. Install with 'pip install transformers torch'."
            ) from exc

    def _load_hf(self):
        try:
            model = self._hf_pipeline(
                "sentiment-analysis",
                model=CARDIFF_MODEL_ID,
                tokenizer=CARDIFF_MODEL_ID,
                truncation=True,
                max_length=512,
            )
            print(f"Loaded Cardiff model: {CARDIFF_MODEL_ID}")
            return model
        except Exception as exc:
            raise RuntimeError(f"Could not load Cardiff model: {CARDIFF_MODEL_ID}\n{exc}") from exc

    @staticmethod
    def _ranked_from_output(out) -> dict:
        candidates = out
        if isinstance(candidates, dict):
            candidates = [candidates]
        if isinstance(candidates, list) and len(candidates) > 0 and isinstance(candidates[0], list):
            candidates = candidates[0]

        agg = {"POS": 0.0, "NEG": 0.0, "NEU": 0.0}
        if isinstance(candidates, list):
            for item in candidates:
                lab = _normalize_hf_label(str(item.get("label", "NEU")))
                sc = float(item.get("score", 0.0))
                agg[lab] = max(agg.get(lab, 0.0), sc)

        ranked = sorted(agg.items(), key=lambda x: x[1], reverse=True)
        top1_label, top1_prob = ranked[0]
        top2_label, top2_prob = ranked[1]
        margin = float(top1_prob - top2_prob)

        return {
            "ranked": ranked,
            "top1_label": top1_label,
            "top1_prob": float(top1_prob),
            "top2_label": top2_label,
            "top2_prob": float(top2_prob),
            "margin": margin,
            "prob_pos": float(agg.get("POS", 0.0)),
            "prob_neg": float(agg.get("NEG", 0.0)),
            "prob_neu": float(agg.get("NEU", 0.0)),
        }

    @staticmethod
    def _apply_neutral_suppression(
        top1_label: str,
        top1_prob: float,
        top2_label: str,
        margin: float,
        neutral_conf_threshold: float,
        neutral_margin_threshold: float,
    ) -> tuple[str, str]:
        if top1_label != "NEU":
            return top1_label, "cardiff_default"

        if top1_prob >= neutral_conf_threshold:
            return "NEU", "neutral_confident"

        if margin < neutral_margin_threshold:
            return "NEU", "neutral_keep_ambiguous"

        return top2_label, "neutral_suppressed_low_conf"

    def classify_dataframe(
        self,
        df: pd.DataFrame,
        neutral_conf_threshold: float = NEUTRAL_CONF_THRESHOLD,
        neutral_margin_threshold: float = NEUTRAL_MARGIN_THRESHOLD,
    ) -> pd.DataFrame:
        dfr = df.copy()
        dfr["text_clean"] = dfr.get("text_clean", "").fillna("").astype(str)

        if "date" not in dfr.columns:
            dfr["date"] = pd.Timestamp.now().date().isoformat()
        else:
            dfr["date"] = dfr["date"].fillna(pd.Timestamp.now().date().isoformat()).astype(str)

        dfr["source"] = "reddit"

        # Keep source_id in output; fallback to id when source_id is unavailable.
        if "source_id" not in dfr.columns:
            dfr["source_id"] = dfr["id"].astype(str) if "id" in dfr.columns else ""
        else:
            dfr["source_id"] = dfr["source_id"].fillna("").astype(str)
        dfr["post_body"] = dfr["text_clean"]

        preds = []
        texts = dfr["text_clean"].tolist()
        total_rows = len(texts)
        total_batches = max(1, (total_rows + self.batch_size - 1) // self.batch_size)
        progress_step = max(1, total_batches // 10)
        print(
            f"[progress] Starting inference: rows={total_rows}, batch_size={self.batch_size}, batches={total_batches}",
            flush=True,
        )

        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            try:
                outs = self.hf(batch, truncation=True, max_length=128, top_k=None)
            except TypeError:
                outs = self.hf(batch)
            except Exception:
                outs = [{"label": "NEU", "score": 0.0} for _ in batch]

            if isinstance(outs, dict):
                outs = [outs]

            for out in outs:
                ranked = self._ranked_from_output(out)
                final_norm, route = self._apply_neutral_suppression(
                    top1_label=ranked["top1_label"],
                    top1_prob=float(ranked["top1_prob"]),
                    top2_label=ranked["top2_label"],
                    margin=float(ranked["margin"]),
                    neutral_conf_threshold=neutral_conf_threshold,
                    neutral_margin_threshold=neutral_margin_threshold,
                )

                pred_label = {
                    "POS": "Positive",
                    "NEG": "Negative",
                    "NEU": "Neutral",
                }.get(final_norm, "Neutral")

                preds.append(
                    {
                        "top1_label": ranked["top1_label"],
                        "top1_prob": float(ranked["top1_prob"]),
                        "top2_label": ranked["top2_label"],
                        "top2_prob": float(ranked["top2_prob"]),
                        "margin": float(ranked["margin"]),
                        "prob_pos": float(ranked["prob_pos"]),
                        "prob_neg": float(ranked["prob_neg"]),
                        "prob_neu": float(ranked["prob_neu"]),
                        "decision_route": route,
                        "final_norm": final_norm,
                        "pred_label": pred_label,
                    }
                )

            batch_idx = (i // self.batch_size) + 1
            if (batch_idx % progress_step == 0) or (batch_idx == total_batches):
                done = min((i + self.batch_size), total_rows)
                print(f"[progress] processed {done}/{total_rows} rows", flush=True)

        pred_df = pd.DataFrame(preds)
        out = pd.concat([dfr.reset_index(drop=True), pred_df], axis=1)

        out["sentiment"] = out["pred_label"]
        out["confidence"] = out["top1_prob"].astype(float)
        out["subjectivity"] = (1.0 - out["prob_neu"].astype(float)).clip(lower=0.0, upper=1.0)
        out["sarcasm"] = "no"
        out["category"] = out.apply(_build_category_value, axis=1)

        preferred = [
            "source_id",
            "id",
            "post_id",
            "record_type",
            "text_part",
            "date",
            "text_clean",
            "source",
            "sentiment",
            "confidence",
            "subjectivity",
            "sarcasm",
            "tool",
            "reason",
            "workflow",
            "trust",
        ]
        final_cols = [c for c in preferred if c in out.columns]
        return out[final_cols]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Cardiff-only reference classification on input.csv")
    parser.add_argument("--input-csv", default="input.csv", help="Path to input.csv")
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

    input_csv = _resolve_existing_input_path(args.input_csv, script_dir=here)

    if not input_csv.exists():
        print(f"Input file not found: {input_csv}")
        return 1

    df = pd.read_csv(input_csv)
    if "text_clean" not in df.columns:
        print("Input is missing required column: text_clean")
        return 1

    t0 = time.time()
    classifier = CardiffOnlyClassifier(batch_size=args.batch_size)
    out_df = classifier.classify_dataframe(
        df,
        neutral_conf_threshold=float(args.neutral_conf_threshold),
        neutral_margin_threshold=float(args.neutral_margin_threshold),
    )
    summary_df = build_summary_table(out_df)
    elapsed = time.time() - t0

    run_id = str(args.run_id).strip() or datetime.now().strftime("%Y%m%d_%H%M%S")
    output_root = _resolve_output_path(
        args.output_root,
        script_dir=here,
        prefer_script_for_simple=True,
    )
    run_dir = output_root / f"run_{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)

    output_csv = run_dir / "outputClassification.csv"
    output_summary_csv = run_dir / "outputSummary.csv"

    out_df.to_csv(output_csv, index=False)
    summary_df.to_csv(output_summary_csv, index=False)

    if str(args.output_csv).strip():
        legacy_copy = _resolve_output_path(args.output_csv, script_dir=here)
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




