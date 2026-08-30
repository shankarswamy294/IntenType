import time
from AppKit import NSPasteboard, NSStringPboardType
import Quartz

_CMD = 0x37
_V = 0x09


def inject(text: str) -> None:
    pb = NSPasteboard.generalPasteboard()

    # Backup current clipboard
    orig_types = list(pb.types() or [])
    orig_data: dict = {}
    for t in orig_types:
        data = pb.dataForType_(t)
        if data is not None:
            orig_data[t] = data

    # Write polished text
    pb.declareTypes_owner_([NSStringPboardType], None)
    pb.setString_forType_(text, NSStringPboardType)

    # Synthesise Cmd+V
    src = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStateCombinedSessionState)
    cmd_dn = Quartz.CGEventCreateKeyboardEvent(src, _CMD, True)
    v_dn = Quartz.CGEventCreateKeyboardEvent(src, _V, True)
    v_up = Quartz.CGEventCreateKeyboardEvent(src, _V, False)
    cmd_up = Quartz.CGEventCreateKeyboardEvent(src, _CMD, False)

    Quartz.CGEventSetFlags(cmd_dn, Quartz.kCGEventFlagMaskCommand)
    Quartz.CGEventSetFlags(v_dn, Quartz.kCGEventFlagMaskCommand)

    Quartz.CGEventPost(Quartz.kCGHIDEventTap, cmd_dn)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, v_dn)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, v_up)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, cmd_up)

    time.sleep(0.1)

    # Restore original clipboard (best-effort)
    if orig_data:
        try:
            pb.declareTypes_owner_(list(orig_data.keys()), None)
            for t, d in orig_data.items():
                pb.setData_forType_(d, t)
        except Exception:
            pass
