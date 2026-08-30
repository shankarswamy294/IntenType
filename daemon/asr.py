import numpy as np
from faster_whisper import WhisperModel


class ASR:
    def __init__(self, model_size: str = "small.en"):
        self._model = WhisperModel(model_size, device="auto", compute_type="auto")
        self._model_size = model_size

    def transcribe(self, audio: np.ndarray) -> str:
        if len(audio) == 0:
            return ""
        segments, _ = self._model.transcribe(audio, language="en", beam_size=5)
        return "".join(s.text for s in segments).strip()

    def reload(self, model_size: str) -> None:
        self._model_size = model_size
        self._model = WhisperModel(model_size, device="auto", compute_type="auto")
