import json
import sys as _sys
from pathlib import Path

# Guard: preserve path constants through importlib.reload so that unittest.mock
# patches applied before the reload remain in effect.  On the very first import
# _initialized is absent on the (partially-constructed) module, so the block
# runs normally and sets the real paths.  On subsequent reloads the guard
# short-circuits, leaving any patch-applied values intact.
_mod = _sys.modules.get(__name__)
if _mod is None or not getattr(_mod, "_initialized", False):
    APP_SUPPORT = Path.home() / "Library" / "Application Support" / "IntenType"
    SETTINGS_PATH = APP_SUPPORT / "settings.json"
    _initialized = True

DEFAULT_SETTINGS: dict = {
    "openai_api_key": "",
    "whisper_model": "small.en",
    "tone_mappings": {},
    "history_enabled": True,
}

BUILTIN_TONES: dict[str, str] = {
    "Formal": "Use professional language, complete sentences, no contractions.",
    "Casual": "Natural, conversational. Contractions fine.",
    "Terse": "Minimal words. Drop pleasantries. Bullet points if listing.",
}


def load() -> dict:
    if not SETTINGS_PATH.exists():
        return DEFAULT_SETTINGS.copy()
    with open(SETTINGS_PATH) as f:
        data = json.load(f)
    return {**DEFAULT_SETTINGS, **data}


def save(s: dict) -> None:
    APP_SUPPORT.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_PATH, "w") as f:
        json.dump(s, f, indent=2)


def get_tone(app_name: str) -> tuple[str, str]:
    s = load()
    mapping = s.get("tone_mappings", {}).get(app_name, {})
    tone_name = mapping.get("tone", "Casual")
    if tone_name == "Custom":
        return tone_name, mapping.get("custom_instruction", "")
    return tone_name, BUILTIN_TONES.get(tone_name, BUILTIN_TONES["Casual"])
