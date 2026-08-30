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
