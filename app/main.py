import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import ai, content, prompts, sessions

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
MAX_MESSAGES = 80

app = FastAPI(title="ClientLens - Bank Client Discovery Simulator")

_busy: set[str] = set()
_busy_lock = threading.Lock()


class NewSessionRequest(BaseModel):
    client_id: str


class MessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class FeedbackRequest(BaseModel):
    summary: str = Field(default="", max_length=6000)
    recommended_product_ids: list[str] = []


def _require_client(client_id: str) -> dict:
    client = content.get_client(client_id)
    if not client:
        raise HTTPException(404, f"Unknown client '{client_id}'")
    return client


def _require_session(session_id: str) -> dict:
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found. Start a new interview.")
    return session


def _acquire(session_id: str) -> None:
    with _busy_lock:
        if session_id in _busy:
            raise HTTPException(409, "Please wait for the previous reply.")
        _busy.add(session_id)


def _release(session_id: str) -> None:
    with _busy_lock:
        _busy.discard(session_id)


def _conversation(client: dict, messages: list[dict]) -> list[dict]:
    return [{"role": "assistant", "content": client["opening_line"]}] + messages[-MAX_MESSAGES:]


def _session_view(session: dict) -> dict:
    return {
        "session_id": session["id"],
        "client_id": session["client_id"],
        "messages": session["messages"],
        "summary": session["summary"],
        "recommended_product_ids": session["recommended_product_ids"],
        "feedback": session["feedback"],
    }


@app.get("/api/clients")
def list_clients():
    return [content.public_client_view(c) for c in content.load_clients().values()]


@app.get("/api/products")
def list_products():
    return content.load_products()


@app.post("/api/sessions")
def create_session(req: NewSessionRequest):
    _require_client(req.client_id)
    return _session_view(sessions.create(req.client_id))


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str):
    return _session_view(_require_session(session_id))


@app.post("/api/sessions/{session_id}/messages")
def send_message(session_id: str, req: MessageRequest):
    session = _require_session(session_id)
    client = _require_client(session["client_id"])
    student_msg = {"role": "user", "content": req.content.strip()}

    _acquire(session_id)
    try:
        system = prompts.client_system_prompt(client, content.load_products())
        convo = _conversation(client, session["messages"] + [student_msg])
        try:
            reply = ai.chat([{"role": "system", "content": system}] + convo, temperature=0.5, max_tokens=1000)
        except ai.AIError as e:
            raise HTTPException(502, str(e))
        sessions.add_messages(session, student_msg, {"role": "assistant", "content": reply})
    finally:
        _release(session_id)
    return {"reply": reply}


@app.post("/api/sessions/{session_id}/feedback")
def feedback(session_id: str, req: FeedbackRequest):
    session = _require_session(session_id)
    client = _require_client(session["client_id"])
    if not any(m["role"] == "user" for m in session["messages"]):
        raise HTTPException(400, "Interview the client before asking for feedback.")

    _acquire(session_id)
    try:
        products = content.load_products()
        user_msg = prompts.coach_user_message(client, products, _conversation(client, session["messages"]),
                                              req.summary, req.recommended_product_ids)
        try:
            text = ai.chat(
                [{"role": "system", "content": prompts.coach_system_prompt()},
                 {"role": "user", "content": user_msg}],
                model=ai.AI_COACH_MODEL, temperature=0.3, max_tokens=4000,
            )
        except ai.AIError as e:
            raise HTTPException(502, str(e))
        sessions.set_feedback(session, req.summary, req.recommended_product_ids, text)
    finally:
        _release(session_id)
    return {"feedback": text}


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
