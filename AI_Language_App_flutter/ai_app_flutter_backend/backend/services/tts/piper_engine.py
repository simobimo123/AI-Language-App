"""Fast Piper TTS engine with in-memory voice reuse.

The old implementation started a new Piper subprocess for every synthesis
request. That forces Piper to reload the ONNX model every time, which is
unnecessarily slow for an interactive tutor. This implementation loads each
voice once and reuses it for subsequent requests.

A subprocess fallback is kept for environments where the Python Piper API is
not available.
"""

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import wave


PIPER_TIMEOUT_SECONDS = 60

try:
    from piper import PiperVoice
except ImportError:  # pragma: no cover - exercised only in fallback environments
    PiperVoice = None  # type: ignore[assignment,misc]


class PiperEngine:
    def __init__(self) -> None:
        self._piper_executable = shutil.which("piper")
        self._voices: dict[str, object] = {}
        self._voices_lock = threading.RLock()

    def _command(self, model_path: Path, output_path: Path) -> list[str]:
        if self._piper_executable:
            return [
                self._piper_executable,
                "--model",
                str(model_path),
                "--output_file",
                str(output_path),
            ]

        return [
            sys.executable,
            "-m",
            "piper",
            "--model",
            str(model_path),
            "--output_file",
            str(output_path),
        ]

    def _load_voice(self, model_path: Path) -> object:
        if PiperVoice is None:
            raise RuntimeError("Piper Python API is not available.")

        key = str(model_path)

        with self._voices_lock:
            cached = self._voices.get(key)
            if cached is not None:
                return cached

            voice = PiperVoice.load(key)
            self._voices[key] = voice
            return voice

    def _synthesize_with_python_api(
        self,
        text: str,
        model_path: Path,
        output_path: Path,
    ) -> None:
        voice = self._load_voice(model_path)

        # Piper's high-level API writes a standard mono 16-bit WAV and reuses
        # the already-loaded ONNX session for repeated requests.
        with wave.open(str(output_path), "wb") as wav_file:
            voice.synthesize(text, wav_file)  # type: ignore[attr-defined]

    def _synthesize_with_cli(
        self,
        text: str,
        model_path: Path,
        output_path: Path,
    ) -> None:
        result = subprocess.run(
            self._command(model_path, output_path),
            input=text,
            text=True,
            capture_output=True,
            check=False,
            timeout=PIPER_TIMEOUT_SECONDS,
        )

        if result.returncode != 0:
            details = (result.stderr or result.stdout or "Piper failed").strip()
            raise RuntimeError(details)

    def synthesize(self, text: str, model_path: Path) -> Path:
        cleaned = text.strip()
        if not cleaned:
            raise ValueError("TTS text cannot be empty.")

        model_path = model_path.resolve()
        if not model_path.is_file():
            raise FileNotFoundError(f"Piper model not found: {model_path}")

        output_file = tempfile.NamedTemporaryFile(
            prefix="tts_",
            suffix=".wav",
            delete=False,
        )
        output_path = Path(output_file.name)
        output_file.close()

        try:
            if PiperVoice is not None:
                with self._voices_lock:
                    self._synthesize_with_python_api(
                        cleaned,
                        model_path,
                        output_path,
                    )
            else:
                self._synthesize_with_cli(
                    cleaned,
                    model_path,
                    output_path,
                )
        except subprocess.TimeoutExpired as exc:
            output_path.unlink(missing_ok=True)
            raise RuntimeError(
                f"Piper synthesis timed out after {PIPER_TIMEOUT_SECONDS} seconds."
            ) from exc
        except Exception:
            output_path.unlink(missing_ok=True)
            raise

        if not output_path.is_file() or output_path.stat().st_size == 0:
            output_path.unlink(missing_ok=True)
            raise RuntimeError("Piper completed without producing audio.")

        return output_path
