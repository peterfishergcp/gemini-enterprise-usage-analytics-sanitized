#!/bin/bash
# ==============================================================================
# Script: setup_token_tracing.sh
# Description: Automates Cloud Logging Link creation to _Trace bucket and
#              deploys the token usage BigQuery view.
# ==============================================================================

set -e

PROJECT_ID="${PROJECT_ID:-your_project_id}"
LOCATION="${LOCATION:-global}"
ANALYTICS_DATASET="${ANALYTICS_DATASET:-agent_analytics}"
BQ_LOCATION="${BQ_LOCATION:-US}"
GE_DATASET_PREFIX="${GE_DATASET_PREFIX:-ge_raw_logs_}"

echo "======================================================================"
echo "🚀 Setting up Token Usage Tracing Link & BigQuery View"
echo "======================================================================"
echo "Project ID: ${PROJECT_ID}"
echo "Dataset:    ${ANALYTICS_DATASET}"
echo "======================================================================"

# Step 1: Create Logging Link for Trace Data
echo "-> Creating Cloud Logging link to _Trace bucket..."
gcloud logging links create trace_link \
    --bucket=_Trace \
    --location="${LOCATION}" \
    --project="${PROJECT_ID}" 2>/dev/null || true

# Step 2: Ensure destination dataset exists
echo "-> Verifying analytics dataset '${PROJECT_ID}:${ANALYTICS_DATASET}'..."
bq mk -f -d --location="${BQ_LOCATION}" "${PROJECT_ID}:${ANALYTICS_DATASET}" || true

# Step 3: Deploy Unified Token Usage View
echo "-> Creating 'gemini_token_usage_by_user' view in BigQuery..."
bq query --use_legacy_sql=false --project_id="${PROJECT_ID}" "
CREATE OR REPLACE VIEW \`${PROJECT_ID}.${ANALYTICS_DATASET}.gemini_token_usage_by_user\` AS
WITH user_logs AS (
  SELECT
    REGEXP_EXTRACT(trace, r'([^/]+)$') as trace_id,
    ANY_VALUE(jsonPayload.userIamPrincipal) as user_principal,
    ANY_VALUE(COALESCE(
      jsonPayload.request.query.text,
      (SELECT STRING_AGG(p.text, '\n') FROM UNNEST(jsonPayload.request.query.parts) p)
    )) as query_text
  FROM
    \`${PROJECT_ID}.${GE_DATASET_PREFIX}streamassist.discoveryengine_googleapis_com_gemini_enterprise_user_activity_*\`
  WHERE
    jsonPayload.userIamPrincipal IS NOT NULL
  GROUP BY
    1
),
spans AS (
  SELECT
    trace_id,
    start_time,
    STRING(attributes['gen_ai.conversation.id']) as conversation_id,
    STRING(attributes['gen_ai.request.model']) as model,
    CAST(STRING(attributes['gen_ai.usage.input_tokens']) AS INT64) as input_tokens,
    CAST(STRING(attributes['gen_ai.usage.output_tokens']) AS INT64) as output_tokens
  FROM
    \`${PROJECT_ID}.trace_link._AllSpans\`
  WHERE
    name LIKE 'generate_content%'
    AND attributes['gen_ai.usage.input_tokens'] IS NOT NULL
)
SELECT
  s.start_time,
  u.user_principal,
  u.query_text,
  s.conversation_id,
  s.model,
  s.input_tokens,
  s.output_tokens
FROM
  spans s
LEFT JOIN
  user_logs u
ON
  s.trace_id = u.trace_id;
"

echo "======================================================================"
echo "✅ Token Usage Tracing Setup Complete!"
echo "View Created: ${PROJECT_ID}.${ANALYTICS_DATASET}.gemini_token_usage_by_user"
echo "======================================================================"
