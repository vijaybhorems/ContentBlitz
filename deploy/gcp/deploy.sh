#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# ContentBlitz — Build, push, and deploy to Cloud Run
#
# Usage:
#   cd deploy/gcp
#   chmod +x deploy.sh
#   ./deploy.sh
# ──────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
source "${SCRIPT_DIR}/variables.sh"

echo "==> Project root: ${PROJECT_ROOT}"
echo "==> Target image: ${IMAGE_NAME}"

# ──────────────────────────────────────────────────────────────
# 1. Build & push Docker image
# ──────────────────────────────────────────────────────────────
echo ""
echo "==> Building Docker image with Cloud Build..."
cd "${PROJECT_ROOT}"

# Tag with git SHA for traceability + :latest for convenience
GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "dev")
TAGGED_IMAGE="${IMAGE_NAME}:${GIT_SHA}"
LATEST_IMAGE="${IMAGE_NAME}:latest"

gcloud builds submit \
    --tag="${TAGGED_IMAGE}" \
    --timeout=600 \
    --quiet

# Also tag as :latest
gcloud artifacts docker tags add "${TAGGED_IMAGE}" "${LATEST_IMAGE}" --quiet 2>/dev/null || true

echo "    Pushed: ${TAGGED_IMAGE}"

# ──────────────────────────────────────────────────────────────
# 2. Get Redis IP (Memorystore)
# ──────────────────────────────────────────────────────────────
echo ""
echo "==> Fetching Redis IP..."
REDIS_HOST=$(gcloud redis instances describe "${REDIS_INSTANCE}" \
    --region="${GCP_REGION}" \
    --format="value(host)" 2>/dev/null || echo "")

if [ -z "${REDIS_HOST}" ]; then
    echo "    WARNING: Redis instance not found. Deploying without Redis (in-memory checkpointer)."
    REDIS_URL_VALUE=""
else
    REDIS_PORT=$(gcloud redis instances describe "${REDIS_INSTANCE}" \
        --region="${GCP_REGION}" \
        --format="value(port)")
    REDIS_URL_VALUE="redis://${REDIS_HOST}:${REDIS_PORT}/0"
    echo "    Redis URL: ${REDIS_URL_VALUE}"
fi

# ──────────────────────────────────────────────────────────────
# 3. Deploy to Cloud Run
# ──────────────────────────────────────────────────────────────
echo ""
echo "==> Deploying to Cloud Run..."

# Build env vars string (combine base vars + optional Redis URL into one flag)
ENV_VARS="ENVIRONMENT=production,LOG_LEVEL=INFO"
if [ -n "${REDIS_URL_VALUE}" ]; then
    ENV_VARS="${ENV_VARS},REDIS_URL=${REDIS_URL_VALUE}"
fi

# Build the deploy command
DEPLOY_CMD=(
    gcloud run deploy "${CLOUD_RUN_SERVICE}"
    --image="${TAGGED_IMAGE}"
    --region="${GCP_REGION}"
    --platform=managed
    --port=8501
    --memory="${CLOUD_RUN_MEMORY}"
    --cpu="${CLOUD_RUN_CPU}"
    --min-instances="${CLOUD_RUN_MIN_INSTANCES}"
    --max-instances="${CLOUD_RUN_MAX_INSTANCES}"
    --timeout="${CLOUD_RUN_TIMEOUT}"
    --concurrency="${CLOUD_RUN_CONCURRENCY}"
    --allow-unauthenticated
    --set-secrets="OPENAI_API_KEY=contentblitz-openai-key:latest,ANTHROPIC_API_KEY=contentblitz-anthropic-key:latest,TAVILY_API_KEY=contentblitz-tavily-key:latest,STABILITY_API_KEY=contentblitz-stability-key:latest,GOOGLE_CLIENT_ID=${OAUTH_CLIENT_ID_SECRET}:latest,GOOGLE_CLIENT_SECRET=${OAUTH_CLIENT_SECRET_SECRET}:latest"
    --set-env-vars="${ENV_VARS},OAUTH_REDIRECT_URI=${OAUTH_REDIRECT_URI}"
    --vpc-connector="${VPC_CONNECTOR}"
    --vpc-egress=private-ranges-only
    --quiet
)

"${DEPLOY_CMD[@]}"

# ──────────────────────────────────────────────────────────────
# 4. Show deployment info
# ──────────────────────────────────────────────────────────────
echo ""
SERVICE_URL=$(gcloud run services describe "${CLOUD_RUN_SERVICE}" \
    --region="${GCP_REGION}" \
    --format="value(status.url)")

echo "============================================================"
echo " Deployment complete!"
echo "============================================================"
echo ""
echo " Service URL : ${SERVICE_URL}"
echo " Image       : ${TAGGED_IMAGE}"
echo " Region      : ${GCP_REGION}"
echo " Redis       : ${REDIS_URL_VALUE:-'(in-memory fallback)'}"
echo ""
echo " Useful commands:"
echo "   # View recent logs"
echo "   gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=${CLOUD_RUN_SERVICE}' --limit=50 --format='table(timestamp,textPayload)' --project=${GCP_PROJECT_ID}"
echo ""
echo "   # Stream logs (requires gcloud beta components)"
echo "   gcloud beta run services logs tail ${CLOUD_RUN_SERVICE} --region=${GCP_REGION}"
echo ""
echo "   # View revisions"
echo "   gcloud run revisions list --service=${CLOUD_RUN_SERVICE} --region=${GCP_REGION}"
echo ""
echo "   # Rollback to previous revision"
echo "   gcloud run services update-traffic ${CLOUD_RUN_SERVICE} --region=${GCP_REGION} --to-revisions=REVISION_NAME=100"
echo ""
