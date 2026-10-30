import os
import pytest
from unittest.mock import patch, MagicMock
from langgraph.checkpoint.sqlite import SqliteSaver
from app.pipeline.graph import build_graph
from app.pipeline.runner import make_initial_state


def test_pipeline_smoke_mocked(tmp_path):
    sample_file = tmp_path / "sample.txt"
    sample_file.write_text("Pip the lavender firefly woke up the ancient forest.", encoding="utf-8")

    initial = make_initial_state("smoke_test_run", str(sample_file), "txt")

    mock_analyst = {
        "title": "Story of Pip",
        "genre": "fantasy",
        "overall_tone": "gentle",
        "characters": [
            {
                "name": "Pip",
                "role": "protagonist",
                "personality_traits": ["gentle"],
                "physical_description": "Small firefly with soft lavender light",
                "voice_profile": "soft",
            }
        ],
        "chapter_summaries": ["A firefly wakes the forest"],
        "key_locations": ["Woods"],
        "themes": ["hope"],
        "target_audience": "children",
    }

    mock_scene = {
        "scene_id": "scene_001",
        "title": "First Light",
        "story_excerpt": "Pip woke the woods.",
        "emotional_beat": "wonder",
        "key_characters": ["Pip"],
        "location": "Woods",
        "estimated_duration_sec": 5,
        "narrative_importance": "critical",
    }

    mock_script = {
        "scene_id": "scene_001",
        "shot_description": "Pip hovers among leaves.",
        "dialogue": [{"character": "Pip", "line": "Wake up forest!", "emotion": "gentle"}],
        "action_beats": ["Pip flutters softly"],
        "motion_prompt": "A small firefly hovers near glowing leaves.",
        "mood_note": "wonder",
        "transition_in": "cut",
        "transition_out": "cut",
    }

    with patch("app.agents.story_analyst.llm_pro", return_value=__import__("json").dumps(mock_analyst)), \
         patch("app.agents.director.llm_pro", return_value=__import__("json").dumps([mock_scene])), \
         patch("app.agents.char_consistency.llm_pro", return_value='{"Pip": "small glowing lavender firefly"}'), \
         patch("app.agents.scene_writer.llm_flash", return_value=__import__("json").dumps(mock_script)), \
         patch("app.agents.art_director.llm_flash", return_value='{"scene_id": "scene_001", "prompt": "Pip watercolor", "negative_prompt": "", "aspect_ratio": "16:9"}'), \
         patch("app.agents.sound_designer.llm_flash", return_value='{"scene_id": "scene_001", "music_prompt": "gentle harp", "mix_notes": "soft"}'), \
         patch("app.tools.image_generator.run") as mock_img, \
         patch("app.tools.video_animator.run") as mock_anim, \
         patch("app.tools.audio_generator.run") as mock_aud, \
         patch("app.tools.editor.run") as mock_edit:

        mock_img.side_effect = lambda state: {"generated_image_paths": state.get("generated_image_paths", []) + ["fake_keyframe.jpg"]}
        mock_anim.side_effect = lambda state: {"video_clip_paths": state.get("video_clip_paths", []) + ["fake_clip.mp4"]}
        mock_aud.side_effect = lambda state: {"audio_assets": state.get("audio_assets", [])}
        mock_edit.side_effect = lambda state: {"final_video_path": "fake_final.mp4", "pipeline_status": "completed"}

        db_path = str(tmp_path / "test_checkpoints.sqlite")
        with SqliteSaver.from_conn_string(db_path) as checkpointer:
            graph = build_graph(checkpointer)
            config = {"configurable": {"thread_id": "test_thread"}}

            final_state = graph.invoke(initial, config)

            assert final_state["pipeline_status"] == "completed"
            assert final_state["final_video_path"] == "fake_final.mp4"
            assert len(final_state["scene_plan"]) == 1
            assert os.path.exists(final_state["subtitle_srt_path"])
