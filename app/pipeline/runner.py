import asyncio
from typing import Optional
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from app.pipeline.graph import build_graph
from app.pipeline.state import PipelineState


def make_initial_state(
    run_id: str,
    input_path: str,
    fmt: str,
    story_bible: Optional[dict] = None,
    scene_plan: Optional[list] = None,
) -> PipelineState:
    return PipelineState(
        run_id=run_id,
        input_file_path=input_path,
        input_format=fmt,
        raw_text="",
        story_bible=story_bible,
        scene_plan=scene_plan or [],
        character_prompt_anchors={},
        visual_scripts=[],
        image_prompts=[],
        generated_image_paths=[],
        video_clip_paths=[],
        audio_assets=[],
        subtitle_srt_path=None,
        final_video_path=None,
        current_scene_index=0,
        completed_scene_ids=[],
        pipeline_status="running",
        error_log=[],
    )


async def run_pipeline(
    run_id: str,
    input_path: str,
    fmt: str,
    job_registry: dict,
    story_bible: Optional[dict] = None,
    scene_plan: Optional[list] = None,
):
    """Async pipeline runner. Updates job_registry in-place for status polling."""
    job_registry[run_id].update({"status": "running", "current_node": "starting"})
    try:
        # Use AsyncSqliteSaver for async astream / ainvoke execution
        async with AsyncSqliteSaver.from_conn_string("checkpoints.sqlite") as checkpointer:
            graph = build_graph(checkpointer)
            config = {"configurable": {"thread_id": run_id}}
            initial = make_initial_state(run_id, input_path, fmt, story_bible, scene_plan)

            # Stream updates from graph execution asynchronously
            async for event in graph.astream(initial, config, stream_mode="updates"):
                node_name = next(iter(event))
                job_registry[run_id]["current_node"] = node_name
                print(f"[{run_id[:8]}] Completed stage: {node_name}")

            final_snapshot = await graph.aget_state(config)
            final = final_snapshot.values
            job_registry[run_id].update({
                "status": "completed",
                "current_node": "done",
                "final_video": final.get("final_video_path"),
            })
    except Exception as exc:
        print(f"[{run_id[:8]}] Pipeline failed: {exc}")
        job_registry[run_id].update({"status": "failed", "error": str(exc)})
        raise
