from unittest.mock import patch, MagicMock, call


_RIGHT_OPTION = 0x3D


_ALT_FLAG = 0x80000  # kCGEventFlagMaskAlternate


def _make_quartz_mock():
    q = MagicMock()
    q.kCGHIDEventTap = 0
    q.kCGHeadInsertEventTap = 0
    q.kCGEventTapOptionDefault = 0
    q.kCGEventFlagsChanged = 12
    q.kCGEventFlagMaskAlternate = _ALT_FLAG
    q.CGEventMaskBit.side_effect = lambda x: 1 << x
    q.CGEventGetIntegerValueField.return_value = _RIGHT_OPTION
    q.kCGKeyboardEventKeycode = 9
    q.CGEventGetFlags.return_value = _ALT_FLAG  # default: Alt held (key down)
    q.CGEventTapCreate.return_value = MagicMock()
    q.CFMachPortCreateRunLoopSource.return_value = MagicMock()
    return q


def test_on_down_callback_fires_on_flags_changed_with_alt():
    q = _make_quartz_mock()
    q.CGEventGetFlags.return_value = _ALT_FLAG  # Right Option pressed
    on_down = MagicMock()
    on_up = MagicMock()

    with patch.dict("sys.modules", {"Quartz": q, "CoreFoundation": MagicMock()}):
        from daemon import hotkey
        import importlib; importlib.reload(hotkey)
        hotkey.create_event_tap(on_down, on_up)

    callback = q.CGEventTapCreate.call_args[0][4]
    callback(None, q.kCGEventFlagsChanged, MagicMock(), None)

    on_down.assert_called_once()
    on_up.assert_not_called()


def test_on_up_callback_fires_on_flags_changed_without_alt():
    q = _make_quartz_mock()
    q.CGEventGetFlags.return_value = 0x0  # Right Option released
    on_down = MagicMock()
    on_up = MagicMock()

    with patch.dict("sys.modules", {"Quartz": q, "CoreFoundation": MagicMock()}):
        from daemon import hotkey
        import importlib; importlib.reload(hotkey)
        hotkey.create_event_tap(on_down, on_up)

    callback = q.CGEventTapCreate.call_args[0][4]
    callback(None, q.kCGEventFlagsChanged, MagicMock(), None)

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
    callback(None, q.kCGEventFlagsChanged, MagicMock(), None)
    on_down.assert_not_called()
