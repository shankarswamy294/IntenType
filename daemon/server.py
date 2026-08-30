import os
import threading
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
from daemon import settings as settings_mod

app = FastAPI(title="IntenType")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8421"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_history: list[dict] = []


class SettingsUpdate(BaseModel):
    openai_api_key: str | None = None
    whisper_model: str | None = None
    tone_mappings: dict | None = None
    history_enabled: bool | None = None


@app.get("/api/settings")
def get_settings():
    s = settings_mod.load()
    if s.get("openai_api_key"):
        s["openai_api_key"] = "sk-...hidden"
    return s


@app.post("/api/settings")
def update_settings(body: SettingsUpdate):
    s = settings_mod.load()
    if body.openai_api_key is not None and not body.openai_api_key.startswith("sk-..."):
        s["openai_api_key"] = body.openai_api_key
    if body.whisper_model is not None:
        s["whisper_model"] = body.whisper_model
    if body.tone_mappings is not None:
        s["tone_mappings"] = body.tone_mappings
    if body.history_enabled is not None:
        s["history_enabled"] = body.history_enabled
    settings_mod.save(s)
    return {"status": "ok"}


@app.get("/api/tones")
def get_tones():
    return settings_mod.BUILTIN_TONES


@app.get("/api/history")
def get_history():
    return _history[-50:]


@app.post("/api/history/clear")
def clear_history():
    _history.clear()
    return {"status": "ok"}


def add_history_entry(entry: dict) -> None:
    _history.append(entry)
    if len(_history) > 50:
        _history.pop(0)


def start(port: int = 8421, dist_dir: str | None = None) -> None:
    if dist_dir is None:
        import sys
        bundle_resources = os.path.join(
            os.path.dirname(sys.executable), "..", "Resources", "dist"
        )
        if os.path.isdir(bundle_resources):
            dist_dir = bundle_resources
        elif os.path.isdir("dashboard/dist"):
            dist_dir = "dashboard/dist"

    if dist_dir and os.path.isdir(dist_dir):
        app.mount("/", StaticFiles(directory=dist_dir, html=True), name="static")

    t = threading.Thread(
        target=uvicorn.run,
        args=(app,),
        kwargs={"host": "127.0.0.1", "port": port, "log_level": "error"},
        daemon=True,
    )
    t.start()
