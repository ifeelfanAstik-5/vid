import os
import time
import ffmpeg
from google import genai
from google.genai import types

from app.config import settings
from app.pipeline.state import PipelineState


def _create_ken_burns_motion_clip(img_path: str, out_path: str, duration: int):
    """Create a smooth 1080p animated Ken Burns motion clip from the keyframe image using FFmpeg."""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    total_frames = duration * 25
    
    (
        ffmpeg.input(img_path, loop=1, t=duration)
        .filter(
            "zoompan",
            z="min(zoom+0.0015,1.25)",
            x="iw/2-(iw/zoom/2)",
            y="ih/2-(ih/zoom/2)",
            d=total_frames,
            s=f"{settings.target_width}x{settings.target_height}",
            fps=25
        )
        .output(out_path, vcodec="libx264", pix_fmt="yuv420p", t=duration, preset="fast")
        .overwrite_output()
        .run(quiet=True)
    )
    print(f"[VideoAnimator] Generated fallback motion animation clip at {out_path}")


def run(state: PipelineState) -> dict:
    script = state["visual_scripts"][-1]
    scene_id = script["scene_id"]
    img_path = state["generated_image_paths"][-1]
    idx = state.get("current_scene_index", 0)
    plan = state["scene_plan"][idx]
    out_path = os.path.join(settings.artifacts_dir, state["run_id"], scene_id, "clip.mp4")

    existing_clips = list(state.get("video_clip_paths", []))

    # Cache hit check
    if os.path.exists(out_path):
        print(f"[VideoAnimator] Cache hit for {scene_id} clip: {out_path}")
        return {"video_clip_paths": existing_clips + [out_path]}

    # Veo 3.1 supports [4, 6, 8] seconds
    target_duration = 6
    print(f"[VideoAnimator] Generating real AI video for {scene_id} via {settings.veo_model} (duration={target_duration}s)...")

    # Generate real AI video via Veo 3.1
    try:
        client = genai.Client(
            vertexai=True,
            project=settings.gcp_project_id,
            location=settings.gcp_location,
        )

        with open(img_path, "rb") as f:
            img_bytes = f.read()

        src_image = types.Image(image_bytes=img_bytes, mime_type="image/jpeg")

        operation = client.models.generate_videos(
            model=settings.veo_model,
            prompt=script.get("motion_prompt") or "Cinematic slow camera pan across the storybook scene with gentle motion",
            image=src_image,
            config=dict(
                aspect_ratio="16:9",
                duration_seconds=target_duration,
            ),
        )

        print(f"[VideoAnimator] Polling Veo 3.1 operation {operation.name}...")
        while not operation.done:
            time.sleep(10)
            operation = client.operations.get(operation)

        if operation.response and operation.response.generated_videos:
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            operation.response.generated_videos[0].video.save(out_path)
            print(f"[VideoAnimator] SUCCESS! Real Veo 3.1 video clip saved to {out_path}")
            return {"video_clip_paths": existing_clips + [out_path]}
        elif operation.error:
            print(f"[VideoAnimator] Veo 3.1 operation returned error: {operation.error}")
    except Exception as e:
        print(f"[VideoAnimator] Veo 3.1 call encountered an exception: {e}")

    # Fallback if needed
    _create_ken_burns_motion_clip(img_path, out_path, target_duration)
    return {"video_clip_paths": existing_clips + [out_path]}
