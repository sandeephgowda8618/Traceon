import cv2
import numpy as np


def extract_clothing_histogram(image: np.ndarray, bbox) -> np.ndarray | None:
    """Extract normalized HSV histogram (64D) from lower body region."""
    if image is None or image.size == 0 or bbox is None:
        return None

    x1, y1, x2, y2 = map(int, bbox)
    h_img, w_img = image.shape[:2]

    x1 = max(0, min(x1, w_img - 1))
    y1 = max(0, min(y1, h_img - 1))
    x2 = max(1, min(x2, w_img))
    y2 = max(1, min(y2, h_img))

    if x2 <= x1 or y2 <= y1:
        return None

    person = image[y1:y2, x1:x2]
    if person.size == 0:
        return None

    h = person.shape[0]
    clothing_region = person[int(h * 0.4):h, :]
    if clothing_region.size == 0:
        return None

    hsv = cv2.cvtColor(clothing_region, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1], None, [8, 8], [0, 180, 0, 256])
    hist = cv2.normalize(hist, hist).flatten().astype(np.float32)

    norm = np.linalg.norm(hist)
    if norm <= 1e-12:
        return None
    return hist / norm
