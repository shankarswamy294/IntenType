import asyncio
import subprocess
import threading
from datetime import datetime, timezone

import objc
from AppKit import NSApplication, NSObject, NSStatusBar, NSVariableStatusItemLength

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
        self._setup()

    @objc.python_method
    def _setup(self):
        s = settings.load()

        # Load ASR model once
        self._asr = asr_mod.ASR(s.get("whisper_model", "small.en"))
        self._audio = audio_mod.AudioCapture()
        self._state = "IDLE"
        self._state_lock = threading.Lock()
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
    @objc.python_method
    def _on_record_start(self):
        with self._state_lock:
            if self._state != "IDLE":
                return
            self._state = "RECORDING"
        ctx = context.get_context()
        if not ctx["safe"]:
            self._warn(ctx["reason"])
            with self._state_lock:
                self._state = "IDLE"
            return
        self._ctx = ctx
        self._status_item.button().setTitle_("🔴")
        self._audio.start()

    @objc.python_method
    def _on_record_stop(self):
        with self._state_lock:
            if self._state != "RECORDING":
                return
            self._state = "TRANSCRIBING"
        try:
            audio_data = self._audio.stop()
        except Exception as exc:
            print(f"[IntenType] audio capture error: {exc}")
            with self._state_lock:
                self._state = "IDLE"
            self._status_item.button().setTitle_("🎤")
            return
        asyncio.run_coroutine_threadsafe(
            self._process(audio_data, dict(self._ctx)),
            self._loop,
        )

    @objc.python_method
    async def _process(self, audio_data, ctx: dict):
        try:
            raw = self._asr.transcribe(audio_data)
            if not raw:
                return
            with self._state_lock:
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
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                "resetToIdle:", None, False
            )

    def resetToIdle_(self, _):
        with self._state_lock:
            self._state = "IDLE"
        self._status_item.button().setTitle_("🎤")

    def openDashboard_(self, _sender):
        subprocess.Popen(["open", "http://localhost:8421"])

    @objc.python_method
    def _warn(self, reason: str):
        label = {
            "secure_input": "Secure input active — injection blocked",
            "password_field": "Password field — injection skipped",
        }.get(reason, "Injection blocked")
        self._status_item.button().setTitle_(f"⚠️ {label[:35]}")
        # Reset after 2s
        threading.Timer(2.0, lambda: self._status_item.button().setTitle_("🎤")).start()


def run():
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(1)  # NSApplicationActivationPolicyAccessory — no Dock icon
    delegate = _Delegate.alloc().init()
    app.setDelegate_(delegate)
    app.run()


if __name__ == "__main__":
    run()
