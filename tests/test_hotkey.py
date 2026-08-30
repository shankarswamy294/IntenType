from unittest.mock import patch, MagicMock, call


_RIGHT_OPTION = 0x3D


def _make_quartz_mock():
    q = MagicMock()
    q.kCGHIDEventTap = 0
    q.kCGHeadInsertEventTap = 0
    q.kCGEventTapOptionDefault = 0
    q.kCGEventKeyDown = 10
    q.kCGEventKeyUp = 11
    q.CGEventMaskBit.side_effect = lambda x: 1 << x
    q.CGEventGetIntegerValueField.return_value = _RIGHT_OPTION
    q.kCGKeyboardEventKeycode = 9
    q.CGEventTapCreate.return_value = MagicMock()
    q.CFMachPortCreateRunLoopSource.return_value = MagicMock()
    return q


def test_on_down_callback_fires_on_key_down():
    q = _make_quartz_mock()
    on_down = MagicMock()
    on_up = MagicMock()

    with patch.dict("sys.modules", {"Quartz": q, "CoreFoundation": MagicMock()}):
        from daemon import hotkey
        import importlib; importlib.reload(hotkey)
        tap = hotkey.create_event_tap(on_down, on_up)

    # Extract the callback passed to CGEventTapCreate
    callback = q.CGEventTapCreate.call_args[0][4]
    callback(None, q.kCGEventKeyDown, MagicMock(), None)

    on_down.assert_called_once()
    on_up.assert_not_called()


def test_on_up_callback_fires_on_key_up():
    q = _make_quartz_mock()
    on_down = MagicMock()
    on_up = MagicMock()

    with patch.dict("sys.modules", {"Quartz": q, "CoreFoundation": MagicMock()}):
        from daemon import hotkey
        import importlib; importlib.reload(hotkey)
        hotkey.create_event_tap(on_down, on_up)

    callback = q.CGEventTapCreate.call_args[0][4]
    callback(None, q.kCGEventKeyUp, MagicMock(), None)

    on_up.assert_called_once()
    on_down.assert_not_called()


def test_ignores_other_keycodes():
    q = _make_quartz_mock()
    q.CGEventGetIntegerValueField.return_value = 0x00  # not Right Option
    on_down = MagicMock()
    on_up = MagicMock()

    with patch.dict("sys.modules", {"Quartz": q, "CoreFoundation": MagicMock()}):
        from daemon import hotkey
        import importlib; importlib.reload(hotkey)
        hotkey.create_event_tap(on_down, on_up)

    callback = q.CGEventTapCreate.call_args[0][4]
    callback(None, q.kCGEventKeyDown, MagicMock(), None)
    on_down.assert_not_called()
