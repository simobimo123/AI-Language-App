"""Smoke tests for the structured Teaching AI TTS contract."""

import json

from services.ai.provider import OpenRouterProvider


provider = OpenRouterProvider()

SYSTEM = "You are the **TEACHING AI** for a German lesson."

VALID = json.dumps(
    {
        "reply": "هذا يعني أن اسمك. Ich heiße Anna.",
        "target_completed": False,
        "target_order": 1,
        "stage_completed": False,
        "speech_segments": [
            {"role": "NATIVE", "text": "هذا يعني أن اسمك."},
            {"role": "LEARNING", "text": "Ich heiße Anna."},
        ],
    },
    ensure_ascii=False,
)

normalized = provider._normalize_teaching_tts_response(VALID, SYSTEM)
payload = json.loads(normalized)

assert payload["reply"].startswith("[NATIVE]")
assert "[LEARNING] Ich heiße Anna." in payload["reply"]
assert "speech_segments" not in payload

INVALID = json.dumps(
    {
        "reply": "Hallo.",
        "target_completed": False,
        "target_order": 1,
        "stage_completed": False,
        "speech_segments": [
            {"role": "NATIVE", "text": "Falscher Inhalt."},
        ],
    },
    ensure_ascii=False,
)

invalid_normalized = provider._normalize_teaching_tts_response(
    INVALID,
    SYSTEM,
)
assert json.loads(invalid_normalized)["reply"] == "Hallo."

print("Teaching TTS contract: OK")
