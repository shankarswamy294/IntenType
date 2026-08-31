# IntenType — Design Spec

**Date:** 2026-08-30  
**Status:** Approved

---

## Overview

IntenType is an always-on, system-wide voice-to-intent typing utility for macOS. The user holds Right Option to record speech; on release, audio is transcribed locally, rewritten by an LLM with per-app tone awareness, and injected into the active text field via clipboard paste — working in any app without plugins.

---

## Architecture

Three-tier local system:

```
Right Option held
      │
      ▼
CGEventTap (PyObjC/Quartz)
      │
      ├─► Context Harvest (NSWorkspace + AXUIElement)
      │
      ▼
sounddevice (16kHz mono PCM, buffered in memory)
      │
      ▼
faster-whisper (local ASR, small.en default)
      │
      ▼
GPT-4o-mini (intent rewrite, tone-aware)
      │
      ▼
NSPasteboard swap + CGEventPost Cmd+V
      │
      ▼
Text appears in active app
```

**Parallel:** FastAPI server (port 8421, embedded in daemon) + React dashboard — tone mappings, history, settings.

---

## Component Design

### 1. Core Daemon (`daemon/main.py`)

Runs as `LSUIElement = True` background agent — no Dock icon, no menu bar app window. Entry point starts:
- `CGEventTap` listener for Right Option (key code `0x3D`)
- `NSStatusItem` menubar icon (microphone; turns red while recording)
- FastAPI/uvicorn server thread on port 8421
- `NSApplication.run()` event loop

**State machine:** `IDLE → RECORDING → TRANSCRIBING → INJECTING → IDLE`

Transitions are synchronous except TRANSCRIBING (runs in `asyncio` event loop). Only one recording session active at a time; overlapping key presses are ignored.

### 2. Hotkey Listener (`daemon/hotkey.py`)

`CGEventTap` at `kCGHIDEventTap` level, listening for `kCGEventKeyDown` / `kCGEventKeyUp` on keycode `0x3D` (Right Option).

- Key down → call `on_record_start()`
- Key up → call `on_record_stop()`

The tap runs on the main `CFRunLoop` thread. Audio capture and ASR are dispatched to a background thread to avoid blocking the event loop.

### 3. Context Harvester (`daemon/context.py`)

Called on key down, before audio capture starts. Returns:

```python
{
    "app": str,        # NSWorkspace frontmostApplication localizedName
    "tone": str,       # looked up from settings, default "Casual"
    "tone_instructions": str
}
```

Also checks:
- `AXIsSecure` on focused element → if True, abort and show menubar warning "Password field — injection skipped"
- `CGSIsSecureEventInputEnabled()` → if True, abort and show "Secure input active — injection blocked"

### 4. Audio Capture (`daemon/audio.py`)

`sounddevice.RawInputStream` at 16kHz, mono, `int16`. Frames are appended to an in-memory `bytearray` on each callback. Capture starts on key down, stops on key up. The full buffer is returned as a `numpy` array for ASR.

No streaming to ASR mid-recording — hold-to-talk gives us the complete utterance on key-up, eliminating partial-transcript complexity.

### 5. ASR (`daemon/asr.py`)

`faster-whisper` with `WhisperModel` loaded once at daemon startup (not per-request). Default: `small.en`. User can switch to `medium.en` in settings (requires ~1.5GB RAM).

```python
segments, _ = model.transcribe(audio_buffer, language="en", beam_size=5)
raw_transcript = " ".join(s.text for s in segments).strip()
```

Estimated latency on Apple Silicon M-series: 200–400ms for a 10-second utterance with `small.en`.

### 6. Intent Layer (`daemon/intent.py`)

Single `openai.chat.completions.create` call per utterance using `gpt-4o-mini`. API key read from `settings.json` at call time (not cached in memory).

System prompt template:
```
You are a voice-to-text assistant. Clean up the transcript — remove filler words ("um", "uh", "like", "you know"), fix grammar and punctuation, and output natural written text. Do not add content that wasn't said. Output only the cleaned text with no preamble or explanation.
Tone: {tone_name}. {tone_instructions}
```

**Built-in tones:**

| Name | Instructions |
|------|-------------|
| Formal | Use professional language, complete sentences, no contractions. |
| Casual | Natural, conversational. Contractions fine. |
| Terse | Minimal words. Drop pleasantries. Bullet points if listing. |
| Custom | User-defined string stored per-app in settings.json. |

Default tone for unmapped apps: Casual.

Estimated latency: 300–600ms.

### 7. Text Injector (`daemon/injector.py`)

```
1. Backup NSPasteboard (all types)
2. Write polished text as NSStringPboardType
3. CGEventPost Cmd+V (key down + key up, kCGHIDEventTap)
4. Sleep 100ms
5. Restore original clipboard
```

If backup or restore fails (e.g. clipboard held by another process), log the error and proceed — text injection is the priority; clipboard restoration is best-effort.

### 8. Settings (`daemon/settings.py`)

Stored at `~/Library/Application Support/IntenType/settings.json`:

```json
{
  "openai_api_key": "sk-...",
  "whisper_model": "small.en",
  "tone_mappings": {
    "Mail": { "tone": "Formal", "custom_instruction": "" },
    "Slack": { "tone": "Casual", "custom_instruction": "" },
    "Terminal": { "tone": "Terse", "custom_instruction": "" }
  },
  "history_enabled": true
}
```

Read on every LLM call (not cached) so dashboard changes take effect immediately without restart.

### 9. FastAPI Server (`daemon/server.py`)

Runs in a daemon thread via `uvicorn`. Port 8421.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/settings` | GET | Return full settings (API key masked) |
| `/api/settings` | POST | Update settings |
| `/api/tones` | GET | List built-in tone names + instructions |
| `/api/history` | GET | Last 50 transcriptions |
| `/api/history/clear` | POST | Clear history |
| `/` | GET | Serve React `dist/index.html` |

History entries:
```json
{
  "timestamp": "2026-08-30T12:34:56",
  "app": "Slack",
  "tone": "Casual",
  "raw": "um yeah I wanted to ask about the meeting",
  "polished": "I wanted to ask about the meeting."
}
```

History stored in memory (last 50 entries). Not persisted to disk.

### 10. React Dashboard (`dashboard/`)

Vite + TypeScript + TailwindCSS + Zustand. Three views accessible via tab navigation:

**Tone Mapper**
- Table of apps seen so far (populated from history)
- Tone dropdown per row: Formal / Casual / Terse / Custom
- Custom tone shows a text input for the instruction string
- Save button POSTs to `/api/settings`

**History**
- Scrollable list: timestamp, app name, tone badge, raw → polished
- Clear history button

**Settings**
- OpenAI API key (password input, masked)
- Whisper model selector: `small.en` / `medium.en`
- Hotkey display: "Right Option" (read-only in v1)

Dashboard opens when user clicks the menubar icon. Closes on window blur.

---

## Security Considerations

- **Password fields:** Detected via `AXIsSecure`; injection skipped entirely.
- **Secure keyboard input:** Detected via `CGSIsSecureEventInputEnabled()`; injection blocked with menubar warning.
- **API key storage:** Stored in `settings.json` in `~/Library/Application Support/IntenType/` (user-only permissions). Never logged or included in history. Masked in dashboard and API responses.
- **Audio:** Never leaves the device. Only the plain-text transcript is sent to OpenAI.
- **`.env`:** Used during development only. Production reads from `settings.json`.

---

## Error Handling

| Failure | Behavior |
|---------|----------|
| No microphone permission | On launch, show system permission dialog. If denied, menubar icon shows ⚠️. |
| No accessibility permission | On launch, open System Settings → Accessibility. Menubar shows ⚠️. |
| faster-whisper fails | Log error, show brief menubar notification "Transcription failed". No injection. |
| OpenAI API error / no key | If key missing, open dashboard Settings. If API error, inject raw transcript as fallback. |
| Clipboard restore failure | Log, continue. Best-effort. |
| Secure input active | Menubar notification. No injection. |

---

## Project Structure

```
IntenType/
├── daemon/
│   ├── main.py
│   ├── hotkey.py
│   ├── audio.py
│   ├── asr.py
│   ├── intent.py
│   ├── injector.py
│   ├── context.py
│   ├── settings.py
│   └── server.py
├── dashboard/
│   ├── src/
│   │   ├── stores/
│   │   │   ├── settingsStore.ts
│   │   │   ├── historyStore.ts
│   │   │   └── toneStore.ts
│   │   ├── views/
│   │   │   ├── ToneMapper.tsx
│   │   │   ├── History.tsx
│   │   │   └── Settings.tsx
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
├── setup.py
├── requirements.txt
├── .env               # dev only, gitignored
├── .gitignore
└── docs/
    └── superpowers/
        └── specs/
            └── 2026-08-30-intentype-design.md
```

---

## Build & Packaging

**Development:**
```bash
# Terminal 1 — daemon
pip install -r requirements.txt
python daemon/main.py

# Terminal 2 — dashboard (dev server)
cd dashboard && npm install && npm run dev
```

**Production build:**
```bash
cd dashboard && npm run build        # outputs dist/
cd .. && python setup.py py2app      # bundles into IntenType.app
```

**py2app `setup.py` key settings:**
```python
OPTIONS = {
    'plist': {
        'LSUIElement': True,
        'NSMicrophoneUsageDescription': 'Required to record audio for voice typing.',
        'NSAccessibilityUsageDescription': 'Required to read cursor focus and inject text.',
    },
    'packages': ['fastapi', 'uvicorn', 'websockets', 'sounddevice', 'objc', 'Quartz', 'faster_whisper', 'openai'],
}
```

---

## Milestones

| Week | Deliverable |
|------|-------------|
| 1 | Daemon skeleton: CGEventTap, context harvest, clipboard injection, accessibility/microphone permissions |
| 2 | Audio capture + faster-whisper ASR working end-to-end (raw transcript injected) |
| 3 | GPT-4o-mini intent layer + tone system + settings.json |
| 4 | React dashboard (Tone Mapper, History, Settings) + FastAPI server + py2app bundle |
