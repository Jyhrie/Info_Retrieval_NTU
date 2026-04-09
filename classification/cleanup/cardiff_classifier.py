#!/usr/bin/env python3

from transformers import pipeline as hf_pipeline
from utils import _normalize_hf_label
from utils import _build_category_value
import pandas as pd
import torch

NEUTRAL_CONF_THRESHOLD = 0.60
NEUTRAL_MARGIN_THRESHOLD = 0.10
CARDIFF_MODEL_ID = "cardiffnlp/twitter-roberta-base-sentiment-latest"

class CardiffClassifier:
    def __init__(self, batch_size: int = 32) -> None:
        self.batch_size = max(1, int(batch_size))
        self.hf = self._load_hf()

    def _load_hf(self):
        try:
            model = hf_pipeline(
                "sentiment-analysis",
                model=CARDIFF_MODEL_ID,
                tokenizer=CARDIFF_MODEL_ID,
                truncation=True,
                max_length=512,
            )
            print(f"Loaded Cardiff model: {CARDIFF_MODEL_ID}")
            return model
        except Exception as exc:
            raise RuntimeError(
                f"Could not load Cardiff model: {CARDIFF_MODEL_ID}\n{exc}"
            ) from exc

    @staticmethod
    def _ranked_from_output(out) -> dict:
        candidates = out
        if isinstance(candidates, dict):
            candidates = [candidates]
        if (
            isinstance(candidates, list)
            and len(candidates) > 0
            and isinstance(candidates[0], list)
        ):
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
        
        # 1. Prepare Batching
        texts = df["text_clean"].fillna("").astype(str).tolist()
        total_rows = len(texts)
        total_batches = max(1, (total_rows + self.batch_size - 1) // self.batch_size)
        progress_step = max(1, total_batches // 10)

        print(f"[progress] Starting inference: rows={total_rows}, batch_size={self.batch_size}", flush=True)

        preds = []
        # 2. Batch Inference Loop
        for i in range(0, total_rows, self.batch_size):
            batch = texts[i : i + self.batch_size]
            
            try:
                # Run the Cardiff Sentiment Brain
                outs = self.hf(batch, truncation=True, max_length=128, top_k=None)
            except Exception:
                outs = [{"label": "NEU", "score": 0.0} for _ in batch]

            if isinstance(outs, dict):
                outs = [outs]

            # 3. Decision Logic (Polarity & Subjectivity)
            for out in outs:
                ranked = self._ranked_from_output(out)
                
                # Apply the specific Neutral Suppression requested by the brief
                final_norm, route = self._apply_neutral_suppression(
                    top1_label=ranked["top1_label"],
                    top1_prob=float(ranked["top1_prob"]),
                    top2_label=ranked["top2_label"],
                    margin=float(ranked["margin"]),
                    neutral_conf_threshold=neutral_conf_threshold,
                    neutral_margin_threshold=neutral_margin_threshold,
                )

                pred_label = {"POS": "Positive", "NEG": "Negative", "NEU": "Neutral"}.get(final_norm, "Neutral")

                preds.append({
                    "sentiment": pred_label,
                    "confidence": float(ranked["top1_prob"]),
                    # Subjectivity Detection: 1 - prob_neu
                    "subjectivity": round((1.0 - float(ranked["prob_neu"])), 4),
                    "decision_route": route,
                    "prob_pos": float(ranked["prob_pos"]),
                    "prob_neg": float(ranked["prob_neg"]),
                    "prob_neu": float(ranked["prob_neu"]),
                })

            # Progress Reporting
            batch_idx = (i // self.batch_size) + 1
            if (batch_idx % progress_step == 0) or (batch_idx == total_batches):
                done = min((i + self.batch_size), total_rows)
                print(f"[progress] processed {done}/{total_rows} rows", flush=True)

        # 4. Final Merge: Glue the AI results back to the
        pred_df = pd.DataFrame(preds)
        return pd.concat([df.reset_index(drop=True), pred_df], axis=1)