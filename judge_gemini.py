"""Gemini backend for HingeAuto judging.

Sends profile screenshots to a Gemini vision model with a forced
function call to extract a structured Decision. Same interface as `judge.py`.

Usage: set JUDGE_BACKEND = "gemini" in config.py, add GEMINI_API_KEY to .env.
"""

import os
import time

from dotenv import load_dotenv

from google import genai
from google.genai import types

import config
from judge_common import (
    DECIDE_INPUT_SCHEMA,
    Decision,
    build_system_prompt,
    enforce_premade_verbatim,
)


DECIDE_DECLARATION = types.FunctionDeclaration(
    name="submit_decision",
    description="Submit a like/skip decision for this Hinge profile.",
    parameters=DECIDE_INPUT_SCHEMA,
)


def _image_part(png_bytes: bytes) -> types.Part:
    return types.Part(
        inline_data=types.Blob(mime_type="image/png", data=png_bytes)
    )


def judge(frames: list[bytes]) -> Decision:
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set. Add it to .env or export it.")

    client = genai.Client(api_key=api_key)
    model = getattr(config, "GEMINI_MODEL", "gemini-3.7-flash")

    # Gemini 3.x exposes tunable thinking levels. Map config.EFFORT onto
    # them so this backend honours the same knob as the Anthropic one,
    # which reads EFFORT via output_config. ThinkingLevel also accepts
    # MINIMAL; EFFORT does not currently expose it.
    # include_thoughts surfaces the model's thought summaries as parts
    # with .thought set, so the run can show its reasoning live. Without
    # it the model still thinks, but the trace is discarded server-side.
    thinking = types.ThinkingConfig(include_thoughts=True)
    level = str(getattr(config, "EFFORT", "") or "").strip().upper()
    if level in ("MINIMAL", "LOW", "MEDIUM", "HIGH"):
        thinking = types.ThinkingConfig(
            thinking_level=level, include_thoughts=True
        )

    parts = [_image_part(f) for f in frames]
    parts.append(types.Part(
        text=(
            f"Above are {len(frames)} screenshots of one Hinge profile, in "
            "order from top to bottom. Decide whether to like or skip."
        )
    ))

    gen_config = types.GenerateContentConfig(
        system_instruction=build_system_prompt(),
        temperature=0.2,
        # Thought summaries draw on this same budget, so this is well
        # above the ~2000 the tool call alone needs. Too low and the
        # response truncates mid-thought and never emits the call.
        max_output_tokens=8000,
        thinking_config=thinking,
        tools=[types.Tool(function_declarations=[DECIDE_DECLARATION])],
    )

    # gemini-3.7-flash is new and capacity-constrained: 503 UNAVAILABLE
    # ("experiencing high demand") is common and transient. Retry it here
    # with patient backoff rather than letting it bubble up — main.py's
    # retry is 5s/10s, too short for a capacity spike, and once its three
    # attempts are spent it force-skips the profile, burning it from the
    # queue with no real decision.
    last_exc = None
    for delay in (0, 5, 15, 35):
        if delay:
            time.sleep(delay)
        try:
            response = client.models.generate_content(
                model=model,
                contents=types.Content(role="user", parts=parts),
                config=gen_config,
            )
            break
        except Exception as e:
            text = f"{type(e).__name__}: {e}"
            transient = any(s in text for s in (
                "503", "UNAVAILABLE", "high demand",
                "500", "INTERNAL", "504", "DEADLINE_EXCEEDED",
            ))
            if not transient:
                raise
            last_exc = e
            print(f"[gemini] transient {type(e).__name__}, retrying...")
    else:
        raise RuntimeError(
            f"Gemini unavailable after 4 attempts: {last_exc}"
        )

    if not response.candidates:
        raise RuntimeError(f"No candidates. feedback={response.prompt_feedback}")

    candidate = response.candidates[0]
    if not candidate.content or not candidate.content.parts:
        raise RuntimeError(f"No content. finish_reason={candidate.finish_reason}")

    # Capture token usage from the response
    usage = {}
    if response.usage_metadata:
        usage = {
            "input_tokens": response.usage_metadata.prompt_token_count or 0,
            "output_tokens": response.usage_metadata.candidates_token_count or 0,
            "total_tokens": response.usage_metadata.total_token_count or 0,
        }

    thoughts = [
        part.text for part in candidate.content.parts
        if getattr(part, "thought", False) and part.text
    ]
    for part in candidate.content.parts:
        if part.function_call and part.function_call.name == "submit_decision":
            args = {k: v for k, v in part.function_call.args.items()}
            decision = Decision(
                **args, usage=usage, thinking="\n".join(thoughts).strip()
            )
            enforce_premade_verbatim(decision)
            return decision

    raise RuntimeError(
        f"No submit_decision call. finish_reason={candidate.finish_reason}"
    )
