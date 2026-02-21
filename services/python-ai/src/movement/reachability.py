from __future__ import annotations

import math

import networkx as nx
import osmnx as ox


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _nearest_node_fallback(G, lat: float, lon: float):
    best_node = None
    best_dist = float("inf")
    for node, data in G.nodes(data=True):
        ny = data.get("y")
        nx_ = data.get("x")
        if ny is None or nx_ is None:
            continue
        dist = _haversine_m(lat, lon, float(ny), float(nx_))
        if dist < best_dist:
            best_dist = dist
            best_node = node
    if best_node is None:
        raise ValueError("Could not resolve nearest graph node for input coordinates.")
    return best_node


def compute_reachable_nodes(G, lat: float, lon: float, max_distance_m: float):
    try:
        start_node = ox.distance.nearest_nodes(G, lon, lat)
    except ImportError:
        # OSMnx can require optional deps (e.g., scikit-learn) for unprojected graphs.
        start_node = _nearest_node_fallback(G, lat, lon)
    lengths = nx.single_source_dijkstra_path_length(
        G,
        start_node,
        cutoff=max_distance_m,
        weight="weight",
    )
    return lengths
