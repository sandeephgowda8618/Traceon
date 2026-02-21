from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from .image_processor import ImageSearcher
from .logger import append_search_log
from .query_processor import QueryProcessor
from .video_processor import VideoSearcher


class SearchEngine:
    """End-to-end query vs image/video folder search with adaptive fusion."""

    IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv"}

    def __init__(self, threshold: float = 0.6, log_path: str | Path | None = None):
        self.query = QueryProcessor()
        self.image_searcher = ImageSearcher(threshold=threshold)
        self.video_searcher = VideoSearcher(threshold=threshold)
        self.threshold = float(threshold)
        if log_path is None:
            log_path = Path(__file__).resolve().parents[2] / "logs" / "search_logs.json"
        self.log_path = Path(log_path)

    def _log_event(self, query_id: str, target_file: str, metrics: dict, decision: bool) -> None:
        append_search_log(
            self.log_path,
            {
                "query_id": query_id,
                "target_file": target_file,
                "face_score": float(metrics.get("face_score", 0.0)),
                "cloth_score": float(metrics.get("cloth_score", 0.0)),
                "face_quality": float(metrics.get("face_quality", 0.0)),
                "final_score": float(metrics.get("score", 0.0)),
                "decision": bool(decision),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    def search_folder(self, query_image_path: str, target_folder: str, query_id: str | None = None):
        query_id = query_id or str(uuid.uuid4())
        q_face, q_cloth = self.query.process_query(query_image_path)

        results = []
        for path in sorted(Path(target_folder).rglob("*")):
            if not path.is_file():
                continue

            suffix = path.suffix.lower()
            if suffix in self.IMAGE_EXTS:
                matched, conf, evidence, bbox, debug = self.image_searcher.search(
                    q_face, q_cloth, str(path), return_debug=True
                )
                self._log_event(query_id=query_id, target_file=str(path), metrics=debug or {}, decision=bool(matched))
                if matched:
                    results.append(
                        {
                            "source": str(path),
                            "type": "image",
                            "matched": True,
                            "confidence": conf,
                            "bbox": bbox,
                            "timestamp": None,
                            "evidence": evidence,
                            "face_score": debug.get("face_score", 0.0),
                            "cloth_score": debug.get("cloth_score", 0.0),
                            "face_quality": debug.get("face_quality", 0.0),
                            "final_score": debug.get("score", 0.0),
                            "decision": debug.get("decision", False),
                        }
                    )
            elif suffix in self.VIDEO_EXTS:
                matched, conf, evidence, bbox, ts, debug = self.video_searcher.search(
                    q_face,
                    q_cloth,
                    str(path),
                    return_debug=True,
                )
                self._log_event(query_id=query_id, target_file=str(path), metrics=debug or {}, decision=bool(matched))
                if matched:
                    results.append(
                        {
                            "source": str(path),
                            "type": "video",
                            "matched": True,
                            "confidence": conf,
                            "bbox": bbox,
                            "timestamp": ts,
                            "evidence": evidence,
                            "face_score": debug.get("face_score", 0.0),
                            "cloth_score": debug.get("cloth_score", 0.0),
                            "face_quality": debug.get("face_quality", 0.0),
                            "final_score": debug.get("score", 0.0),
                            "decision": debug.get("decision", False),
                        }
                    )

        results.sort(key=lambda x: x["confidence"], reverse=True)
        return {
            "query_id": query_id,
            "match_found": len(results) > 0,
            "results": results,
        }
