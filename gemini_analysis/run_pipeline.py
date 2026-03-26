#!/usr/bin/env python3
"""Single-file Gemini evaluator that fills one-hot sentiment columns in a CSV."""

from __future__ import annotations

import argparse
import csv
import json
import os
import time
from pathlib import Path
from typing import Any

from google import genai


def discover_evaluation_files(data_root: Path) -> list[Path]:
    if not data_root.exists():
        return []
    return sorted(data_root.rglob("evaluation_dataset_1000.csv"))


def choose_input_from_menu(candidates: list[Path], data_root: Path) -> Path:
    if not candidates:
        raise FileNotFoundError(f"No evaluation_dataset_1000.csv found under: {data_root}")

    print("Select dataset to analyze:")
    for idx, path in enumerate(candidates, start=1):
        try:
            rel = path.relative_to(data_root)
            folder_name = rel.parts[0] if rel.parts else path.parent.name
            print(f"{idx}. {folder_name} ({rel})")
        except ValueError:
            print(f"{idx}. {path.parent.name} ({path})")

    while True:
        choice = input("Enter number: ").strip()
        if not choice.isdigit():
            print("Invalid choice. Please enter a number.")
            continue

        selected_idx = int(choice)
        if 1 <= selected_idx <= len(candidates):
            return candidates[selected_idx - 1]

        print(f"Choice out of range. Enter 1 to {len(candidates)}.")


def load_env_file(env_file: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not env_file.exists():
        return values

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def get_api_key(cli_key: str | None, env_file: Path) -> str:
    file_vars = load_env_file(env_file)
    key = cli_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_AI_API_KEY") or file_vars.get("GEMINI_API_KEY", "")
    if not key:
        raise ValueError(
            "Missing Gemini API key. Set GEMINI_API_KEY in gemini.env, or use --api-key, or export GEMINI_API_KEY."
        )
    return key


def extract_json_obj(text: str) -> dict[str, Any]:
    content = (text or "").strip()
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()

    try:
        return json.loads(content)
    except Exception:
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(content[start : end + 1])
        raise


def normalize_probs(neu: float, pos: float, neg: float) -> tuple[float, float, float]:
    vals = [max(0.0, float(neu)), max(0.0, float(pos)), max(0.0, float(neg))]
    total = sum(vals)
    if total <= 0:
        return (1.0, 0.0, 0.0)
    return (vals[0] / total, vals[1] / total, vals[2] / total)


def to_one_hot(neu: float, pos: float, neg: float) -> tuple[int, int, int]:
    vals = [neu, pos, neg]
    winner = max(range(3), key=lambda i: vals[i])
    if winner == 0:
        return (1, 0, 0)
    if winner == 1:
        return (0, 1, 0)
    return (0, 0, 1)


def predict_one_hot(client: genai.Client, model: str, text: str, retries: int = 3) -> tuple[int, int, int]:
    prompt = f"""
Return ONLY valid JSON with these keys:
- neutral: float in [0,1]
- positive: float in [0,1]
- negative: float in [0,1]

Text:
{text}
"""
    last_err: Exception | None = None

    for attempt in range(retries):
        try:
            response = client.models.generate_content(model=model, contents=prompt)
            payload = extract_json_obj(response.text or "")
            neu = float(payload.get("neutral", 0.0))
            pos = float(payload.get("positive", 0.0))
            neg = float(payload.get("negative", 0.0))
            neu, pos, neg = normalize_probs(neu, pos, neg)
            return to_one_hot(neu, pos, neg)
        except Exception as exc:
            last_err = exc
            time.sleep(1.5 * (attempt + 1))

    if last_err:
        print(f"Warning: fallback to neutral for one row due to API/parsing error: {last_err}")
    return (1, 0, 0)


def run(input_csv: Path, output_csv: Path, text_column: str, model: str, api_key: str) -> int:
    with open(input_csv, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        raise ValueError("Input CSV has no rows")

    client = genai.Client(api_key=api_key)
    updated_rows: list[dict[str, Any]] = []

    for idx, row in enumerate(rows, start=1):
        text = str(row.get(text_column, "") or "").strip()
        neutral, positive, negative = predict_one_hot(client=client, model=model, text=text)

        new_row = dict(row)
        new_row["neutral"] = str(neutral)
        new_row["positive"] = str(positive)
        new_row["negative"] = str(negative)
        updated_rows.append(new_row)

        if idx % 25 == 0 or idx == len(rows):
            print(f"Processed {idx}/{len(rows)} rows")

    out_fields = list(rows[0].keys())
    for col in ["neutral", "positive", "negative"]:
        if col not in out_fields:
            out_fields.append(col)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(output_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        writer.writerows(updated_rows)

    return len(rows)


def main() -> None:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Fill neutral/positive/negative as one-hot 1/0 using Gemini")
    parser.add_argument(
        "--menu",
        action="store_true",
        help="Show interactive menu to choose evaluation_dataset_1000.csv from redditscrapper/data",
    )
    parser.add_argument(
        "--data-root",
        default="../redditscrapper/data",
        help="Root folder to search when using --menu",
    )
    parser.add_argument(
        "--input-csv",
        default="",
        help="Input CSV path",
    )
    parser.add_argument(
        "--output-csv",
        default="",
        help="Output CSV path (default: evaluated_dataset_1000.csv in the input file's folder)",
    )
    parser.add_argument("--text-column", default="text_clean", help="Column containing text to classify")
    parser.add_argument("--model", default="gemini-2.5-flash", help="Gemini model name")
    parser.add_argument("--api-key", default="", help="Optional API key override")
    parser.add_argument("--env-file", default="gemini.env", help="Path to env file containing GEMINI_API_KEY")
    args = parser.parse_args()

    data_root = (here / args.data_root).resolve() if not Path(args.data_root).is_absolute() else Path(args.data_root)

    use_menu = args.menu or not args.input_csv

    if use_menu:
        candidates = discover_evaluation_files(data_root)
        input_csv = choose_input_from_menu(candidates=candidates, data_root=data_root)
    else:
        input_csv = (here / args.input_csv).resolve() if not Path(args.input_csv).is_absolute() else Path(args.input_csv)

    if args.output_csv:
        output_csv = (here / args.output_csv).resolve() if not Path(args.output_csv).is_absolute() else Path(args.output_csv)
    else:
        output_csv = input_csv.parent / "evaluated_dataset_1000.csv"

    env_file = (here / args.env_file).resolve() if not Path(args.env_file).is_absolute() else Path(args.env_file)

    if not input_csv.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_csv}")

    api_key = get_api_key(args.api_key or None, env_file=env_file)
    total = run(
        input_csv=input_csv,
        output_csv=output_csv,
        text_column=args.text_column,
        model=args.model,
        api_key=api_key,
    )

    print("Gemini evaluation complete")
    print(f"Rows processed: {total}")
    print(f"Output written to: {output_csv}")


if __name__ == "__main__":
    main()
