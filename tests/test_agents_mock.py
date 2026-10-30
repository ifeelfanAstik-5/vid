from unittest.mock import patch
from app.agents import story_analyst, director, scene_writer
from app.pipeline.state import PipelineState


@patch("app.agents.story_analyst.llm_pro")
def test_story_analyst(mock_llm):
    mock_llm.return_value = """{
      "title": "The Forest Star",
      "genre": "fantasy",
      "overall_tone": "whimsical",
      "characters": [{"name": "Pip", "role": "protagonist", "personality_traits": ["brave"], "physical_description": "A glowing firefly", "voice_profile": "gentle"}],
      "chapter_summaries": ["Pip awakens the forest"],
      "key_locations": ["Whispering Woods"],
      "themes": ["hope", "light"],
      "target_audience": "children"
    }"""

    state = {"raw_text": "Pip the firefly flew."}
    res = story_analyst.run(state)
    assert "story_bible" in res
    assert res["story_bible"]["title"] == "The Forest Star"
    assert len(res["story_bible"]["characters"]) == 1


@patch("app.agents.director.llm_pro")
def test_director(mock_llm):
    mock_llm.return_value = """[
      {
        "scene_id": "scene_001",
        "title": "Introduction",
        "story_excerpt": "Pip the firefly flew.",
        "emotional_beat": "wonder",
        "key_characters": ["Pip"],
        "location": "Forest",
        "estimated_duration_sec": 10,
        "narrative_importance": "critical"
      }
    ]"""

    state = {
        "story_bible": {"title": "Test"},
        "raw_text": "Pip the firefly flew."
    }
    res = director.run(state)
    assert "scene_plan" in res
    assert len(res["scene_plan"]) == 1
    assert res["scene_plan"][0]["scene_id"] == "scene_001"
