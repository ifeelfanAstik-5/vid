import os
from app.config import settings
from app.pipeline.state import PipelineState


def _format_timestamp(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def run(state: PipelineState) -> dict:
    out_dir = os.path.join(settings.output_dir, state["run_id"])
    srt_path = os.path.join(out_dir, "subtitles.srt")
    os.makedirs(out_dir, exist_ok=True)

    print(f"[SubtitleGenerator] Creating SRT subtitles at {srt_path}...")
    entries = []
    idx = 1
    cursor = 0.0

    for script, plan in zip(state.get("visual_scripts", []), state.get("scene_plan", [])):
        lines = script.get("dialogue", [])
        duration = float(plan.get("estimated_duration_sec", 5))

        if not lines:
            cursor += duration
            continue

        per_line = duration / len(lines)
        for line in lines:
            start_time = cursor
            end_time = cursor + per_line
            speaker = f"[{line['character']}] " if line.get("character") and line["character"] != "NARRATOR" else ""
            subtitle_text = f"{speaker}{line['line']}"

            entry = f"{idx}\n{_format_timestamp(start_time)} --> {_format_timestamp(end_time)}\n{subtitle_text}"
            entries.append(entry)
            idx += 1
            cursor = end_time

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(entries) + ("\n" if entries else ""))

    print(f"[SubtitleGenerator] Generated {len(entries)} subtitle entries.")
    return {"subtitle_srt_path": srt_path}
