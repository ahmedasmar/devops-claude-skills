#!/bin/bash
# Flux 2.7+ Bootstrap Script for GitHub

set -e

# Configuration
GITHUB_USER="${GITHUB_USER:-your-org}"
GITHUB_REPO="${GITHUB_REPO:-fleet-infra}"
GITHUB_TOKEN="${GITHUB_TOKEN:-}"
CLUSTER_NAME="${CLUSTER_NAME:-production}"
CLUSTER_PATH="clusters/${CLUSTER_NAME}"

# Check prerequisites
command -v flux >/dev/null 2>&1 || { echo "flux CLI required"; exit 1; }
command -v kubectl >/dev/null 2>&1 || { echo "kubectl required"; exit 1; }

# Check GitHub token
if [ -z "$GITHUB_TOKEN" ]; then
  echo "Error: GITHUB_TOKEN environment variable not set"
  exit 1
fi

# Bootstrap Flux
echo "🚀 Bootstrapping Flux for cluster: $CLUSTER_NAME"

flux bootstrap github \
  --owner="$GITHUB_USER" \
  --repository="$GITHUB_REPO" \
  --branch=main \
  --path="$CLUSTER_PATH" \
  --personal \
  --token-auth

# Enable source-watcher (Flux 2.7+)
echo "✨ Enabling source-watcher component..."
flux install --components-extra=source-watcher

# Verify installation
echo "✅ Verifying Flux installation..."
flux check

echo "
✅ Flux bootstrapped successfully!

Next steps:
1. Add your applications to ${CLUSTER_PATH}/apps/
2. Commit and push to trigger Flux reconciliation
3. Monitor with: flux get all
"
