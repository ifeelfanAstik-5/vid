"""Director Agent - Gemini.

Breaks the story into a sequenced list of ScenePlans with pacing,
emotional beats, duration hints, and narrative importance ratings.
"""
import json
from app.agents import llm_pro
from app.config import settings
from app.pipeline.state import PipelineState

PROMPT_TEMPLATE = """\
You are a film director adapting a written story into an animated short film.
Using the story bible and the full text, break the story into scenes for animation.

Rules:
- You MUST create EXACTLY {max_scenes} scenes (no more, no less). The total video will be {target_duration} seconds.
- Each scene should correspond to a meaningful story beat.
- Each scene's estimated_duration_sec must be {scene_duration} seconds.
- Assign "critical" importance to turning points, "transitional" to connector scenes,
  "atmospheric" to mood/world-building scenes.
- story_excerpt must be the actual text from the story that this scene covers (verbatim or paraphrased closely).

Return ONLY valid JSON - no markdown, no commentary - as an array with exactly {max_scenes} items:
[
  {{
    "scene_id": "scene_001",
    "title": "string",
    "story_excerpt": "string",
    "emotional_beat": "tension|joy|melancholy|action|wonder|calm",
    "key_characters": ["character name"],
    "location": "string",
    "estimated_duration_sec": {scene_duration},
    "narrative_importance": "critical|transitional|atmospheric"
  }}
]

Story Bible:
{story_bible}

Full Story Text:
---
{raw_text}
"""


def run(state: PipelineState) -> dict:
    if state.get("scene_plan"):
        print(f"[Director] Using pre-approved scene plan ({len(state['scene_plan'])} scenes).")
        return {"scene_plan": state["scene_plan"]}

    print("[Director] Breaking story into scenes with Gemini...")
    prompt = PROMPT_TEMPLATE.format(
        max_scenes=settings.max_scenes,
        scene_duration=settings.scene_duration_sec,
        target_duration=settings.max_scenes * settings.scene_duration_sec,
        story_bible=json.dumps(state["story_bible"], indent=2),
        raw_text=state["raw_text"],
    )
    raw_json = llm_pro(prompt)
    scene_plan = json.loads(raw_json)
    # Strictly cap at max_scenes (e.g. 5 scenes for 30 seconds)
    if len(scene_plan) > settings.max_scenes:
        print(f"[Director] Capping scenes from {len(scene_plan)} to {settings.max_scenes}.")
        scene_plan = scene_plan[:settings.max_scenes]
    # Ensure scene_ids are zero-padded consistently and duration matches Veo supported duration
    for i, scene in enumerate(scene_plan):
        scene["scene_id"] = f"scene_{i + 1:03d}"
        scene["estimated_duration_sec"] = settings.scene_duration_sec
    print(f"[Director] Created {len(scene_plan)} scenes, "
          f"total ~{sum(s['estimated_duration_sec'] for s in scene_plan)}s.")
    return {"scene_plan": scene_plan}
