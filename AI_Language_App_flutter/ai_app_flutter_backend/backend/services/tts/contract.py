"""Shared contract for lesson-AI to TTS language routing.

The lesson model remains responsible for teaching content. This module only
specifies the small, machine-readable contract used when a reply mixes the
learner language with the explanation language.
"""

from __future__ import annotations

NATIVE_MARKER = "[NATIVE]"
LEARNING_MARKER = "[LEARNING]"

TTS_MARKER_INSTRUCTIONS = f"""
**TTS LANGUAGE CONTRACT — MANDATORY**:

The teacher reply may contain both the learner's target language and the
explanation language. Mark every spoken part explicitly so the audio layer
never has to guess the language.

- Put {NATIVE_MARKER} immediately before text spoken in the learner's native/
  explanation language.
- Put {LEARNING_MARKER} immediately before text spoken in the lesson's
  learning language.
- The marker applies until the next marker.
- Markers are control tags only. Never explain them, pronounce them, or put
  them inside the learner-facing wording.
- If the whole reply is in one language, still mark it explicitly.
- Short learner-language examples must be marked {LEARNING_MARKER} even when the
  surrounding explanation is in the native language.
- Corrections must mark the actual target-language form as {LEARNING_MARKER}; a
  native-language explanation of the error must be {NATIVE_MARKER}.
- Do not use any other language-routing markers.

Example:
{NATIVE_MARKER} This means "my name is".
{LEARNING_MARKER} Ich heiße Thomas.
{NATIVE_MARKER} Now you try.

The JSON `reply` field MUST contain these markers when the reply mixes
languages.
""".strip()


def append_tts_contract(prompt: str) -> str:
    """Append the TTS contract without changing the caller's teaching rules."""
    return f"{prompt.rstrip()}\n\n{TTS_MARKER_INSTRUCTIONS}"
