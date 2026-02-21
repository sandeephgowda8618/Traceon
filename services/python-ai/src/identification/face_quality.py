import cv2
import numpy as np


def estimate_face_quality(face_crop: np.ndarray) -> float:
    """Estimate face quality in [0, 1] using sharpness + size heuristics."""
    if face_crop is None or face_crop.size == 0:
        return 0.0

    gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    h, w = face_crop.shape[:2]
    size_score = min(h, w) / 100.0

    quality = 0.6 * min(sharpness / 100.0, 1.0) + 0.4 * min(size_score, 1.0)
    return float(min(max(quality, 0.0), 1.0))
