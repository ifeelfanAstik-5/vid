import os
import subprocess
import ffmpeg
from app.config import settings
from app.pipeline.state import PipelineState


def has_audio_stream(filepath: str) -> bool:
    """Check if a video clip contains its own native audio stream (e.g. Veo AI sound)."""
    try:
        cmd = ["ffprobe", "-v", "error", "-show_streams", "-select_streams", "a", filepath]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return bool(res.stdout.strip())
    except Exception:
        return False


def run(state: PipelineState) -> dict:
    run_id = state["run_id"]
    out_dir = os.path.join(settings.output_dir, run_id)
    os.makedirs(out_dir, exist_ok=True)

    print(f"[Editor] Starting video assembly for run {run_id}...")

    # Stage 1: Mix each clip. Prioritize native AI audio from Veo clips!
    mixed_clips = []
    for clip_path, audio, plan in zip(
        state.get("video_clip_paths", []),
        state.get("audio_assets", []),
        state.get("scene_plan", []),
    ):
        duration = plan.get("estimated_duration_sec", settings.scene_duration_sec)
        out_clip = clip_path.replace("clip.mp4", "mixed.mp4")

        has_native_audio = has_audio_stream(clip_path)

        if has_native_audio:
            # 1. Veo clip already has rich native AI sound effects/audio -> Use it directly!
            print(f"[Editor] Preserving native Veo AI audio for {os.path.basename(os.path.dirname(clip_path))}")
            inp = ffmpeg.input(clip_path, t=duration)
            v = inp.video
            a = inp.audio.filter("aformat", sample_fmts="fltp", sample_rates=48000, channel_layouts="stereo")
        else:
            # 2. Fallback motion clip without audio -> Use ambient background audio bed
            v = ffmpeg.input(clip_path, loop=1, t=duration).video
            music_path = audio.get("music_local_path")
            if music_path and os.path.exists(music_path):
                a = (
                    ffmpeg.input(music_path, loop=1, t=duration)
                    .audio
                    .filter("volume", 0.45)
                    .filter("aformat", sample_fmts="fltp", sample_rates=48000, channel_layouts="stereo")
                )
            else:
                a = ffmpeg.input("anullsrc=r=48000:cl=stereo", f="lavfi", t=duration).audio

        (
            ffmpeg.output(
                v, a, out_clip,
                vcodec="libx264", acodec="aac", audio_bitrate="256k",
                t=duration, crf=20, preset="fast"
            )
            .overwrite_output()
            .run(quiet=True)
        )
        mixed_clips.append(out_clip)

    # Stage 2: Concat clips with unified stream specs
    concat_txt = os.path.join(out_dir, "concat.txt")
    with open(concat_txt, "w", encoding="utf-8") as f:
        for c in mixed_clips:
            clean_path = os.path.abspath(c).replace("\\", "/")
            f.write(f"file '{clean_path}'\n")

    concat_mp4 = os.path.join(out_dir, "concat.mp4")
    (
        ffmpeg.input(concat_txt, format="concat", safe=0)
        .output(concat_mp4, c="copy")
        .overwrite_output()
        .run(quiet=True)
    )

    # Stage 3: Scale to 1080p and burn in subtitles if srt exists
    final_path = os.path.join(out_dir, "final.mp4")
    srt_path = state.get("subtitle_srt_path")

    # Use relative forward-slash path to avoid Windows drive colon escaping issues (D\:)
    has_subtitles = False
    if srt_path and os.path.exists(srt_path) and os.path.getsize(srt_path) > 0:
        rel_srt = os.path.relpath(srt_path).replace("\\", "/")
        try:
            stream = ffmpeg.input(concat_mp4)
            v_stream = stream.video.filter("scale", settings.target_width, settings.target_height)
            v_stream = v_stream.filter(
                "subtitles",
                rel_srt,
                force_style=(
                    "FontName=Arial,FontSize=22,"
                    "PrimaryColour=&H00FFFFFF&,"
                    "OutlineColour=&H00000000&,"
                    "BorderStyle=1,Outline=2,Shadow=1"
                )
            )
            (
                ffmpeg.output(
                    v_stream,
                    stream.audio,
                    final_path,
                    vcodec="libx264",
                    acodec="copy",
                    crf=20,
                    preset="medium"
                )
                .overwrite_output()
                .run(quiet=True)
            )
            has_subtitles = True
            print(f"[Editor] Successfully burned subtitles into final video.")
        except Exception as e:
            print(f"[Editor] Burning subtitles warning ({e}). Falling back to clean assembly without burned text...")

    if not has_subtitles:
        stream = ffmpeg.input(concat_mp4)
        v_stream = stream.video.filter("scale", settings.target_width, settings.target_height)
        (
            ffmpeg.output(
                v_stream,
                stream.audio,
                final_path,
                vcodec="libx264",
                acodec="copy",
                crf=20,
                preset="medium"
            )
            .overwrite_output()
            .run(quiet=True)
        )

    print(f"[Editor] Assembled final video at {final_path}")
    return {"final_video_path": final_path, "pipeline_status": "completed"}
