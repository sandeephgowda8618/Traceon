from __future__ import annotations

from pathlib import Path

import yaml
from shapely.geometry import mapping

from .crowd_model import apply_crowd_penalty
from .graph_loader import ROOT_DIR, load_graph
from .heatmap_renderer import render_heatmap
from .probability_model import compute_probabilities
from .reachability import compute_reachable_nodes
from .zone_extractor import extract_high_risk_zone

_CONFIG_PATH = Path(__file__).resolve().parent / "configs" / "movement_config.yaml"


def load_movement_config(path: str | Path | None = None):
    cfg_path = Path(path) if path else _CONFIG_PATH
    if not cfg_path.exists():
        return {}

    with cfg_path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def compute_max_distance(age: int, time_minutes: float, base_speed_m_per_min: float = 70.0, venue_factor: float = 1.0):
    if age < 6:
        age_factor = 0.6
    elif age < 12:
        age_factor = 0.8
    else:
        age_factor = 1.0

    return float(base_speed_m_per_min) * float(age_factor) * float(time_minutes) * float(venue_factor)


def run_movement_engine(
    case_id: str,
    lat: float,
    lon: float,
    age: int,
    time_elapsed_minutes: float,
    crowd_level: str = "medium",
    venue_type: str = "unknown",
    trigger_reason: str = "confirmed_identification",
):
    config = load_movement_config()
    defaults = config.get("defaults", {})
    venue_speed_factor = config.get("venue_speed_factor", {})

    graph_radius_m = int(defaults.get("graph_radius_m", 3000))
    base_speed = float(defaults.get("base_speed_m_per_min", 70))
    zone_threshold = float(defaults.get("zone_threshold", 0.6))
    sigma_divisor = float(defaults.get("sigma_divisor", 2.0))

    venue_factor = float(venue_speed_factor.get(venue_type, venue_speed_factor.get("unknown", 1.0)))

    graph = load_graph(lat=lat, lon=lon, radius_m=graph_radius_m)
    apply_crowd_penalty(graph, crowd_level)

    max_distance = compute_max_distance(
        age=age,
        time_minutes=time_elapsed_minutes,
        base_speed_m_per_min=base_speed,
        venue_factor=venue_factor,
    )

    lengths = compute_reachable_nodes(graph, lat, lon, max_distance)
    sigma = max(max_distance / max(sigma_divisor, 1e-6), 1.0)
    probabilities = compute_probabilities(lengths, sigma)

    heatmap_path = ROOT_DIR / "outputs" / "heatmaps" / f"{case_id}.html"
    render_heatmap(graph, probabilities, lat, lon, heatmap_path)

    high_risk_zone = extract_high_risk_zone(graph, probabilities, threshold=zone_threshold)
    high_risk_zone_geojson = mapping(high_risk_zone) if high_risk_zone is not None else None

    result = {
        "case_id": case_id,
        "radius_m": max_distance,
        "reachable_nodes": len(lengths),
        "heatmap_path": str(heatmap_path),
        "high_risk_zone": high_risk_zone_geojson,
        "trigger_reason": trigger_reason,
        "inputs": {
            "lat": lat,
            "lon": lon,
            "age": age,
            "time_elapsed_minutes": time_elapsed_minutes,
            "crowd_level": crowd_level,
            "venue_type": venue_type,
        },
    }

    return result
