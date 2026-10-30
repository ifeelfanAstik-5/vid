# Animated Video Generation Pipeline

An agentic animated video generation system powered by **LangGraph**, **Gemini 2.5 Flash/Pro**, **Vertex AI Imagen 3** and **Veo 2**, with automated subtitle generation and audio assembly via **FFmpeg**.

## Overview

The pipeline takes a story in `.txt`, `.pdf`, or `.docx` format and transforms it into a 1080p animated MP4 with:
- Consistent 2D watercolor storybook aesthetic
- Locked character visual consistency across scenes
- Synchronized subtitles burned into the video
- Background music loops matching scene mood
- Checkpointed state using LangGraph + SQLite to allow graceful crash resumption

## Project Layout

- `app/pipeline/`: LangGraph state definitions, graph routing, and runner logic.
- `app/agents/`: Gemini-powered agents (`story_analyst`, `director`, `scene_writer`, `char_consistency`, `art_director`, `sound_designer`).
- `app/tools/`: Deterministic tools for ingestion (`document_ingestor`), image generation (`image_generator`), animation (`video_animator`), audio (`audio_generator`), subtitles (`subtitle_generator`), and video assembly (`editor`).
- `app/api/`: FastAPI REST endpoints for async job submission, status polling, and video download.
- `samples/`: Sample story inputs for quick testing.
- `tests/`: Smoke and mock unit test suites.

## Quickstart

### 1. Install Dependencies
```bash
.venv/bin/pip install -r requirements.txt
```

### 2. Verify External Tooling
Make sure FFmpeg is installed and accessible in your system PATH:
```bash
ffmpeg -version
```

### 3. Run FastAPI Server
```bash
.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

### 4. Trigger Video Generation
```bash
curl -X POST http://localhost:8000/api/v1/generate -F "file=@samples/sample_story.txt"
```
