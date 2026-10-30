"""Shared Gemini client helpers used by all LLM agents."""
from google import genai
from google.genai import types
from app.config import settings


def _client() -> genai.Client:
    return genai.Client(api_key=settings.gemini_api_key)


def _generate_with_fallback(prompt: str, preferred_model: str) -> str:
    client = _client()
    candidate_models = [
        preferred_model,
        "gemini-flash-lite-latest",
        "gemini-3.5-flash-lite",
        "gemini-2.5-flash",
    ]
    seen = set()
    models = []
    for m in candidate_models:
        if m and m not in seen:
            seen.add(m)
            models.append(m)

    last_err = None
    for model_name in models:
        try:
            resp = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
            return resp.text
        except Exception as e:
            print(f"[LLM] Model {model_name} error ({e}). Trying next fallback candidate...")
            last_err = e

    raise last_err


def llm_pro(prompt: str) -> str:
    """Complex reasoning, story analysis, scene breakdown with fallback."""
    return _generate_with_fallback(prompt, settings.llm_heavy)


def llm_flash(prompt: str) -> str:
    """Fast structured generation (scripts, prompts, SFX) with fallback."""
    return _generate_with_fallback(prompt, settings.llm_light)
