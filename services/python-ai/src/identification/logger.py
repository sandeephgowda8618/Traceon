from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_LOCK = threading.Lock()


def _ensure_json_array(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("[]\n", encoding="utf-8")
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8") or "[]")
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass
    return []


def append_search_log(log_path: str | Path, event: dict[str, Any]) -> None:
    """Append a structured search event to logs/search_logs.json."""
    path = Path(log_path)
    with _LOCK:
        records = _ensure_json_array(path)
        if "timestamp" not in event:
            event["timestamp"] = datetime.now(timezone.utc).isoformat()
        records.append(event)
        path.write_text(json.dumps(records, indent=2), encoding="utf-8")
