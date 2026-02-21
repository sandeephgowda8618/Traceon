from __future__ import annotations

import cv2
import numpy as np


class FaceEmbedder:
    """
    Face-like embedding extractor.

    This baseline avoids heavy runtime dependencies and provides a deterministic
    normalized descriptor from the upper body/face region.
    """

    def get_embedding(self, person_crop) -> np.ndarray | None:
        if person_crop is None or person_crop.size == 0:
            return None

        h, w = person_crop.shape[:2]
        top_region = person_crop[: max(1, int(h * 0.45)), :]
        if top_region.size == 0:
            return None

        gray = cv2.cvtColor(top_region, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA)
        emb = resized.flatten().astype(np.float32)

        norm = np.linalg.norm(emb)
        if norm <= 1e-12:
            return None
        return emb / norm
