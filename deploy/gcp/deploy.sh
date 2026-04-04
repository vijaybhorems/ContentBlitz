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

# ── Build secrets list (only include optional publishing secrets if they exist) ──
SECRETS="OPENAI_API_KEY=contentblitz-openai-key:latest"
SECRETS="${SECRETS},ANTHROPIC_API_KEY=contentblitz-anthropic-key:latest"
SECRETS="${SECRETS},TAVILY_API_KEY=contentblitz-tavily-key:latest"
SECRETS="${SECRETS},STABILITY_API_KEY=contentblitz-stability-key:latest"
SECRETS="${SECRETS},GOOGLE_CLIENT_ID=${OAUTH_CLIENT_ID_SECRET}:latest"
SECRETS="${SECRETS},GOOGLE_CLIENT_SECRET=${OAUTH_CLIENT_SECRET_SECRET}:latest"

# Optional: Squarespace (skip if secret doesn't exist)
if gcloud secrets describe contentblitz-squarespace-key --project="${GCP_PROJECT_ID}" &>/dev/null; then
    SECRETS="${SECRETS},SQUARESPACE_API_KEY=contentblitz-squarespace-key:latest"
    echo "    ✓ Squarespace secret found"
else
    echo "    ⏭ Squarespace secret not found — skipping (button will be hidden)"
fi

# Optional: Ghost (skip if secret doesn't exist)
if gcloud secrets describe contentblitz-ghost-admin-key --project="${GCP_PROJECT_ID}" &>/dev/null; then
    SECRETS="${SECRETS},GHOST_ADMIN_API_KEY=contentblitz-ghost-admin-key:latest"
    echo "    ✓ Ghost secret found"
else
    echo "    ⏭ Ghost secret not found — skipping (button will be hidden)"
fi

# ── Build env vars for publishing endpoints ──
PUBLISH_ENV="GHOST_API_URL=https://the-algorithmic-lens.ghost.io"
PUBLISH_ENV="${PUBLISH_ENV},SQUARESPACE_SITE_URL=https://www.vijaybhore.dev"
PUBLISH_ENV="${PUBLISH_ENV},SQUARESPACE_BLOG_COLLECTION_ID=5c7a3571652dea887e9e8bbf"

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
    --set-secrets="${SECRETS}"
    --set-env-vars="${ENV_VARS},OAUTH_REDIRECT_URI=${OAUTH_REDIRECT_URI},${PUBLISH_ENV}"
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
