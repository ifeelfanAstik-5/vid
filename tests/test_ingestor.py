import os
import pytest
from app.tools import document_ingestor
from app.pipeline.state import PipelineState


def test_document_ingestor_txt(tmp_path):
    txt_file = tmp_path / "story.txt"
    txt_file.write_text("Once upon a time in a faraway forest.", encoding="utf-8")

    state: PipelineState = {
        "run_id": "test_run",
        "input_file_path": str(txt_file),
        "input_format": "txt",
        "raw_text": "",
        "story_bible": None,
        "scene_plan": [],
        "character_prompt_anchors": {},
        "visual_scripts": [],
        "image_prompts": [],
        "generated_image_paths": [],
        "video_clip_paths": [],
        "audio_assets": [],
        "subtitle_srt_path": None,
        "final_video_path": None,
        "current_scene_index": 0,
        "completed_scene_ids": [],
        "pipeline_status": "running",
        "error_log": [],
    }

    result = document_ingestor.run(state)
    assert "raw_text" in result
    assert result["raw_text"] == "Once upon a time in a faraway forest."
