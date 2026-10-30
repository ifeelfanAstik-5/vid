import os
import subprocess
from app.config import settings
from app.pipeline.state import PipelineState

# Musical chords by emotional beat (frequencies in Hz)
CHORD_PROFILES = {
    "wonder": [261.63, 329.63, 392.00, 493.88, 587.33],     # Cmaj9 (C, E, G, B, D) - shimmering, magical
    "joy": [349.23, 440.00, 523.25, 659.25, 698.46],        # Fmaj7 (F, A, C, E, F) - bright, uplifting
    "calm": [196.00, 246.94, 293.66, 329.63, 392.00],       # G pentatonic (G, B, D, E, G) - peaceful, serene
    "tension": [220.00, 261.63, 311.13, 415.30, 440.00],    # Am / Dim (A, C, Eb, G#, A) - mysterious, suspenseful
    "melancholy": [220.00, 261.63, 329.63, 392.00, 440.00], # Am7 (A, C, E, G, A) - nostalgic, thoughtful
    "action": [293.66, 369.99, 440.00, 587.33, 739.99],     # Dsus / energetic (D, F#, A, D, F#)
}


def _create_ambient_synth_audio(out_path: str, duration: int, scene_id: str, emotional_beat: str = "wonder"):
    """Generate a rich, audible storybook musical bell & ambient chime track with harmonics and reverb."""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    
    beat = (emotional_beat or "wonder").lower()
    freqs = CHORD_PROFILES.get(beat, CHORD_PROFILES["wonder"])
    
    # 5 cascading notes with delays, bell decay, and ethereal reverb
    delays = [0, 250, 550, 850, 1150]
    inputs = []
    filter_parts = []
    
    for i, (f, delay) in enumerate(zip(freqs, delays)):
        inputs.extend(["-f", "lavfi", "-i", f"sine=f={f:.2f}:d={duration}"])
        fade_start = max(1, duration - 2)
        filter_parts.append(
            f"[{i}:a]adelay={delay}|{delay},volume=0.45,afade=t=in:ss=0:d=0.3,afade=t=out:st={fade_start}:d=2[a{i}];"
        )
    
    filter_parts.append(
        f"[a0][a1][a2][a3][a4]amix=inputs=5:dropout_transition=0,"
        f"aecho=0.8:0.88:80|160:0.45|0.35,"
        f"loudnorm=I=-16:TP=-1.5:LRA=11[out]"
    )
    
    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", "".join(filter_parts),
        "-map", "[out]",
        "-c:a", "libmp3lame", "-b:a", "192k",
        out_path
    ]
    
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"[AudioGenerator] Generated storybook audio ({beat} mode) at {out_path} ({duration}s)")


def run(state: PipelineState) -> dict:
    idx = state.get("current_scene_index", 0)
    plan = state["scene_plan"][idx] if idx < len(state.get("scene_plan", [])) else {}
    duration = plan.get("estimated_duration_sec", settings.scene_duration_sec)
    emotional_beat = plan.get("emotional_beat", "wonder")

    stub = state["audio_assets"][-1]
    scene_id = stub["scene_id"]
    out_path = os.path.join(settings.artifacts_dir, state["run_id"], scene_id, "music.mp3")

    if not os.path.exists(out_path):
        print(f"[AudioGenerator] Synthesizing storybook musical score for {scene_id} ({emotional_beat}, {duration}s)...")
        _create_ambient_synth_audio(out_path, duration, scene_id, emotional_beat)

    updated = list(state["audio_assets"])
    updated[-1] = {**stub, "music_local_path": out_path if os.path.exists(out_path) else None}
    return {"audio_assets": updated}
