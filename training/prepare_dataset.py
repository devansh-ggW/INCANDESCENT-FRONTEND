#!/usr/bin/env python3
"""Validate, deduplicate, and split documented training examples into JSONL sets."""
from __future__ import annotations
import argparse, hashlib, json, random, sys
from pathlib import Path

REQUIRED = {"instruction", "response", "category", "source", "license"}
MIN_TEXT = 8

def load_rows(path: Path):
    rows, seen = [], set()
    rejected = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            rejected.append({"line": line_no, "reason": f"invalid JSON: {exc.msg}"})
            continue
        if not isinstance(row, dict) or not REQUIRED.issubset(row):
            rejected.append({"line": line_no, "reason": "row must include " + ", ".join(sorted(REQUIRED))})
            continue
        if not all(isinstance(row[key], str) and row[key].strip() for key in REQUIRED):
            rejected.append({"line": line_no, "reason": "required fields must be non-empty strings"})
            continue
        if len(row["instruction"].strip()) < MIN_TEXT or len(row["response"].strip()) < MIN_TEXT:
            rejected.append({"line": line_no, "reason": "instruction and response must each contain at least 8 characters"})
            continue
        license_label = row["license"].strip().lower()
        if license_label in {"unknown", "none", "unlicensed", "n/a", "not sure", "unspecified", "no license"}:
            rejected.append({"line": line_no, "reason": "document a usable license or explicit permission for this example"})
            continue
        normalized = {key: row[key].strip() for key in REQUIRED}
        digest = hashlib.sha256((normalized["instruction"].casefold() + "\0" + normalized["response"].casefold()).encode()).hexdigest()
        if digest in seen:
            rejected.append({"line": line_no, "reason": "duplicate instruction/response pair"})
            continue
        seen.add(digest)
        rows.append(normalized)
    return rows, rejected

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", type=Path, help="UTF-8 JSONL with instruction/response/category/source/license")
    ap.add_argument("--out-dir", type=Path, default=Path("training/data/split"))
    ap.add_argument("--min-examples", type=int, default=32)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    rows, rejected = load_rows(args.input)
    if rejected:
        print(json.dumps({"rejected": rejected[:25], "rejected_count": len(rejected)}, indent=2))
    if len(rows) < args.min_examples:
        print(f"STOP: found {len(rows)} valid unique examples; at least {args.min_examples} are required. No training split was written.", file=sys.stderr)
        return 2
    # Keep identical normalized instructions in one split, even when responses
    # differ. Otherwise near-identical task prompts can leak between train and test.
    groups = {}
    for row in rows:
        key = " ".join(row["instruction"].casefold().split())
        groups.setdefault(key, []).append(row)
    group_rows = list(groups.values())
    random.Random(args.seed).shuffle(group_rows)
    n_test = max(2, round(len(rows) * .10))
    n_val = max(2, round(len(rows) * .10))
    test, validation, train = [], [], []
    for group in group_rows:
        if len(test) < n_test:
            test.extend(group)
        elif len(validation) < n_val:
            validation.extend(group)
        else:
            train.extend(group)
    if len(train) < 25 or len(validation) < 2 or len(test) < 2:
        print("STOP: split must contain at least 25 training examples and 2 each for validation and held-out test.", file=sys.stderr)
        return 2
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for name, subset in (("train", train), ("validation", validation), ("test", test)):
        (args.out_dir / f"{name}.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in subset), encoding="utf-8")
    split_instruction_sets = {
        name: {" ".join(row["instruction"].casefold().split()) for row in subset}
        for name, subset in (("train", train), ("validation", validation), ("test", test))
    }
    overlaps = {
        "train_validation": len(split_instruction_sets["train"] & split_instruction_sets["validation"]),
        "train_test": len(split_instruction_sets["train"] & split_instruction_sets["test"]),
        "validation_test": len(split_instruction_sets["validation"] & split_instruction_sets["test"]),
    }
    if any(overlaps.values()):
        print(f"STOP: instruction leakage found across data splits: {overlaps}", file=sys.stderr)
        return 2
    manifest = {"input": str(args.input), "seed": args.seed, "valid_unique_examples": len(rows), "unique_instructions": len(groups), "train": len(train), "validation": len(validation), "test": len(test), "rejected": len(rejected), "categories": dict(sorted({cat: sum(1 for row in rows if row['category'] == cat) for cat in {row['category'] for row in rows}}.items())), "instruction_split_overlap": overlaps, "test_rows_used_for_training": False}
    (args.out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
