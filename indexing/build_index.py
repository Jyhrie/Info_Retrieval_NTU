import argparse
from pathlib import Path

from common import (
    BASE_FIELDS,
    DEFAULT_BASELINE_PATH,
    DEFAULT_CSV_PATH,
    DEFAULT_INDEXED_PATH,
    DERIVED_FIELDS,
    build_base_document,
    count_nonempty_rows,
    load_csv_rows,
    to_output_row,
    write_csv,
)
from rules import derive_metadata


def build_rows(csv_path, mode, limit=None):
    rows = []
    yielded = 0

    for row_index, row in load_csv_rows(csv_path):
        record = build_base_document(row_index, row)

        if mode == "indexed":
            metadata = derive_metadata(row["text_clean"])
            for field in DERIVED_FIELDS:
                record[field] = metadata.get(field, [])
            rows.append(to_output_row(record, include_derived=True))
        else:
            rows.append(to_output_row(record))

        yielded += 1
        if limit is not None and yielded >= limit:
            break

    return rows


def parse_args():
    parser = argparse.ArgumentParser(description="Build a baseline or indexed CSV from refined_dataset.csv")
    parser.add_argument("--csv", default=str(DEFAULT_CSV_PATH), help="Path to refined_dataset.csv")
    parser.add_argument(
        "--mode",
        choices=["baseline", "indexed"],
        default="baseline",
        help="Choose whether to build the baseline file or the indexed file",
    )
    parser.add_argument("--out", default=None, help="Optional output CSV path")
    parser.add_argument("--limit", type=int, default=None, help="Optional limit for trial output")
    return parser.parse_args()


def main():
    args = parse_args()
    csv_path = Path(args.csv).resolve()
    if args.out:
        out_path = Path(args.out).resolve()
    elif args.mode == "indexed":
        out_path = DEFAULT_INDEXED_PATH.resolve()
    else:
        out_path = DEFAULT_BASELINE_PATH.resolve()

    rows = build_rows(csv_path, args.mode, args.limit)
    if args.mode == "indexed":
        write_csv(out_path, rows, BASE_FIELDS + DERIVED_FIELDS)
    else:
        write_csv(out_path, rows, BASE_FIELDS)

    expected = len(rows) if args.limit is not None else count_nonempty_rows(csv_path)

    print("Build complete")
    print(f"- mode={args.mode}")
    print(f"- csv={csv_path}")
    print(f"- out={out_path}")
    print(f"- expected_nonempty_rows={expected}")
    print(f"- rows_written={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
