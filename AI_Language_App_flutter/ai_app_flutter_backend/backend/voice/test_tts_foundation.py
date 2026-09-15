"""Local smoke test for the TTS foundation.

Run from the backend directory after Piper voice models are installed.
"""

from services.tts.text_segments import split_tts_segments
from services.tts.voice_registry import VOICE_SPECS, get_voice


print("=== TTS marker parser ===")
example = "[LEARNING] Ich heiße Thomas. [NATIVE] هذا يعني: اسمي توماس."
for segment in split_tts_segments(example):
    print(f"{segment.role}: {segment.text}")

print("\n=== Installed Piper voices ===")
for language in sorted({voice.language for voice in VOICE_SPECS}):
    try:
        voice = get_voice(language)
        print(f"{language}: {voice.model_stem} ({voice.quality})")
    except FileNotFoundError:
        print(f"{language}: NOT INSTALLED")

print("\nTTS foundation smoke test finished.")
