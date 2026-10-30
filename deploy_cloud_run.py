import os
import subprocess
import google.auth
from google.auth.transport.requests import Request
from app.config import settings

print("[Deploy] Refreshing Google Cloud credentials...")
creds, project = google.auth.default()
creds.refresh(Request())
token = creds.token
project_id = project or settings.gcp_project_id
region = settings.gcp_location
service_name = "vid-studio"

print(f"[Deploy] Authenticated as project {project_id}. Preparing Cloud Run deployment...")

env = os.environ.copy()
env["CLOUDSDK_AUTH_ACCESS_TOKEN"] = token

gcloud = r"C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

env_vars = [
    f"GCP_PROJECT_ID={project_id}",
    f"GCP_LOCATION={region}",
    f"MAX_SCENES={settings.max_scenes}",
    f"SOFT_BUDGET_LIMIT_USD={settings.soft_budget_limit_usd}",
    f"HARD_BUDGET_LIMIT_USD={settings.hard_budget_limit_usd}",
    f"GEMINI_API_KEY={settings.gemini_api_key}",
    f"STUDIO_ACCESS_TOKEN={settings.studio_access_token}",
]

cmd = [
    gcloud, "run", "deploy", service_name,
    "--source", ".",
    "--region", region,
    f"--project={project_id}",
    "--platform", "managed",
    "--allow-unauthenticated",
    "--memory", "4Gi",
    "--cpu", "2",
    "--timeout", "3600",
    "--set-env-vars", ",".join(env_vars),
    "--quiet"
]

print("[Deploy] Submitting build to Google Cloud Build and deploying service...")
print("Command:", " ".join(cmd[:8]), "...")
process = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

for line in iter(process.stdout.readline, ""):
    print(line, end="", flush=True)

process.stdout.close()
process.wait()
print(f"\n[Deploy] Process finished with exit code {process.returncode}")
