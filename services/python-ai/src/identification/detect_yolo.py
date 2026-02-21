from __future__ import annotations

import cv2


class PersonDetector:
    """
    Lightweight person detector wrapper.

    Uses OpenCV HOG people detector as a zero-dependency baseline.
    Returns list of (x1, y1, x2, y2).
    """

    def __init__(self):
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    def detect(self, image):
        if image is None or image.size == 0:
            return []

        rects, _ = self.hog.detectMultiScale(
            image,
            winStride=(8, 8),
            padding=(8, 8),
            scale=1.05,
        )

        boxes = []
        for (x, y, w, h) in rects:
            boxes.append((int(x), int(y), int(x + w), int(y + h)))

        # Fallback to full image as one person crop when detector misses.
        if not boxes:
            h, w = image.shape[:2]
            boxes = [(0, 0, w, h)]

        return boxes
