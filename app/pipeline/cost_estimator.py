from typing import TypedDict
from app.config import settings
from app.pipeline.state import ScenePlan


class CostBreakdown(TypedDict):
    total_scenes: int
    total_duration_sec: int
    veo_video_cost_usd: float
    sdxl_image_cost_usd: float
    gemini_llm_cost_usd: float
    total_estimated_cost_usd: float
    is_soft_warned: bool
    is_hard_blocked: bool
    soft_limit_usd: float
    hard_limit_usd: float
    warning_message: str


def calculate_cost_estimate(scenes: list[ScenePlan], estimated_tokens: int = 15000) -> CostBreakdown:
    total_scenes = len(scenes)
    total_duration = sum(s.get("estimated_duration_sec", settings.scene_duration_sec) for s in scenes)
    
    # Veo 3.1 Fast video cost ($0.10/second)
    veo_cost = round(total_duration * settings.cost_per_veo_second, 3)

    # SDXL image cost per scene keyframe
    sdxl_cost = round(total_scenes * settings.cost_per_sdxl_image, 3)

    # Gemini 2.5 Flash token cost
    llm_cost = round((estimated_tokens / 1_000_000) * settings.cost_per_gemini_output_1m, 4)

    total_cost = round(veo_cost + sdxl_cost + llm_cost, 2)

    is_hard_blocked = total_cost > settings.hard_budget_limit_usd
    is_soft_warned = total_cost > settings.soft_budget_limit_usd and not is_hard_blocked

    warning = ""
    if is_hard_blocked:
        warning = f"HARD BLOCK: Total cost (${total_cost:.2f}) exceeds the hard budget limit of ${settings.hard_budget_limit_usd:.2f}. Reduce scene count or duration."
    elif is_soft_warned:
        warning = f"SOFT WARNING: Total cost (${total_cost:.2f}) exceeds the advisory budget limit of ${settings.soft_budget_limit_usd:.2f}. Please confirm carefully before proceeding."

    return {
        "total_scenes": total_scenes,
        "total_duration_sec": total_duration,
        "veo_video_cost_usd": veo_cost,
        "sdxl_image_cost_usd": sdxl_cost,
        "gemini_llm_cost_usd": llm_cost,
        "total_estimated_cost_usd": total_cost,
        "is_soft_warned": is_soft_warned,
        "is_hard_blocked": is_hard_blocked,
        "soft_limit_usd": settings.soft_budget_limit_usd,
        "hard_limit_usd": settings.hard_budget_limit_usd,
        "warning_message": warning,
    }
