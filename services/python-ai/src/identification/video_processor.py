from __future__ import annotations

from collections import deque
from pathlib import Path

import cv2

from .adaptive_fusion import adaptive_fusion
from .annotate import draw_bbox
from .clothing_features import extract_clothing_histogram
from .detect_yolo import PersonDetector
from .face_embed import FaceEmbedder
from .face_quality import estimate_face_quality
from .similarity import cosine_similarity


class VideoSearcher:
    def __init__(self, threshold: float = 0.6, detections_dir: str | Path | None = None):
        self.detector = PersonDetector()
        self.embedder = FaceEmbedder()
        self.threshold = float(threshold)
        if detections_dir is None:
            detections_dir = Path(__file__).resolve().parents[2] / "outputs" / "detections"
        self.detections_dir = Path(detections_dir)
        self.detections_dir.mkdir(parents=True, exist_ok=True)

    def search(
        self,
        query_face_embedding,
        query_cloth_hist,
        video_path: str,
        frame_stride: int = 5,
        resize_to: tuple[int, int] = (960, 540),
        min_consecutive_hits: int = 2,
        smoothing_window: int = 5,
        return_debug: bool = False,
    ):
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            if return_debug:
                return False, None, None, None, None, None
            return False, None, None, None, None

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        frame_idx = 0

        best = {
            "score": -1.0,
            "bbox": None,
            "save_path": None,
            "timestamp": None,
            "face_score": 0.0,
            "cloth_score": 0.0,
            "face_quality": 0.0,
            "decision": False,
        }

        rolling_scores = deque(maxlen=max(1, smoothing_window))
        consecutive_hits = 0
        confirmed = False

        while True:
            ok, frame = cap.read()
            if not ok:
                break

            if frame_idx % max(1, frame_stride) != 0:
                frame_idx += 1
                continue

            frame = cv2.resize(frame, resize_to)
            boxes = self.detector.detect(frame)

            frame_best_score = -1.0
            frame_best_data = None

            for box in boxes:
                x1, y1, x2, y2 = box
                crop = frame[y1:y2, x1:x2]

                face_embedding = self.embedder.get_embedding(crop)
                cloth_hist = extract_clothing_histogram(frame, box)
                if face_embedding is None or cloth_hist is None:
                    continue

                face_score = cosine_similarity(query_face_embedding, face_embedding)
                cloth_score = cosine_similarity(query_cloth_hist, cloth_hist)
                face_quality = estimate_face_quality(crop)
                final_score = adaptive_fusion(face_score, cloth_score, face_quality)

                if final_score > frame_best_score:
                    frame_best_score = float(final_score)
                    frame_best_data = {
                        "bbox": box,
                        "face_score": float(face_score),
                        "cloth_score": float(cloth_score),
                        "face_quality": float(face_quality),
                    }

            if frame_best_data is None:
                frame_idx += 1
                continue

            rolling_scores.append(frame_best_score)
            smoothed_score = sum(rolling_scores) / len(rolling_scores)

            if frame_best_score > self.threshold:
                consecutive_hits += 1
            else:
                consecutive_hits = 0

            decision = (smoothed_score > self.threshold) and (consecutive_hits >= min_consecutive_hits)

            if frame_best_score > best["score"]:
                annotated = draw_bbox(frame, frame_best_data["bbox"], frame_best_score)
                save_name = f"{Path(video_path).stem}_frame_{frame_idx}.jpg"
                save_path = self.detections_dir / save_name
                cv2.imwrite(str(save_path), annotated)

                best = {
                    "score": frame_best_score,
                    "bbox": frame_best_data["bbox"],
                    "save_path": str(save_path),
                    "timestamp": float(frame_idx / fps),
                    "face_score": frame_best_data["face_score"],
                    "cloth_score": frame_best_data["cloth_score"],
                    "face_quality": frame_best_data["face_quality"],
                    "decision": bool(decision),
                }

            if decision:
                confirmed = True
                break

            frame_idx += 1

        cap.release()

        if confirmed or best["score"] > self.threshold:
            if best["score"] > self.threshold:
                best["decision"] = True
            if return_debug:
                return True, best["score"], best["save_path"], best["bbox"], best["timestamp"], best
            return True, best["score"], best["save_path"], best["bbox"], best["timestamp"]

        if return_debug:
            return False, None, None, None, None, best
        return False, None, None, None, None
