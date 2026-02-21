from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
SETTINGS_PATH = ROOT_DIR / "data" / "config" / "settings.json"

DEFAULT_SETTINGS: dict[str, Any] = {
    "risk_weights": {
        "age_under_10": 0.3,
        "time_over_30_min": 0.3,
        "venue_risky": 0.2,
        "crowd_high": 0.1,
        "movement_radius_over_1000": 0.1,
        "low_face_confidence_adjustment": -0.05,
    },
    "session_ttl_minutes": 30,
    "purge_days": 30,
}


def get_settings() -> dict[str, Any]:
    if not SETTINGS_PATH.exists():
        return DEFAULT_SETTINGS.copy()
    try:
        payload = json.loads(SETTINGS_PATH.read_text(encoding="utf-8") or "{}")
        if isinstance(payload, dict):
            out = DEFAULT_SETTINGS.copy()
            out.update(payload)
            return out
    except json.JSONDecodeError:
        pass
    return DEFAULT_SETTINGS.copy()


def save_settings(settings: dict[str, Any]) -> dict[str, Any]:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    settings = {**settings, "updated_at": datetime.now(timezone.utc).isoformat()}
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    return settings


def update_risk_weights(new_weights: dict[str, float]) -> dict[str, Any]:
    settings = get_settings()
    cur = settings.get("risk_weights", {})
    cur.update(new_weights)
    settings["risk_weights"] = cur
    return save_settings(settings)
