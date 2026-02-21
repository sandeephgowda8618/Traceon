from __future__ import annotations

from pathlib import Path

import folium
from folium.plugins import HeatMap


def render_heatmap(G, probabilities: dict, center_lat: float, center_lon: float, output_path: str | Path):
    heat_data = []

    for node, prob in probabilities.items():
        lat = G.nodes[node]["y"]
        lon = G.nodes[node]["x"]
        heat_data.append([lat, lon, float(prob)])

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    m = folium.Map(location=[center_lat, center_lon], zoom_start=15)
    if heat_data:
        HeatMap(heat_data).add_to(m)

    m.save(str(output))
    return str(output)
