"""Local Piper voice registry.

Model binaries are intentionally not stored in Git. The registry only stores
portable metadata and resolves matching local .onnx files at runtime.
"""

from dataclasses import dataclass
from pathlib import Path


VOICE_DIR = Path(__file__).resolve().parents[2] / "voice"

QUALITY_RANK = {"x_low": 0, "low": 1, "medium": 2, "high": 3}


@dataclass(frozen=True)
class VoiceSpec:
    language: str
    model_stem: str
    gender: str | None = None
    quality: str = "medium"


# Keep candidates ordered from the most useful/preferred voice to fallbacks.
# Only locally present .onnx files are ever selected. The binaries themselves
# are intentionally ignored by Git.
VOICE_SPECS: tuple[VoiceSpec, ...] = (
    VoiceSpec("ar", "ar_JO-kareem-medium", "male", "medium"),
    VoiceSpec("de", "de_DE-kerstin-low", "female", "low"),
    VoiceSpec("de", "de_DE-eva_k-x_low", "female", "x_low"),
    VoiceSpec("en", "en_US-lessac-high", "female", "high"),
    VoiceSpec("es", "es_AR-daniela-high", "female", "high"),
    VoiceSpec("fr", "fr_FR-siwis-medium", "female", "medium"),
    VoiceSpec("id", "id_ID-news_tts-medium", None, "medium"),
    VoiceSpec("it", "it_IT-serena-high", "female", "high"),
    VoiceSpec("it", "it_IT-paola-medium", "female", "medium"),
    VoiceSpec("ja", "ja_JP-hi_fi_captain-medium", None, "medium"),
    VoiceSpec("ko", "ko_KR-kss-medium", None, "medium"),
    VoiceSpec("nl", "nl_BE-nathalie-medium", "female", "medium"),
    VoiceSpec("nl", "nl_NL-mls_5809-low", None, "low"),
    VoiceSpec("pl", "pl_PL-gosia-medium", "female", "medium"),
    VoiceSpec("pt", "pt_BR-edresson-low", "male", "low"),
    VoiceSpec("ru", "ru_RU-irina-medium", "female", "medium"),
    VoiceSpec("th", "th_TH-tsync2-medium", None, "medium"),
    VoiceSpec("tr", "tr_TR-dfki-medium", None, "medium"),
    VoiceSpec("uk", "uk_UA-tetiana-high", "female", "high"),
    VoiceSpec("vi", "vi_VN-vais1000-medium", None, "medium"),
    VoiceSpec("zh", "zh_CN-huayan-medium", None, "medium"),
)


def _model_path(stem: str) -> Path:
    return VOICE_DIR / f"{stem}.onnx"


def _available(spec: VoiceSpec) -> bool:
    return _model_path(spec.model_stem).is_file()


def get_available_voices(language: str | None = None) -> list[VoiceSpec]:
    """Return registry voices whose .onnx model is physically installed."""
    normalized = None
    if language:
        normalized = language.lower().replace("-", "_").split("_")[0]

    voices = [voice for voice in VOICE_SPECS if _available(voice)]
    if normalized is not None:
        voices = [voice for voice in voices if voice.language == normalized]

    return voices


def get_voice(
    language: str,
    *,
    gender: str | None = None,
) -> VoiceSpec:
    """Return the best locally available voice for a language.

    A requested gender is preferred, but if that gender is not installed we
    deliberately fall back to the best available voice for the language.
    Quality is the primary ranking inside the selected gender group.
    """
    language = language.lower().replace("-", "_").split("_")[0]
    candidates = get_available_voices(language)

    if not candidates:
        raise FileNotFoundError(
            f"No local Piper voice is installed for language '{language}'. "
            f"Expected models under {VOICE_DIR}."
        )

    if gender:
        matching = [voice for voice in candidates if voice.gender == gender.lower()]
        if matching:
            candidates = matching

    return max(candidates, key=lambda voice: QUALITY_RANK.get(voice.quality, -1))


def get_model_path(spec: VoiceSpec) -> Path:
    path = _model_path(spec.model_stem)
    if not path.is_file():
        raise FileNotFoundError(f"Piper model not found: {path}")
    return path
