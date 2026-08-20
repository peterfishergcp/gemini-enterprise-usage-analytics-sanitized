#!/bin/bash
# ==============================================================================
# Deploy Usage Analytics Dashboard to Google Cloud Run
# ==============================================================================

set -e

PROJECT_ID="${PROJECT_ID:-ai-hub-459714}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-ge-usage-analytics-dashboard}"

echo "======================================================================"
echo "🚀 Deploying Usage Analytics Dashboard to Cloud Run"
echo "======================================================================"
echo "Project ID:   ${PROJECT_ID}"
echo "Region:       ${REGION}"
echo "Service Name: ${SERVICE_NAME}"
echo "======================================================================"

# Build and deploy source directly to Cloud Run
gcloud run deploy "${SERVICE_NAME}" \
  --source . \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --allow-unauthenticated \
  --set-env-vars "PROJECT_ID=${PROJECT_ID},GE_TRANSFORMED_DATASET=ge_transformed,GE_VIEW=ge_logs" \
  --memory "512Mi" \
  --cpu "1" \
  --min-instances "0" \
  --max-instances "2"

echo ""
echo "======================================================================"
echo "✅ Cloud Run Dashboard Service Successfully Deployed!"
echo "======================================================================"
