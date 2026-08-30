import numpy as np
from unittest.mock import patch, MagicMock


def _make_mock_faster_whisper(segments_text: list[str]):
    mock_fw = MagicMock()
    mock_model = MagicMock()
    fake_segments = [MagicMock(text=t) for t in segments_text]
    mock_model.transcribe.return_value = (iter(fake_segments), MagicMock())
    mock_fw.WhisperModel.return_value = mock_model
    return mock_fw, mock_model


def test_transcribe_joins_segments():
    mock_fw, mock_model = _make_mock_faster_whisper([" Hello", " world"])
    with patch.dict("sys.modules", {"faster_whisper": mock_fw}):
        from daemon import asr
        import importlib; importlib.reload(asr)
        engine = asr.ASR("small.en")
        audio = np.zeros(16000, dtype=np.float32)
        result = engine.transcribe(audio)
    assert result == "Hello world"


def test_transcribe_returns_empty_for_empty_audio():
    mock_fw, _ = _make_mock_faster_whisper([])
    with patch.dict("sys.modules", {"faster_whisper": mock_fw}):
        from daemon import asr
        import importlib; importlib.reload(asr)
        engine = asr.ASR("small.en")
        result = engine.transcribe(np.array([], dtype=np.float32))
    assert result == ""


def test_reload_reinitialises_model():
    mock_fw, mock_model = _make_mock_faster_whisper([])
    with patch.dict("sys.modules", {"faster_whisper": mock_fw}):
        from daemon import asr
        import importlib; importlib.reload(asr)
        engine = asr.ASR("small.en")
        engine.reload("medium.en")
    assert mock_fw.WhisperModel.call_count == 2
    assert mock_fw.WhisperModel.call_args_list[1][0][0] == "medium.en"
