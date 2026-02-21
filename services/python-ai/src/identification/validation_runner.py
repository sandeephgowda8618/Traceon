from __future__ import annotations

import argparse
import csv
from pathlib import Path

from .image_processor import ImageSearcher
from .query_processor import QueryProcessor
from .video_processor import VideoSearcher


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv"}


def _iter_files(folder: Path):
    for p in sorted(folder.rglob("*")):
        if p.is_file() and p.name != ".gitkeep":
            yield p


def run_validation(query_path: Path, positive_dir: Path, negative_dir: Path, output_csv: Path, threshold: float = 0.6):
    qp = QueryProcessor()
    image_searcher = ImageSearcher(threshold=threshold)
    video_searcher = VideoSearcher(threshold=threshold)

    q_face, q_cloth = qp.process_query(str(query_path))

    rows = []

    def process_file(file_path: Path, label: int):
        suffix = file_path.suffix.lower()
        if suffix in IMAGE_EXTS:
            matched, _, _, _, debug = image_searcher.search(q_face, q_cloth, str(file_path), return_debug=True)
        elif suffix in VIDEO_EXTS:
            matched, _, _, _, _, debug = video_searcher.search(q_face, q_cloth, str(file_path), return_debug=True)
        else:
            return

        debug = debug or {}
        rows.append(
            {
                "file": str(file_path),
                "label": label,
                "face_score": float(debug.get("face_score", 0.0)),
                "cloth_score": float(debug.get("cloth_score", 0.0)),
                "face_quality": float(debug.get("face_quality", 0.0)),
                "final_score": float(debug.get("score", 0.0)),
                "decision": int(bool(matched)),
            }
        )

    for f in _iter_files(positive_dir):
        # Skip query image if stored under positives.
        if f.resolve() == query_path.resolve():
            continue
        process_file(f, label=1)

    for f in _iter_files(negative_dir):
        process_file(f, label=0)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["file", "label", "face_score", "cloth_score", "face_quality", "final_score", "decision"],
        )
        writer.writeheader()
        writer.writerows(rows)

    return rows


def main():
    parser = argparse.ArgumentParser(description="Run adaptive fusion validation and export CSV.")
    parser.add_argument("--query", required=True, help="Query image path")
    parser.add_argument("--positive-dir", required=True, help="Positive samples directory")
    parser.add_argument("--negative-dir", required=True, help="Negative samples directory")
    parser.add_argument("--output-csv", default="test_data/results/validation_results.csv", help="Output CSV path")
    parser.add_argument("--threshold", type=float, default=0.6)
    args = parser.parse_args()

    rows = run_validation(
        query_path=Path(args.query),
        positive_dir=Path(args.positive_dir),
        negative_dir=Path(args.negative_dir),
        output_csv=Path(args.output_csv),
        threshold=args.threshold,
    )
    print(f"Validation complete: {len(rows)} samples -> {args.output_csv}")


if __name__ == "__main__":
    main()
