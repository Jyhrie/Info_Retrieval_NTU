from pathlib import Path
import pandas as pd

base = Path("redditscrapper/data/ai_coding_agents_1")
indexed = base / "indexed.csv"
eval_csv = base / "evaluation_dataset_1000.csv"

if not indexed.exists():
    raise FileNotFoundError(indexed)

df = pd.read_csv(indexed)
required = ["id", "post_id", "record_type", "text_part", "text_clean"]
missing = [c for c in required if c not in df.columns]
if missing:
    raise ValueError(f"Missing columns in indexed.csv: {missing}")

df = df.copy()
df["text_clean"] = df["text_clean"].fillna("").astype(str)
df = df[df["text_clean"].str.strip().str.len() > 0].reset_index(drop=True)
if len(df) < 1000:
    raise ValueError(f"Not enough rows to sample 1000. Available: {len(df)}")

sample = df.sample(n=1000, random_state=8888).reset_index(drop=True)
out = sample[["id", "record_type", "text_part", "post_id", "text_clean"]].copy()
out["neutral"] = ""
out["positive"] = ""
out["negative"] = ""
out.to_csv(eval_csv, index=False)

print(f"Wrote {len(out)} rows to {eval_csv}")
print("Columns:", ",".join(out.columns))
print("Unique id count:", int(out["id"].nunique()))
