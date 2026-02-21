from __future__ import annotations

from shapely.geometry import MultiPoint


def extract_high_risk_zone(G, probabilities: dict, threshold: float = 0.6):
    points = []

    for node, prob in probabilities.items():
        if float(prob) >= threshold:
            lat = G.nodes[node]["y"]
            lon = G.nodes[node]["x"]
            points.append((lon, lat))

    if not points:
        return None

    return MultiPoint(points).convex_hull
