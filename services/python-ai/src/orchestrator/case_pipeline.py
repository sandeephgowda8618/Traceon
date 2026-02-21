from __future__ import annotations

from alert.alert_service import run_alert_service
from activation.activation_service import dispatch_geo_activation
from movement.movement_service import run_movement_engine
from orchestrator.case_state import create_case, transition_case_state, update_case_snapshot
from utils.blockchain_ledger import append_blockchain_event


def handle_case_update(
    *,
    case_id: str,
    identification_result: dict,
    age: int,
    time_elapsed_minutes: float,
    crowd_level: str,
    venue_type: str,
    repeat_sightings: int,
    face_confidence: float,
    query_image_path: str | None = None,
    db_dsn: str | None = None,
):
    create_case(case_id, meta={"venue_type": venue_type, "age": age})
    matched = bool(identification_result.get("matched", False))
    if not matched:
        update_case_snapshot(case_id, identification=identification_result)
        return {
            "case_id": case_id,
            "matched": False,
            "status": "NO_MATCH",
            "timeline": [],
        }

    append_blockchain_event(
        event_type="MATCH_CONFIRMED",
        case_id=case_id,
        payload={
            "timestamp": identification_result.get("timestamp"),
            "lat": identification_result.get("lat"),
            "lon": identification_result.get("lon"),
            "face_confidence": face_confidence,
        },
    )
    transition_case_state(case_id, "ACTIVE")

    movement_result = run_movement_engine(
        case_id=case_id,
        lat=float(identification_result["lat"]),
        lon=float(identification_result["lon"]),
        age=age,
        time_elapsed_minutes=time_elapsed_minutes,
        crowd_level=crowd_level,
        venue_type=venue_type,
        trigger_reason="confirmed_identification",
    )

    append_blockchain_event(
        event_type="HEATMAP_GENERATED",
        case_id=case_id,
        payload={
            "heatmap_path": movement_result.get("heatmap_path"),
            "radius_m": movement_result.get("radius_m"),
        },
    )

    alert_result = run_alert_service(
        case_id=case_id,
        age=age,
        time_elapsed_minutes=time_elapsed_minutes,
        crowd_level=crowd_level,
        movement_radius=float(movement_result.get("radius_m", 0.0)),
        venue_type=venue_type,
        repeat_sightings=repeat_sightings,
        face_confidence=face_confidence,
    )

    activation_result = {"activated_volunteers": [], "police_units": []}
    if alert_result["alert_level"] == "HIGH":
        transition_case_state(case_id, "HIGH_ALERT")
        activation_result = dispatch_geo_activation(
            case_id=case_id,
            high_risk_zone=movement_result.get("high_risk_zone"),
            center_lat=float(identification_result["lat"]),
            center_lon=float(identification_result["lon"]),
            query_image_path=query_image_path,
            db_dsn=db_dsn,
        )
    else:
        transition_case_state(case_id, "ACTIVE")

    case_snapshot = update_case_snapshot(
        case_id,
        identification=identification_result,
        movement=movement_result,
        alert=alert_result,
        activation=activation_result,
    )

    return {
        "case_id": case_id,
        "matched": True,
        "state": case_snapshot.get("state"),
        "movement": movement_result,
        "alert": alert_result,
        "activation": activation_result,
        "timeline": [
            "MATCH_CONFIRMED",
            "HEATMAP_GENERATED",
            "ALERT_LEVEL_ASSIGNED",
            "ACTIVATION_DISPATCHED" if alert_result["alert_level"] == "HIGH" else "NO_ACTIVATION",
        ],
    }
