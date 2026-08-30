import threading
import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "int16"


class AudioCapture:
    def __init__(self):
        self._frames: list[bytes] = []
        self._stream = None
        self._lock = threading.Lock()

    def start(self) -> None:
        self._frames = []
        self._stream = sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> np.ndarray:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        with self._lock:
            if not self._frames:
                return np.array([], dtype=np.float32)
            raw = np.frombuffer(b"".join(self._frames), dtype=np.int16)
            return raw.astype(np.float32) / 32768.0

    def _callback(self, indata, frames, time, status) -> None:
        with self._lock:
            self._frames.append(bytes(indata))
