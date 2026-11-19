import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _read_json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_products() -> list[dict]:
    return _read_json(DATA_DIR / "products.json")


def load_clients() -> dict[str, dict]:
    clients = {}
    for path in sorted((DATA_DIR / "clients").glob("*.json")):
        client = _read_json(path)
        clients[client["id"]] = client
    return clients


def get_client(client_id: str) -> dict | None:
    return load_clients().get(client_id)


def public_client_view(client: dict) -> dict:
    return {
        "id": client["id"],
        "name": client["name"],
        "headline": client["headline"],
        "public_profile": client["public_profile"],
        "opening_line": client["opening_line"],
    }
