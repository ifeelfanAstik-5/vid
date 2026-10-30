import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import settings

app = FastAPI(title="Animated Video Generation Pipeline", version="0.1.0")

# Enable CORS for local React development and network access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure static directories exist
os.makedirs(settings.artifacts_dir, exist_ok=True)
os.makedirs(settings.output_dir, exist_ok=True)

# Mount artifacts and output as static paths so UI can preview images/videos
app.mount("/artifacts", StaticFiles(directory=settings.artifacts_dir), name="artifacts")
app.mount("/output", StaticFiles(directory=settings.output_dir), name="output")

app.include_router(router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}
