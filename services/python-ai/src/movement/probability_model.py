from __future__ import annotations

import numpy as np


def compute_probabilities(lengths: dict, sigma: float):
    if sigma <= 1e-9:
        sigma = 1.0

    probs = {}
    for node, dist in lengths.items():
        probs[node] = float(np.exp(-((float(dist) ** 2) / (2.0 * (sigma**2)))))
    return probs
