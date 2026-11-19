import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_missing = [name for name in ("AI_BASE_URL", "AI_API_KEY", "AI_MODEL") if not os.getenv(name)]
if _missing:
    raise RuntimeError(f"Missing in .env: {', '.join(_missing)}. Copy .env.example to .env and fill them in.")

AI_BASE_URL = os.environ["AI_BASE_URL"]
AI_API_KEY = os.environ["AI_API_KEY"]
AI_MODEL = os.environ["AI_MODEL"]
AI_COACH_MODEL = os.getenv("AI_COACH_MODEL") or AI_MODEL

_client = OpenAI(
    base_url=AI_BASE_URL,
    api_key=AI_API_KEY,
    default_headers={"X-Title": "ClientLens - Bank Client Discovery Simulator"},
)


class AIError(Exception):
    pass


def chat(messages: list[dict], *, model: str | None = None, temperature: float = 0.7,
         max_tokens: int = 1500) -> str:
    try:
        resp = _client.chat.completions.create(
            model=model or AI_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as e:
        raise AIError(f"AI provider error: {e}") from e

    if not resp.choices or not resp.choices[0].message.content:
        if resp.choices and resp.choices[0].finish_reason == "length":
            raise AIError("The AI model used up its token limit before answering (reasoning models think first). "
                          "Try again or raise max_tokens.")
        raise AIError("The AI model returned an empty response. Try again or switch AI_MODEL.")
    return resp.choices[0].message.content.strip()
