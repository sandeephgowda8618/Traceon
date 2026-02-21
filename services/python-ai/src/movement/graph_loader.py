from __future__ import annotations

from pathlib import Path

import osmnx as ox

ROOT_DIR = Path(__file__).resolve().parents[2]
GRAPH_CACHE = ROOT_DIR / "data" / "graphs"
GRAPH_CACHE.mkdir(parents=True, exist_ok=True)


def _cache_path(lat: float, lon: float, radius_m: int) -> Path:
    # Rounded coordinates keep cache cardinality manageable.
    return GRAPH_CACHE / f"{lat:.5f}_{lon:.5f}_{int(radius_m)}.graphml"


def load_graph(lat: float, lon: float, radius_m: int = 2000):
    cache_file = _cache_path(lat, lon, radius_m)

    if cache_file.exists():
        return ox.load_graphml(cache_file)

    graph = ox.graph_from_point((lat, lon), dist=radius_m, network_type="walk")
    ox.save_graphml(graph, cache_file)
    return graph
