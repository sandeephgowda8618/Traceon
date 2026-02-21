from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import jwt
from shapely.geometry import Point, shape
from shapely.wkt import dumps as wkt_dumps

from utils.blockchain_ledger import append_blockchain_event
from utils.watermark import apply_text_watermark

ROOT_DIR = Path(__file__).resolve().parents[2]
ACTIVATION_LOG = ROOT_DIR / "logs" / "activation_records.json"


def _append_activation_record(record: dict[str, Any]) -> None:
    ACTIVATION_LOG.parent.mkdir(parents=True, exist_ok=True)
    if ACTIVATION_LOG.exists():
        try:
            data = json.loads(ACTIVATION_LOG.read_text(encoding="utf-8") or "[]")
            if not isinstance(data, list):
                data = []
        except json.JSONDecodeError:
            data = []
    else:
        data = []
    data.append(record)
    ACTIVATION_LOG.write_text(json.dumps(data, indent=2), encoding="utf-8")


def generate_activation_token(volunteer_id: str, case_id: str, expiry_minutes: int = 30) -> str:
    secret = os.getenv("TRACEON_JWT_SECRET", "traceon-dev-secret")
    now = datetime.now(timezone.utc)
    payload = {
        "volunteer_id": volunteer_id,
        "case_id": case_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expiry_minutes)).timestamp()),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def _fallback_volunteers():
    return []


def _fallback_police():
    return []


def query_volunteers_inside_polygon(polygon_geojson: dict[str, Any], db_dsn: str | None = None):
    polygon = shape(polygon_geojson) if polygon_geojson else None
    if polygon is None:
        return []

    if db_dsn:
        import psycopg2  # lazy import

        polygon_wkt = wkt_dumps(polygon, rounding_precision=6)
        sql = (
            "SELECT id::text, name, ST_Y(location::geometry) AS lat, ST_X(location::geometry) AS lon "
            "FROM volunteers "
            "WHERE verified = true AND is_active = true "
            "AND ST_Within(location::geometry, ST_GeomFromText(%s, 4326));"
        )
        with psycopg2.connect(db_dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (polygon_wkt,))
                rows = cur.fetchall()
        return [{"id": r[0], "name": r[1], "lat": float(r[2]), "lon": float(r[3])} for r in rows]

    # Local fallback, if no DB is configured.
    volunteers = []
    for v in _fallback_volunteers():
        pt = Point(v["lon"], v["lat"])
        if polygon.contains(pt):
            volunteers.append(v)
    return volunteers


def query_nearby_police_stations(center_lat: float, center_lon: float, radius_m: float = 2000, db_dsn: str | None = None):
    if db_dsn:
        import psycopg2  # lazy import

        center_wkt = f"SRID=4326;POINT({center_lon} {center_lat})"
        sql = (
            "SELECT id::text, name, ST_Y(location::geometry) AS lat, ST_X(location::geometry) AS lon "
            "FROM police_stations "
            "WHERE ST_DWithin(location, ST_GeogFromText(%s), %s);"
        )
        with psycopg2.connect(db_dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (center_wkt, radius_m))
                rows = cur.fetchall()
        return [{"id": r[0], "name": r[1], "lat": float(r[2]), "lon": float(r[3])} for r in rows]

    return _fallback_police()


def dispatch_geo_activation(
    *,
    case_id: str,
    high_risk_zone: dict[str, Any] | None,
    center_lat: float,
    center_lon: float,
    query_image_path: str | None = None,
    db_dsn: str | None = None,
):
    volunteers = query_volunteers_inside_polygon(high_risk_zone, db_dsn=db_dsn) if high_risk_zone else []
    police_units = query_nearby_police_stations(center_lat, center_lon, radius_m=2000, db_dsn=db_dsn)

    activated = []
    volunteer_media_dir = ROOT_DIR / "outputs" / "volunteer_media"
    for vol in volunteers:
        token = generate_activation_token(vol["id"], case_id)
        watermarked_image = None
        if query_image_path:
            watermarked_image = apply_text_watermark(
                input_image=query_image_path,
                output_image=volunteer_media_dir / f"{case_id}_{vol['id']}.jpg",
                text=f"Traceon Authorized Use | Case {case_id} | Volunteer {vol['id']}",
            )
        activated.append(
            {
                **vol,
                "activation_token": token,
                "token_expires_minutes": 30,
                "watermarked_image": watermarked_image,
            }
        )
        append_blockchain_event(
            event_type="VOLUNTEER_ACTIVATED",
            case_id=case_id,
            payload={"volunteer_id": vol["id"], "geo_lat": vol.get("lat"), "geo_lon": vol.get("lon")},
        )

    if police_units:
        append_blockchain_event(
            event_type="POLICE_NOTIFIED",
            case_id=case_id,
            payload={"count": len(police_units)},
        )

    append_blockchain_event(
        event_type="ACTIVATION_DISPATCHED",
        case_id=case_id,
        payload={
            "volunteer_count": len(activated),
            "police_count": len(police_units),
            "query_image_path": query_image_path,
        },
    )

    _append_activation_record(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "case_id": case_id,
            "volunteers": [{"id": v["id"], "name": v.get("name")} for v in activated],
            "police_units": police_units,
        }
    )

    return {"activated_volunteers": activated, "police_units": police_units}
