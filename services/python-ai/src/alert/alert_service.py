from __future__ import annotations

from .alert_engine import determine_alert_level
from .risk_model import compute_risk_score
from utils.blockchain_ledger import append_blockchain_event


def run_alert_service(
    *,
    case_id: str,
    age: int,
    time_elapsed_minutes: float,
    crowd_level: str,
    movement_radius: float,
    venue_type: str,
    repeat_sightings: int,
    face_confidence: float,
):
    risk_score = compute_risk_score(
        age=age,
        time_elapsed_minutes=time_elapsed_minutes,
        crowd_level=crowd_level,
        movement_radius=movement_radius,
        venue_type=venue_type,
        repeat_sightings=repeat_sightings,
        face_confidence=face_confidence,
    )
    alert_level = determine_alert_level(risk_score)

    append_blockchain_event(
        event_type="ALERT_LEVEL_ASSIGNED",
        case_id=case_id,
        payload={
            "alert_level": alert_level,
            "priority_score": risk_score,
            "inputs": {
                "age": age,
                "time_elapsed_minutes": time_elapsed_minutes,
                "crowd_level": crowd_level,
                "movement_radius": movement_radius,
                "venue_type": venue_type,
                "repeat_sightings": repeat_sightings,
                "face_confidence": face_confidence,
            },
        },
    )

    return {"risk_score": risk_score, "alert_level": alert_level}
