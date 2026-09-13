from pathlib import Path

path = Path("AI_Language_App_flutter/ai_app_flutter_backend/backend/routers/lesson_stage_ai.py")
text = path.read_text(encoding="utf-8")

old_prompt = '''    return f"""
You are the **TEACHING AI** for a {lesson.level} language lesson.

Teach the **CURRENT TARGET** through a short teacher-learner exchange. You are the teacher, not the practice partner.

{_prompt_context(lesson=lesson, targets=targets)}

{current_target_text}

**RULES**:
- Focus on the current target and its **SUCCESS CRITERIA**.
- **TARGET PATTERNS** guide teaching; they are not exact required sentences.
- Respond to what the learner actually says and let them attempt; never answer for them.
- Keep explanations brief and level-appropriate; prefer short examples/prompts.
- If incorrect or incomplete, give the smallest useful correction/model and ask for another attempt.
- Do not move on until the success criteria are clearly met.
- Accept natural alternatives that satisfy the criteria.
- Answer useful target questions briefly, then return to practice.
- Handle unrelated replies naturally and guide back to the target.
- Keep normal responses to 2-3 short sentences.

{task}

**COMPLETION**:
Only when the learner clearly meets the success criteria, give brief positive feedback and append:
[[TARGET_COMPLETE:{current_target_order}]]

The marker must be last and never be shown or explained.
""".strip()
'''

new_prompt = '''    return f"""
You are the **TEACHING AI** for a {lesson.level} language lesson.

Teach the **CURRENT TARGET** through a short teacher-learner exchange. You are the teacher, not the practice partner.

{_prompt_context(lesson=lesson, targets=targets)}

{current_target_text}

**RULES**:
- Focus on the current target and its **SUCCESS CRITERIA**.
- **TARGET PATTERNS** guide teaching; they are not exact required sentences.
- Evaluate the learner's latest answer against the **SUCCESS CRITERIA** before deciding whether the target is complete.
- A target is complete only when the learner's latest answer clearly satisfies the success criteria. Do not mark it complete merely because the answer is understandable or close.
- Respond to what the learner actually says and let them attempt; never answer for them.
- Keep explanations brief and level-appropriate; prefer short examples/prompts.
- If incorrect or incomplete, give the smallest useful correction/model and ask for another attempt.
- Do not move on until the success criteria are clearly met.
- Accept natural alternatives that satisfy the criteria.
- Answer useful target questions briefly, then return to practice.
- Handle unrelated replies naturally and guide back to the target.
- Keep normal responses to 2-3 short sentences.

{task}

**OUTPUT FORMAT — MANDATORY JSON**:
Return ONLY one valid JSON object with exactly these fields:
{{
  "reply": "the short learner-facing response",
  "target_completed": true,
  "target_order": {current_target_order},
  "stage_completed": false
}}

- **reply** must contain only the learner-facing message. Never put JSON, metadata, markers, or evaluation text inside it.
- **target_completed** must be true only if the learner's latest answer clearly satisfies the current target's success criteria; otherwise false.
- **target_order** must be the current target order when evaluating a target, and null when there is no current target.
- **stage_completed** must be true only when this completed target causes all required teaching targets to be complete; otherwise false.
- When the learner is incorrect or incomplete, set **target_completed** to false and keep **target_order** equal to the current target order.
- The backend, not the model, controls lesson state. Never assume that merely writing true changes the lesson state.
""".strip()
'''

if old_prompt not in text:
    raise SystemExit("Expected teaching prompt block was not found")
text = text.replace(old_prompt, new_prompt, 1)

old_marker = '''def _extract_target_completion(
    reply: str,
) -> tuple[str, int | None, bool]:
    target_match = TARGET_COMPLETE_PATTERN.search(
        reply
    )
    teaching_complete = bool(
        TEACHING_COMPLETE_PATTERN.search(
            reply
        )
    )
    target_order: int | None = None
    if target_match:
        try:
            target_order = int(
                target_match.group(1)
            )
        except ValueError:
            target_order = None
    clean_reply = _remove_control_markers(
        reply
    )
    return (
        clean_reply,
        target_order,
        teaching_complete,
    )
'''

new_marker = old_marker + '''\n\ndef _parse_teaching_evaluation(\n    raw_reply: str,\n    *,\n    current_target_order: int | None,\n    is_control_message: bool,\n) -> tuple[str, bool, int | None, bool]:\n    """Parse structured Teaching AI evaluation while keeping backend authority."""\n    try:\n        payload = json.loads(raw_reply)\n    except (TypeError, ValueError, json.JSONDecodeError):\n        reply, marker_target, teaching_complete = _extract_target_completion(\n            raw_reply\n        )\n        valid_marker = (\n            not is_control_message\n            and marker_target is not None\n            and current_target_order is not None\n            and marker_target == current_target_order\n        )\n        return (\n            reply,\n            valid_marker,\n            marker_target if valid_marker else None,\n            teaching_complete if valid_marker else False,\n        )\n\n    if not isinstance(payload, dict):\n        raise RuntimeError("Teaching AI returned an invalid evaluation object.")\n\n    reply = str(payload.get("reply") or "").strip()\n    if not reply:\n        raise RuntimeError(\n            "Teaching AI evaluation did not contain a learner-facing reply."\n        )\n\n    target_completed = payload.get("target_completed") is True\n    target_order_raw = payload.get("target_order")\n    target_order: int | None = None\n    if target_order_raw is not None:\n        try:\n            target_order = int(target_order_raw)\n        except (TypeError, ValueError):\n            target_order = None\n\n    stage_completed = payload.get("stage_completed") is True\n    valid_target_completion = (\n        not is_control_message\n        and target_completed\n        and current_target_order is not None\n        and target_order == current_target_order\n    )\n\n    return (\n        reply,\n        valid_target_completion,\n        target_order if valid_target_completion else None,\n        stage_completed if valid_target_completion else False,\n    )\n'''

if old_marker not in text:
    raise SystemExit("Expected marker parser block was not found")
text = text.replace(old_marker, new_marker, 1)

old_call = '''        response = provider.generate_text(
            model=AI_MODEL,
            prompt=messages,
            system_instruction=_system_prompt(
                stage=request.stage,
                lesson=lesson,
                targets=targets,
                scenario=scenario,
                current_target_order=current_target_order,
                is_start=is_control_message,
            ),
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )
'''

new_call = '''        response = provider.generate_text(
            model=AI_MODEL,
            prompt=messages,
            system_instruction=_system_prompt(
                stage=request.stage,
                lesson=lesson,
                targets=targets,
                scenario=scenario,
                current_target_order=current_target_order,
                is_start=is_control_message,
            ),
            max_output_tokens=MAX_OUTPUT_TOKENS,
            response_mime_type=(
                "application/json"
                if request.stage == "teaching"
                else None
            ),
        )
'''

if old_call not in text:
    raise SystemExit("Expected provider call was not found")
text = text.replace(old_call, new_call, 1)

old_parse = '''        (
            reply,
            completed_target_order,
            teaching_complete_marker,
        ) = _extract_target_completion(
            raw_reply
        )
        if not reply:
'''

new_parse = '''        if request.stage == "teaching":
            (
                reply,
                valid_target_completion,
                completed_target_order,
                teaching_complete_marker,
            ) = _parse_teaching_evaluation(
                raw_reply,
                current_target_order=current_target_order,
                is_control_message=is_control_message,
            )
        else:
            (
                reply,
                completed_target_order,
                teaching_complete_marker,
            ) = _extract_target_completion(
                raw_reply
            )
            valid_target_completion = False
        if not reply:
'''

if old_parse not in text:
    raise SystemExit("Expected response parser call was not found")
text = text.replace(old_parse, new_parse, 1)

old_validation = '''        valid_target_completion = False
        if (
            request.stage == "teaching"
            and completed_target_order is not None
            and current_target_order is not None
            and completed_target_order
            == current_target_order
            and not is_control_message
        ):
            valid_target_completion = True
'''

if old_validation not in text:
    raise SystemExit("Expected marker validation block was not found")
text = text.replace(old_validation, "", 1)

path.write_text(text, encoding="utf-8")
print("Teaching evaluation architecture applied")
