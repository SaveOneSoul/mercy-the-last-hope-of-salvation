#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${1:-}"
GITHUB_ORIGIN="${2:-}"
REGION="${REGION:-asia-south1}"
SERVICE_NAME="${SERVICE_NAME:-mercy-catholic-api}"
SECRET_NAME="${SECRET_NAME:-mercy-openai-api-key}"

if [[ -z "$PROJECT_ID" || -z "$GITHUB_ORIGIN" ]]; then
  echo "Usage: ./cloudrun/deploy.sh PROJECT_ID https://USERNAME.github.io"
  exit 2
fi
if ! command -v gcloud >/dev/null 2>&1; then
  echo "gcloud is not installed or not in PATH." >&2
  exit 1
fi
GITHUB_ORIGIN="${GITHUB_ORIGIN%/}"

gcloud config set project "$PROJECT_ID"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com iam.googleapis.com

SA_NAME="${SERVICE_NAME}-runtime"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
if ! gcloud iam service-accounts describe "$SA_EMAIL" --project "$PROJECT_ID" >/dev/null 2>&1; then
  gcloud iam service-accounts create "$SA_NAME" --project "$PROJECT_ID" --display-name "Mercy Catholic AI Cloud Run runtime"
fi

if ! gcloud secrets describe "$SECRET_NAME" --project "$PROJECT_ID" >/dev/null 2>&1; then
  read -rsp "Paste your OpenAI API key: " OPENAI_KEY
  echo
  printf '%s' "$OPENAI_KEY" | gcloud secrets create "$SECRET_NAME" --project "$PROJECT_ID" --replication-policy=automatic --data-file=-
  unset OPENAI_KEY
fi

gcloud secrets add-iam-policy-binding "$SECRET_NAME" --project "$PROJECT_ID" \
  --member="serviceAccount:$SA_EMAIL" --role="roles/secretmanager.secretAccessor"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$BACKEND_DIR"

gcloud run deploy "$SERVICE_NAME" \
  --project "$PROJECT_ID" \
  --source . \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --service-account "$SA_EMAIL" \
  --cpu 1 --memory 512Mi \
  --min-instances 0 --max-instances 3 \
  --concurrency 40 --timeout 60 \
  --set-env-vars "ENVIRONMENT=production,ALLOWED_ORIGINS=$GITHUB_ORIGIN,PERSIST_CONTACT_MESSAGES=false,OPENAI_MODEL=gpt-5.6-luna,OPENAI_CLASSIFIER_MODEL=gpt-5.6-luna,RATE_LIMIT_PER_MINUTE=20" \
  --set-secrets "OPENAI_API_KEY=$SECRET_NAME:latest"

SERVICE_URL="$(gcloud run services describe "$SERVICE_NAME" --project "$PROJECT_ID" --region "$REGION" --format='value(status.url)')"
CONFIG_PATH="$BACKEND_DIR/../javascript/config.js"
python3 - "$CONFIG_PATH" "$SERVICE_URL" <<'PY'
from pathlib import Path
import re, sys
p = Path(sys.argv[1]); url = sys.argv[2]
s = p.read_text(encoding='utf-8')
s = re.sub(r'apiBaseUrl:\s*"[^"]*"', f'apiBaseUrl: "{url}"', s)
s = re.sub(r'enableRemoteAI:\s*(true|false)', 'enableRemoteAI: true', s)
p.write_text(s, encoding='utf-8')
PY

echo "Deployment complete: $SERVICE_URL"
echo "Health: $SERVICE_URL/health"
echo "Frontend config updated: $CONFIG_PATH"
