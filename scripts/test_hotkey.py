#!/usr/bin/env python3
"""
Test Right Option key detection + simulate the keypress programmatically.
Run: cd ~/IntenType && .venv/bin/python scripts/test_hotkey.py
"""
import time, threading, sys
import Quartz
import CoreFoundation

_RIGHT_OPTION = 0x3D
_ALT_FLAG = Quartz.kCGEventFlagMaskAlternate

detected_down = []
detected_up   = []


def _callback(proxy, event_type, event, refcon):
    if event_type != Quartz.kCGEventFlagsChanged:
        return event
    kc = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
    if kc != _RIGHT_OPTION:
        return event
    flags = Quartz.CGEventGetFlags(event)
    if flags & _ALT_FLAG:
        detected_down.append(time.time())
        print("[tap] RIGHT OPTION DOWN detected")
    else:
        detected_up.append(time.time())
        print("[tap] RIGHT OPTION UP detected")
    return event


def _create_tap():
    mask = Quartz.CGEventMaskBit(Quartz.kCGEventFlagsChanged)
    tap = Quartz.CGEventTapCreate(
        Quartz.kCGHIDEventTap,
        Quartz.kCGHeadInsertEventTap,
        Quartz.kCGEventTapOptionDefault,
        mask,
        _callback,
        None,
    )
    return tap


def _simulate_right_option():
    """Post a synthetic Right Option down+up via CGEventPost."""
    time.sleep(1.0)
    src = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStateHIDSystemState)

    # Right Option keydown — FlagsChanged with Alt flag set
    ev_down = Quartz.CGEventCreateKeyboardEvent(src, _RIGHT_OPTION, False)
    Quartz.CGEventSetType(ev_down, Quartz.kCGEventFlagsChanged)
    Quartz.CGEventSetFlags(ev_down, _ALT_FLAG)

    # Right Option keyup — FlagsChanged with Alt flag cleared
    ev_up = Quartz.CGEventCreateKeyboardEvent(src, _RIGHT_OPTION, False)
    Quartz.CGEventSetType(ev_up, Quartz.kCGEventFlagsChanged)
    Quartz.CGEventSetFlags(ev_up, 0)

    print("[sim] posting RIGHT OPTION DOWN")
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev_down)
    time.sleep(0.3)
    print("[sim] posting RIGHT OPTION UP")
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev_up)


def _stop_after(delay):
    time.sleep(delay)
    print("\n--- Results ---")
    print(f"DOWN events detected : {len(detected_down)}")
    print(f"UP   events detected : {len(detected_up)}")
    if detected_down and detected_up:
        print("✓ PASS — Right Option detection is WORKING")
    else:
        print("✗ FAIL — Right Option NOT detected (check Input Monitoring permission)")
    CoreFoundation.CFRunLoopStop(CoreFoundation.CFRunLoopGetCurrent())


tap = _create_tap()
if tap is None:
    print("✗ FAIL — CGEventTapCreate returned None (Input Monitoring permission missing)")
    sys.exit(1)

print("✓ Event tap created successfully")

source = Quartz.CFMachPortCreateRunLoopSource(None, tap, 0)
CoreFoundation.CFRunLoopAddSource(
    CoreFoundation.CFRunLoopGetCurrent(),
    source,
    CoreFoundation.kCFRunLoopCommonModes,
)
Quartz.CGEventTapEnable(tap, True)

print("Simulating Right Option keypress in 1s...")
threading.Thread(target=_simulate_right_option, daemon=True).start()
threading.Thread(target=_stop_after, args=(3.0,), daemon=True).start()

CoreFoundation.CFRunLoopRun()
