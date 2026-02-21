from __future__ import annotations

import argparse
import csv
from pathlib import Path


def _read_rows(csv_path: Path):
    with csv_path.open("r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = []
        for row in reader:
            rows.append(
                {
                    "label": int(row["label"]),
                    "final_score": float(row["final_score"]),
                }
            )
    return rows


def _metrics(rows, threshold: float):
    tp = fp = tn = fn = 0
    for r in rows:
        pred = 1 if r["final_score"] >= threshold else 0
        label = r["label"]
        if pred == 1 and label == 1:
            tp += 1
        elif pred == 1 and label == 0:
            fp += 1
        elif pred == 0 and label == 0:
            tn += 1
        else:
            fn += 1

    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    return {
        "threshold": threshold,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "fpr": fpr,
        "recall": recall,
        "precision": precision,
    }


def calibrate_threshold(csv_path: Path, max_fpr: float = 0.05, step: float = 0.01):
    rows = _read_rows(csv_path)

    candidates = []
    t = 0.0
    while t <= 1.000001:
        m = _metrics(rows, round(t, 4))
        if m["fpr"] <= max_fpr:
            candidates.append(m)
        t += step

    if not candidates:
        return None

    # Prefer highest recall, then highest precision, then highest threshold.
    candidates.sort(key=lambda m: (m["recall"], m["precision"], m["threshold"]), reverse=True)
    return candidates[0]


def main():
    parser = argparse.ArgumentParser(description="Calibrate threshold from validation CSV.")
    parser.add_argument("--csv", required=True, help="Validation CSV path")
    parser.add_argument("--max-fpr", type=float, default=0.05)
    parser.add_argument("--step", type=float, default=0.01)
    args = parser.parse_args()

    best = calibrate_threshold(Path(args.csv), max_fpr=args.max_fpr, step=args.step)
    if best is None:
        print("No threshold satisfies the requested FPR constraint.")
        return

    print("Recommended threshold calibration:")
    print(
        f"threshold={best['threshold']:.2f} fpr={best['fpr']:.4f} "
        f"recall={best['recall']:.4f} precision={best['precision']:.4f}"
    )


if __name__ == "__main__":
    main()
