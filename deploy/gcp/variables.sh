#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# GCP deployment variables — edit these before running setup.sh
# ──────────────────────────────────────────────────────────────

# GCP project & region
export GCP_PROJECT_ID="contentblitz"   # <-- CHANGE THIS
export GCP_REGION="us-central1"
export GCP_ZONE="${GCP_REGION}-a"

# Artifact Registry
export AR_REPO="contentblitz"
export IMAGE_NAME="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${AR_REPO}/app"

# Cloud Run
export CLOUD_RUN_SERVICE="contentblitz"
export CLOUD_RUN_MEMORY="1Gi"
export CLOUD_RUN_CPU="1"
export CLOUD_RUN_MIN_INSTANCES="1"      # keep 1 warm instance to eliminate cold starts (~3-5s)
export CLOUD_RUN_MAX_INSTANCES="3"
export CLOUD_RUN_TIMEOUT="300"          # seconds
export CLOUD_RUN_CONCURRENCY="80"

# VPC (needed for Cloud Run ↔ Memorystore)
export VPC_NETWORK="default"
export VPC_CONNECTOR="contentblitz-vpc"
export VPC_CONNECTOR_RANGE="10.8.0.0/28"

# Memorystore Redis
export REDIS_INSTANCE="contentblitz-redis"
export REDIS_TIER="BASIC"               # BASIC (no HA) or STANDARD_HA
export REDIS_SIZE_GB="1"
export REDIS_VERSION="redis_7_0"

# Google OAuth — Secret Manager secret names
# Store values with: gcloud secrets create <name> --data-file=-
export OAUTH_CLIENT_ID_SECRET="contentblitz-google-client-id"
export OAUTH_CLIENT_SECRET_SECRET="contentblitz-google-client-secret"
# Public redirect URI (not secret — passed as plain env var)
export OAUTH_REDIRECT_URI="https://$(gcloud run services describe contentblitz \
    --region="${GCP_REGION}" --format='value(status.url)' 2>/dev/null | sed 's|https://||')/"
