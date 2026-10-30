from __future__ import annotations

from typing import Optional
from typing_extensions import TypedDict


class Character(TypedDict):
    name: str
    role: str                       # "protagonist" | "antagonist" | "supporting"
    personality_traits: list[str]
    physical_description: str       # seed text for image prompt anchors
    voice_profile: str              # e.g. "warm, elderly male narrator"


class StoryBible(TypedDict):
    title: str
    genre: str
    overall_tone: str
    characters: list[Character]
    chapter_summaries: list[str]
    key_locations: list[str]
    themes: list[str]
    target_audience: str


class ScenePlan(TypedDict):
    scene_id: str                   # "scene_001", "scene_002", ...
    title: str
    story_excerpt: str
    emotional_beat: str             # "tension"|"joy"|"melancholy"|"action"|"wonder"
    key_characters: list[str]
    location: str
    estimated_duration_sec: int
    narrative_importance: str       # "critical"|"transitional"|"atmospheric"


class DialogueLine(TypedDict):
    character: str                  # "NARRATOR" or character name
    line: str
    emotion: str


class VisualScript(TypedDict):
    scene_id: str
    shot_description: str           # what the viewer sees
    dialogue: list[DialogueLine]
    action_beats: list[str]         # movement cues
    motion_prompt: str              # 1-sentence motion description for Veo 2
    mood_note: str                  # for the sound designer
    transition_in: str              # "fade_in" | "cut" | "dissolve"
    transition_out: str


class ImagePrompt(TypedDict):
    scene_id: str
    prompt: str                     # full Imagen 3 prompt (style + anchors + scene)
    negative_prompt: str
    aspect_ratio: str               # always "16:9"


class AudioAssets(TypedDict):
    scene_id: str
    music_prompt: str
    music_local_path: Optional[str]
    mix_notes: str                  # e.g. "fade in over 2s, 30% during dialogue"


class PipelineState(TypedDict):
    # -- Input ------------------------------------------------------
    run_id: str
    input_file_path: str
    input_format: str               # "pdf" | "txt" | "docx"

    # -- Global stage outputs ----------------------------------------
    raw_text: str
    story_bible: Optional[StoryBible]
    scene_plan: list[ScenePlan]
    character_prompt_anchors: dict  # name -> prompt fragment string

    # -- Per-scene outputs (grows as loop iterates) ------------------
    visual_scripts: list[VisualScript]
    image_prompts: list[ImagePrompt]
    generated_image_paths: list[str]
    video_clip_paths: list[str]
    audio_assets: list[AudioAssets]

    # -- Assembly outputs --------------------------------------------
    subtitle_srt_path: Optional[str]
    final_video_path: Optional[str]

    # -- Loop control ------------------------------------------------
    current_scene_index: int
    completed_scene_ids: list[str]

    # -- Status ------------------------------------------------------
    pipeline_status: str            # "running" | "completed" | "failed"
    error_log: list[str]
