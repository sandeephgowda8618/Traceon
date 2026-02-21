from __future__ import annotations

from pathlib import Path

import cv2

from .adaptive_fusion import adaptive_fusion
from .annotate import draw_bbox
from .clothing_features import extract_clothing_histogram
from .detect_yolo import PersonDetector
from .face_embed import FaceEmbedder
from .face_quality import estimate_face_quality
from .similarity import cosine_similarity


class ImageSearcher:
    def __init__(self, threshold: float = 0.6, detections_dir: str | Path | None = None):
        self.detector = PersonDetector()
        self.embedder = FaceEmbedder()
        self.threshold = float(threshold)
        if detections_dir is None:
            detections_dir = Path(__file__).resolve().parents[2] / "outputs" / "detections"
        self.detections_dir = Path(detections_dir)
        self.detections_dir.mkdir(parents=True, exist_ok=True)

    def search(self, query_face_embedding, query_cloth_hist, image_path: str, return_debug: bool = False):
        img = cv2.imread(str(image_path))
        if img is None:
            return (False, None, None, None, None) if return_debug else (False, None, None, None)

        boxes = self.detector.detect(img)

        best = {
            "score": -1.0,
            "bbox": None,
            "save_path": None,
            "face_score": 0.0,
            "cloth_score": 0.0,
            "face_quality": 0.0,
            "decision": False,
        }

        for box in boxes:
            x1, y1, x2, y2 = box
            crop = img[y1:y2, x1:x2]

            face_embedding = self.embedder.get_embedding(crop)
            cloth_hist = extract_clothing_histogram(img, box)
            if face_embedding is None or cloth_hist is None:
                continue

            face_score = cosine_similarity(query_face_embedding, face_embedding)
            cloth_score = cosine_similarity(query_cloth_hist, cloth_hist)
            face_quality = estimate_face_quality(crop)
            final_score = adaptive_fusion(face_score, cloth_score, face_quality)

            if final_score > best["score"]:
                annotated = draw_bbox(img, box, final_score)
                save_name = f"{Path(image_path).stem}_det.jpg"
                save_path = self.detections_dir / save_name
                cv2.imwrite(str(save_path), annotated)

                best = {
                    "score": float(final_score),
                    "bbox": box,
                    "save_path": str(save_path),
                    "face_score": float(face_score),
                    "cloth_score": float(cloth_score),
                    "face_quality": float(face_quality),
                    "decision": bool(final_score > self.threshold),
                }

        if best["score"] > self.threshold:
            if return_debug:
                return True, best["score"], best["save_path"], best["bbox"], best
            return True, best["score"], best["save_path"], best["bbox"]

        if return_debug:
            return False, None, None, None, best
        return False, None, None, None
