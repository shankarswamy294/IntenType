<div align="center">
  <img src="assets/menubar.png" width="64" alt="IntenType logo"/>

  # IntenType

  **Voice typing with AI polish — for every Mac app.**

  Hold `⌥ Right Option` → speak → release → polished text appears wherever you're typing.

  [![macOS](https://img.shields.io/badge/macOS-14%2B-black?logo=apple)](https://github.com/shankarswamy294/IntenType/releases)
  [![Python](https://img.shields.io/badge/Python-3.14-blue?logo=python)](https://python.org)
  [![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
  [![Download](https://img.shields.io/github/v/release/shankarswamy294/IntenType?label=download&color=red)](https://github.com/shankarswamy294/IntenType/releases/latest)

  [**🌐 Website**](https://shankarswamy294.github.io/IntenType/)  ·  [**⬇ Download for Mac (v0.1.0)**](https://github.com/shankarswamy294/IntenType/releases/download/v0.1.0/IntenType-0.1.0.dmg)

</div>

---

## What it does

IntenType sits silently in your menubar. When you need to type:

1. **Hold** `⌥ Right Option` — the waveform overlay appears
2. **Speak** naturally — Whisper transcribes locally on your device
3. **Release** — GPT rewrites it to clean, context-aware text
4. **Done** — text is injected wherever your cursor is

Works in **Notes, Slack, Teams, Gmail, VS Code, Terminal, browsers** — anywhere you can type.

---

## Demo

| Step | What happens |
|------|-------------|
| Hold `⌥ Right Option` | Waveform overlay appears, recording starts |
| Speak | "uh hey can you send me that report from last week" |
| Release | "Could you please send me last week's report?" |
| Text injected | Cursor position receives the polished text |

---

## Features

- **One-key activation** — `⌥ Right Option`, nothing to click
- **Local transcription** — Whisper runs on-device, audio never leaves your Mac
- **AI polish** — GPT rewrites for clarity, tone, and grammar
- **App-aware** — detects the focused app and adapts tone (casual in Messages, formal in email)
- **Password-safe** — automatically skips secure/password fields
- **Animated menubar icon** — waveform pulses while recording
- **Lightweight** — runs as a background daemon, ~0% CPU when idle

---

## Installation

### Option A — DMG (recommended)

1. [Download `IntenType-*.dmg`](https://github.com/shankarswamy294/IntenType/releases/latest)
2. Open the DMG
3. Double-click **`Install.command`** inside the DMG
4. Terminal opens and asks for your Mac password once — this installs the app and removes the Gatekeeper warning automatically
5. IntenType launches — the waveform icon appears in your menubar
6. Enter your [OpenAI API key](https://platform.openai.com/api-keys) when prompted
7. Grant the 3 permissions when the setup wizard appears

### Option B — Run from source

```bash
git clone https://github.com/shankarswamy294/IntenType.git
cd IntenType
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m daemon.main
```

---

## Permissions

IntenType needs three macOS permissions — the setup wizard walks you through each one:

| Permission | Why |
|-----------|-----|
| **Input Monitoring** | Detects the `⌥ Right Option` key |
| **Microphone** | Records your voice while the key is held |
| **Accessibility** | Reads the focused app to skip password fields |

---

## Requirements

- macOS 14 Sonoma or later (Apple Silicon or Intel)
- [OpenAI API key](https://platform.openai.com/api-keys) (pay-as-you-go, ~$0.01 per use)

---

## Build from source

```bash
# Generate app icon and menubar images
python scripts/make_icon.py

# Build IntenType.app + DMG
bash scripts/build_dmg.sh
# → dist/IntenType.app
# → dist/IntenType-0.1.0.dmg
```

---

## Project structure

```
daemon/
  main.py          # NSApplication delegate, menubar, recording state machine
  hotkey.py        # CGEventTap for Right Option key detection
  audio.py         # Microphone capture via sounddevice
  asr.py           # faster-whisper local transcription
  intent.py        # GPT rewriting via OpenAI API
  injector.py      # CGEvent keyboard injection
  overlay.py       # Waveform recording overlay window
  permissions.py   # TCC permission checks and setup wizard
  context.py       # Focused app detection, secure field check
  settings.py      # Local settings (API key, Whisper model)
  history.py       # Transcription history log
scripts/
  make_icon.py     # Generate .icns and menubar PNG frames
  build_dmg.sh     # py2app build + sign + DMG packaging
docs/
  index.html       # Landing page
assets/
  icon.icns        # App icon
  menubar.png      # Idle menubar icon
  menubar_rec_*.png # Recording animation frames
```

---

## Privacy

- **Audio** is processed locally by Whisper — never sent anywhere
- **Transcribed text** is sent to OpenAI for rewriting (same as using ChatGPT)
- **Your API key** is stored locally in `~/Library/Application Support/IntenType/settings.json`
- No analytics, no telemetry, no accounts

---

## License

MIT — see [LICENSE](LICENSE)

---

<div align="center">
  Made for people who talk faster than they type.
</div>
