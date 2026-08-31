from AppKit import NSWorkspace

try:
    import ApplicationServices as _AS
    _AX_AVAILABLE = True
except ImportError:
    _AX_AVAILABLE = False


def get_context() -> dict:
    """Returns app name and whether text injection is safe to proceed."""
    frontmost = NSWorkspace.sharedWorkspace().frontmostApplication()
    app_name = frontmost.localizedName() if frontmost else "Unknown"

    if not _AX_AVAILABLE:
        return {"app": app_name, "safe": True, "reason": None}

    try:
        import Quartz
        if Quartz.CGSIsSecureEventInputEnabled():
            return {"app": app_name, "safe": False, "reason": "secure_input"}
    except AttributeError:
        pass

    try:
        system_el = _AS.AXUIElementCreateSystemWide()
        err, focused = _AS.AXUIElementCopyAttributeValue(
            system_el, _AS.kAXFocusedUIElementAttribute, None
        )
        if err == 0 and focused is not None:
            err2, subrole = _AS.AXUIElementCopyAttributeValue(focused, "AXSubrole", None)
            if err2 == 0 and subrole == "AXSecureTextField":
                return {"app": app_name, "safe": False, "reason": "password_field"}
    except Exception:
        pass

    return {"app": app_name, "safe": True, "reason": None}
