from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
REVOKED_PATH = ROOT_DIR / "data" / "security" / "revoked_tokens.json"


def _read() -> list[dict[str, Any]]:
    if not REVOKED_PATH.exists():
        return []
    try:
        payload = json.loads(REVOKED_PATH.read_text(encoding="utf-8") or "[]")
        if isinstance(payload, list):
            return payload
    except json.JSONDecodeError:
        pass
    return []


def _write(items: list[dict[str, Any]]) -> None:
    REVOKED_PATH.parent.mkdir(parents=True, exist_ok=True)
    REVOKED_PATH.write_text(json.dumps(items, indent=2), encoding="utf-8")


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def is_token_revoked(token: str) -> bool:
    h = token_hash(token)
    return any(x.get("token_hash") == h for x in _read())


def revoke_token(token: str, reason: str = "manual_revoke", case_id: str | None = None) -> dict[str, Any]:
    h = token_hash(token)
    items = _read()
    for item in items:
        if item.get("token_hash") == h:
            return item
    entry = {
        "token_hash": h,
        "reason": reason,
        "case_id": case_id,
        "revoked_at": datetime.now(timezone.utc).isoformat(),
    }
    items.append(entry)
    _write(items)
    return entry


def list_revoked() -> list[dict[str, Any]]:
    return _read()
