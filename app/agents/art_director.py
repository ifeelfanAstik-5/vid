"""Art Director Agent — Gemini 2.5 Flash.

Translates the VisualScript for the current scene into a complete Imagen 3
image prompt that includes:
  - Style preamble (2D watercolor storybook)
  - Shot description from the VisualScript
  - Character visual anchors for every character present
  - Emotional lighting note derived from the emotional_beat
"""
import json
from app.agents import llm_flash
from app.pipeline.state import PipelineState

STYLE_PREAMBLE = (
    "2D children's storybook illustration, soft watercolor painting, "
    "warm golden-hour palette, gentle linework, cinematic 16:9 widescreen "
    "composition, highly detailed background, storybook art style,"
)

NEGATIVE_PROMPT = (
    "3D render, CGI, photorealistic, photograph, dark, violent, scary, "
    "adult content, text, watermark, signature, blurry, low quality, "
    "extra limbs, malformed"
)

EMOTIONAL_LIGHTING = {
    "joy":       "bright warm sunlight, cheerful soft shadows,",
    "wonder":    "magical golden glow, soft sparkles, ethereal light,",
    "tension":   "dramatic side lighting, cool shadows, overcast sky,",
    "melancholy": "muted cool tones, soft diffused light, gentle mist,",
    "action":    "dynamic diagonal lighting, high contrast,",
    "calm":      "soft diffused natural light, peaceful and serene,",
}

PROMPT_TEMPLATE = """\
You are an art director writing Imagen 3 image prompts for a 2D animated storybook film.
Given the scene details below, write a single detailed image prompt.

The prompt MUST:
1. Start with the style preamble provided.
2. Describe exactly what is in the scene (characters, setting, action).
3. Include the character visual anchors verbatim for each character present.
4. Include the lighting note for the emotional beat.
5. Be one continuous paragraph, no bullet points.

Style preamble: {style_preamble}
Emotional lighting: {lighting}
Shot description: {shot_description}
Characters present: {characters_present}
Character anchors:
{anchors_text}

Return ONLY valid JSON — no markdown, no commentary:
{{
  "scene_id": "{scene_id}",
  "prompt": "string — the complete Imagen 3 prompt",
  "negative_prompt": "{negative_prompt}",
  "aspect_ratio": "16:9"
}}
"""


def run(state: PipelineState) -> dict:
    idx = state.get("current_scene_index", 0)
    scene = state["scene_plan"][idx]
    script = state["visual_scripts"][-1]
    anchors = state.get("character_prompt_anchors", {})

    print(f"[ArtDirector] Crafting Imagen 3 prompt for {scene['scene_id']}...")

    lighting = EMOTIONAL_LIGHTING.get(scene["emotional_beat"], "soft natural light,")
    chars_present = scene.get("key_characters", [])
    anchors_text = "\n".join(
        f"  {name}: {anchors[name]}" for name in chars_present if name in anchors
    ) or "  (no specific characters)"

    prompt = PROMPT_TEMPLATE.format(
        style_preamble=STYLE_PREAMBLE,
        lighting=lighting,
        shot_description=script["shot_description"],
        characters_present=", ".join(chars_present) or "none specified",
        anchors_text=anchors_text,
        scene_id=scene["scene_id"],
        negative_prompt=NEGATIVE_PROMPT,
    )
    raw = llm_flash(prompt)
    image_prompt = json.loads(raw)

    existing = list(state.get("image_prompts", []))
    existing.append(image_prompt)
    return {"image_prompts": existing}
