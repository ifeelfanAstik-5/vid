"""Story Analyst Agent - Gemini.

Reads the full raw text and extracts a structured StoryBible containing
characters, tone, themes, chapter summaries, and key locations.
"""
import json
from app.agents import llm_pro
from app.pipeline.state import PipelineState

PROMPT_TEMPLATE = """\
You are a literary analyst specialising in visual storytelling.
Read the following story carefully and extract a structured story bible.

Return ONLY valid JSON - no markdown fences, no commentary - matching this exact schema:
{{
  "title": "string",
  "genre": "string (e.g. fantasy, thriller, children, adventure)",
  "overall_tone": "string (e.g. whimsical and hopeful, dark and tense)",
  "characters": [
    {{
      "name": "string",
      "role": "protagonist|antagonist|supporting",
      "personality_traits": ["string"],
      "physical_description": "string - detailed visual description for image generation (hair, eyes, skin, age, clothing, build)",
      "voice_profile": "string - speaking style for subtitles (e.g. warm elderly female, shy young boy)"
    }}
  ],
  "chapter_summaries": ["string"],
  "key_locations": ["string"],
  "themes": ["string"],
  "target_audience": "string (e.g. children 6-10, young adult, general adult)"
}}

Story:
---
{raw_text}
"""


def run(state: PipelineState) -> dict:
    if state.get("story_bible"):
        print("[StoryAnalyst] Using pre-analyzed story bible.")
        return {"story_bible": state["story_bible"]}

    print("[StoryAnalyst] Analysing story with Gemini...")
    prompt = PROMPT_TEMPLATE.format(raw_text=state["raw_text"])
    raw_json = llm_pro(prompt)
    story_bible = json.loads(raw_json)
    print(f"[StoryAnalyst] Found {len(story_bible.get('characters', []))} characters, "
          f"{len(story_bible.get('chapter_summaries', []))} chapters.")
    return {"story_bible": story_bible}
