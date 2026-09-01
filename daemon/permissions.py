"""
Permission checking and requesting for IntenType.
Three permissions required: Input Monitoring, Accessibility, Microphone.
"""
import subprocess
import objc
import Quartz


def check_input_monitoring() -> bool:
    # Must use kCGHIDEventTap — the only tap that intercepts global keyboard events.
    # kCGSessionEventTap succeeds without Input Monitoring but can't see other apps' keys.
    mask = Quartz.CGEventMaskBit(Quartz.kCGEventFlagsChanged)
    tap = Quartz.CGEventTapCreate(
        Quartz.kCGHIDEventTap,
        Quartz.kCGHeadInsertEventTap,
        Quartz.kCGEventTapOptionListenOnly,
        mask,
        lambda *a: a[2],
        None,
    )
    if tap:
        Quartz.CGEventTapEnable(tap, False)
        return True
    return False


def check_accessibility() -> bool:
    try:
        import ApplicationServices as AS
        # AXIsProcessTrustedWithOptions with no prompt — just check status
        result = AS.AXIsProcessTrustedWithOptions({"AXTrustedCheckOptionPrompt": False})
        if result:
            return True
        # Fallback: AXIsProcessTrusted
        return bool(AS.AXIsProcessTrusted())
    except Exception:
        return True  # can't check — assume granted


def check_microphone() -> bool:
    try:
        AVCaptureDevice = objc.lookUpClass("AVCaptureDevice")
        if AVCaptureDevice is None:
            return True  # can't check — assume OK
        # authorizationStatusForMediaType_: 3 = authorized
        return int(AVCaptureDevice.authorizationStatusForMediaType_("soun")) == 3
    except Exception:
        return True  # can't check — assume OK


def request_microphone():
    """Trigger mic permission by attempting a short recording — macOS prompts automatically."""
    import threading
    done = threading.Event()

    def _try():
        try:
            import sounddevice as sd
            # A 0.1s recording is enough to trigger the system permission dialog
            sd.rec(int(0.1 * 16000), samplerate=16000, channels=1, dtype="int16", blocking=True)
        except Exception:
            pass
        finally:
            done.set()

    threading.Thread(target=_try, daemon=True).start()
    done.wait(timeout=10)


def request_input_monitoring():
    """Trigger Input Monitoring permission dialog by attempting a real (non-listen-only) CGEventTap."""
    import time
    mask = Quartz.CGEventMaskBit(Quartz.kCGEventFlagsChanged)
    tap = Quartz.CGEventTapCreate(
        Quartz.kCGHIDEventTap,
        Quartz.kCGHeadInsertEventTap,
        Quartz.kCGEventTapOptionDefault,
        mask,
        lambda *a: a[2],
        None,
    )
    if tap:
        Quartz.CGEventTapEnable(tap, False)
    else:
        # macOS didn't auto-prompt — fall back to opening the pane
        open_settings("input_monitoring")
    time.sleep(0.5)


def request_accessibility():
    """Opens System Settings prompt for Accessibility (or the pane if already shown)."""
    try:
        import ApplicationServices as AS
        AS.AXIsProcessTrustedWithOptions({"AXTrustedCheckOptionPrompt": True})
    except Exception:
        open_settings("accessibility")


def open_settings(pane: str):
    urls = {
        "input_monitoring": "x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent",
        "accessibility": "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
        "microphone": "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone",
    }
    subprocess.Popen(["open", urls[pane]])


def missing_permissions() -> list[str]:
    """Return list of permission names that are not yet granted."""
    import os, traceback
    log_path = "/tmp/intentype_perms.log"
    results = {}
    missing = []
    for name, fn in [
        ("input_monitoring", check_input_monitoring),
        ("accessibility", check_accessibility),
        ("microphone", check_microphone),
    ]:
        try:
            ok = fn()
            results[name] = ok
            if not ok:
                missing.append(name)
        except Exception as e:
            results[name] = f"ERROR: {e}\n{traceback.format_exc()}"
            missing.append(name)
    try:
        with open(log_path, "a") as f:
            f.write(f"pid={os.getpid()} {results} missing={missing}\n")
    except Exception:
        pass
    return missing
