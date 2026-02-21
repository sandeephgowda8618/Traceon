from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
CASE_STORE_PATH = ROOT_DIR / "data" / "cases" / "case_states.json"

CASE_STATES = {"OPEN", "ACTIVE", "HIGH_ALERT", "CLOSED", "PURGED"}
_ALLOWED = {
    "OPEN": {"ACTIVE", "CLOSED"},
    "ACTIVE": {"HIGH_ALERT", "CLOSED"},
    "HIGH_ALERT": {"ACTIVE", "CLOSED"},
    "CLOSED": {"PURGED"},
    "PURGED": set(),
}


def _read_cases() -> dict[str, Any]:
    if not CASE_STORE_PATH.exists():
        return {}
    try:
        payload = json.loads(CASE_STORE_PATH.read_text(encoding="utf-8") or "{}")
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        pass
    return {}


def _write_cases(data: dict[str, Any]) -> None:
    CASE_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CASE_STORE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_case(case_id: str) -> dict[str, Any] | None:
    return _read_cases().get(case_id)


def list_cases() -> list[dict[str, Any]]:
    return list(_read_cases().values())


def create_case(case_id: str, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    data = _read_cases()
    now = datetime.now(timezone.utc).isoformat()
    if case_id in data:
        case = data[case_id]
        if meta:
            case.setdefault("meta", {}).update(meta)
        case["updated_at"] = now
    else:
        case = {
            "case_id": case_id,
            "state": "OPEN",
            "created_at": now,
            "updated_at": now,
            "meta": meta or {},
            "risk_score": None,
            "alert_level": None,
            "movement": None,
            "activation": None,
            "last_identification": None,
        }
        data[case_id] = case
    _write_cases(data)
    return case


def transition_case_state(case_id: str, to_state: str) -> dict[str, Any]:
    if to_state not in CASE_STATES:
        raise ValueError(f"Invalid target state: {to_state}")

    data = _read_cases()
    if case_id not in data:
        data[case_id] = create_case(case_id)
        data = _read_cases()

    case = data[case_id]
    cur = case.get("state", "OPEN")
    if to_state != cur and to_state not in _ALLOWED.get(cur, set()):
        raise ValueError(f"Invalid state transition: {cur} -> {to_state}")

    case["state"] = to_state
    case["updated_at"] = datetime.now(timezone.utc).isoformat()
    data[case_id] = case
    _write_cases(data)
    return case


def update_case_snapshot(
    case_id: str,
    *,
    identification: dict[str, Any] | None = None,
    movement: dict[str, Any] | None = None,
    alert: dict[str, Any] | None = None,
    activation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = _read_cases()
    case = data.get(case_id) or create_case(case_id)

    if identification is not None:
        case["last_identification"] = identification
    if movement is not None:
        case["movement"] = movement
    if alert is not None:
        case["alert_level"] = alert.get("alert_level")
        case["risk_score"] = alert.get("risk_score")
    if activation is not None:
        case["activation"] = activation

    case["updated_at"] = datetime.now(timezone.utc).isoformat()
    data[case_id] = case
    _write_cases(data)
    return case
