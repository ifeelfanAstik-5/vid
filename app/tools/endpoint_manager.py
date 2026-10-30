"""Endpoint Manager for Vertex AI Model Garden endpoints.

Handles status queries and undeployment for the dedicated Stable Diffusion XL
endpoint to prevent unintended idle GPU billing.
"""
import google.auth
from google.auth.transport.requests import Request
import requests
from app.config import settings


def get_gcp_access_token() -> str:
    creds, _ = google.auth.default()
    creds.refresh(Request())
    return creds.token


def get_endpoint_status() -> dict:
    """Check whether any models are currently deployed on the SDXL endpoint."""
    try:
        token = get_gcp_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        endpoint_res = f"projects/{settings.gcp_project_id}/locations/{settings.gcp_location}/endpoints/{settings.sdxl_endpoint_id}"
        url = f"https://{settings.gcp_location}-aiplatform.googleapis.com/v1/{endpoint_res}"
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200:
            return {
                "deployed": False,
                "endpoint_id": settings.sdxl_endpoint_id,
                "error": f"GCP API returned {res.status_code}: {res.text}",
            }
        data = res.json()
        deployed_models = data.get("deployedModels", [])
        if deployed_models:
            first_model = deployed_models[0]
            return {
                "deployed": True,
                "endpoint_id": settings.sdxl_endpoint_id,
                "deployed_model_id": first_model.get("id"),
                "model_resource": first_model.get("model"),
                "display_name": first_model.get("displayName") or "Stable Diffusion XL",
                "create_time": first_model.get("createTime"),
            }
        return {
            "deployed": False,
            "endpoint_id": settings.sdxl_endpoint_id,
            "deployed_model_id": None,
        }
    except Exception as e:
        return {
            "deployed": False,
            "endpoint_id": settings.sdxl_endpoint_id,
            "error": str(e),
        }


def undeploy_endpoint_model() -> dict:
    """Undeploy the SDXL model from the dedicated Vertex AI endpoint to stop GPU billing."""
    try:
        # First check current deployed model ID
        status_info = get_endpoint_status()
        deployed_id = status_info.get("deployed_model_id") or settings.sdxl_deployed_model_id
        if not status_info.get("deployed"):
            return {
                "success": True,
                "message": "Endpoint is already undeployed (no active deployed models).",
            }

        token = get_gcp_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        endpoint_res = f"projects/{settings.gcp_project_id}/locations/{settings.gcp_location}/endpoints/{settings.sdxl_endpoint_id}"
        url = f"https://{settings.gcp_location}-aiplatform.googleapis.com/v1/{endpoint_res}:undeployModel"
        body = {
            "deployedModelId": deployed_id,
        }
        res = requests.post(url, json=body, headers=headers, timeout=15)
        if res.status_code in (200, 202):
            return {
                "success": True,
                "operation": res.json(),
                "message": f"Undeploy initiated for model {deployed_id}. GPU billing stopped.",
            }
        return {
            "success": False,
            "error": f"Failed to undeploy (HTTP {res.status_code}): {res.text}",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
