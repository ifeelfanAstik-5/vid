from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # GCP
    gcp_project_id: str = "project-enclave-507717"
    gcp_location: str = "us-central1"
    gcs_bucket_name: str = "vid-pipeline-507717"

    # Gemini / Google AI
    gemini_api_key: str = ""

    # Security: Studio Access Token (Locks generation & GPU actions)
    studio_access_token: str = "VID_STUDIO_TOKEN_2026_X9Q7"

    # Model identifiers
    llm_heavy: str = "gemini-flash-lite-latest"
    llm_light: str = "gemini-flash-lite-latest"
    imagen_model: str = "imagen-3.0-generate-002"
    veo_model: str = "veo-3.1-fast-generate-001"
    music_model: str = "lyria-3-clip-preview"

    # Stable Diffusion XL Dedicated Endpoint (Vertex AI Model Garden)
    sdxl_endpoint_id: str = "mg-endpoint-1cb911b9-e02d-4de6-9352-3fb410c15485"
    sdxl_dedicated_dns: str = "mg-endpoint-1cb911b9-e02d-4de6-9352-3fb410c15485.us-central1-207752638308.prediction.vertexai.goog"
    sdxl_deployed_model_id: str = "666465124885725184"

    # Budget Guardrails (USD)
    soft_budget_limit_usd: float = 5.00
    hard_budget_limit_usd: float = 7.00

    # Pricing constants (USD)
    cost_per_veo_second: float = 0.10      # Veo 3.1 Fast ($0.10/sec)
    cost_per_sdxl_image: float = 0.01      # Inference cost estimate per image
    cost_per_gemini_input_1m: float = 0.075 # Gemini 2.5 Flash input
    cost_per_gemini_output_1m: float = 0.30 # Gemini 2.5 Flash output

    # Pipeline
    output_dir: str = "./output"
    artifacts_dir: str = "./artifacts"
    max_scenes: int = 5                     # Default 5 scenes = 30 seconds
    scene_duration_sec: int = 6             # Supported Veo duration: 4, 6, or 8s
    target_width: int = 1920
    target_height: int = 1080


settings = Settings()
