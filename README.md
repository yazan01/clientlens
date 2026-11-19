# ClientLens - Bank Client Discovery Simulator

## How to install and run

Requires Python 3.10 or newer.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

On macOS/Linux, use `source .venv/bin/activate` and `cp .env.example .env` instead.

Open <http://localhost:8000>.

## How to configure the AI connection

Set these values in the `.env` file:

| Variable | Description |
|---|---|
| `AI_BASE_URL` | URL of the OpenAI-compatible API |
| `AI_API_KEY` | API key |
| `AI_MODEL` | Model name |
| `AI_COACH_MODEL` | Optional model for the AI Coach (uses `AI_MODEL` if empty) |

Example:

```env
AI_BASE_URL=https://openrouter.ai/api/v1
AI_API_KEY=sk-or-v1-your-key-here
AI_MODEL=baidu/ernie-5.5-flash-preview:free
AI_COACH_MODEL=nvidia/nemotron-3-ultra-550b-a55b:free
```

Restart the server after changing `.env`.

## AI provider and model used for testing

- Provider: OpenRouter
- AI Client model: `baidu/ernie-5.5-flash-preview:free`
- AI Coach model: `nvidia/nemotron-3-ultra-550b-a55b:free`
