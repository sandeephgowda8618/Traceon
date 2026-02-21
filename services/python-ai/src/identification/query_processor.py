from __future__ import annotations

import cv2
import numpy as np

from .clothing_features import extract_clothing_histogram
from .detect_yolo import PersonDetector
from .face_embed import FaceEmbedder


class QueryProcessor:
    def __init__(self):
        self.embedder = FaceEmbedder()
        self.detector = PersonDetector()

    def process_query(self, image_path: str):
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Failed to read query image: {image_path}")

        boxes = self.detector.detect(img)
        if not boxes:
            raise ValueError("No person detected in query")

        box = boxes[0]
        x1, y1, x2, y2 = box
        crop = img[y1:y2, x1:x2]

        face_embedding = self.embedder.get_embedding(crop)
        cloth_hist = extract_clothing_histogram(img, box)

        if face_embedding is None or cloth_hist is None:
            raise ValueError("Failed to extract features")

        face_embedding = face_embedding / (np.linalg.norm(face_embedding) + 1e-12)
        cloth_hist = cloth_hist / (np.linalg.norm(cloth_hist) + 1e-12)
        return face_embedding, cloth_hist
