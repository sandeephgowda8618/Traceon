import numpy as np


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Safe cosine similarity in [0, 1] for non-negative style features."""
    if a is None or b is None:
        return 0.0

    a = np.asarray(a, dtype=np.float32).flatten()
    b = np.asarray(b, dtype=np.float32).flatten()

    if a.size == 0 or b.size == 0 or a.size != b.size:
        return 0.0

    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom <= 1e-12:
        return 0.0

    score = float(np.dot(a, b) / denom)
    return max(0.0, min(1.0, score))
