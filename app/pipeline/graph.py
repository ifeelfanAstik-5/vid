from typing import Literal
from langgraph.graph import StateGraph, START, END

from app.pipeline.state import PipelineState
from app.tools import (
    document_ingestor,
    image_generator,
    video_animator,
    audio_generator,
    subtitle_generator,
    editor,
)
from app.agents import (
    story_analyst,
    director,
    scene_writer,
    char_consistency,
    art_director,
    sound_designer,
)


def _scene_loop_router(state: PipelineState) -> Literal["scene_writer", "subtitle_generator"]:
    """Route back to scene_writer if more scenes remain, else proceed to assembly."""
    idx = state.get("current_scene_index", 0)
    total = len(state.get("scene_plan", []))
    if idx < total:
        return "scene_writer"
    return "subtitle_generator"


def build_graph(checkpointer):
    b = StateGraph(PipelineState)

    # -- Register nodes ------------------------------------------
    b.add_node("document_ingestor",  document_ingestor.run)
    b.add_node("story_analyst",      story_analyst.run)
    b.add_node("director",           director.run)
    b.add_node("char_consistency",   char_consistency.run)   # ← acts as loop-gate
    b.add_node("scene_writer",       scene_writer.run)
    b.add_node("art_director",       art_director.run)
    b.add_node("image_generator",    image_generator.run)
    b.add_node("video_animator",     video_animator.run)
    b.add_node("sound_designer",     sound_designer.run)
    b.add_node("audio_generator",    audio_generator.run)
    b.add_node("subtitle_generator", subtitle_generator.run)
    b.add_node("editor",             editor.run)

    # -- Pre-loop linear edges -----------------------------------
    b.add_edge(START,               "document_ingestor")
    b.add_edge("document_ingestor", "story_analyst")
    b.add_edge("story_analyst",     "director")
    b.add_edge("director",          "char_consistency")

    # -- Conditional edge — the scene loop ----------------------
    b.add_conditional_edges(
        "char_consistency",
        _scene_loop_router,
        {"scene_writer": "scene_writer", "subtitle_generator": "subtitle_generator"},
    )

    # -- Per-scene chain -----------------------------------------
    b.add_edge("scene_writer",    "art_director")
    b.add_edge("art_director",    "image_generator")
    b.add_edge("image_generator", "video_animator")
    b.add_edge("video_animator",  "sound_designer")
    b.add_edge("sound_designer",  "audio_generator")
    b.add_edge("audio_generator", "char_consistency")    # ← loop back

    # -- Post-loop assembly --------------------------------------
    b.add_edge("subtitle_generator", "editor")
    b.add_edge("editor",             END)

    return b.compile(checkpointer=checkpointer)
