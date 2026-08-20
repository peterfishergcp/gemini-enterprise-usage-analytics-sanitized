#!/bin/bash
# ==============================================================================
# Script: deploy_all_sanitized.sh
# Description: Automated non-interactive deployment script for Gemini Enterprise
#              and NotebookLM Usage Analytics pipeline.
# ==============================================================================

set -e

# Configuration / Environment Variables with defaults
export PROJECT_ID="${PROJECT_ID:-your_project_id}"
export APP_ID="${APP_ID:-your_app_id}"
export BQ_LOCATION="${BQ_LOCATION:-US}"
export GE_DATASET_PREFIX="${GE_DATASET_PREFIX:-ge_raw_logs_}"
export NLM_DATASET_PREFIX="${NLM_DATASET_PREFIX:-nlm_raw_logs_}"
export GE_TRANSFORMED_DATASET="${GE_TRANSFORMED_DATASET:-ge_transformed}"
export NLM_TRANSFORMED_DATASET="${NLM_TRANSFORMED_DATASET:-nlm_transformed}"

echo "======================================================================"
echo "🚀 Starting Automated Usage Analytics Deployment"
echo "======================================================================"
echo "Project ID:            ${PROJECT_ID}"
echo "App ID(s):             ${APP_ID}"
echo "BigQuery Location:     ${BQ_LOCATION}"
echo "GE Dataset Prefix:     ${GE_DATASET_PREFIX}"
echo "NLM Dataset Prefix:    ${NLM_DATASET_PREFIX}"
echo "GE Transformed View:   ${GE_TRANSFORMED_DATASET}.ge_logs"
echo "NLM Transformed View:  ${NLM_TRANSFORMED_DATASET}.nlm_logs"
echo "======================================================================"

if [ "$PROJECT_ID" = "your_project_id" ] || [ -z "$PROJECT_ID" ]; then
    echo "❌ [Error] PROJECT_ID is not set or set to default placeholder."
    echo "   Please pass PROJECT_ID via env variable or script argument."
    echo "   Example: PROJECT_ID=\"my-gcp-project\" APP_ID=\"my-app-id\" ./deploy_all_sanitized.sh"
    exit 1
fi

chmod +x enable_audit_logging.sh bigquery_realitime_sink/setup_user_logs_raw.sh bigquery_realitime_sink/setup_transformed_views.sh

echo ""
echo "[Step 1] Enabling Global Usage Audit Logging..."
./enable_audit_logging.sh

echo ""
echo "[Step 2] Deploying Raw BigQuery Log Sinks..."
cd bigquery_realitime_sink
./setup_user_logs_raw.sh

echo ""
echo "[Step 3] Deploying Consolidated Transformed Views..."
./setup_transformed_views.sh

echo ""
echo "======================================================================"
echo "✅ Automated Usage Analytics Deployment Successfully Completed!"
echo "======================================================================"
