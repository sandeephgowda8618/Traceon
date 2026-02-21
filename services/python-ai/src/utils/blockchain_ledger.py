from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_LEDGER_PATH = ROOT_DIR / "blockchain" / "ledger.json"


def _read_ledger(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8") or "[]")
        if isinstance(payload, list):
            return payload
    except json.JSONDecodeError:
        pass
    return []


def verify_ledger(ledger_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(ledger_path) if ledger_path else DEFAULT_LEDGER_PATH
    records = _read_ledger(path)

    prev_hash = ""
    for index, record in enumerate(records):
        if "event_type" in record:
            event = {
                "timestamp": record.get("timestamp"),
                "event_type": record.get("event_type"),
                "case_id": record.get("case_id"),
                "payload": record.get("payload", {}),
            }
            serialized = json.dumps(event, sort_keys=True, separators=(",", ":"))
            expected_hash = hashlib.sha256(f"{serialized}{prev_hash}".encode("utf-8")).hexdigest()
        elif "type" in record:
            # Legacy chain compatibility (older movement-only entries).
            legacy_event = {
                "type": record.get("type"),
                "timestamp": record.get("timestamp"),
                "case_id": record.get("case_id"),
                "trigger_reason": record.get("trigger_reason"),
                "summary": record.get("summary"),
            }
            legacy_payload = json.dumps({"prev_hash": prev_hash, **legacy_event}, sort_keys=True)
            expected_hash = hashlib.sha256(legacy_payload.encode("utf-8")).hexdigest()
        else:
            return {"valid": False, "records_checked": index + 1, "error_index": index, "reason": "unknown_record_format"}

        if record.get("hash") != expected_hash:
            return {"valid": False, "records_checked": index + 1, "error_index": index}
        prev_hash = record.get("hash", "")

    return {"valid": True, "records_checked": len(records)}


def get_case_ledger(case_id: str, ledger_path: str | Path | None = None) -> list[dict[str, Any]]:
    path = Path(ledger_path) if ledger_path else DEFAULT_LEDGER_PATH
    return [r for r in _read_ledger(path) if str(r.get("case_id")) == str(case_id)]


def get_ledger_tail(limit: int = 10, ledger_path: str | Path | None = None) -> list[dict[str, Any]]:
    path = Path(ledger_path) if ledger_path else DEFAULT_LEDGER_PATH
    records = _read_ledger(path)
    return records[-max(1, int(limit)) :]


def append_blockchain_event(
    event_type: str,
    case_id: str,
    payload: dict[str, Any] | None = None,
    ledger_path: str | Path | None = None,
) -> dict[str, Any]:
    path = Path(ledger_path) if ledger_path else DEFAULT_LEDGER_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    immutable_mode = os.getenv("TRACEON_LEDGER_IMMUTABLE", "false").lower() == "true"
    integrity = verify_ledger(path)
    if immutable_mode and not integrity["valid"]:
        raise RuntimeError("Ledger integrity check failed in immutable mode; refusing append.")

    records = _read_ledger(path)
    prev_hash = records[-1].get("hash", "") if records else ""

    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "case_id": case_id,
        "payload": payload or {},
    }

    serialized_event = json.dumps(event, sort_keys=True, separators=(",", ":"))
    current_hash = hashlib.sha256(f"{serialized_event}{prev_hash}".encode("utf-8")).hexdigest()

    entry = {**event, "prev_hash": prev_hash, "hash": current_hash}
    records.append(entry)
    path.write_text(json.dumps(records, indent=2), encoding="utf-8")
    return entry
