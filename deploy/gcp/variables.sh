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
export CLOUD_RUN_MIN_INSTANCES="0"      # scale to zero when idle (saves cost)
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
