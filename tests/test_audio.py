import numpy as np
from unittest.mock import patch, MagicMock, call
import struct


def test_stop_returns_empty_when_no_frames():
    with patch.dict("sys.modules", {"sounddevice": MagicMock()}):
        from daemon import audio
        import importlib; importlib.reload(audio)
        cap = audio.AudioCapture()
        result = cap.stop()
    assert isinstance(result, np.ndarray)
    assert len(result) == 0


def test_stop_returns_normalised_float32():
    with patch.dict("sys.modules", {"sounddevice": MagicMock()}):
        from daemon import audio
        import importlib; importlib.reload(audio)
        cap = audio.AudioCapture()
        # Simulate two int16 frames: max positive and zero
        frame = struct.pack("<hh", 32767, 0)
        cap._frames.append(frame)
        result = cap.stop()
    assert result.dtype == np.float32
    assert abs(result[0] - 1.0) < 0.001
    assert result[1] == 0.0


def test_start_creates_stream_and_stop_closes_it():
    mock_sd = MagicMock()
    mock_stream = MagicMock()
    mock_sd.RawInputStream.return_value.__enter__ = MagicMock(return_value=mock_stream)
    mock_sd.RawInputStream.return_value = mock_stream

    with patch.dict("sys.modules", {"sounddevice": mock_sd}):
        from daemon import audio
        import importlib; importlib.reload(audio)
        cap = audio.AudioCapture()
        cap.start()
        cap.stop()

    mock_stream.start.assert_called_once()
    mock_stream.stop.assert_called_once()
    mock_stream.close.assert_called_once()
