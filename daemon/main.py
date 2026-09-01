import asyncio
import os
import subprocess
import threading
from datetime import datetime, timezone

import objc
from AppKit import (
    NSApplication, NSObject, NSStatusBar, NSVariableStatusItemLength,
    NSMenu, NSMenuItem, NSAlert, NSTextField, NSMakeRect,
    NSAlertFirstButtonReturn, NSImage, NSBundle,
    NSPasteboard, NSPasteboardTypeString,
)


class _PastableTextField(NSTextField):
    """NSTextField with a delegate that intercepts paste: at the field-editor level."""

    @objc.python_method
    def setup_paste_delegate(self):
        self._paste_delegate = _FieldDelegate.alloc().init()
        self._paste_delegate._field = self
        self.setDelegate_(self._paste_delegate)


class _FieldDelegate(NSObject):
    """NSTextFieldDelegate — intercepts paste: before the field editor handles it."""

    def control_textView_doCommandBySelector_(self, control, textView, selector):
        sel = selector if isinstance(selector, str) else selector.decode()
        if sel == "paste:":
            pb = NSPasteboard.generalPasteboard()
            text = pb.stringForType_(NSPasteboardTypeString)
            if text:
                cleaned = text.strip()
                textView.setString_(cleaned)
                textView.setSelectedRange_((0, 0))
                # Also update the NSTextField so wrapping redraws
                if hasattr(self, '_field') and self._field is not None:
                    self._field.setStringValue_(cleaned)
                    self._field.needsDisplay = True
            return True
        return False

from daemon import (
    hotkey as hotkey_mod,
    audio as audio_mod,
    asr as asr_mod,
    intent,
    injector,
    context,
    settings,
    history,
    permissions as perms_mod,
)
from daemon.overlay import RecordingOverlay

_WHISPER_MODELS = ["tiny.en", "base.en", "small.en", "medium.en"]


def _load_png(name: str, template: bool = True) -> NSImage:
    """Load a PNG from the app bundle or repo assets/."""
    bundle_path = NSBundle.mainBundle().pathForResource_ofType_(name, "png")
    path = bundle_path or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", f"{name}.png"
    )
    if path and os.path.exists(path):
        img = NSImage.alloc().initWithContentsOfFile_(path)
        if img:
            img.setSize_((22, 22))
            img.setTemplate_(template)
            return img
    return None


def _load_menubar_image() -> NSImage:
    return _load_png("menubar", template=True)


class _Delegate(NSObject):
    def applicationDidFinishLaunching_(self, _notification):
        self._setup()

    @objc.python_method
    def _setup(self):
        import traceback
        def _log(msg):
            try:
                with open("/tmp/intentype_setup.log", "a") as f:
                    f.write(msg + "\n")
            except Exception:
                pass
        _log("_setup start")
        try:
            self._setup_inner()
        except Exception as e:
            _log(f"_setup CRASHED: {e}\n{traceback.format_exc()}")
        _log("_setup end")

    @objc.python_method
    def _setup_inner(self):
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
        self._menubar_img = _load_menubar_image()
        self._rec_frames = [
            _load_png(f"menubar_rec_{i}", template=False) for i in range(4)
        ]
        self._rec_frames = [f for f in self._rec_frames if f]
        self._rec_frame_idx = 0
        self._rec_timer = None

        btn = self._status_item.button()
        if self._menubar_img:
            btn.setImage_(self._menubar_img)
            btn.setTitle_("")
        else:
            btn.setTitle_("🎤")
        self._build_menu()

        # Try to create event tap; if it fails, permissions setup will guide the user
        try:
            self._tap = hotkey_mod.create_event_tap(
                on_down=self._on_record_start,
                on_up=self._on_record_stop,
            )
        except RuntimeError:
            self._tap = None

        # Rebuild menu now that tap state is known (first build happened before tap was created)
        self._build_menu()

        # Only prompt wizard if the tap itself failed (Input Monitoring missing)
        missing = [] if self._tap is not None else perms_mod.missing_permissions()
        if missing:
            from AppKit import NSTimer
            NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                0.8, self, "runPermissionSetup:", None, False
            )

        # Minimal main menu so Cmd+V works in dialogs
        main_menu = NSMenu.alloc().init()
        edit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Edit", None, "")
        edit_menu = NSMenu.alloc().initWithTitle_("Edit")
        for title, action, key in [
            ("Cut", "cut:", "x"),
            ("Copy", "copy:", "c"),
            ("Paste", "paste:", "v"),
            ("Select All", "selectAll:", "a"),
        ]:
            edit_menu.addItem_(
                NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, action, key)
            )
        edit_item.setSubmenu_(edit_menu)
        main_menu.addItem_(edit_item)
        NSApplication.sharedApplication().setMainMenu_(main_menu)

    @objc.python_method
    def _build_menu(self):
        s = settings.load()
        current_model = s.get("whisper_model", "small.en")

        menu = NSMenu.alloc().init()

        # Only show warning if the event tap itself failed (Input Monitoring missing).
        # Accessibility/Microphone issues show up naturally when the user tries to record.
        tap_ok = getattr(self, '_tap', None) is not None
        perm_title = "⚠️ Setup Permissions…" if not tap_ok else "Permissions ✓"
        perm_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            perm_title, "setupPermissions:", ""
        )
        perm_item.setTarget_(self)
        menu.addItem_(perm_item)

        menu.addItem_(NSMenuItem.separatorItem())

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

    def runPermissionSetup_(self, _):
        self.setupPermissions_(None)

    def setupPermissions_(self, _sender):
        _LABELS = {
            "input_monitoring": ("Input Monitoring", "Lets IntenType detect the Right Option key."),
            "accessibility":    ("Accessibility",    "Lets IntenType read the focused app to skip password fields."),
            "microphone":       ("Microphone",       "Lets IntenType record your voice while you hold Right Option."),
        }
        app = NSApplication.sharedApplication()
        app.setActivationPolicy_(0)
        app.activateIgnoringOtherApps_(True)

        missing = perms_mod.missing_permissions()
        if not missing:
            alert = NSAlert.alloc().init()
            alert.setMessageText_("All permissions granted ✓")
            alert.setInformativeText_("IntenType has everything it needs. Hold Right Option to record.")
            alert.addButtonWithTitle_("OK")
            alert.runModal()
            app.setActivationPolicy_(1)
            return

        for perm in ["input_monitoring", "accessibility", "microphone"]:
            if perm not in missing:
                continue
            name, desc = _LABELS[perm]
            alert = NSAlert.alloc().init()
            alert.setMessageText_(f"Permission needed: {name}")
            alert.setInformativeText_(
                f"{desc}\n\n"
                "Click \"Open Settings\" — IntenType will appear in the list.\n"
                "Toggle it ON, then return here and click \"Done\"."
            )
            alert.addButtonWithTitle_("Open Settings")
            alert.addButtonWithTitle_("Skip")
            result = alert.runModal()
            if result == NSAlertFirstButtonReturn:
                if perm == "input_monitoring":
                    perms_mod.open_settings("input_monitoring")
                elif perm == "accessibility":
                    perms_mod.request_accessibility()
                elif perm == "microphone":
                    perms_mod.request_microphone()
                # Wait for user to come back
                done_alert = NSAlert.alloc().init()
                done_alert.setMessageText_(f"Grant {name}, then click Done")
                done_alert.setInformativeText_(
                    "After toggling IntenType ON in System Settings, click Done."
                )
                done_alert.addButtonWithTitle_("Done")
                done_alert.runModal()

        # Restart if input monitoring was in the list (tap needs a restart to take effect)
        if "input_monitoring" in missing:
            import os, sys
            alert = NSAlert.alloc().init()
            alert.setMessageText_("Restart required")
            alert.setInformativeText_(
                "Input Monitoring takes effect after a restart.\n"
                "IntenType will relaunch now."
            )
            alert.addButtonWithTitle_("Restart Now")
            alert.runModal()
            app.setActivationPolicy_(1)
            import subprocess
            subprocess.Popen(["open", "-a", "IntenType"])
            app.terminate_(None)
            return

        app.setActivationPolicy_(1)
        # Re-create event tap now that permissions are granted
        if self._tap is None:
            try:
                self._tap = hotkey_mod.create_event_tap(
                    on_down=self._on_record_start,
                    on_up=self._on_record_stop,
                )
            except RuntimeError:
                pass

    def setApiKey_(self, _sender):
        s = settings.load()

        field = _PastableTextField.alloc().initWithFrame_(NSMakeRect(0, 0, 380, 52))
        field.setStringValue_(s.get("openai_api_key", ""))
        field.setPlaceholderString_("sk-proj-...")
        field.cell().setWraps_(True)
        field.cell().setScrollable_(False)
        field.setFont_(field.font())  # trigger layout
        field.setup_paste_delegate()

        alert = NSAlert.alloc().init()
        alert.setMessageText_("Connect to OpenAI")
        alert.setInformativeText_(
            "IntenType uses OpenAI to polish your speech.\n\n"
            "1. Go to platform.openai.com/api-keys\n"
            "2. Click \"Create new secret key\"\n"
            "3. Paste it below with Cmd+V\n\n"
            "Your key is stored locally and never shared."
        )
        alert.addButtonWithTitle_("Save")
        alert.addButtonWithTitle_("Cancel")
        alert.setAccessoryView_(field)

        app = NSApplication.sharedApplication()
        app.setActivationPolicy_(0)
        app.activateIgnoringOtherApps_(True)

        # Re-apply Edit menu after activation-policy switch so Cmd+V routes to paste:
        main_menu = NSMenu.alloc().init()
        edit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Edit", None, "")
        edit_menu = NSMenu.alloc().initWithTitle_("Edit")
        for title, action, key in [
            ("Cut", "cut:", "x"), ("Copy", "copy:", "c"),
            ("Paste", "paste:", "v"), ("Select All", "selectAll:", "a"),
        ]:
            edit_menu.addItem_(
                NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, action, key)
            )
        edit_item.setSubmenu_(edit_menu)
        main_menu.addItem_(edit_item)
        app.setMainMenu_(main_menu)

        win = alert.window()
        win.setInitialFirstResponder_(field)
        win.makeKeyAndOrderFront_(None)
        win.makeFirstResponder_(field)

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
        # kept for _warn fallback
        if title.startswith("⚠️"):
            self._status_item.button().setImage_(None)
            self._status_item.button().setTitle_(title)
        else:
            self._stop_menubar_anim()

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

    def _startRecordingAnimation_(self, _=None):
        if not self._rec_frames:
            return
        self._rec_frame_idx = (self._rec_frame_idx + 1) % len(self._rec_frames)
        self._status_item.button().setImage_(self._rec_frames[self._rec_frame_idx])

    @objc.python_method
    def _start_menubar_anim(self):
        from AppKit import NSTimer
        if self._rec_frames:
            self._status_item.button().setImage_(self._rec_frames[0])
            self._rec_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                0.18, self, "_startRecordingAnimation_:", None, True
            )

    @objc.python_method
    def _stop_menubar_anim(self):
        if self._rec_timer:
            self._rec_timer.invalidate()
            self._rec_timer = None
        btn = self._status_item.button()
        if self._menubar_img:
            btn.setImage_(self._menubar_img)
            btn.setTitle_("")
        else:
            btn.setTitle_("🎤")

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
            self._start_menubar_anim()
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
        self._stop_menubar_anim()

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
