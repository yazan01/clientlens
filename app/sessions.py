import json
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

SESSIONS_DIR = Path(__file__).resolve().parent.parent / "sessions"
_ID_RE = re.compile(r"^[0-9a-f]{32}$")
_lock = threading.Lock()
_cache: dict[str, dict] = {}


def _path(session_id: str) -> Path:
    return SESSIONS_DIR / f"{session_id}.json"


def _save(session: dict) -> None:
    SESSIONS_DIR.mkdir(exist_ok=True)
    session["updated_at"] = datetime.now(timezone.utc).isoformat()
    tmp = _path(session["id"]).with_suffix(".tmp")
    tmp.write_text(json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(_path(session["id"]))


def create(client_id: str) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    session = {
        "id": uuid.uuid4().hex,
        "client_id": client_id,
        "created_at": now,
        "updated_at": now,
        "messages": [],
        "summary": "",
        "recommended_product_ids": [],
        "feedback": "",
    }
    with _lock:
        _cache[session["id"]] = session
        _save(session)
    return session


def get(session_id: str) -> dict | None:
    if not _ID_RE.match(session_id or ""):
        return None
    with _lock:
        if session_id in _cache:
            return _cache[session_id]
        path = _path(session_id)
        if not path.exists():
            return None
        session = json.loads(path.read_text(encoding="utf-8"))
        _cache[session_id] = session
        return session


def add_messages(session: dict, *messages: dict) -> None:
    with _lock:
        session["messages"].extend(messages)
        session["feedback"] = ""
        _save(session)


def set_feedback(session: dict, summary: str, recommended_ids: list[str], feedback: str) -> None:
    with _lock:
        session["summary"] = summary
        session["recommended_product_ids"] = recommended_ids
        session["feedback"] = feedback
        _save(session)
