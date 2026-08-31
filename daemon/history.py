import json
from daemon.settings import APP_SUPPORT

HISTORY_PATH = APP_SUPPORT / "history.json"
_MAX = 100


def load() -> list[dict]:
    if not HISTORY_PATH.exists():
        return []
    try:
        return json.loads(HISTORY_PATH.read_text())
    except Exception:
        return []


def add(entry: dict) -> None:
    entries = load()
    entries.append(entry)
    if len(entries) > _MAX:
        entries = entries[-_MAX:]
    try:
        APP_SUPPORT.mkdir(parents=True, exist_ok=True)
        HISTORY_PATH.write_text(json.dumps(entries, indent=2))
    except Exception:
        pass


def get_examples_for_app(app_name: str, n: int = 4) -> list[dict]:
    """Return last n (raw, polished) pairs for this app as few-shot examples."""
    matches = [
        {"raw": e["raw"], "polished": e["polished"]}
        for e in load()
        if e.get("app") == app_name and e.get("raw") and e.get("polished")
    ]
    return matches[-n:]
