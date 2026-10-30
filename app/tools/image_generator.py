import base64
import os
from io import BytesIO
import google.auth
from google.auth.transport.requests import Request
from PIL import Image, ImageDraw
import requests

from app.config import settings
from app.pipeline.state import PipelineState


def _generate_sdxl_endpoint_image(prompt: str, out_path: str) -> bool:
    """Generate image via Vertex AI Model Garden Stable Diffusion XL Dedicated Endpoint."""
    try:
        creds, project = google.auth.default()
        creds.refresh(Request())

        url = f"https://{settings.sdxl_dedicated_dns}/v1/projects/{project}/locations/{settings.gcp_location}/endpoints/{settings.sdxl_endpoint_id}:predict"
        headers = {
            "Authorization": f"Bearer {creds.token}",
            "Content-Type": "application/json",
        }
        payload = {
            "instances": [
                {"prompt": prompt}
            ],
            "parameters": {
                "num_inference_steps": 25,
                "guidance_scale": 7.5,
            }
        }

        print(f"[ImageGenerator] Sending request to SDXL Endpoint: {settings.sdxl_endpoint_id}...")
        r = requests.post(url, headers=headers, json=payload, timeout=60)
        if r.status_code == 200:
            res = r.json()
            predictions = res.get("predictions", [])
            if predictions:
                raw_pred = predictions[0]
                # Predictions might be base64 string or dict
                img_b64 = raw_pred.get("bytesBase64Encoded") if isinstance(raw_pred, dict) else raw_pred
                if isinstance(img_b64, str):
                    img_data = base64.b64decode(img_b64)
                    os.makedirs(os.path.dirname(out_path), exist_ok=True)
                    # Convert & save as 1080p
                    with Image.open(BytesIO(img_data)) as im:
                        im.convert("RGB").resize((settings.target_width, settings.target_height)).save(out_path, quality=95)
                    print(f"[ImageGenerator] SUCCESS! Saved SDXL image to {out_path}")
                    return True
        else:
            print(f"[ImageGenerator] SDXL Endpoint returned status {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"[ImageGenerator] SDXL Endpoint call failed ({e}).")
    return False


def _create_storybook_fallback_keyframe(out_path: str, scene_id: str, prompt: str):
    """Generate an aesthetic watercolor-style 16:9 1080p canvas with scene mood."""
    width, height = 1920, 1080
    palettes = [
        [(24, 28, 48), (44, 53, 90), (120, 110, 180), (230, 210, 180)],   # Night / lavender starlight
        [(18, 40, 32), (35, 75, 55), (90, 140, 100), (220, 240, 200)],   # Enchanted forest
        [(45, 20, 30), (85, 40, 60), (160, 80, 100), (250, 210, 180)],   # Warm dawn / sunset
        [(20, 35, 55), (40, 70, 110), (95, 150, 190), (210, 235, 255)],  # Mist / wonder
    ]
    palette = palettes[hash(scene_id) % len(palettes)]

    img = Image.new("RGB", (width, height), color=palette[0])
    draw = ImageDraw.Draw(img)

    for y in range(height):
        factor = y / height
        r = int(palette[0][0] * (1 - factor) + palette[1][0] * factor)
        g = int(palette[0][1] * (1 - factor) + palette[1][1] * factor)
        b = int(palette[0][2] * (1 - factor) + palette[1][2] * factor)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    center_x = int(width * 0.5 + (hash(scene_id) % 300) - 150)
    center_y = int(height * 0.45)
    for radius in range(350, 10, -20):
        draw.ellipse(
            [center_x - radius, center_y - radius, center_x + radius, center_y + radius],
            outline=palette[3],
            width=2
        )

    draw.rectangle([60, 60, width - 60, height - 60], outline=palette[2], width=3)
    draw.rectangle([70, 70, width - 70, height - 70], outline=palette[3], width=1)

    title_text = f"STORYBOARD KEYFRAME — {scene_id.upper().replace('_', ' ')}"
    draw.text((100, 100), title_text, fill=(255, 255, 255))

    clean_prompt = prompt.replace("2D children's storybook illustration,", "").strip()
    words = clean_prompt.split()
    lines = []
    curr = []
    for w in words:
        curr.append(w)
        if len(" ".join(curr)) > 90:
            lines.append(" ".join(curr))
            curr = []
    if curr:
        lines.append(" ".join(curr))

    y_offset = height - 180
    for line in lines[:3]:
        draw.text((100, y_offset), line, fill=(240, 240, 240))
        y_offset += 30

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img.save(out_path, quality=95)
    print(f"[ImageGenerator] Illustrated keyframe canvas saved to {out_path}")


def run(state: PipelineState) -> dict:
    prompt_obj = state["image_prompts"][-1]
    scene_id = prompt_obj["scene_id"]
    out_path = os.path.join(settings.artifacts_dir, state["run_id"], scene_id, "keyframe.jpg")

    existing_paths = list(state.get("generated_image_paths", []))

    # Cache hit check
    if os.path.exists(out_path):
        print(f"[ImageGenerator] Cache hit for {scene_id} keyframe: {out_path}")
        return {"generated_image_paths": existing_paths + [out_path]}

    print(f"[ImageGenerator] Generating keyframe for {scene_id}...")

    # 1. Try Stable Diffusion XL Endpoint
    success = _generate_sdxl_endpoint_image(prompt_obj["prompt"], out_path)

    # 2. Fallback to watercolor storybook illustrated canvas if endpoint is stopped/error
    if not success:
        _create_storybook_fallback_keyframe(out_path, scene_id, prompt_obj["prompt"])

    return {"generated_image_paths": existing_paths + [out_path]}
