from __future__ import annotations

import json
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile

from alert.alert_engine import determine_alert_level
from alert.risk_model import compute_risk_score
from identification.search_engine import SearchEngine
from movement.movement_service import run_movement_engine
from observability.metrics import metrics_registry, monotonic_ms

app = FastAPI(title="Traceon Python AI Compute Service", version="2.0.0")


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    start_ms = monotonic_ms()

    try:
        response = await call_next(request)
        status = response.status_code
    except Exception:
        status = 500
        raise
    finally:
        latency_ms = monotonic_ms() - start_ms
        metrics_registry.record_http(
            method=request.method,
            path=request.url.path,
            status=status,
            latency_ms=latency_ms,
        )
        print(
            json.dumps(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "request_id": req_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": status,
                    "latency_ms": round(latency_ms, 3),
                },
                separators=(",", ":"),
            )
        )

    response.headers["X-Request-ID"] = req_id
    return response


@app.get("/health")
def health():
    return {"status": "ok", "service": "python-ai-compute"}


@app.get("/ready")
def ready():
    return {"ready": True}


@app.get("/metrics")
def metrics():
    return Response(content=metrics_registry.render_prometheus(), media_type="text/plain; version=0.0.4")


@app.post("/identify")
async def identify(
    query_image: UploadFile = File(...),
    target_folder: str = Form(...),
    threshold: float = Form(0.6),
):
    target = Path(target_folder)
    if not target.exists() or not target.is_dir():
        raise HTTPException(status_code=400, detail="target_folder must be an existing directory")

    suffix = Path(query_image.filename or "query.jpg").suffix or ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        payload = await query_image.read()
        if not payload:
            raise HTTPException(status_code=400, detail="query_image is empty")
        tmp.write(payload)
        query_path = tmp.name

    try:
        engine = SearchEngine(threshold=threshold)
        result = engine.search_folder(query_image_path=query_path, target_folder=str(target))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    top = (result.get("results") or [None])[0]
    return {
        "matched": bool(result.get("match_found")),
        "confidence": (top or {}).get("confidence"),
        "embedding_score": (top or {}).get("face_score"),
        "query_id": result.get("query_id"),
        "results": result.get("results", []),
    }


@app.post("/movement")
def movement(
    case_id: str = Form(...),
    last_lat: float = Form(...),
    last_lon: float = Form(...),
    time_elapsed_minutes: float = Form(...),
    age: int = Form(...),
    crowd_level: str = Form("medium"),
    venue_type: str = Form("unknown"),
    trigger_reason: str = Form("confirmed_identification"),
    matched: bool = Form(True),
):
    if not matched:
        return {"movement_run": False, "reason": "Identification not confirmed"}

    out = run_movement_engine(
        case_id=case_id,
        lat=last_lat,
        lon=last_lon,
        age=age,
        time_elapsed_minutes=time_elapsed_minutes,
        crowd_level=crowd_level,
        venue_type=venue_type,
        trigger_reason=trigger_reason,
    )
    return {
        "movement_run": True,
        "radius_m": out.get("radius_m"),
        "heatmap_path": out.get("heatmap_path"),
        "high_risk_zone": out.get("high_risk_zone"),
        "reachable_nodes": out.get("reachable_nodes"),
    }


@app.post("/alert")
def alert(
    age: int = Form(...),
    time_elapsed_minutes: float = Form(...),
    crowd_level: str = Form("medium"),
    movement_radius: float = Form(...),
    venue_type: str = Form("unknown"),
    repeat_sightings: int = Form(1),
    face_confidence: float = Form(0.8),
):
    score = compute_risk_score(
        age=age,
        time_elapsed_minutes=time_elapsed_minutes,
        crowd_level=crowd_level,
        movement_radius=movement_radius,
        venue_type=venue_type,
        repeat_sightings=repeat_sightings,
        face_confidence=face_confidence,
    )
    return {"risk_score": score, "alert_level": determine_alert_level(score)}


@app.post("/compute-case")
def compute_case(
    case_id: str = Form(...),
    age: int = Form(...),
    lat: float = Form(...),
    lon: float = Form(...),
    time_elapsed_minutes: float = Form(...),
    crowd_level: str = Form("medium"),
    venue_type: str = Form("unknown"),
    repeat_sightings: int = Form(1),
    face_confidence: float = Form(0.8),
):
    movement_out = run_movement_engine(
        case_id=case_id,
        lat=lat,
        lon=lon,
        age=age,
        time_elapsed_minutes=time_elapsed_minutes,
        crowd_level=crowd_level,
        venue_type=venue_type,
        trigger_reason="confirmed_identification",
    )

    score = compute_risk_score(
        age=age,
        time_elapsed_minutes=time_elapsed_minutes,
        crowd_level=crowd_level,
        movement_radius=float(movement_out.get("radius_m") or 0.0),
        venue_type=venue_type,
        repeat_sightings=repeat_sightings,
        face_confidence=face_confidence,
    )
    level = determine_alert_level(score)

    return {
        "identification": {
            "matched": True,
            "face_confidence": face_confidence,
            "lat": lat,
            "lon": lon,
        },
        "movement": {
            "radius_m": movement_out.get("radius_m"),
            "heatmap_path": movement_out.get("heatmap_path"),
            "high_risk_zone": movement_out.get("high_risk_zone"),
            "reachable_nodes": movement_out.get("reachable_nodes"),
        },
        "alert": {
            "risk_score": score,
            "alert_level": level,
        },
        "activation_suggestion": {
            "should_activate": level == "HIGH",
        },
    }
