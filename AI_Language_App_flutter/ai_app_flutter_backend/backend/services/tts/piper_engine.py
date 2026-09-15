"""Small subprocess wrapper around the installed Piper CLI."""

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


PIPER_TIMEOUT_SECONDS = 60


class PiperEngine:
    def __init__(self) -> None:
        self._piper_executable = shutil.which("piper")

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
            result = subprocess.run(
                self._command(model_path, output_path),
                input=cleaned,
                text=True,
                capture_output=True,
                check=False,
                timeout=PIPER_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            output_path.unlink(missing_ok=True)
            raise RuntimeError(
                f"Piper synthesis timed out after {PIPER_TIMEOUT_SECONDS} seconds."
            ) from exc
        except Exception:
            output_path.unlink(missing_ok=True)
            raise

        if result.returncode != 0:
            output_path.unlink(missing_ok=True)
            details = (result.stderr or result.stdout or "Piper failed").strip()
            raise RuntimeError(details)

        if not output_path.is_file() or output_path.stat().st_size == 0:
            output_path.unlink(missing_ok=True)
            raise RuntimeError("Piper completed without producing audio.")

        return output_path
