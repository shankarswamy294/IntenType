from unittest.mock import patch, MagicMock, call


def _make_mocks():
    mock_appkit = MagicMock()
    mock_pb = MagicMock()
    mock_pb.types.return_value = ["public.utf8-plain-text"]
    mock_pb.dataForType_.return_value = b"original"
    mock_appkit.NSPasteboard.generalPasteboard.return_value = mock_pb
    mock_appkit.NSStringPboardType = "public.utf8-plain-text"

    mock_quartz = MagicMock()
    mock_src = MagicMock()
    mock_quartz.CGEventSourceCreate.return_value = mock_src
    mock_quartz.CGEventCreateKeyboardEvent.return_value = MagicMock()
    mock_quartz.kCGEventSourceStateCombinedSessionState = 1
    mock_quartz.kCGHIDEventTap = 0
    mock_quartz.kCGEventFlagMaskCommand = 1 << 20

    return mock_appkit, mock_pb, mock_quartz


def test_inject_posts_cmd_v(monkeypatch):
    mock_appkit, mock_pb, mock_quartz = _make_mocks()

    with patch.dict("sys.modules", {"AppKit": mock_appkit, "Quartz": mock_quartz}), \
         patch("time.sleep"):
        from daemon import injector
        import importlib; importlib.reload(injector)
        injector.inject("Hello world")

    assert mock_quartz.CGEventPost.call_count == 4


def test_inject_writes_text_to_clipboard(monkeypatch):
    mock_appkit, mock_pb, mock_quartz = _make_mocks()

    with patch.dict("sys.modules", {"AppKit": mock_appkit, "Quartz": mock_quartz}), \
         patch("time.sleep"):
        from daemon import injector
        import importlib; importlib.reload(injector)
        injector.inject("Hello world")

    mock_pb.setString_forType_.assert_called_once_with("Hello world", "public.utf8-plain-text")


def test_inject_restores_original_clipboard(monkeypatch):
    mock_appkit, mock_pb, mock_quartz = _make_mocks()

    with patch.dict("sys.modules", {"AppKit": mock_appkit, "Quartz": mock_quartz}), \
         patch("time.sleep"):
        from daemon import injector
        import importlib; importlib.reload(injector)
        injector.inject("Hello world")

    # declareTypes called twice: once to set new, once to restore
    assert mock_pb.declareTypes_owner_.call_count == 2
