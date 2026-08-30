from unittest.mock import patch, MagicMock
import pytest


def _make_frontmost(name="Slack"):
    app = MagicMock()
    app.localizedName.return_value = name
    return app


def test_returns_app_name(monkeypatch):
    mock_workspace = MagicMock()
    mock_workspace.sharedWorkspace.return_value.frontmostApplication.return_value = _make_frontmost("Mail")

    with patch.dict("sys.modules", {
        "AppKit": MagicMock(NSWorkspace=mock_workspace),
        "Quartz": MagicMock(
            CGSIsSecureEventInputEnabled=lambda: False,
            AXUIElementCreateSystemWide=MagicMock(return_value=MagicMock()),
            AXUIElementCopyAttributeValue=MagicMock(return_value=(1, None)),  # err=1 → no focused element
            kAXFocusedUIElementAttribute="AXFocusedUIElement",
        ),
    }):
        from daemon import context
        import importlib; importlib.reload(context)
        result = context.get_context()

    assert result["app"] == "Mail"
    assert result["safe"] is True


def test_blocks_on_secure_input(monkeypatch):
    mock_workspace = MagicMock()
    mock_workspace.sharedWorkspace.return_value.frontmostApplication.return_value = _make_frontmost("Terminal")

    with patch.dict("sys.modules", {
        "AppKit": MagicMock(NSWorkspace=mock_workspace),
        "Quartz": MagicMock(
            CGSIsSecureEventInputEnabled=lambda: True,
            AXUIElementCreateSystemWide=MagicMock(),
            AXUIElementCopyAttributeValue=MagicMock(return_value=(1, None)),
            kAXFocusedUIElementAttribute="AXFocusedUIElement",
        ),
    }):
        from daemon import context
        import importlib; importlib.reload(context)
        result = context.get_context()

    assert result["safe"] is False
    assert result["reason"] == "secure_input"


def test_blocks_on_password_field(monkeypatch):
    mock_workspace = MagicMock()
    mock_workspace.sharedWorkspace.return_value.frontmostApplication.return_value = _make_frontmost("Safari")

    mock_focused = MagicMock()

    def fake_ax_copy(element, attr, _):
        if attr == "AXFocusedUIElement":
            return (0, mock_focused)
        if attr == "AXSubrole":
            return (0, "AXSecureTextField")
        return (1, None)

    with patch.dict("sys.modules", {
        "AppKit": MagicMock(NSWorkspace=mock_workspace),
        "Quartz": MagicMock(
            CGSIsSecureEventInputEnabled=lambda: False,
            AXUIElementCreateSystemWide=MagicMock(return_value=MagicMock()),
            AXUIElementCopyAttributeValue=MagicMock(side_effect=fake_ax_copy),
            kAXFocusedUIElementAttribute="AXFocusedUIElement",
        ),
    }):
        from daemon import context
        import importlib; importlib.reload(context)
        result = context.get_context()

    assert result["safe"] is False
    assert result["reason"] == "password_field"
