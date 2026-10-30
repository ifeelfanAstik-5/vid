"""Sound Designer Agent — Gemini 2.5 Flash.

Generates a music prompt for Lyria 3 and mix notes for the editor.
Does NOT call any audio API — that is done by audio_generator (tool).
This agent only produces the AudioAssets stub (without the local path).
"""
import json
from app.agents import llm_flash
from app.pipeline.state import PipelineState, AudioAssets

PROMPT_TEMPLATE = """\
You are a sound designer for a 2D animated storybook film.
Design the audio for this scene.

Scene details:
- Emotional beat: {emotional_beat}
- Location: {location}
- Mood note from screenwriter: {mood_note}
- Scene duration: {duration} seconds

Rules for music_prompt:
- Write a Lyria 3 music generation prompt for a ~30-second loopable background music clip.
- Match the emotional beat perfectly.
- Style: orchestral, gentle, storybook feel. No lyrics. Suitable for children.
- Be specific: instruments, tempo, dynamics.

Return ONLY valid JSON — no markdown, no commentary:
{{
  "scene_id": "{scene_id}",
  "music_prompt": "string — Lyria 3 prompt for the background music",
  "mix_notes": "string — brief mixing instruction for the editor (e.g. 'fade in over 2s, keep at 25% during any narration')"
}}
"""


def run(state: PipelineState) -> dict:
    idx = state.get("current_scene_index", 0)
    scene = state["scene_plan"][idx]
    script = state["visual_scripts"][-1]

    print(f"[SoundDesigner] Designing audio for {scene['scene_id']}...")

    prompt = PROMPT_TEMPLATE.format(
        emotional_beat=scene["emotional_beat"],
        location=scene["location"],
        mood_note=script.get("mood_note", ""),
        duration=scene["estimated_duration_sec"],
        scene_id=scene["scene_id"],
    )
    raw = llm_flash(prompt)
    stub = json.loads(raw)
    stub["music_local_path"] = None   # filled in by audio_generator tool

    existing = list(state.get("audio_assets", []))
    existing.append(stub)
    return {"audio_assets": existing}
