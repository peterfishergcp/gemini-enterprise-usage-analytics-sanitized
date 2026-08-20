# Token Usage Analytics Setup Instructions

This subfolder provides instructions and automated setup scripts to link Cloud Trace data with Gemini Enterprise activity logs for token tracking.

## Overview

By linking Cloud Trace (`_Trace` bucket) spans with user activity log sinks in BigQuery, you get real-time observability over:
- Input Token Usage (`input_tokens`)
- Output Token Usage (`output_tokens`)
- LLM Models Used (`gemini-3.5-flash`, `gemini-3.1-pro-preview`, etc.)
- User IAM Principals and Queries mapped via Trace IDs

---

## Step 1: Set up Log Sinks to BigQuery

Ensure your Cloud Logging sinks are configured for Gemini Enterprise activity.

### StreamAssist Sink:
- **Sink Name**: `ge_raw_logs_streamassist`
- **Destination**: BigQuery dataset `ge_raw_logs_streamassist`
- **Filter**:
  ```text
  logName="projects/[PROJECT_ID]/logs/discoveryengine.googleapis.com%2Fgemini_enterprise_user_activity" AND jsonPayload.logMetadata.methodName="StreamAssist"
  ```

### Assist Sink:
- **Sink Name**: `ge_raw_logs_assist`
- **Destination**: BigQuery dataset `ge_raw_logs_assist`
- **Filter**:
  ```text
  logName="projects/[PROJECT_ID]/logs/discoveryengine.googleapis.com%2Fgemini_enterprise_user_activity" AND jsonPayload.logMetadata.methodName="Assist"
  ```

---

## Step 2: Create Logging Link for Trace Data

Run this command in your terminal (authenticated to your project):

```bash
gcloud logging links create trace_link \
    --bucket=_Trace \
    --location=global \
    --project=[PROJECT_ID]
```

This creates a read-only linked dataset in BigQuery named `trace_link` containing the `_AllSpans` view.

---

## Step 3: Create the Unified Real-Time View

Run `setup_token_tracing.sh` or execute the following SQL DDL in BigQuery:

```sql
CREATE OR REPLACE VIEW `[PROJECT_ID].agent_analytics.gemini_token_usage_by_user` AS
WITH user_logs AS (
  SELECT
    REGEXP_EXTRACT(trace, r'([^/]+)$') as trace_id,
    ANY_VALUE(jsonPayload.userIamPrincipal) as user_principal,
    ANY_VALUE(COALESCE(
      jsonPayload.request.query.text,
      (SELECT STRING_AGG(p.text, "\n") FROM UNNEST(jsonPayload.request.query.parts) p)
    )) as query_text
  FROM
    `[PROJECT_ID].ge_raw_logs_streamassist.discoveryengine_googleapis_com_gemini_enterprise_user_activity_*`
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
    `[PROJECT_ID].trace_link._AllSpans`
  WHERE
    name LIKE "generate_content%"
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
```

---

## Step 4: Automated Setup Command

You can execute the setup script non-interactively:

```bash
export PROJECT_ID="your_project_id"
./setup_token_tracing.sh
```
