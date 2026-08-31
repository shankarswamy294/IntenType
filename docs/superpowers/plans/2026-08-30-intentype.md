# IntenType Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a macOS background daemon that transcribes held-hotkey speech locally via faster-whisper, rewrites it tone-aware via GPT-4o-mini, and injects polished text into any active app — with a React dashboard for configuration.

**Architecture:** Python daemon (PyObjC) handles CGEventTap hotkey, sounddevice audio capture, faster-whisper ASR, GPT-4o-mini intent rewriting, and NSPasteboard+CGEventPost text injection. A FastAPI server embedded in the daemon serves a Vite/React/Zustand dashboard on port 8421. Packaged as a `.app` via py2app.

**Tech Stack:** Python 3.11+, PyObjC (Cocoa + Quartz), faster-whisper, sounddevice, openai SDK v1+, FastAPI, uvicorn, React 18, TypeScript, Vite, TailwindCSS, Zustand, py2app.

---

## File Map

```
IntenType/
├── daemon/
│   ├── __init__.py
│   ├── main.py          # NSApplication entry point, NSStatusItem, wires all modules
│   ├── hotkey.py        # CGEventTap listener for Right Option key
│   ├── audio.py         # sounddevice PCM capture buffer
│   ├── asr.py           # faster-whisper model wrapper
│   ├── intent.py        # GPT-4o-mini tone-aware rewrite
│   ├── injector.py      # NSPasteboard swap + CGEventPost Cmd+V
│   ├── context.py       # NSWorkspace app name + AXUIElement safety checks
│   ├── settings.py      # ~/Library/Application Support/IntenType/settings.json
│   └── server.py        # FastAPI app, endpoints, history store, uvicorn bootstrap
├── dashboard/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── stores/
│       │   ├── settingsStore.ts
│       │   ├── historyStore.ts
│       │   └── toneStore.ts
│       └── views/
│           ├── ToneMapper.tsx
│           ├── History.tsx
│           └── SettingsView.tsx
├── tests/
│   ├── __init__.py
│   ├── test_settings.py
│   ├── test_context.py
│   ├── test_audio.py
│   ├── test_asr.py
│   ├── test_intent.py
│   ├── test_injector.py
│   └── test_server.py
├── setup.py             # py2app config
├── requirements.txt
├── .env                 # OPENAI_API_KEY (dev only, gitignored)
└── .gitignore
```

---

## Task 1: Project Scaffold & Git Init

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `.env`
- Create: `daemon/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Initialise git and create directory structure**

```bash
cd /Users/shankar/IntenType
git init
mkdir -p daemon tests dashboard/src/stores dashboard/src/views
touch daemon/__init__.py tests/__init__.py
```

- [ ] **Step 2: Write `requirements.txt`**

```
pyobjc-core>=10.0
pyobjc-framework-Cocoa>=10.0
pyobjc-framework-Quartz>=10.0
faster-whisper>=1.0.3
sounddevice>=0.4.6
numpy>=1.26.0
openai>=1.30.0
fastapi>=0.111.0
uvicorn>=0.29.0
pydantic>=2.7.0
httpx>=0.27.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
```

- [ ] **Step 3: Write `.gitignore`**

```
__pycache__/
*.pyc
.env
*.egg-info/
build/
dist/
*.app/
dashboard/node_modules/
dashboard/dist/
.DS_Store
~/Library/Application\ Support/IntenType/
```

- [ ] **Step 4: Write `.env` (dev template — never committed)**

```
OPENAI_API_KEY=sk-proj-your-key-here
```

- [ ] **Step 5: Install Python dependencies**

```bash
pip install -r requirements.txt
```

Expected: all packages install without error.

- [ ] **Step 6: Commit scaffold**

```bash
git add requirements.txt .gitignore daemon/__init__.py tests/__init__.py
git commit -m "chore: project scaffold"
```

---

## Task 2: Settings Module

**Files:**
- Create: `daemon/settings.py`
- Create: `tests/test_settings.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_settings.py
import json
import pytest
from pathlib import Path
from unittest.mock import patch


def test_load_returns_defaults_when_no_file(tmp_path):
    with patch("daemon.settings.SETTINGS_PATH", tmp_path / "settings.json"):
        from daemon import settings
        result = settings.load()
    assert result["whisper_model"] == "small.en"
    assert result["tone_mappings"] == {}
    assert result["history_enabled"] is True
    assert result["openai_api_key"] == ""


def test_save_and_load_roundtrip(tmp_path):
    settings_path = tmp_path / "settings.json"
    with patch("daemon.settings.SETTINGS_PATH", settings_path), \
         patch("daemon.settings.APP_SUPPORT", tmp_path):
        from daemon import settings
        settings.save({"openai_api_key": "sk-test", "whisper_model": "medium.en",
                       "tone_mappings": {}, "history_enabled": False})
        result = settings.load()
    assert result["openai_api_key"] == "sk-test"
    assert result["whisper_model"] == "medium.en"
    assert result["history_enabled"] is False


def test_get_tone_returns_casual_for_unknown_app(tmp_path):
    with patch("daemon.settings.SETTINGS_PATH", tmp_path / "settings.json"):
        from daemon import settings
        tone_name, instructions = settings.get_tone("UnknownApp")
    assert tone_name == "Casual"
    assert "conversational" in instructions.lower()


def test_get_tone_returns_mapped_builtin(tmp_path):
    settings_path = tmp_path / "settings.json"
    with patch("daemon.settings.SETTINGS_PATH", settings_path), \
         patch("daemon.settings.APP_SUPPORT", tmp_path):
        from daemon import settings
        settings.save({
            "openai_api_key": "",
            "whisper_model": "small.en",
            "tone_mappings": {"Mail": {"tone": "Formal", "custom_instruction": ""}},
            "history_enabled": True,
        })
        tone_name, instructions = settings.get_tone("Mail")
    assert tone_name == "Formal"
    assert "professional" in instructions.lower()


def test_get_tone_returns_custom_instruction(tmp_path):
    settings_path = tmp_path / "settings.json"
    with patch("daemon.settings.SETTINGS_PATH", settings_path), \
         patch("daemon.settings.APP_SUPPORT", tmp_path):
        from daemon import settings
        settings.save({
            "openai_api_key": "",
            "whisper_model": "small.en",
            "tone_mappings": {"Cursor": {"tone": "Custom",
                                          "custom_instruction": "Be concise and technical."}},
            "history_enabled": True,
        })
        tone_name, instructions = settings.get_tone("Cursor")
    assert tone_name == "Custom"
    assert instructions == "Be concise and technical."
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /Users/shankar/IntenType
python -m pytest tests/test_settings.py -v
```

Expected: `ModuleNotFoundError` or `ImportError` — `daemon.settings` doesn't exist yet.

- [ ] **Step 3: Implement `daemon/settings.py`**

```python
import json
from pathlib import Path

APP_SUPPORT = Path.home() / "Library" / "Application Support" / "IntenType"
SETTINGS_PATH = APP_SUPPORT / "settings.json"

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
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
python -m pytest tests/test_settings.py -v
```

Expected: 5 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add daemon/settings.py tests/test_settings.py
git commit -m "feat: settings module with tone mapping"
```

---

## Task 3: Context Harvester

**Files:**
- Create: `daemon/context.py`
- Create: `tests/test_context.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_context.py
from unittest.mock import patch, MagicMock
import pytest


def _make_frontmost(name="Slack"):
    app = MagicMock()
    app.localizedName.return_value = name
    return app


def test_returns_app_name(monkeypatch):
    mock_workspace = MagicMock()
    mock_workspace.sharedWorkspace.return_value.frontmostApplication.return_value = _make_frontmost("Mail")

    with patch.dict("sys.modules", {
        "AppKit": MagicMock(NSWorkspace=mock_workspace),
        "Quartz": MagicMock(
            CGSIsSecureEventInputEnabled=lambda: False,
            AXUIElementCreateSystemWide=MagicMock(return_value=MagicMock()),
            AXUIElementCopyAttributeValue=MagicMock(return_value=(1, None)),  # err=1 → no focused element
            kAXFocusedUIElementAttribute="AXFocusedUIElement",
        ),
    }):
        from daemon import context
        import importlib; importlib.reload(context)
        result = context.get_context()

    assert result["app"] == "Mail"
    assert result["safe"] is True


def test_blocks_on_secure_input(monkeypatch):
    mock_workspace = MagicMock()
    mock_workspace.sharedWorkspace.return_value.frontmostApplication.return_value = _make_frontmost("Terminal")

    with patch.dict("sys.modules", {
        "AppKit": MagicMock(NSWorkspace=mock_workspace),
        "Quartz": MagicMock(
            CGSIsSecureEventInputEnabled=lambda: True,
            AXUIElementCreateSystemWide=MagicMock(),
            AXUIElementCopyAttributeValue=MagicMock(return_value=(1, None)),
            kAXFocusedUIElementAttribute="AXFocusedUIElement",
        ),
    }):
        from daemon import context
        import importlib; importlib.reload(context)
        result = context.get_context()

    assert result["safe"] is False
    assert result["reason"] == "secure_input"


def test_blocks_on_password_field(monkeypatch):
    mock_workspace = MagicMock()
    mock_workspace.sharedWorkspace.return_value.frontmostApplication.return_value = _make_frontmost("Safari")

    mock_focused = MagicMock()

    def fake_ax_copy(element, attr, _):
        if attr == "AXFocusedUIElement":
            return (0, mock_focused)
        if attr == "AXSubrole":
            return (0, "AXSecureTextField")
        return (1, None)

    with patch.dict("sys.modules", {
        "AppKit": MagicMock(NSWorkspace=mock_workspace),
        "Quartz": MagicMock(
            CGSIsSecureEventInputEnabled=lambda: False,
            AXUIElementCreateSystemWide=MagicMock(return_value=MagicMock()),
            AXUIElementCopyAttributeValue=MagicMock(side_effect=fake_ax_copy),
            kAXFocusedUIElementAttribute="AXFocusedUIElement",
        ),
    }):
        from daemon import context
        import importlib; importlib.reload(context)
        result = context.get_context()

    assert result["safe"] is False
    assert result["reason"] == "password_field"
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python -m pytest tests/test_context.py -v
```

Expected: `ModuleNotFoundError` for `daemon.context`.

- [ ] **Step 3: Implement `daemon/context.py`**

```python
from AppKit import NSWorkspace
import Quartz


def get_context() -> dict:
    """Returns app name and whether text injection is safe to proceed."""
    frontmost = NSWorkspace.sharedWorkspace().frontmostApplication()
    app_name = frontmost.localizedName() if frontmost else "Unknown"

    if Quartz.CGSIsSecureEventInputEnabled():
        return {"app": app_name, "safe": False, "reason": "secure_input"}

    system_el = Quartz.AXUIElementCreateSystemWide()
    err, focused = Quartz.AXUIElementCopyAttributeValue(
        system_el, Quartz.kAXFocusedUIElementAttribute, None
    )
    if err == 0 and focused is not None:
        err2, subrole = Quartz.AXUIElementCopyAttributeValue(focused, "AXSubrole", None)
        if err2 == 0 and subrole == "AXSecureTextField":
            return {"app": app_name, "safe": False, "reason": "password_field"}

    return {"app": app_name, "safe": True, "reason": None}
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_context.py -v
```

Expected: 3 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add daemon/context.py tests/test_context.py
git commit -m "feat: context harvester with security checks"
```

---

## Task 4: Audio Capture Module

**Files:**
- Create: `daemon/audio.py`
- Create: `tests/test_audio.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_audio.py
import numpy as np
from unittest.mock import patch, MagicMock, call
import struct


def test_stop_returns_empty_when_no_frames():
    with patch.dict("sys.modules", {"sounddevice": MagicMock()}):
        from daemon import audio
        import importlib; importlib.reload(audio)
        cap = audio.AudioCapture()
        result = cap.stop()
    assert isinstance(result, np.ndarray)
    assert len(result) == 0


def test_stop_returns_normalised_float32():
    with patch.dict("sys.modules", {"sounddevice": MagicMock()}):
        from daemon import audio
        import importlib; importlib.reload(audio)
        cap = audio.AudioCapture()
        # Simulate two int16 frames: max positive and zero
        frame = struct.pack("<hh", 32767, 0)
        cap._frames.append(frame)
        result = cap.stop()
    assert result.dtype == np.float32
    assert abs(result[0] - 1.0) < 0.001
    assert result[1] == 0.0


def test_start_creates_stream_and_stop_closes_it():
    mock_sd = MagicMock()
    mock_stream = MagicMock()
    mock_sd.RawInputStream.return_value.__enter__ = MagicMock(return_value=mock_stream)
    mock_sd.RawInputStream.return_value = mock_stream

    with patch.dict("sys.modules", {"sounddevice": mock_sd}):
        from daemon import audio
        import importlib; importlib.reload(audio)
        cap = audio.AudioCapture()
        cap.start()
        cap.stop()

    mock_stream.start.assert_called_once()
    mock_stream.stop.assert_called_once()
    mock_stream.close.assert_called_once()
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python -m pytest tests/test_audio.py -v
```

Expected: `ModuleNotFoundError` for `daemon.audio`.

- [ ] **Step 3: Implement `daemon/audio.py`**

```python
import threading
import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "int16"


class AudioCapture:
    def __init__(self):
        self._frames: list[bytes] = []
        self._stream = None
        self._lock = threading.Lock()

    def start(self) -> None:
        self._frames = []
        self._stream = sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> np.ndarray:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        with self._lock:
            if not self._frames:
                return np.array([], dtype=np.float32)
            raw = np.frombuffer(b"".join(self._frames), dtype=np.int16)
            return raw.astype(np.float32) / 32768.0

    def _callback(self, indata, frames, time, status) -> None:
        with self._lock:
            self._frames.append(bytes(indata))
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_audio.py -v
```

Expected: 3 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add daemon/audio.py tests/test_audio.py
git commit -m "feat: audio capture module"
```

---

## Task 5: ASR Module

**Files:**
- Create: `daemon/asr.py`
- Create: `tests/test_asr.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_asr.py
import numpy as np
from unittest.mock import patch, MagicMock


def _make_mock_faster_whisper(segments_text: list[str]):
    mock_fw = MagicMock()
    mock_model = MagicMock()
    fake_segments = [MagicMock(text=t) for t in segments_text]
    mock_model.transcribe.return_value = (iter(fake_segments), MagicMock())
    mock_fw.WhisperModel.return_value = mock_model
    return mock_fw, mock_model


def test_transcribe_joins_segments():
    mock_fw, mock_model = _make_mock_faster_whisper([" Hello", " world"])
    with patch.dict("sys.modules", {"faster_whisper": mock_fw}):
        from daemon import asr
        import importlib; importlib.reload(asr)
        engine = asr.ASR("small.en")
        audio = np.zeros(16000, dtype=np.float32)
        result = engine.transcribe(audio)
    assert result == "Hello world"


def test_transcribe_returns_empty_for_empty_audio():
    mock_fw, _ = _make_mock_faster_whisper([])
    with patch.dict("sys.modules", {"faster_whisper": mock_fw}):
        from daemon import asr
        import importlib; importlib.reload(asr)
        engine = asr.ASR("small.en")
        result = engine.transcribe(np.array([], dtype=np.float32))
    assert result == ""


def test_reload_reinitialises_model():
    mock_fw, mock_model = _make_mock_faster_whisper([])
    with patch.dict("sys.modules", {"faster_whisper": mock_fw}):
        from daemon import asr
        import importlib; importlib.reload(asr)
        engine = asr.ASR("small.en")
        engine.reload("medium.en")
    assert mock_fw.WhisperModel.call_count == 2
    assert mock_fw.WhisperModel.call_args_list[1][0][0] == "medium.en"
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python -m pytest tests/test_asr.py -v
```

Expected: `ModuleNotFoundError` for `daemon.asr`.

- [ ] **Step 3: Implement `daemon/asr.py`**

```python
import numpy as np
from faster_whisper import WhisperModel


class ASR:
    def __init__(self, model_size: str = "small.en"):
        self._model = WhisperModel(model_size, device="auto", compute_type="auto")
        self._model_size = model_size

    def transcribe(self, audio: np.ndarray) -> str:
        if len(audio) == 0:
            return ""
        segments, _ = self._model.transcribe(audio, language="en", beam_size=5)
        return " ".join(s.text for s in segments).strip()

    def reload(self, model_size: str) -> None:
        self._model_size = model_size
        self._model = WhisperModel(model_size, device="auto", compute_type="auto")
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_asr.py -v
```

Expected: 3 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add daemon/asr.py tests/test_asr.py
git commit -m "feat: ASR module wrapping faster-whisper"
```

---

## Task 6: Intent Layer

**Files:**
- Create: `daemon/intent.py`
- Create: `tests/test_intent.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_intent.py
from unittest.mock import patch, MagicMock


def _mock_openai_response(text: str):
    mock_openai = MagicMock()
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = text
    mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])
    mock_openai.OpenAI.return_value = mock_client
    return mock_openai, mock_client


def test_rewrite_calls_gpt_with_tone(tmp_path):
    mock_openai, mock_client = _mock_openai_response("I wanted to ask about the meeting.")

    with patch.dict("sys.modules", {"openai": mock_openai}), \
         patch("daemon.settings.SETTINGS_PATH", tmp_path / "settings.json"), \
         patch("daemon.settings.APP_SUPPORT", tmp_path):
        from daemon import settings, intent
        import importlib; importlib.reload(settings); importlib.reload(intent)
        settings.save({
            "openai_api_key": "sk-test",
            "whisper_model": "small.en",
            "tone_mappings": {"Slack": {"tone": "Casual", "custom_instruction": ""}},
            "history_enabled": True,
        })
        result = intent.rewrite("um yeah I wanted to ask about the meeting", "Slack")

    assert result == "I wanted to ask about the meeting."
    call_kwargs = mock_client.chat.completions.create.call_args[1]
    assert call_kwargs["model"] == "gpt-4o-mini"
    system_msg = call_kwargs["messages"][0]["content"]
    assert "Casual" in system_msg


def test_rewrite_falls_back_to_raw_when_no_api_key(tmp_path):
    mock_openai, _ = _mock_openai_response("")

    with patch.dict("sys.modules", {"openai": mock_openai}), \
         patch("daemon.settings.SETTINGS_PATH", tmp_path / "settings.json"), \
         patch("daemon.settings.APP_SUPPORT", tmp_path):
        from daemon import settings, intent
        import importlib; importlib.reload(settings); importlib.reload(intent)
        # settings.json doesn't exist → key is ""
        result = intent.rewrite("um hello there", "Mail")

    assert result == "um hello there"
    mock_openai.OpenAI.assert_not_called()


def test_rewrite_uses_formal_tone_for_mail(tmp_path):
    mock_openai, mock_client = _mock_openai_response("Please review the attached document.")

    with patch.dict("sys.modules", {"openai": mock_openai}), \
         patch("daemon.settings.SETTINGS_PATH", tmp_path / "settings.json"), \
         patch("daemon.settings.APP_SUPPORT", tmp_path):
        from daemon import settings, intent
        import importlib; importlib.reload(settings); importlib.reload(intent)
        settings.save({
            "openai_api_key": "sk-test",
            "whisper_model": "small.en",
            "tone_mappings": {"Mail": {"tone": "Formal", "custom_instruction": ""}},
            "history_enabled": True,
        })
        result = intent.rewrite("uh please like review the attached document", "Mail")

    system_msg = mock_client.chat.completions.create.call_args[1]["messages"][0]["content"]
    assert "Formal" in system_msg
    assert "professional" in system_msg.lower()
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python -m pytest tests/test_intent.py -v
```

Expected: `ModuleNotFoundError` for `daemon.intent`.

- [ ] **Step 3: Implement `daemon/intent.py`**

```python
from openai import OpenAI
from daemon import settings

_SYSTEM_TEMPLATE = (
    'You are a voice-to-text assistant. Clean up the transcript — remove filler words '
    '("um", "uh", "like", "you know"), fix grammar and punctuation, and output natural '
    "written text. Do not add content that wasn't said. Output only the cleaned text "
    "with no preamble or explanation.\n"
    "Tone: {tone_name}. {tone_instructions}"
)


def rewrite(raw: str, app_name: str) -> str:
    s = settings.load()
    api_key = s.get("openai_api_key", "")
    if not api_key:
        return raw

    tone_name, tone_instructions = settings.get_tone(app_name)
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": _SYSTEM_TEMPLATE.format(
                    tone_name=tone_name,
                    tone_instructions=tone_instructions,
                ),
            },
            {"role": "user", "content": raw},
        ],
        max_tokens=500,
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_intent.py -v
```

Expected: 3 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add daemon/intent.py tests/test_intent.py
git commit -m "feat: intent layer with tone-aware GPT-4o-mini rewrite"
```

---

## Task 7: Text Injector

**Files:**
- Create: `daemon/injector.py`
- Create: `tests/test_injector.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_injector.py
from unittest.mock import patch, MagicMock, call


def _make_mocks():
    mock_appkit = MagicMock()
    mock_pb = MagicMock()
    mock_pb.types.return_value = ["public.utf8-plain-text"]
    mock_pb.dataForType_.return_value = b"original"
    mock_appkit.NSPasteboard.generalPasteboard.return_value = mock_pb
    mock_appkit.NSStringPboardType = "public.utf8-plain-text"

    mock_quartz = MagicMock()
    mock_src = MagicMock()
    mock_quartz.CGEventSourceCreate.return_value = mock_src
    mock_quartz.CGEventCreateKeyboardEvent.return_value = MagicMock()
    mock_quartz.kCGEventSourceStateCombinedSessionState = 1
    mock_quartz.kCGHIDEventTap = 0
    mock_quartz.kCGEventFlagMaskCommand = 1 << 20

    return mock_appkit, mock_pb, mock_quartz


def test_inject_posts_cmd_v(monkeypatch):
    mock_appkit, mock_pb, mock_quartz = _make_mocks()

    with patch.dict("sys.modules", {"AppKit": mock_appkit, "Quartz": mock_quartz}), \
         patch("time.sleep"):
        from daemon import injector
        import importlib; importlib.reload(injector)
        injector.inject("Hello world")

    assert mock_quartz.CGEventPost.call_count == 4


def test_inject_writes_text_to_clipboard(monkeypatch):
    mock_appkit, mock_pb, mock_quartz = _make_mocks()

    with patch.dict("sys.modules", {"AppKit": mock_appkit, "Quartz": mock_quartz}), \
         patch("time.sleep"):
        from daemon import injector
        import importlib; importlib.reload(injector)
        injector.inject("Hello world")

    mock_pb.setString_forType_.assert_called_once_with("Hello world", "public.utf8-plain-text")


def test_inject_restores_original_clipboard(monkeypatch):
    mock_appkit, mock_pb, mock_quartz = _make_mocks()

    with patch.dict("sys.modules", {"AppKit": mock_appkit, "Quartz": mock_quartz}), \
         patch("time.sleep"):
        from daemon import injector
        import importlib; importlib.reload(injector)
        injector.inject("Hello world")

    # declareTypes called twice: once to set new, once to restore
    assert mock_pb.declareTypes_owner_.call_count == 2
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python -m pytest tests/test_injector.py -v
```

Expected: `ModuleNotFoundError` for `daemon.injector`.

- [ ] **Step 3: Implement `daemon/injector.py`**

```python
import time
from AppKit import NSPasteboard, NSStringPboardType
import Quartz

_CMD = 0x37
_V = 0x09


def inject(text: str) -> None:
    pb = NSPasteboard.generalPasteboard()

    # Backup current clipboard
    orig_types = list(pb.types() or [])
    orig_data: dict = {}
    for t in orig_types:
        data = pb.dataForType_(t)
        if data is not None:
            orig_data[t] = data

    # Write polished text
    pb.declareTypes_owner_([NSStringPboardType], None)
    pb.setString_forType_(text, NSStringPboardType)

    # Synthesise Cmd+V
    src = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStateCombinedSessionState)
    cmd_dn = Quartz.CGEventCreateKeyboardEvent(src, _CMD, True)
    v_dn = Quartz.CGEventCreateKeyboardEvent(src, _V, True)
    v_up = Quartz.CGEventCreateKeyboardEvent(src, _V, False)
    cmd_up = Quartz.CGEventCreateKeyboardEvent(src, _CMD, False)

    Quartz.CGEventSetFlags(cmd_dn, Quartz.kCGEventFlagMaskCommand)
    Quartz.CGEventSetFlags(v_dn, Quartz.kCGEventFlagMaskCommand)

    Quartz.CGEventPost(Quartz.kCGHIDEventTap, cmd_dn)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, v_dn)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, v_up)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, cmd_up)

    time.sleep(0.1)

    # Restore original clipboard (best-effort)
    if orig_data:
        try:
            pb.declareTypes_owner_(list(orig_data.keys()), None)
            for t, d in orig_data.items():
                pb.setData_forType_(d, t)
        except Exception:
            pass
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_injector.py -v
```

Expected: 3 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add daemon/injector.py tests/test_injector.py
git commit -m "feat: text injector via clipboard swap and Cmd+V"
```

---

## Task 8: Hotkey Listener

**Files:**
- Create: `daemon/hotkey.py`
- Create: `tests/test_hotkey.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_hotkey.py
from unittest.mock import patch, MagicMock, call


_RIGHT_OPTION = 0x3D


def _make_quartz_mock():
    q = MagicMock()
    q.kCGHIDEventTap = 0
    q.kCGHeadInsertEventTap = 0
    q.kCGEventTapOptionDefault = 0
    q.kCGEventKeyDown = 10
    q.kCGEventKeyUp = 11
    q.CGEventMaskBit.side_effect = lambda x: 1 << x
    q.CGEventGetIntegerValueField.return_value = _RIGHT_OPTION
    q.kCGKeyboardEventKeycode = 9
    q.CGEventTapCreate.return_value = MagicMock()
    q.CFMachPortCreateRunLoopSource.return_value = MagicMock()
    return q


def test_on_down_callback_fires_on_key_down():
    q = _make_quartz_mock()
    on_down = MagicMock()
    on_up = MagicMock()

    with patch.dict("sys.modules", {"Quartz": q, "CoreFoundation": MagicMock()}):
        from daemon import hotkey
        import importlib; importlib.reload(hotkey)
        tap = hotkey.create_event_tap(on_down, on_up)

    # Extract the callback passed to CGEventTapCreate
    callback = q.CGEventTapCreate.call_args[0][4]
    callback(None, q.kCGEventKeyDown, MagicMock(), None)

    on_down.assert_called_once()
    on_up.assert_not_called()


def test_on_up_callback_fires_on_key_up():
    q = _make_quartz_mock()
    on_down = MagicMock()
    on_up = MagicMock()

    with patch.dict("sys.modules", {"Quartz": q, "CoreFoundation": MagicMock()}):
        from daemon import hotkey
        import importlib; importlib.reload(hotkey)
        hotkey.create_event_tap(on_down, on_up)

    callback = q.CGEventTapCreate.call_args[0][4]
    callback(None, q.kCGEventKeyUp, MagicMock(), None)

    on_up.assert_called_once()
    on_down.assert_not_called()


def test_ignores_other_keycodes():
    q = _make_quartz_mock()
    q.CGEventGetIntegerValueField.return_value = 0x00  # not Right Option
    on_down = MagicMock()
    on_up = MagicMock()

    with patch.dict("sys.modules", {"Quartz": q, "CoreFoundation": MagicMock()}):
        from daemon import hotkey
        import importlib; importlib.reload(hotkey)
        hotkey.create_event_tap(on_down, on_up)

    callback = q.CGEventTapCreate.call_args[0][4]
    callback(None, q.kCGEventKeyDown, MagicMock(), None)
    on_down.assert_not_called()
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python -m pytest tests/test_hotkey.py -v
```

Expected: `ModuleNotFoundError` for `daemon.hotkey`.

- [ ] **Step 3: Implement `daemon/hotkey.py`**

```python
from typing import Callable
import Quartz
import CoreFoundation

_RIGHT_OPTION = 0x3D


def create_event_tap(on_down: Callable, on_up: Callable):
    def _callback(proxy, event_type, event, refcon):
        keycode = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
        if keycode != _RIGHT_OPTION:
            return event
        if event_type == Quartz.kCGEventKeyDown:
            on_down()
        elif event_type == Quartz.kCGEventKeyUp:
            on_up()
        return event

    mask = (
        Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown)
        | Quartz.CGEventMaskBit(Quartz.kCGEventKeyUp)
    )
    tap = Quartz.CGEventTapCreate(
        Quartz.kCGHIDEventTap,
        Quartz.kCGHeadInsertEventTap,
        Quartz.kCGEventTapOptionDefault,
        mask,
        _callback,
        None,
    )
    if tap is None:
        raise RuntimeError("CGEventTap could not be created. Check Accessibility permissions.")

    source = Quartz.CFMachPortCreateRunLoopSource(None, tap, 0)
    CoreFoundation.CFRunLoopAddSource(
        CoreFoundation.CFRunLoopGetCurrent(),
        source,
        CoreFoundation.kCFRunLoopCommonModes,
    )
    Quartz.CGEventTapEnable(tap, True)
    return tap
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_hotkey.py -v
```

Expected: 3 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add daemon/hotkey.py tests/test_hotkey.py
git commit -m "feat: CGEventTap hotkey listener for Right Option"
```

---

## Task 9: FastAPI Server

**Files:**
- Create: `daemon/server.py`
- Create: `tests/test_server.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_server.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from pathlib import Path


@pytest.fixture
def client(tmp_path):
    with patch("daemon.settings.SETTINGS_PATH", tmp_path / "settings.json"), \
         patch("daemon.settings.APP_SUPPORT", tmp_path):
        from daemon import server
        import importlib; importlib.reload(server)
        yield TestClient(server.app)


def test_get_settings_returns_defaults(client):
    resp = client.get("/api/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["whisper_model"] == "small.en"
    assert data["openai_api_key"] == ""


def test_post_settings_saves_model(client, tmp_path):
    with patch("daemon.settings.SETTINGS_PATH", tmp_path / "settings.json"), \
         patch("daemon.settings.APP_SUPPORT", tmp_path):
        resp = client.post("/api/settings", json={"whisper_model": "medium.en"})
    assert resp.status_code == 200
    resp2 = client.get("/api/settings")
    assert resp2.json()["whisper_model"] == "medium.en"


def test_api_key_is_masked_in_get(client, tmp_path):
    with patch("daemon.settings.SETTINGS_PATH", tmp_path / "settings.json"), \
         patch("daemon.settings.APP_SUPPORT", tmp_path):
        client.post("/api/settings", json={"openai_api_key": "sk-realkey123"})
        resp = client.get("/api/settings")
    assert "sk-realkey123" not in resp.json()["openai_api_key"]


def test_history_starts_empty(client):
    resp = client.get("/api/history")
    assert resp.status_code == 200
    assert resp.json() == []


def test_add_and_retrieve_history_entry(client):
    from daemon import server
    server.add_history_entry({
        "timestamp": "2026-08-30T10:00:00",
        "app": "Slack",
        "tone": "Casual",
        "raw": "um hello",
        "polished": "Hello.",
    })
    resp = client.get("/api/history")
    assert len(resp.json()) == 1
    assert resp.json()[0]["app"] == "Slack"


def test_clear_history(client):
    from daemon import server
    server.add_history_entry({"timestamp": "t", "app": "A", "tone": "Casual",
                               "raw": "r", "polished": "p"})
    client.post("/api/history/clear")
    assert client.get("/api/history").json() == []


def test_get_tones_returns_all_builtins(client):
    resp = client.get("/api/tones")
    data = resp.json()
    assert "Formal" in data
    assert "Casual" in data
    assert "Terse" in data
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python -m pytest tests/test_server.py -v
```

Expected: `ModuleNotFoundError` for `daemon.server`.

- [ ] **Step 3: Implement `daemon/server.py`**

```python
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
    if dist_dir:
        app.mount("/", StaticFiles(directory=dist_dir, html=True), name="static")
    t = threading.Thread(
        target=uvicorn.run,
        args=(app,),
        kwargs={"host": "127.0.0.1", "port": port, "log_level": "error"},
        daemon=True,
    )
    t.start()
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_server.py -v
```

Expected: 7 tests PASSED.

- [ ] **Step 5: Run the full test suite to confirm nothing regressed**

```bash
python -m pytest tests/ -v
```

Expected: All tests PASSED.

- [ ] **Step 6: Commit**

```bash
git add daemon/server.py tests/test_server.py
git commit -m "feat: FastAPI server with settings, history, and tone endpoints"
```

---

## Task 10: Main Daemon Entry Point

**Files:**
- Create: `daemon/main.py`

No unit tests for `main.py` — it wires PyObjC NSApplication, which requires a live macOS run loop. Manual test checklist at the end of this task.

- [ ] **Step 1: Implement `daemon/main.py`**

```python
import asyncio
import threading
from datetime import datetime, timezone

from AppKit import NSApplication, NSObject, NSStatusBar, NSVariableStatusItemLength
from Cocoa import NSRunningApplication, NSApplicationActivateIgnoringOtherApps
import Quartz

from daemon import (
    hotkey as hotkey_mod,
    audio as audio_mod,
    asr as asr_mod,
    intent,
    injector,
    context,
    settings,
    server,
)


class _Delegate(NSObject):
    def applicationDidFinishLaunching_(self, _notification):
        s = settings.load()

        # Load ASR model once
        self._asr = asr_mod.ASR(s.get("whisper_model", "small.en"))
        self._audio = audio_mod.AudioCapture()
        self._state = "IDLE"
        self._ctx: dict = {}

        # Async event loop for LLM calls (runs in background thread)
        self._loop = asyncio.new_event_loop()
        threading.Thread(target=self._loop.run_forever, daemon=True).start()

        # Menubar icon
        self._status_item = (
            NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
        )
        self._status_item.button().setTitle_("🎤")
        self._status_item.button().setAction_("openDashboard:")
        self._status_item.button().setTarget_(self)

        # FastAPI server
        server.start(port=8421)

        # Hotkey tap (must happen after run loop is active)
        self._tap = hotkey_mod.create_event_tap(
            on_down=self._on_record_start,
            on_up=self._on_record_stop,
        )

    def _on_record_start(self):
        if self._state != "IDLE":
            return
        ctx = context.get_context()
        if not ctx["safe"]:
            self._warn(ctx["reason"])
            return
        self._ctx = ctx
        self._state = "RECORDING"
        self._status_item.button().setTitle_("🔴")
        self._audio.start()

    def _on_record_stop(self):
        if self._state != "RECORDING":
            return
        self._state = "TRANSCRIBING"
        audio_data = self._audio.stop()
        asyncio.run_coroutine_threadsafe(
            self._process(audio_data, dict(self._ctx)),
            self._loop,
        )

    async def _process(self, audio_data, ctx: dict):
        try:
            raw = self._asr.transcribe(audio_data)
            if not raw:
                return
            self._state = "INJECTING"
            polished = intent.rewrite(raw, ctx["app"])
            injector.inject(polished)
            server.add_history_entry({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "app": ctx["app"],
                "tone": settings.get_tone(ctx["app"])[0],
                "raw": raw,
                "polished": polished,
            })
        except Exception as exc:
            print(f"[IntenType] pipeline error: {exc}")
        finally:
            self._state = "IDLE"
            self._status_item.button().setTitle_("🎤")

    def openDashboard_(self, _sender):
        import subprocess
        subprocess.Popen(["open", "http://localhost:8421"])

    def _warn(self, reason: str):
        label = {
            "secure_input": "Secure input active — injection blocked",
            "password_field": "Password field — injection skipped",
        }.get(reason, "Injection blocked")
        self._status_item.button().setTitle_(f"⚠️ {label[:20]}")
        # Reset after 2s
        import threading
        threading.Timer(2.0, lambda: self._status_item.button().setTitle_("🎤")).start()


def run():
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(1)  # NSApplicationActivationPolicyAccessory — no Dock icon
    delegate = _Delegate.alloc().init()
    app.setDelegate_(delegate)
    app.run()


if __name__ == "__main__":
    run()
```

- [ ] **Step 2: Smoke-test the daemon manually**

```bash
python -m daemon.main
```

Expected:
- A 🎤 icon appears in the macOS menu bar.
- No crash on launch.
- Console shows uvicorn starting on port 8421.
- `curl http://localhost:8421/api/settings` returns a JSON object.

- [ ] **Step 3: Test hold-to-talk manually**

1. Click into any text field (Notes, TextEdit).
2. Hold Right Option. The icon should turn 🔴.
3. Speak a sentence with filler words: "um yeah I wanted to test this thing".
4. Release Right Option.
5. Icon returns to 🎤; polished text appears in the text field.

- [ ] **Step 4: Commit**

```bash
git add daemon/main.py
git commit -m "feat: main daemon entry point with NSApplication and state machine"
```

---

## Task 11: React Dashboard Scaffold

**Files:**
- Create: `dashboard/package.json`
- Create: `dashboard/vite.config.ts`
- Create: `dashboard/tailwind.config.js`
- Create: `dashboard/tsconfig.json`
- Create: `dashboard/index.html`
- Create: `dashboard/src/main.tsx`
- Create: `dashboard/src/App.tsx`
- Create: `dashboard/src/stores/settingsStore.ts`
- Create: `dashboard/src/stores/historyStore.ts`
- Create: `dashboard/src/stores/toneStore.ts`

- [ ] **Step 1: Initialise Vite + React project**

```bash
cd /Users/shankar/IntenType/dashboard
npm create vite@latest . -- --template react-ts
npm install
npm install zustand
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

- [ ] **Step 2: Configure TailwindCSS — update `dashboard/tailwind.config.js`**

```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: { extend: {} },
  plugins: [],
}
```

- [ ] **Step 3: Add Tailwind directives to `dashboard/src/index.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 4: Update `dashboard/vite.config.ts` to proxy API calls to port 8421**

```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8421',
    },
  },
})
```

- [ ] **Step 5: Write `dashboard/src/stores/settingsStore.ts`**

```ts
import { create } from 'zustand'

interface ToneMapping {
  tone: 'Formal' | 'Casual' | 'Terse' | 'Custom'
  custom_instruction: string
}

interface Settings {
  openai_api_key: string
  whisper_model: string
  tone_mappings: Record<string, ToneMapping>
  history_enabled: boolean
}

interface SettingsStore {
  settings: Settings | null
  fetch: () => Promise<void>
  update: (patch: Partial<Settings>) => Promise<void>
}

export const useSettingsStore = create<SettingsStore>((set, get) => ({
  settings: null,
  fetch: async () => {
    const res = await fetch('/api/settings')
    set({ settings: await res.json() })
  },
  update: async (patch) => {
    await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch),
    })
    await get().fetch()
  },
}))
```

- [ ] **Step 6: Write `dashboard/src/stores/historyStore.ts`**

```ts
import { create } from 'zustand'

export interface HistoryEntry {
  timestamp: string
  app: string
  tone: string
  raw: string
  polished: string
}

interface HistoryStore {
  entries: HistoryEntry[]
  fetch: () => Promise<void>
  clear: () => Promise<void>
}

export const useHistoryStore = create<HistoryStore>((set) => ({
  entries: [],
  fetch: async () => {
    const res = await fetch('/api/history')
    set({ entries: await res.json() })
  },
  clear: async () => {
    await fetch('/api/history/clear', { method: 'POST' })
    set({ entries: [] })
  },
}))
```

- [ ] **Step 7: Write `dashboard/src/stores/toneStore.ts`**

```ts
import { create } from 'zustand'

interface ToneStore {
  tones: Record<string, string>
  fetch: () => Promise<void>
}

export const useToneStore = create<ToneStore>((set) => ({
  tones: {},
  fetch: async () => {
    const res = await fetch('/api/tones')
    set({ tones: await res.json() })
  },
}))
```

- [ ] **Step 8: Write minimal `dashboard/src/App.tsx`**

```tsx
import { useState, useEffect } from 'react'
import ToneMapper from './views/ToneMapper'
import History from './views/History'
import SettingsView from './views/SettingsView'

type Tab = 'tones' | 'history' | 'settings'

export default function App() {
  const [tab, setTab] = useState<Tab>('tones')

  const tabs: { id: Tab; label: string }[] = [
    { id: 'tones', label: 'Tone Mapper' },
    { id: 'history', label: 'History' },
    { id: 'settings', label: 'Settings' },
  ]

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex flex-col">
      <header className="bg-gray-900 border-b border-gray-800 px-6 py-4 flex items-center gap-3">
        <span className="text-xl">🎤</span>
        <h1 className="text-lg font-semibold">IntenType</h1>
      </header>

      <nav className="bg-gray-900 border-b border-gray-800 px-6 flex gap-1">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
              tab === t.id
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <main className="flex-1 p-6">
        {tab === 'tones' && <ToneMapper />}
        {tab === 'history' && <History />}
        {tab === 'settings' && <SettingsView />}
      </main>
    </div>
  )
}
```

- [ ] **Step 9: Create placeholder view files so the app compiles**

```tsx
// dashboard/src/views/ToneMapper.tsx
export default function ToneMapper() { return <div>Tone Mapper</div> }
```

```tsx
// dashboard/src/views/History.tsx
export default function History() { return <div>History</div> }
```

```tsx
// dashboard/src/views/SettingsView.tsx
export default function SettingsView() { return <div>Settings</div> }
```

- [ ] **Step 10: Verify dev server starts**

```bash
cd /Users/shankar/IntenType/dashboard
npm run dev
```

Expected: Vite dev server starts on http://localhost:5173. Opening it shows "IntenType" header with three tabs.

- [ ] **Step 11: Commit**

```bash
cd /Users/shankar/IntenType
git add dashboard/
git commit -m "feat: React dashboard scaffold with Vite, Tailwind, Zustand stores"
```

---

## Task 12: Tone Mapper View

**Files:**
- Modify: `dashboard/src/views/ToneMapper.tsx`

- [ ] **Step 1: Implement `ToneMapper.tsx`**

```tsx
import { useEffect } from 'react'
import { useSettingsStore } from '../stores/settingsStore'
import { useHistoryStore } from '../stores/historyStore'
import { useToneStore } from '../stores/toneStore'

const TONE_OPTIONS = ['Formal', 'Casual', 'Terse', 'Custom'] as const
type ToneName = typeof TONE_OPTIONS[number]

export default function ToneMapper() {
  const { settings, fetch: fetchSettings, update } = useSettingsStore()
  const { entries, fetch: fetchHistory } = useHistoryStore()
  const { tones, fetch: fetchTones } = useToneStore()

  useEffect(() => {
    fetchSettings()
    fetchHistory()
    fetchTones()
  }, [])

  const seenApps = Array.from(
    new Set([
      ...Object.keys(settings?.tone_mappings ?? {}),
      ...entries.map((e) => e.app),
    ])
  ).sort()

  const getMapping = (app: string) =>
    settings?.tone_mappings?.[app] ?? { tone: 'Casual', custom_instruction: '' }

  const setTone = async (app: string, tone: ToneName) => {
    const current = getMapping(app)
    await update({
      tone_mappings: {
        ...settings?.tone_mappings,
        [app]: { ...current, tone },
      },
    })
  }

  const setCustomInstruction = async (app: string, custom_instruction: string) => {
    const current = getMapping(app)
    await update({
      tone_mappings: {
        ...settings?.tone_mappings,
        [app]: { ...current, custom_instruction },
      },
    })
  }

  if (!settings) return <div className="text-gray-400">Loading...</div>

  return (
    <div className="max-w-2xl">
      <h2 className="text-lg font-semibold mb-1">Tone Mapper</h2>
      <p className="text-sm text-gray-400 mb-6">
        Set the writing tone IntenType uses per app. Apps appear here once they've been used.
      </p>

      {seenApps.length === 0 && (
        <p className="text-gray-500 text-sm">
          No apps detected yet. Use the hotkey in any app to see it here.
        </p>
      )}

      <div className="space-y-3">
        {seenApps.map((app) => {
          const mapping = getMapping(app)
          return (
            <div key={app} className="bg-gray-900 rounded-lg p-4 border border-gray-800">
              <div className="flex items-center justify-between gap-4">
                <span className="font-medium text-gray-100 w-40 truncate">{app}</span>
                <select
                  value={mapping.tone}
                  onChange={(e) => setTone(app, e.target.value as ToneName)}
                  className="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-gray-100 focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  {TONE_OPTIONS.map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>

              {mapping.tone === 'Custom' && (
                <input
                  type="text"
                  placeholder="Custom tone instruction…"
                  value={mapping.custom_instruction}
                  onChange={(e) => setCustomInstruction(app, e.target.value)}
                  className="mt-3 w-full bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              )}

              {mapping.tone !== 'Custom' && tones[mapping.tone] && (
                <p className="mt-2 text-xs text-gray-500">{tones[mapping.tone]}</p>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Manually verify in the dev server**

With the daemon running (`python -m daemon.main`) and dev server running (`npm run dev`):
1. Open http://localhost:5173
2. Use the hotkey in Slack and Mail — both should appear in the Tone Mapper
3. Change Mail to Formal — verify the change persists after refresh
4. Set Cursor to Custom — verify the instruction input appears

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/views/ToneMapper.tsx
git commit -m "feat: Tone Mapper view with per-app tone selection"
```

---

## Task 13: History View

**Files:**
- Modify: `dashboard/src/views/History.tsx`

- [ ] **Step 1: Implement `History.tsx`**

```tsx
import { useEffect } from 'react'
import { useHistoryStore } from '../stores/historyStore'

export default function History() {
  const { entries, fetch, clear } = useHistoryStore()

  useEffect(() => { fetch() }, [])

  return (
    <div className="max-w-3xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold">History</h2>
          <p className="text-sm text-gray-400">Last 50 transcriptions</p>
        </div>
        {entries.length > 0 && (
          <button
            onClick={clear}
            className="text-sm text-red-400 hover:text-red-300 transition-colors"
          >
            Clear history
          </button>
        )}
      </div>

      {entries.length === 0 && (
        <p className="text-gray-500 text-sm">No transcriptions yet.</p>
      )}

      <div className="space-y-3">
        {[...entries].reverse().map((entry, i) => (
          <div key={i} className="bg-gray-900 rounded-lg p-4 border border-gray-800">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-xs text-gray-500">
                {new Date(entry.timestamp).toLocaleString()}
              </span>
              <span className="text-xs bg-gray-800 text-gray-300 px-2 py-0.5 rounded">
                {entry.app}
              </span>
              <span className="text-xs bg-blue-900 text-blue-300 px-2 py-0.5 rounded">
                {entry.tone}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-xs text-gray-500 mb-1 uppercase tracking-wide">Raw</p>
                <p className="text-gray-400 italic">{entry.raw}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1 uppercase tracking-wide">Polished</p>
                <p className="text-gray-100">{entry.polished}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Manually verify**

1. Use the hotkey twice in different apps.
2. Open History tab — both entries appear, newest first.
3. Click "Clear history" — list empties.

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/views/History.tsx
git commit -m "feat: History view showing raw and polished transcriptions"
```

---

## Task 14: Settings View

**Files:**
- Modify: `dashboard/src/views/SettingsView.tsx`

- [ ] **Step 1: Implement `SettingsView.tsx`**

```tsx
import { useEffect, useState } from 'react'
import { useSettingsStore } from '../stores/settingsStore'

export default function SettingsView() {
  const { settings, fetch, update } = useSettingsStore()
  const [apiKey, setApiKey] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => { fetch() }, [])

  const handleSaveKey = async () => {
    if (!apiKey) return
    await update({ openai_api_key: apiKey })
    setApiKey('')
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const handleModelChange = async (model: string) => {
    await update({ whisper_model: model })
  }

  if (!settings) return <div className="text-gray-400">Loading...</div>

  return (
    <div className="max-w-lg space-y-8">
      <h2 className="text-lg font-semibold">Settings</h2>

      {/* OpenAI API Key */}
      <div className="bg-gray-900 rounded-lg p-5 border border-gray-800">
        <h3 className="font-medium mb-1">OpenAI API Key</h3>
        <p className="text-xs text-gray-400 mb-4">
          Used for GPT-4o-mini intent rewriting. Stored locally — never sent anywhere else.
          {settings.openai_api_key ? (
            <span className="ml-2 text-green-400">✓ Key saved</span>
          ) : (
            <span className="ml-2 text-yellow-400">⚠ No key set</span>
          )}
        </p>
        <div className="flex gap-2">
          <input
            type="password"
            placeholder="sk-proj-…"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            className="flex-1 bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <button
            onClick={handleSaveKey}
            disabled={!apiKey}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 rounded text-sm font-medium transition-colors"
          >
            {saved ? 'Saved ✓' : 'Save'}
          </button>
        </div>
      </div>

      {/* Whisper Model */}
      <div className="bg-gray-900 rounded-lg p-5 border border-gray-800">
        <h3 className="font-medium mb-1">Whisper Model</h3>
        <p className="text-xs text-gray-400 mb-4">
          Larger model = better accuracy, higher RAM usage. Restart the daemon after changing.
        </p>
        <div className="flex gap-3">
          {['small.en', 'medium.en'].map((model) => (
            <button
              key={model}
              onClick={() => handleModelChange(model)}
              className={`px-4 py-2 rounded text-sm font-medium border transition-colors ${
                settings.whisper_model === model
                  ? 'border-blue-500 bg-blue-900 text-blue-200'
                  : 'border-gray-700 bg-gray-800 text-gray-300 hover:border-gray-500'
              }`}
            >
              {model}
              {model === 'small.en' && <span className="text-xs text-gray-400 ml-1">(~240MB)</span>}
              {model === 'medium.en' && <span className="text-xs text-gray-400 ml-1">(~1.5GB)</span>}
            </button>
          ))}
        </div>
      </div>

      {/* Hotkey (read-only) */}
      <div className="bg-gray-900 rounded-lg p-5 border border-gray-800">
        <h3 className="font-medium mb-1">Hotkey</h3>
        <p className="text-xs text-gray-400 mb-3">Hold to record, release to transcribe.</p>
        <kbd className="px-3 py-1.5 bg-gray-800 border border-gray-600 rounded text-sm font-mono text-gray-200">
          Right Option ⌥
        </kbd>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Manually verify**

1. Open Settings tab.
2. Enter a new API key and click Save — key indicator shows "✓ Key saved".
3. Switch Whisper model to medium.en — button highlights correctly.
4. Hotkey display shows Right Option (non-interactive).

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/views/SettingsView.tsx
git commit -m "feat: Settings view with API key, model selector, and hotkey display"
```

---

## Task 15: py2app Packaging

**Files:**
- Create: `setup.py`
- Modify: `daemon/server.py` (mount `dist/` path relative to `.app` bundle)

- [ ] **Step 1: Write `setup.py`**

```python
from setuptools import setup
import os

APP = ["daemon/main.py"]
DIST_DIR = os.path.join("dashboard", "dist")
DATA_FILES = [("dist", [os.path.join(DIST_DIR, f) for f in os.listdir(DIST_DIR)])]

OPTIONS = {
    "argv_emulation": False,
    "plist": {
        "LSUIElement": True,
        "CFBundleName": "IntenType",
        "CFBundleDisplayName": "IntenType",
        "CFBundleIdentifier": "com.intentype.app",
        "NSMicrophoneUsageDescription": "Required to record audio for voice typing.",
        "NSAccessibilityUsageDescription": "Required to read cursor focus and inject text.",
    },
    "packages": [
        "fastapi", "uvicorn", "starlette", "pydantic",
        "sounddevice", "numpy", "faster_whisper",
        "openai", "httpx", "anyio",
        "objc", "Cocoa", "Quartz", "AppKit", "CoreFoundation",
    ],
    "includes": ["daemon"],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
```

- [ ] **Step 2: Update `daemon/server.py` `start()` to resolve `dist/` from the bundle**

Replace the `start` function with:

```python
def start(port: int = 8421, dist_dir: str | None = None) -> None:
    if dist_dir is None:
        import sys
        # When running inside .app, resources are at ../Resources relative to the binary
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
```

Add `import os` to the top of `daemon/server.py`.

- [ ] **Step 3: Build the React dashboard**

```bash
cd /Users/shankar/IntenType/dashboard
npm run build
```

Expected: `dashboard/dist/` directory created with `index.html` and `assets/`.

- [ ] **Step 4: Install py2app and build the `.app`**

```bash
cd /Users/shankar/IntenType
pip install py2app
python setup.py py2app
```

Expected: `dist/IntenType.app` is created (takes 2–5 minutes).

- [ ] **Step 5: Smoke-test the `.app`**

```bash
open dist/IntenType.app
```

Expected:
- macOS may prompt for Microphone and Accessibility permissions — grant both.
- 🎤 icon appears in menu bar.
- Clicking it opens `http://localhost:8421` in the browser with the full dashboard.
- Hold Right Option, speak, release — text injects into the active app.

- [ ] **Step 6: Final commit**

```bash
git add setup.py daemon/server.py
git commit -m "feat: py2app packaging config and bundle-relative dist path"
```

---

## Self-Review

**Spec coverage check:**

| Spec Section | Task |
|---|---|
| Core Daemon — CGEventTap, state machine, NSStatusItem | Task 8 (hotkey), Task 10 (main) |
| Context Harvest — NSWorkspace, AXUIElement safety | Task 3 |
| Audio Capture — sounddevice 16kHz mono | Task 4 |
| ASR — faster-whisper small.en/medium.en | Task 5 |
| Intent Layer — GPT-4o-mini, tone system | Task 6 |
| Text Injector — clipboard swap + Cmd+V | Task 7 |
| Settings — settings.json, BUILTIN_TONES | Task 2 |
| FastAPI Server — all 6 endpoints | Task 9 |
| React Dashboard — ToneMapper, History, Settings | Tasks 11–14 |
| py2app packaging | Task 15 |
| Security: password field, secure keyboard input | Task 3 |
| Error handling: no API key fallback | Task 6 |
| Error handling: accessibility/microphone permissions | Task 10 |
| Milestones 1–4 | Tasks 1–10 (wk1–3), Tasks 11–15 (wk4) |

All spec requirements are covered. No gaps found.
