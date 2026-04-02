#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# ContentBlitz — GCP infrastructure setup (run once)
#
# Creates:
#   1. Artifact Registry repository
#   2. Memorystore Redis instance
#   3. Serverless VPC Connector (Cloud Run ↔ Redis)
#   4. Secret Manager secrets for API keys
#
# Prerequisites:
#   - gcloud CLI installed & authenticated (gcloud auth login)
#   - Billing enabled on the GCP project
#   - Edit deploy/gcp/variables.sh with your project ID
#
# Usage:
#   cd deploy/gcp
#   chmod +x setup.sh
#   ./setup.sh
# ──────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/variables.sh"

echo "==> Setting GCP project to ${GCP_PROJECT_ID}"
gcloud config set project "${GCP_PROJECT_ID}"

# ──────────────────────────────────────────────────────────────
# 1. Enable required APIs
# ──────────────────────────────────────────────────────────────
echo "==> Enabling GCP APIs..."
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    redis.googleapis.com \
    secretmanager.googleapis.com \
    vpcaccess.googleapis.com \
    compute.googleapis.com

# ──────────────────────────────────────────────────────────────
# 2. Artifact Registry — container image repo
# ──────────────────────────────────────────────────────────────
echo "==> Creating Artifact Registry repository..."
if ! gcloud artifacts repositories describe "${AR_REPO}" \
    --location="${GCP_REGION}" --format="value(name)" 2>/dev/null; then
    gcloud artifacts repositories create "${AR_REPO}" \
        --repository-format=docker \
        --location="${GCP_REGION}" \
        --description="ContentBlitz Docker images"
    echo "    Created: ${AR_REPO}"
else
    echo "    Already exists: ${AR_REPO}"
fi

# Configure Docker auth for Artifact Registry
gcloud auth configure-docker "${GCP_REGION}-docker.pkg.dev" --quiet

# ──────────────────────────────────────────────────────────────
# 3. VPC Connector — connects Cloud Run to Memorystore
# ──────────────────────────────────────────────────────────────
echo "==> Creating Serverless VPC Connector..."
if ! gcloud compute networks vpc-access connectors describe "${VPC_CONNECTOR}" \
    --region="${GCP_REGION}" --format="value(name)" 2>/dev/null; then
    gcloud compute networks vpc-access connectors create "${VPC_CONNECTOR}" \
        --region="${GCP_REGION}" \
        --network="${VPC_NETWORK}" \
        --range="${VPC_CONNECTOR_RANGE}" \
        --min-instances=2 \
        --max-instances=3
    echo "    Created: ${VPC_CONNECTOR}"
else
    echo "    Already exists: ${VPC_CONNECTOR}"
fi

# ──────────────────────────────────────────────────────────────
# 4. Memorystore Redis
# ──────────────────────────────────────────────────────────────
echo "==> Creating Memorystore Redis instance (this takes ~5 min)..."
if ! gcloud redis instances describe "${REDIS_INSTANCE}" \
    --region="${GCP_REGION}" --format="value(name)" 2>/dev/null; then
    gcloud redis instances create "${REDIS_INSTANCE}" \
        --region="${GCP_REGION}" \
        --tier="${REDIS_TIER}" \
        --size="${REDIS_SIZE_GB}" \
        --redis-version="${REDIS_VERSION}" \
        --network="${VPC_NETWORK}" \
        --async
    echo "    Redis creation started (async). Check status with:"
    echo "    gcloud redis instances describe ${REDIS_INSTANCE} --region=${GCP_REGION}"
else
    echo "    Already exists: ${REDIS_INSTANCE}"
fi

# ──────────────────────────────────────────────────────────────
# 5. Secret Manager — store API keys securely
# ──────────────────────────────────────────────────────────────
echo "==> Setting up Secret Manager..."

create_secret() {
    local name="$1"
    local description="$2"
    if ! gcloud secrets describe "${name}" --format="value(name)" 2>/dev/null; then
        gcloud secrets create "${name}" \
            --replication-policy="automatic" \
            --labels="app=contentblitz"
        echo "    Created secret: ${name}"
        echo "    Add value: echo -n 'your-key' | gcloud secrets versions add ${name} --data-file=-"
    else
        echo "    Already exists: ${name}"
    fi
}

create_secret "contentblitz-openai-key"     "OpenAI API key"
create_secret "contentblitz-anthropic-key"  "Anthropic API key"
create_secret "contentblitz-tavily-key"     "Tavily search API key"
create_secret "contentblitz-stability-key"  "Stability AI API key"

# Grant Cloud Run service account access to secrets
PROJECT_NUMBER=$(gcloud projects describe "${GCP_PROJECT_ID}" --format="value(projectNumber)")
SA_EMAIL="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "==> Granting Secret Manager access to Cloud Run service account..."
for secret in contentblitz-openai-key contentblitz-anthropic-key contentblitz-tavily-key contentblitz-stability-key; do
    gcloud secrets add-iam-policy-binding "${secret}" \
        --member="serviceAccount:${SA_EMAIL}" \
        --role="roles/secretmanager.secretAccessor" \
        --quiet
done

echo ""
echo "============================================================"
echo " GCP infrastructure setup complete!"
echo "============================================================"
echo ""
echo "Next steps:"
echo "  1. Add your API keys to Secret Manager:"
echo "     echo -n 'sk-...' | gcloud secrets versions add contentblitz-openai-key --data-file=-"
echo "     echo -n 'sk-ant-...' | gcloud secrets versions add contentblitz-anthropic-key --data-file=-"
echo "     echo -n 'tvly-...' | gcloud secrets versions add contentblitz-tavily-key --data-file=-"
echo "     echo -n 'sk-...' | gcloud secrets versions add contentblitz-stability-key --data-file=-"
echo ""
echo "  2. Wait for Redis to be ready:"
echo "     gcloud redis instances describe ${REDIS_INSTANCE} --region=${GCP_REGION} --format='value(state)'"
echo ""
echo "  3. Deploy the app:"
echo "     ./deploy.sh"
echo ""
