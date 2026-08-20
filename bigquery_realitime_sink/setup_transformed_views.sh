#!/bin/bash
# ==============================================================================
# Setup Transformed Views for Gemini Enterprise & NotebookLM Logs
# ==============================================================================

set -e # Exit immediately on error

PROJECT_ID="${PROJECT_ID:-your_project_id}"
BQ_LOCATION="${BQ_LOCATION:-US}"

GE_TRANSFORMED_DATASET="${GE_TRANSFORMED_DATASET:-ge_transformed}"
NLM_TRANSFORMED_DATASET="${NLM_TRANSFORMED_DATASET:-nlm_transformed}"

GE_DATASET_PREFIX="${GE_DATASET_PREFIX:-ge_raw_logs_}"
NLM_DATASET_PREFIX="${NLM_DATASET_PREFIX:-nlm_raw_logs_}"

SQL_GE="${SQL_GE:-$(dirname "$0")/ge_transformed.sql}"
SQL_NLM="${SQL_NLM:-$(dirname "$0")/nlm_transformed.sql}"

echo "======================================================================"
echo "Starting deployment of transformed views in project: ${PROJECT_ID}"
echo "GE Transformed Dataset: ${GE_TRANSFORMED_DATASET}"
echo "NLM Transformed Dataset: ${NLM_TRANSFORMED_DATASET}"
echo "======================================================================"

echo "-> Verifying Destination Datasets..."
bq mk -f -d --location="${BQ_LOCATION}" "${PROJECT_ID}:${GE_TRANSFORMED_DATASET}" || true
bq mk -f -d --location="${BQ_LOCATION}" "${PROJECT_ID}:${NLM_TRANSFORMED_DATASET}" || true

echo "-> Deploying Gemini Enterprise (GE) Logs View..."

if [ ! -f "$SQL_GE" ]; then
  echo "[Error] file not found: $SQL_GE"
  exit 1
fi

TEMP_SQL_GE=$(mktemp)
cat "$SQL_GE" | \
sed "s/\${PROJECT_ID}/${PROJECT_ID}/g" | \
sed "s/\${GE_TRANSFORMED_DATASET}/${GE_TRANSFORMED_DATASET}/g" | \
sed "s/\${GE_DATASET_PREFIX}/${GE_DATASET_PREFIX}/g" > "$TEMP_SQL_GE"

# Dynamic filtering for active tables in GE
FILTERED_SQL_GE=$(mktemp)
python3 -c "
import sys, re, subprocess

with open('$TEMP_SQL_GE') as f:
    sql = f.read()

lines = sql.splitlines()
new_lines = []
in_base_logs = False
valid_unions = []

for line in lines:
    if 'WITH base_logs AS (' in line:
        in_base_logs = True
        new_lines.append(line)
        continue
    if in_base_logs and (line.strip().startswith('),') or 'agent_mappings AS (' in line):
        in_base_logs = False
        # filter unions
        filtered_unions = []
        for u in valid_unions:
            m = re.search(r'FROM \`([^\`]+)\`', u)
            if m:
                table_spec = m.group(1).rstrip('*')
                ds_table = table_spec.split('.', 1)[1]
                ds = ds_table.split('.')[0]
                res = subprocess.run(['bq', 'ls', '--project_id=$PROJECT_ID', ds], capture_output=True, text=True)
                if 'discoveryengine_googleapis_com_gemini_enterprise_user_activity' in res.stdout:
                    filtered_unions.append(u)
        if not filtered_unions:
            # Fallback if no tables exist yet
            filtered_unions.append('SELECT CAST(NULL AS STRING) as json_str, CAST(NULL AS TIMESTAMP) as timestamp')
        new_lines.append('  ' + '\n  UNION ALL\n  '.join(filtered_unions))
        new_lines.append(line)
        continue
    if in_base_logs:
        clean_u = line.strip().replace('UNION ALL', '').strip()
        if clean_u:
            valid_unions.append(clean_u)
    else:
        new_lines.append(line)

with open('$FILTERED_SQL_GE', 'w') as f:
    f.write('\n'.join(new_lines))
"

bq query --use_legacy_sql=false --project_id="${PROJECT_ID}" < "$FILTERED_SQL_GE"
rm -f "$TEMP_SQL_GE" "$FILTERED_SQL_GE"

echo "----------------------------------------------------------------------"
echo "[Caution] If you encounter a 'Not found: Table' error above, it means"
echo "          your newly created sinks have not captured any real user logs"
echo "          yet. BigQuery materializes sink tables on first insert."
echo ""
echo "          Generate a few active logs in your Gemini/NotebookLM engines,"
echo "          then simply re-run this setup_transformed_views.sh script!"
echo "----------------------------------------------------------------------"

echo "[Success] GE View deployed."

echo "-> Deploying NotebookLM (NLM) Logs View..."

if [ ! -f "$SQL_NLM" ]; then
  echo "[Error] file not found: $SQL_NLM"
  exit 1
fi

cat "$SQL_NLM" | \
sed "s/\${PROJECT_ID}/${PROJECT_ID}/g" | \
sed "s/\${NLM_TRANSFORMED_DATASET}/${NLM_TRANSFORMED_DATASET}/g" | \
sed "s/\${NLM_DATASET_PREFIX}/${NLM_DATASET_PREFIX}/g" | \
bq query --use_legacy_sql=false --project_id="${PROJECT_ID}"

echo "[Success] NLM View deployed."

echo "======================================================================"
echo "Deployment Complete!"
echo "======================================================================"
