"""Character Consistency Agent — Gemini 2.5 Pro (initial) / Flash (incremental).

Maintains a dictionary of character -> canonical image-prompt fragment so that
Imagen 3 produces visually consistent characters across every scene.

This node also acts as the loop gate:
  - Before the first scene (current_scene_index == 0): builds the full anchor map.
  - After each scene: checks for new characters, updates anchors if needed,
    then increments current_scene_index.

The conditional edge on this node routes to scene_writer or subtitle_generator.
"""
import json
from app.agents import llm_pro, llm_flash
from app.pipeline.state import PipelineState

INITIAL_PROMPT = """\
You are an art director for a 2D watercolor storybook animated film.
For each character in the story bible, create a concise but complete
visual descriptor to be prepended to every Imagen 3 image prompt.

The descriptor must lock in: approximate age, gender expression, hair (colour, length, style),
eye colour, skin tone, and signature clothing/accessories.
Always end with: "2D watercolor storybook illustration style, consistent character design"

Return ONLY valid JSON — no markdown, no commentary:
{{
  "character_name": "descriptor string",
  ...
}}

Characters:
{characters}
"""

UPDATE_PROMPT = """\
You are maintaining character visual consistency for an animated storybook film.
A new scene features these characters: {new_characters}

Some may not yet have a visual descriptor. For any character NOT in the existing anchors,
create one following the same format as the existing ones.
Use the physical_description from the story bible to inform your descriptor.
Always end descriptors with: "2D watercolor storybook illustration style, consistent character design"

Story Bible characters for reference:
{story_bible_chars}

Existing anchors (DO NOT change these):
{existing_anchors}

Return ONLY valid JSON with ONLY the NEW anchors to add (omit existing ones):
{{
  "new_character_name": "descriptor string"
}}
If no new characters, return: {{}}
"""


def run(state: PipelineState) -> dict:
    anchors = dict(state.get("character_prompt_anchors", {}))

    # If anchors have not been initialized yet, build them from story_bible
    if not anchors:
        print("[CharConsistency] Building initial character anchors with Gemini 2.5 Pro...")
        chars = state["story_bible"]["characters"]
        prompt = INITIAL_PROMPT.format(characters=json.dumps(chars, indent=2))
        raw = llm_pro(prompt)
        anchors = json.loads(raw)
        print(f"[CharConsistency] Created {len(anchors)} character anchors.")
        return {"character_prompt_anchors": anchors}

    # Subsequent loop iterations: a scene has just finished
    visual_scripts = state.get("visual_scripts", [])
    if not visual_scripts:
        return {"character_prompt_anchors": anchors}

    last_script = visual_scripts[-1]
    idx = state.get("current_scene_index", 0)
    scene_plan = state.get("scene_plan", [])

    scene_chars = scene_plan[idx].get("key_characters", []) if idx < len(scene_plan) else []
    new_chars = [c for c in scene_chars if c not in anchors]

    if new_chars:
        print(f"[CharConsistency] New characters detected: {new_chars}. Updating anchors...")
        prompt = UPDATE_PROMPT.format(
            new_characters=json.dumps(new_chars),
            story_bible_chars=json.dumps(state["story_bible"]["characters"], indent=2),
            existing_anchors=json.dumps(anchors, indent=2),
        )
        raw = llm_flash(prompt)
        new_anchors = json.loads(raw)
        anchors.update(new_anchors)

    completed = list(state.get("completed_scene_ids", []))
    completed.append(last_script["scene_id"])
    next_idx = idx + 1
    print(f"[CharConsistency] Scene {last_script['scene_id']} complete. "
          f"Index {idx} -> {next_idx} of {len(scene_plan)}.")

    return {
        "character_prompt_anchors": anchors,
        "current_scene_index": next_idx,
        "completed_scene_ids": completed,
    }
