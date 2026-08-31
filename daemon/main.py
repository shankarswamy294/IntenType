import asyncio
import subprocess
import threading
from datetime import datetime, timezone

import objc
from AppKit import (
    NSApplication, NSObject, NSStatusBar, NSVariableStatusItemLength,
    NSMenu, NSMenuItem, NSAlert, NSTextField, NSMakeRect,
    NSAlertFirstButtonReturn,
)

from daemon import (
    hotkey as hotkey_mod,
    audio as audio_mod,
    asr as asr_mod,
    intent,
    injector,
    context,
    settings,
    history,
)
from daemon.overlay import RecordingOverlay

_WHISPER_MODELS = ["tiny.en", "base.en", "small.en", "medium.en"]


class _Delegate(NSObject):
    def applicationDidFinishLaunching_(self, _notification):
        self._setup()

    @objc.python_method
    def _setup(self):
        s = settings.load()

        self._asr = asr_mod.ASR(s.get("whisper_model", "small.en"))
        self._audio = audio_mod.AudioCapture()
        self._state = "IDLE"
        self._state_lock = threading.Lock()
        self._ctx: dict = {"app": "Unknown", "safe": True, "reason": None}
        self._overlay = RecordingOverlay()

        self._loop = asyncio.new_event_loop()
        threading.Thread(target=self._loop.run_forever, daemon=True).start()

        self._status_item = (
            NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
        )
        self._status_item.button().setTitle_("🎤")
        self._build_menu()

        self._tap = hotkey_mod.create_event_tap(
            on_down=self._on_record_start,
            on_up=self._on_record_stop,
        )

    @objc.python_method
    def _build_menu(self):
        s = settings.load()
        current_model = s.get("whisper_model", "small.en")

        menu = NSMenu.alloc().init()

        # API key
        key_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Set API Key…", "setApiKey:", ""
        )
        key_item.setTarget_(self)
        menu.addItem_(key_item)

        menu.addItem_(NSMenuItem.separatorItem())

        # Whisper model submenu
        model_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Whisper Model", None, ""
        )
        model_menu = NSMenu.alloc().init()
        for m in _WHISPER_MODELS:
            mi = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                m, "selectModel:", ""
            )
            mi.setTarget_(self)
            mi.setRepresentedObject_(m)
            if m == current_model:
                mi.setState_(1)
            model_menu.addItem_(mi)
        model_item.setSubmenu_(model_menu)
        menu.addItem_(model_item)

        menu.addItem_(NSMenuItem.separatorItem())

        # History
        hist_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Open History", "openHistory:", ""
        )
        hist_item.setTarget_(self)
        menu.addItem_(hist_item)

        menu.addItem_(NSMenuItem.separatorItem())

        # Quit
        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Quit IntenType", "terminate:", "q"
        )
        quit_item.setTarget_(NSApplication.sharedApplication())
        menu.addItem_(quit_item)

        self._status_item.setMenu_(menu)

        # Prompt for API key on first launch
        if not settings.load().get("openai_api_key"):
            from AppKit import NSTimer
            NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                0.5, self, "promptApiKeyIfMissing:", None, False
            )

    def promptApiKeyIfMissing_(self, _):
        if not settings.load().get("openai_api_key"):
            self.setApiKey_(None)

    def setApiKey_(self, _sender):
        alert = NSAlert.alloc().init()
        alert.setMessageText_("Connect to OpenAI")
        alert.setInformativeText_(
            "IntenType uses OpenAI to polish your speech.\n\n"
            "1. Go to platform.openai.com/api-keys\n"
            "2. Click \"Create new secret key\"\n"
            "3. Paste it below\n\n"
            "Your key is stored locally and never shared."
        )
        alert.addButtonWithTitle_("Save")
        alert.addButtonWithTitle_("Cancel")

        field = NSTextField.alloc().initWithFrame_(NSMakeRect(0, 0, 320, 24))
        s = settings.load()
        field.setStringValue_(s.get("openai_api_key", ""))
        field.setPlaceholderString_("sk-proj-...")
        alert.setAccessoryView_(field)
        alert.window().setInitialFirstResponder_(field)

        # Temporarily become a regular app so Cmd+V / typing works in the dialog
        app = NSApplication.sharedApplication()
        app.setActivationPolicy_(0)
        app.activateIgnoringOtherApps_(True)
        result = alert.runModal()
        app.setActivationPolicy_(1)

        if result == NSAlertFirstButtonReturn:
            key = field.stringValue().strip()
            if key:
                s["openai_api_key"] = key
                settings.save(s)

    def selectModel_(self, sender):
        model = sender.representedObject()
        s = settings.load()
        s["whisper_model"] = model
        settings.save(s)
        # Reload ASR in background
        def _reload():
            self._asr = asr_mod.ASR(model)
        threading.Thread(target=_reload, daemon=True).start()
        # Rebuild menu to update checkmark
        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            "rebuildMenu:", None, False
        )

    def rebuildMenu_(self, _):
        self._build_menu()

    def openHistory_(self, _sender):
        subprocess.Popen(["open", str(history.HISTORY_PATH)])

    @objc.python_method
    def _set_title(self, title: str):
        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            "setMenubarTitle:", title, False
        )

    def setMenubarTitle_(self, title: str):
        self._status_item.button().setTitle_(title)

    @objc.python_method
    def _on_record_start(self):
        with self._state_lock:
            if self._state != "IDLE":
                return
            self._state = "RECORDING"
        self._audio.start()
        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            "checkContextAndBeginRecording:", None, True
        )

    def checkContextAndBeginRecording_(self, _):
        try:
            ctx = context.get_context()
            if not ctx["safe"]:
                self._audio.stop()
                self._warn(ctx["reason"])
                with self._state_lock:
                    self._state = "IDLE"
                return
            self._ctx = ctx
            self._status_item.button().setTitle_("🔴")
            self._overlay.show()
        except Exception:
            import traceback
            traceback.print_exc()

    @objc.python_method
    def _on_record_stop(self):
        with self._state_lock:
            if self._state != "RECORDING":
                return
            self._state = "TRANSCRIBING"
        ctx = dict(self._ctx)
        try:
            audio_data = self._audio.stop()
        except Exception:
            with self._state_lock:
                self._state = "IDLE"
            self._set_title("🎤")
            return
        asyncio.run_coroutine_threadsafe(
            self._process(audio_data, ctx),
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
            examples = history.get_examples_for_app(ctx["app"])
            polished = intent.rewrite(raw, ctx["app"], examples=examples)
            injector.inject(polished)
            history.add({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "app": ctx["app"],
                "tone": settings.get_tone(ctx["app"])[0],
                "raw": raw,
                "polished": polished,
            })
        except Exception:
            import traceback
            traceback.print_exc()
        finally:
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                "resetToIdle:", None, False
            )

    def resetToIdle_(self, _):
        with self._state_lock:
            self._state = "IDLE"
        self._overlay.hide()
        self._status_item.button().setTitle_("🎤")

    @objc.python_method
    def _warn(self, reason: str):
        label = {
            "secure_input": "Secure input active",
            "password_field": "Password field — skipped",
        }.get(reason, "Injection blocked")
        self._status_item.button().setTitle_(f"⚠️ {label}")
        threading.Timer(2.0, lambda: self._status_item.button().setTitle_("🎤")).start()


def run():
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(1)
    delegate = _Delegate.alloc().init()
    app.setDelegate_(delegate)
    app.run()


if __name__ == "__main__":
    run()
