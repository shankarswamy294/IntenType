from AppKit import NSWorkspace
import Quartz


def get_context() -> dict:
    """Returns app name and whether text injection is safe to proceed."""
    frontmost = NSWorkspace.sharedWorkspace().frontmostApplication()
    app_name = frontmost.localizedName() if frontmost else "Unknown"

    try:
        if Quartz.CGSIsSecureEventInputEnabled():
            return {"app": app_name, "safe": False, "reason": "secure_input"}
    except AttributeError:
        pass  # Not available on this PyObjC version — skip secure-input check

    system_el = Quartz.AXUIElementCreateSystemWide()
    err, focused = Quartz.AXUIElementCopyAttributeValue(
        system_el, Quartz.kAXFocusedUIElementAttribute, None
    )
    if err == 0 and focused is not None:
        err2, subrole = Quartz.AXUIElementCopyAttributeValue(focused, "AXSubrole", None)
        if err2 == 0 and subrole == "AXSecureTextField":
            return {"app": app_name, "safe": False, "reason": "password_field"}

    return {"app": app_name, "safe": True, "reason": None}
