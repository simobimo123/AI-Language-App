"""Local smoke test for the TTS foundation.

Run from the backend directory after Piper voice models are installed.
This script intentionally reports missing local model binaries instead of
failing the whole project when a language has not been downloaded yet.
"""

from services.tts.text_segments import split_tts_segments
from services.tts.voice_registry import VOICE_SPECS, get_available_voices, get_voice


print("=== TTS marker parser ===")
example = (
    "[[TARGET_COMPLETE:1]] "
    "[LEARNING] Ich heiße Thomas. "
    "[NATIVE] هذا يعني: اسمي توماس. "
    "[[TEACHING_COMPLETE]]"
)

segments = split_tts_segments(example)
for segment in segments:
    print(f"{segment.role}: {segment.text}")

assert [segment.role for segment in segments] == [
    "LEARNING",
    "NATIVE",
]
assert all("TARGET_COMPLETE" not in segment.text for segment in segments)
assert all("TEACHING_COMPLETE" not in segment.text for segment in segments)

print("Marker parser: OK")

print("\n=== Installed Piper voices ===")
for language in sorted({voice.language for voice in VOICE_SPECS}):
    voices = get_available_voices(language)
    if not voices:
        print(f"{language}: NOT INSTALLED")
        continue

    selected = get_voice(language)
    print(
        f"{language}: {selected.model_stem} "
        f"({selected.quality}) | "
        f"{len(voices)} local candidate(s)"
    )

print("\nTTS foundation smoke test finished.")
