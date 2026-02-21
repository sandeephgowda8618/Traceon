from __future__ import annotations


def compute_risk_score(
    age: int,
    time_elapsed_minutes: float,
    crowd_level: str,
    movement_radius: float,
    venue_type: str,
    repeat_sightings: int,
    face_confidence: float,
) -> float:
    score = 0.0

    if age < 10:
        score += 0.3

    if time_elapsed_minutes > 30:
        score += 0.3

    if venue_type in {"railway_station", "bus_terminal"}:
        score += 0.2

    if crowd_level == "high":
        score += 0.1

    if movement_radius > 1000:
        score += 0.1

    if repeat_sightings >= 3:
        score += 0.05

    if face_confidence < 0.7:
        score -= 0.05

    return max(0.0, min(score, 1.0))
