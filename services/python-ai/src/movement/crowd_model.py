from __future__ import annotations


def apply_crowd_penalty(G, crowd_level: str):
    penalty_factor = {
        "low": 1.0,
        "medium": 1.3,
        "high": 1.8,
    }.get((crowd_level or "medium").lower(), 1.3)

    for _, _, _, data in G.edges(keys=True, data=True):
        base_length = float(data.get("length", 1.0))
        data["weight"] = base_length * penalty_factor

    return G
