from transformers import pipeline
from utils import _normalize_hf_label
from utils import _build_category_value
import pandas as pd

NEUTRAL_CONF_THRESHOLD = 0.60
NEUTRAL_MARGIN_THRESHOLD = 0.10
CARDIFF_MODEL_ID = "cardiffnlp/twitter-roberta-base-sentiment-latest"

class HuggingFaceClassifier:
    def __init__(self, batch_size: int = 32) -> None:
        self.batch_size = max(1, int(batch_size))
        self.hf = self._load_hf()
    pass