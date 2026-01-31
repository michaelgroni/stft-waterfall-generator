# waterfall.py

import librosa
import numpy as np
from PIL import Image

from falseColor import falseColorScreen


class WaterfallGenerator:
    """
    Builds a waterfall image (PIL.Image) from audio samples.
    This class has no Tkinter dependencies.
    """

    def __init__(
        self,
        dynamic_db: float = 80.0,
        n_fft: int = 65536,
        win_length: int = 32768,
        hop_length: int = 4096,
        bandwidth_hz: int | None = 3000,
    ):
        self.dynamic_db = float(dynamic_db)
        self.n_fft = int(n_fft)
        self.win_length = int(win_length)
        self.hop_length = int(hop_length)
        self.bandwidth_hz = None if bandwidth_hz is None else float(bandwidth_hz)  # None => no HF cut

    def build_image(self, samples: np.ndarray, samplerate: int) -> Image.Image:
        if samples is None or samplerate is None:
            raise ValueError("samples/samplerate must not be None")

        # STFT -> magnitude -> dB
        D = librosa.stft(
            samples,
            n_fft=self.n_fft,
            win_length=self.win_length,
            hop_length=self.hop_length,
        )
        data = librosa.amplitude_to_db(np.abs(D), ref=np.max, top_db=self.dynamic_db)

        # (freq, time) -> (time, freq)
        data = np.swapaxes(data, 1, 0)
        t_size, f_size = data.shape

        # Optionally cut high frequencies
        if self.bandwidth_hz is not None:
            nyquist = samplerate / 2.0
            bandwidth = min(float(self.bandwidth_hz), nyquist)

            fcut = int((f_size - 1) * bandwidth / nyquist)
            fcut = max(0, min(fcut, f_size - 1))
            data = data[:, : fcut + 1]
            t_size, f_size = data.shape

        # False color mapping to RGB
        dataRgb = bytearray(3 * f_size * t_size)
        scale = 255.0 / self.dynamic_db
        fc = falseColorScreen  # local reference for speed
        i = 0
        for pixel in data.flat:
            value = int(pixel * scale + 255.0)
            if value > 255:
                value = 255
            dataRgb[i:i+3] = fc(value)
            i += 3

        return Image.frombytes("RGB", (f_size, t_size), bytes(dataRgb))
