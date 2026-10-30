"""Scene Writer Agent — Gemini 2.5 Flash.

Writes a detailed VisualScript for the current scene: what the viewer sees,
dialogue lines with character and emotion, action beats, and a
one-sentence motion_prompt for Veo 2.

Note: does NOT increment current_scene_index — that is done by char_consistency
after it has updated the character anchors.
"""
import json
from app.agents import llm_flash
from app.pipeline.state import PipelineState

PROMPT_TEMPLATE = """\
You are a screenwriter adapting a scene for a 2D animated storybook film.
Write a detailed visual production script for this scene.

Scene details:
{scene_plan}

Story Bible (characters & tone):
{story_bible}

Return ONLY valid JSON — no markdown, no commentary:
{{
  "scene_id": "{scene_id}",
  "shot_description": "string — a single vivid paragraph describing exactly what the viewer sees",
  "dialogue": [
    {{
      "character": "NARRATOR or character name",
      "line": "string — the spoken line",
      "emotion": "string — delivery emotion e.g. excited, whispered, sorrowful"
    }}
  ],
  "action_beats": ["string — brief movement descriptions, e.g. 'the door slowly creaks open'"],
  "motion_prompt": "string — ONE sentence describing the primary camera/subject motion for the video animator, e.g. 'A slow pan across a misty forest as golden fireflies rise upward'",
  "mood_note": "string — mood description for the sound designer",
  "transition_in": "fade_in|cut|dissolve",
  "transition_out": "fade_out|cut|dissolve"
}}
"""


def run(state: PipelineState) -> dict:
    idx = state["current_scene_index"]
    scene = state["scene_plan"][idx]
    print(f"[SceneWriter] Writing script for {scene['scene_id']}: \"{scene['title']}\"...")

    prompt = PROMPT_TEMPLATE.format(
        scene_plan=json.dumps(scene, indent=2),
        story_bible=json.dumps(state["story_bible"], indent=2),
        scene_id=scene["scene_id"],
    )
    raw_json = llm_flash(prompt)
    visual_script = json.loads(raw_json)

    existing = list(state.get("visual_scripts", []))
    existing.append(visual_script)
    return {"visual_scripts": existing}
