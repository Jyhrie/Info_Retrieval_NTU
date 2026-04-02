import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV_PATH = PROJECT_ROOT / "redditscrapper" / "data" / "ai_coding_agents_1" / "refined_dataset.csv"
OUTPUT_DIR = PROJECT_ROOT / "indexing" / "outputs"
DEFAULT_BASELINE_PATH = OUTPUT_DIR / "baseline.csv"
DEFAULT_INDEXED_PATH = OUTPUT_DIR / "indexed.csv"
PREVIEW_LENGTH = 160

#the fields both v1 and v2 have.
BASE_FIELDS = [
    "id",
    "post_id",
    "record_type",
    "text_part",
    "date",
    "text_clean",
]

#fields that only v2 has (additional indexed)
DERIVED_FIELDS = [
    "tool",
    "reason",
    "workflow",
    "trust",
    "comparison",
]

#helper functions for indexes.

def load_csv_rows(csv_path):
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw_index, row in enumerate(reader, start=1):
            text_clean = (row.get("text_clean") or "").strip()
            if not text_clean:
                continue
            yield raw_index, {
                "post_id": (row.get("post_id") or "").strip(),
                "record_type": (row.get("record_type") or "").strip(),
                "text_part": (row.get("text_part") or "").strip(),
                "date": (
                    row.get("date")
                    or row.get("created_utc")
                    or row.get("created_at")
                    or row.get("timestamp")
                    or ""
                ).strip(),
                "text_clean": text_clean,
            }


def count_nonempty_rows(csv_path):
    return sum(1 for _ in load_csv_rows(csv_path))


def build_document_id(row_index, row):
    post_id = row.get("post_id") or "row"
    return f"{post_id}-{row_index}"


def build_base_document(row_index, row):
    return {
        "id": build_document_id(row_index, row),
        "post_id": row["post_id"],
        "record_type": row["record_type"],
        "text_part": row["text_part"],
        "date": row.get("date", ""),
        "text_clean": row["text_clean"],
    }


def shorten(text, limit=PREVIEW_LENGTH):
    clean = " ".join(str(text).split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 3].rstrip() + "..."


def join_values(values):
    if not values:
        return ""
    return "|".join(values)


def split_values(value):
    if not value:
        return []
    return [item for item in value.split("|") if item]


def to_output_row(record, include_derived=False):
    row = {field: record.get(field, "") for field in BASE_FIELDS}
    if include_derived:
        for field in DERIVED_FIELDS:
            row[field] = join_values(record.get(field, []))
    return row


def write_csv(path, rows, fieldnames):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def read_output_rows(path, include_derived=False):
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if include_derived:
                for field in DERIVED_FIELDS:
                    row[field] = split_values(row.get(field, ""))
            yield row


def print_document_preview(doc, show_derived=False):
    print(
        f"- id={doc.get('id')} post_id={doc.get('post_id')} "
        f"record_type={doc.get('record_type')} text_part={doc.get('text_part')}"
    )
    print(f"  text_clean={shorten(doc.get('text_clean', ''))}")
    if show_derived:
        for field in DERIVED_FIELDS:
            values = doc.get(field) or []
            if values:
                print(f"  {field}={', '.join(values)}")
