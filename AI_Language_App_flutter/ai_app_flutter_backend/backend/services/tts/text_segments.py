"""Parsing of explicit TTS language markers produced by the lesson AI."""

from dataclasses import dataclass
import re


_MARKER_RE = re.compile(r"\[(NATIVE|LEARNING)\]", re.IGNORECASE)


@dataclass(frozen=True)
class TTSSegment:
    text: str
    role: str


def split_tts_segments(text: str, *, default_role: str = "LEARNING") -> list[TTSSegment]:
    """Split text into explicit NATIVE/LEARNING segments.

    If the model does not emit markers, the whole text uses ``default_role``.
    Marker text itself is never sent to the TTS engine.
    """
    cleaned = text.strip()
    if not cleaned:
        return []

    matches = list(_MARKER_RE.finditer(cleaned))
    if not matches:
        return [TTSSegment(text=cleaned, role=default_role.upper())]

    segments: list[TTSSegment] = []
    first_prefix = cleaned[: matches[0].start()].strip()
    if first_prefix:
        segments.append(TTSSegment(text=first_prefix, role=default_role.upper()))

    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(cleaned)
        part = cleaned[start:end].strip()
        if part:
            segments.append(
                TTSSegment(text=part, role=match.group(1).upper())
            )

    return segments
