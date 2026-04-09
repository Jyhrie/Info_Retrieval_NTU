import pandas as pd

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