# ----------------------------------------------------
# Google Cloud Run Deployment Script (PowerShell)
# ----------------------------------------------------
$PROJECT_ID = "project-enclave-507717"
$REGION = "us-central1"
$SERVICE_NAME = "vid-studio"

Write-Host "Deploying $SERVICE_NAME to Google Cloud Run in $REGION..." -ForegroundColor Cyan

# Set current project
& "C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" config set project $PROJECT_ID

# Deploy directly from source (Cloud Build builds the Dockerfile remotely)
& "C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" run deploy $SERVICE_NAME `
    --source . `
    --region $REGION `
    --platform managed `
    --allow-unauthenticated `
    --memory 4Gi `
    --cpu 2 `
    --timeout 3600 `
    --set-env-vars "GCP_PROJECT_ID=$PROJECT_ID,GCP_LOCATION=$REGION,MAX_SCENES=5,SOFT_BUDGET_LIMIT_USD=5.00,HARD_BUDGET_LIMIT_USD=7.00"

Write-Host "Deployment completed!" -ForegroundColor Green
