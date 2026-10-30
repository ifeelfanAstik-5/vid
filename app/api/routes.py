import os
import shutil
import uuid
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, HTTPException, Header, Depends
from fastapi.responses import FileResponse

from app.pipeline.runner import run_pipeline
from app.pipeline.cost_estimator import calculate_cost_estimate
from app.tools.endpoint_manager import get_endpoint_status, undeploy_endpoint_model
from app.tools import document_ingestor
from app.agents import story_analyst, director
from app.config import settings

router = APIRouter()
JOBS: dict[str, dict] = {}
DRAFTS: dict[str, dict] = {}

ALLOWED_FORMATS = {"pdf", "txt", "docx"}


def verify_access_token(x_access_token: Optional[str] = Header(None, alias="X-Access-Token")):
    """Security guardrail: protect video generation and GPU billing actions with studio access token."""
    if settings.studio_access_token and settings.studio_access_token.strip():
        if not x_access_token or x_access_token.strip() != settings.studio_access_token.strip():
            raise HTTPException(
                status_code=401,
                detail="Unauthorized: Valid Studio Access Token required to run generation or GPU operations."
            )


@router.get("/endpoint/status")
def endpoint_status():
    """Get Vertex AI Dedicated Endpoint deployment and model status (Publicly viewable)."""
    return get_endpoint_status()


@router.post("/endpoint/undeploy")
def endpoint_undeploy(_auth: None = Depends(verify_access_token)):
    """Undeploy model from the dedicated Vertex AI endpoint (Protected by token)."""
    res = undeploy_endpoint_model()
    if not res.get("success"):
        raise HTTPException(status_code=500, detail=res.get("error", "Failed to undeploy endpoint"))
    return res


@router.post("/estimate")
async def estimate_cost(
    file: Optional[UploadFile] = File(None),
    text_content: Optional[str] = Form(None),
    _auth: None = Depends(verify_access_token),
):
    """Phase 1: Ingest input story, plan scenes with Director agent, and compute cost estimate (Protected by token)."""
    draft_id = str(uuid.uuid4())
    draft_dir = os.path.join(settings.artifacts_dir, f"draft_{draft_id}")
    os.makedirs(draft_dir, exist_ok=True)

    if file and file.filename:
        filename = file.filename
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"
        if ext not in ALLOWED_FORMATS:
            raise HTTPException(status_code=400, detail=f"Unsupported format '{ext}'. Must be {ALLOWED_FORMATS}")
        save_path = os.path.join(draft_dir, f"input.{ext}")
        with open(save_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    elif text_content and text_content.strip():
        ext = "txt"
        save_path = os.path.join(draft_dir, "input.txt")
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(text_content.strip())
    else:
        raise HTTPException(status_code=400, detail="Either a story file or text content must be provided.")

    # 1. Ingest text
    raw_text = document_ingestor.run({"input_file_path": save_path, "input_format": ext})["raw_text"]
    if not raw_text:
        raise HTTPException(status_code=400, detail="Input file or text was empty.")

    # 2. Analyze story bible
    analyst_res = story_analyst.run({"raw_text": raw_text})
    story_bible = analyst_res["story_bible"]

    # 3. Direct scene plan (5 scenes x 6s = 30s)
    director_res = director.run({"story_bible": story_bible, "raw_text": raw_text})
    scenes = director_res["scene_plan"]

    # 4. Compute cost estimate
    cost_breakdown = calculate_cost_estimate(scenes, estimated_tokens=15000)

    # 5. Store draft for subsequent approval
    DRAFTS[draft_id] = {
        "draft_id": draft_id,
        "save_path": save_path,
        "ext": ext,
        "raw_text": raw_text,
        "story_bible": story_bible,
        "scenes": scenes,
        "cost_breakdown": cost_breakdown,
    }

    return {
        "draft_id": draft_id,
        "scenes": scenes,
        "cost_breakdown": cost_breakdown,
        "story_bible": story_bible,
    }


@router.post("/confirm/{draft_id}")
async def confirm_and_generate(
    draft_id: str,
    background_tasks: BackgroundTasks,
    _auth: None = Depends(verify_access_token),
):
    """Phase 2: User confirms the cost estimate. Enforces hard budget block before starting video pipeline."""
    if draft_id not in DRAFTS:
        raise HTTPException(status_code=404, detail="Draft not found or expired. Please re-run estimation.")

    draft = DRAFTS[draft_id]
    cost = draft["cost_breakdown"]

    if cost.get("is_hard_blocked"):
        raise HTTPException(
            status_code=400,
            detail=f"Budget Guardrail: Job exceeds hard limit of ${cost.get('hard_limit_usd'):.2f}. Generation blocked.",
        )

    run_id = str(uuid.uuid4())
    run_dir = os.path.join(settings.artifacts_dir, run_id)
    os.makedirs(run_dir, exist_ok=True)

    # Move/copy draft input file to run directory
    target_input = os.path.join(run_dir, f"input.{draft['ext']}")
    shutil.copyfile(draft["save_path"], target_input)

    JOBS[run_id] = {
        "status": "queued",
        "current_node": None,
        "final_video": None,
        "input_format": draft["ext"],
        "input_file": target_input,
        "artifacts_url": f"/artifacts/{run_id}",
        "story_bible": draft["story_bible"],
        "scene_plan": draft["scenes"],
        "character_anchors": {},
        "scenes": [],
        "cost_breakdown": cost,
    }

    background_tasks.add_task(
        run_pipeline,
        run_id,
        target_input,
        draft["ext"],
        JOBS,
        draft["story_bible"],
        draft["scenes"],
    )

    return {"run_id": run_id, "status": "queued", "cost_breakdown": cost}


@router.post("/generate")
async def generate(
    background_tasks: BackgroundTasks,
    file: Optional[UploadFile] = File(None),
    text_content: Optional[str] = Form(None),
    _auth: None = Depends(verify_access_token),
):
    """Legacy direct generate endpoint: estimates and starts immediately if within hard limit."""
    estimate_result = await estimate_cost(file=file, text_content=text_content)
    draft_id = estimate_result["draft_id"]
    return await confirm_and_generate(draft_id=draft_id, background_tasks=background_tasks)


@router.get("/status/{run_id}")
def status(run_id: str):
    if run_id not in JOBS:
        # Check if job exists on disk from prior run
        run_art_dir = os.path.join(settings.artifacts_dir, run_id)
        run_out_dir = os.path.join(settings.output_dir, run_id)
        if os.path.exists(run_art_dir) or os.path.exists(run_out_dir):
            final_disk = os.path.join(run_out_dir, "final.mp4")
            JOBS[run_id] = {
                "status": "completed" if os.path.exists(final_disk) else "running",
                "current_node": "editor" if os.path.exists(final_disk) else "starting",
                "final_video": final_disk if os.path.exists(final_disk) else None,
                "input_format": "txt",
                "input_file": os.path.join(run_art_dir, "input.txt"),
                "artifacts_url": f"/artifacts/{run_id}",
                "story_bible": None,
                "scene_plan": [],
                "character_anchors": {},
                "scenes": [],
            }
        else:
            raise HTTPException(status_code=404, detail="Job not found")

    job = JOBS[run_id]

    # Check for generated scene artifacts on disk to populate UI
    run_dir = os.path.join(settings.artifacts_dir, run_id)
    scenes_data = []
    if os.path.exists(run_dir):
        for item in sorted(os.listdir(run_dir)):
            item_path = os.path.join(run_dir, item)
            if os.path.isdir(item_path) and item.startswith("scene_"):
                keyframe = os.path.join(item_path, "keyframe.jpg")
                clip = os.path.join(item_path, "clip.mp4")
                mixed = os.path.join(item_path, "mixed.mp4")
                music = os.path.join(item_path, "music.mp3")

                scenes_data.append({
                    "scene_id": item,
                    "keyframe_url": f"/artifacts/{run_id}/{item}/keyframe.jpg" if os.path.exists(keyframe) else None,
                    "clip_url": f"/artifacts/{run_id}/{item}/clip.mp4" if os.path.exists(clip) else None,
                    "mixed_url": f"/artifacts/{run_id}/{item}/mixed.mp4" if os.path.exists(mixed) else None,
                    "music_url": f"/artifacts/{run_id}/{item}/music.mp3" if os.path.exists(music) else None,
                })

    final_video = job.get("final_video")
    out_video_disk = os.path.join(settings.output_dir, run_id, "final.mp4")
    if (not final_video or not os.path.exists(final_video)) and os.path.exists(out_video_disk):
        final_video = out_video_disk
        job["final_video"] = out_video_disk
        job["status"] = "completed"
        job["current_node"] = "editor"
        job["error"] = None

    final_video_url = None
    if final_video and os.path.exists(final_video):
        final_video_url = f"/output/{run_id}/final.mp4"

    return {
        "run_id": run_id,
        **job,
        "scenes": scenes_data,
        "final_video_url": final_video_url,
    }


@router.get("/download/{run_id}")
def download(run_id: str):
    job = JOBS.get(run_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    video_path = job.get("final_video")
    out_video_disk = os.path.join(settings.output_dir, run_id, "final.mp4")
    if (not video_path or not os.path.exists(video_path)) and os.path.exists(out_video_disk):
        video_path = out_video_disk
        job["final_video"] = out_video_disk
        job["status"] = "completed"

    if job.get("status") != "completed":
        raise HTTPException(status_code=400, detail=f"Not complete yet - current status: {job.get('status')}")

    if not video_path or not os.path.exists(video_path):
        raise HTTPException(status_code=500, detail="Output file missing on server")

    return FileResponse(
        video_path,
        media_type="video/mp4",
        filename=f"animated_{run_id[:8]}.mp4"
    )
