"""High-level TTS orchestration.

This layer owns language routing and marker handling. Routers do not know
anything about Piper model filenames, and lesson AI code does not execute TTS.
"""

from io import BytesIO
from pathlib import Path
import os

import numpy as np
import soundfile as sf

from services.ai.normalization import normalize_language
from services.tts.piper_engine import PiperEngine
from services.tts.text_segments import split_tts_segments
from services.tts.voice_registry import get_model_path, get_voice


class TTSManager:
    def __init__(self) -> None:
        self._piper = PiperEngine()

    @staticmethod
    def _language_for_role(
        role: str,
        *,
        learning_language: str,
        native_language: str,
    ) -> str:
        return (
            learning_language
            if role.upper() == "LEARNING"
            else native_language
        )

    @staticmethod
    def _resample(samples: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
        if source_rate == target_rate or len(samples) < 2:
            return samples
        target_length = max(1, round(len(samples) * target_rate / source_rate))
        source_x = np.linspace(0.0, 1.0, num=len(samples), endpoint=False)
        target_x = np.linspace(0.0, 1.0, num=target_length, endpoint=False)
        return np.interp(target_x, source_x, samples).astype(np.float32)

    def synthesize(
        self,
        text: str,
        *,
        learning_language: str,
        native_language: str,
        gender: str | None = None,
    ) -> tuple[bytes, list[dict[str, str]]]:
        learning_language = normalize_language(learning_language)
        native_language = normalize_language(native_language)

        segments = split_tts_segments(text)
        if not segments:
            raise ValueError("TTS text cannot be empty.")

        rendered: list[np.ndarray] = []
        metadata: list[dict[str, str]] = []
        target_rate: int | None = None

        temp_files: list[Path] = []
        try:
            for segment in segments:
                language = self._language_for_role(
                    segment.role,
                    learning_language=learning_language,
                    native_language=native_language,
                )
                spec = get_voice(language, gender=gender)
                model_path = get_model_path(spec)
                wav_path = self._piper.synthesize(segment.text, model_path)
                temp_files.append(wav_path)

                samples, sample_rate = sf.read(wav_path, dtype="float32", always_2d=False)
                if samples.ndim > 1:
                    samples = samples.mean(axis=1)

                if target_rate is None:
                    target_rate = sample_rate
                samples = self._resample(samples, sample_rate, target_rate)
                rendered.append(samples)
                metadata.append(
                    {
                        "role": segment.role,
                        "language": language,
                        "voice": spec.model_stem,
                    }
                )

            assert target_rate is not None
            combined = np.concatenate(rendered)
            buffer = BytesIO()
            sf.write(buffer, combined, target_rate, format="WAV", subtype="PCM_16")
            return buffer.getvalue(), metadata
        finally:
            for path in temp_files:
                path.unlink(missing_ok=True)
