from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import ai, content, prompts

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
MAX_MESSAGES = 80

app = FastAPI(title="ClientLens - Bank Client Discovery Simulator")


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class ChatRequest(BaseModel):
    client_id: str
    messages: list[Message]


class FeedbackRequest(BaseModel):
    client_id: str
    messages: list[Message]
    summary: str = Field(default="", max_length=6000)
    recommended_product_ids: list[str] = []


def _require_client(client_id: str) -> dict:
    client = content.get_client(client_id)
    if not client:
        raise HTTPException(404, f"Unknown client '{client_id}'")
    return client


@app.get("/api/clients")
def list_clients():
    return [content.public_client_view(c) for c in content.load_clients().values()]


@app.get("/api/products")
def list_products():
    return content.load_products()


@app.post("/api/chat")
def chat(req: ChatRequest):
    client = _require_client(req.client_id)
    if not req.messages or req.messages[-1].role != "user":
        raise HTTPException(400, "The last message must be from the student.")

    history = [m.model_dump() for m in req.messages[-MAX_MESSAGES:]]
    convo = [{"role": "assistant", "content": client["opening_line"]}] + history
    system = prompts.client_system_prompt(client, content.load_products())
    try:
        reply = ai.chat([{"role": "system", "content": system}] + convo, temperature=0.7, max_tokens=400)
    except ai.AIError as e:
        raise HTTPException(502, str(e))
    return {"reply": reply}


@app.post("/api/feedback")
def feedback(req: FeedbackRequest):
    client = _require_client(req.client_id)
    if not any(m.role == "user" for m in req.messages):
        raise HTTPException(400, "Interview the client before asking for feedback.")

    products = content.load_products()
    convo = [{"role": "assistant", "content": client["opening_line"]}] + \
            [m.model_dump() for m in req.messages[-MAX_MESSAGES:]]
    user_msg = prompts.coach_user_message(client, products, convo, req.summary, req.recommended_product_ids)
    try:
        text = ai.chat(
            [{"role": "system", "content": prompts.coach_system_prompt()},
             {"role": "user", "content": user_msg}],
            model=ai.AI_COACH_MODEL, temperature=0.3, max_tokens=1800,
        )
    except ai.AIError as e:
        raise HTTPException(502, str(e))
    return {"feedback": text}


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
