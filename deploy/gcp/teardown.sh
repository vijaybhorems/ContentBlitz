#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# ContentBlitz — Tear down all GCP resources (to avoid charges)
#
# Usage:
#   cd deploy/gcp
#   ./teardown.sh
# ──────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/variables.sh"

echo "==> This will DELETE all ContentBlitz GCP resources:"
echo "    - Cloud Run service:  ${CLOUD_RUN_SERVICE}"
echo "    - Memorystore Redis:  ${REDIS_INSTANCE}"
echo "    - VPC Connector:      ${VPC_CONNECTOR}"
echo "    - Artifact Registry:  ${AR_REPO}"
echo "    - Secrets:            contentblitz-*"
echo ""
read -p "Are you sure? (y/N): " confirm
if [[ "${confirm}" != "y" && "${confirm}" != "Y" ]]; then
    echo "Aborted."
    exit 0
fi

echo ""
echo "==> Deleting Cloud Run service..."
gcloud run services delete "${CLOUD_RUN_SERVICE}" \
    --region="${GCP_REGION}" --quiet 2>/dev/null || echo "    (not found)"

echo "==> Deleting Memorystore Redis..."
gcloud redis instances delete "${REDIS_INSTANCE}" \
    --region="${GCP_REGION}" --quiet --async 2>/dev/null || echo "    (not found)"

echo "==> Deleting VPC Connector..."
gcloud compute networks vpc-access connectors delete "${VPC_CONNECTOR}" \
    --region="${GCP_REGION}" --quiet 2>/dev/null || echo "    (not found)"

echo "==> Deleting Artifact Registry..."
gcloud artifacts repositories delete "${AR_REPO}" \
    --location="${GCP_REGION}" --quiet 2>/dev/null || echo "    (not found)"

echo "==> Deleting secrets..."
for secret in contentblitz-openai-key contentblitz-anthropic-key contentblitz-tavily-key contentblitz-stability-key; do
    gcloud secrets delete "${secret}" --quiet 2>/dev/null || echo "    (${secret} not found)"
done

echo ""
echo "Done. All ContentBlitz resources have been deleted."
echo "Note: Redis deletion is async — check with:"
echo "  gcloud redis instances list --region=${GCP_REGION}"
