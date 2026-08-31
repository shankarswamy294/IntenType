from typing import Callable
import threading
import Quartz
import CoreFoundation

_RIGHT_OPTION = 0x3D


def create_event_tap(on_down: Callable, on_up: Callable):
    # Right Option is a modifier key — it fires kCGEventFlagsChanged, not KeyDown/KeyUp.
    # Detect press/release by checking keycode + whether Alt flag is now set or cleared.
    # Dispatch callbacks off the event tap thread to avoid AppKit deadlocks.
    _ALT_FLAG = Quartz.kCGEventFlagMaskAlternate

    def _callback(proxy, event_type, event, refcon):
        if event_type != Quartz.kCGEventFlagsChanged:
            return event
        keycode = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
        if keycode != _RIGHT_OPTION:
            return event
        flags = Quartz.CGEventGetFlags(event)
        if flags & _ALT_FLAG:
            open("/tmp/it_pipeline.log", "a").write("[hotkey] DOWN — starting thread\n")
            threading.Thread(target=on_down, daemon=True).start()
        else:
            open("/tmp/it_pipeline.log", "a").write("[hotkey] UP — starting thread\n")
            threading.Thread(target=on_up, daemon=True).start()
        return event

    mask = Quartz.CGEventMaskBit(Quartz.kCGEventFlagsChanged)
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
