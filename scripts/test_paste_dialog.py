#!/usr/bin/env python3
"""
Programmatic test: open the API key dialog and fire Cmd+V.
Run from repo root with: .venv/bin/python scripts/test_paste_dialog.py
"""
import threading, time
import objc
import Quartz
from AppKit import (
    NSApplication, NSObject, NSAlert, NSTextField, NSMakeRect,
    NSAlertFirstButtonReturn, NSPasteboard, NSPasteboardTypeString,
    NSView, NSButton, NSMenu, NSMenuItem,
)

_CMD = 0x37
_V   = 0x09

def _post_cmd_v():
    """Simulate Cmd+V via CGEventPost after a short delay."""
    time.sleep(1.2)
    src    = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStatePrivate)
    dn_cmd = Quartz.CGEventCreateKeyboardEvent(src, _CMD, True)
    dn_v   = Quartz.CGEventCreateKeyboardEvent(src, _V,   True)
    up_v   = Quartz.CGEventCreateKeyboardEvent(src, _V,   False)
    up_cmd = Quartz.CGEventCreateKeyboardEvent(src, _CMD, False)
    Quartz.CGEventSetFlags(dn_cmd, Quartz.kCGEventFlagMaskCommand)
    Quartz.CGEventSetFlags(dn_v,   Quartz.kCGEventFlagMaskCommand)
    tap = Quartz.kCGAnnotatedSessionEventTap
    Quartz.CGEventPost(tap, dn_cmd)
    Quartz.CGEventPost(tap, dn_v)
    Quartz.CGEventPost(tap, up_v)
    Quartz.CGEventPost(tap, up_cmd)
    print("[test] Cmd+V posted")

def _close_after(alert_ref, delay=3.0):
    """Close the modal after delay so the test doesn't hang."""
    time.sleep(delay)
    from AppKit import NSApp
    NSApp.abortModal()

class _Delegate(NSObject):
    def applicationDidFinishLaunching_(self, _n):
        # Put a known string in clipboard
        pb = NSPasteboard.generalPasteboard()
        pb.clearContents()
        pb.setString_forType_("sk-TEST-PASTE-WORKS", NSPasteboardTypeString)
        print("[test] clipboard set to: sk-TEST-PASTE-WORKS")

        # Build Edit menu so paste: action is routable
        main_menu = NSMenu.alloc().init()
        edit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Edit", None, "")
        edit_menu = NSMenu.alloc().initWithTitle_("Edit")
        for title, action, key in [
            ("Cut",        "cut:",       "x"),
            ("Copy",       "copy:",      "c"),
            ("Paste",      "paste:",     "v"),
            ("Select All", "selectAll:", "a"),
        ]:
            edit_menu.addItem_(
                NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, action, key)
            )
        edit_item.setSubmenu_(edit_menu)
        main_menu.addItem_(edit_item)
        NSApplication.sharedApplication().setMainMenu_(main_menu)

        self._run_test()

    @objc.python_method
    def _run_test(self):
        app = NSApplication.sharedApplication()
        app.setActivationPolicy_(0)
        app.activateIgnoringOtherApps_(True)

        field = NSTextField.alloc().initWithFrame_(NSMakeRect(0, 0, 320, 24))
        field.setStringValue_("")
        field.setPlaceholderString_("paste here")

        alert = NSAlert.alloc().init()
        alert.setMessageText_("Paste test")
        alert.setInformativeText_("Cmd+V will be fired automatically in 1.2 s")
        alert.addButtonWithTitle_("OK")
        alert.addButtonWithTitle_("Cancel")
        alert.setAccessoryView_(field)

        win = alert.window()
        win.setInitialFirstResponder_(field)
        win.makeKeyAndOrderFront_(None)
        win.makeFirstResponder_(field)

        # Fire Cmd+V and auto-close in background threads
        threading.Thread(target=_post_cmd_v, daemon=True).start()
        threading.Thread(target=_close_after, args=(alert, 3.0), daemon=True).start()

        alert.runModal()
        app.setActivationPolicy_(1)

        val = field.stringValue()
        print(f"[test] field value after Cmd+V: '{val}'")
        if "TEST-PASTE-WORKS" in val:
            print("[test] ✓ PASS — Cmd+V works correctly")
        else:
            print("[test] ✗ FAIL — Cmd+V did not paste")

        app.terminate_(None)


if __name__ == "__main__":
    app = NSApplication.sharedApplication()
    d = _Delegate.alloc().init()
    app.setDelegate_(d)
    app.run()
