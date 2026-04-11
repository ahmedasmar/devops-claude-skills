# OCI Artifacts with Flux (2024-2025)

## Overview

**GA Status**: Flux v2.6 (June 2025)
**Current**: Fully supported in Flux v2.7

OCI artifacts allow storing Kubernetes manifests, Helm charts, and Kustomize overlays in container registries instead of Git.

## Benefits

✅ **Decoupled from Git**: No Git dependency for deployment
✅ **Immutable**: Content-addressable by digest
✅ **Standard**: Uses OCI spec, works with any OCI registry
✅ **Signature Verification**: Native support for cosign/notation
✅ **Performance**: Faster than Git for large repos

## OCIRepository Resource

```yaml
apiVersion: source.toolkit.fluxcd.io/v1beta2
kind: OC IRepository
metadata:
  name: my-app-oci
  namespace: flux-system
spec:
  interval: 5m
  url: oci://ghcr.io/org/app-config
  ref:
    tag: v1.0.0
    # or digest:
    # digest: sha256:abc123...
    # or semver:
    # semver: ">=1.0.0 <2.0.0"
  provider: generic  # or azure, aws, gcp
  verify:
    provider: cosign
    secretRef:
      name: cosign-public-key
```

## Using with Kustomization

```yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: my-app
spec:
  interval: 10m
  sourceRef:
    kind: OCIRepository
    name: my-app-oci
  path: ./
  prune: true
```

## Using with HelmRelease

**OCIRepository for Helm charts**:
```yaml
apiVersion: source.toolkit.fluxcd.io/v1beta2
kind: OCIRepository
metadata:
  name: podinfo-oci
spec:
  interval: 5m
  url: oci://ghcr.io/stefanprodan/charts/podinfo
  ref:
    semver: ">=6.0.0"
---
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: podinfo
spec:
  chart:
    spec:
      chart: podinfo
      sourceRef:
        kind: OCIRepository
        name: podinfo-oci
```

## Publishing OCI Artifacts

**Using flux CLI**:
```bash
# Build and push Kustomize overlay
flux push artifact oci://ghcr.io/org/app-config:v1.0.0 \
  --path="./kustomize" \
  --source="$(git config --get remote.origin.url)" \
  --revision="$(git rev-parse HEAD)"

# Build and push Helm chart
flux push artifact oci://ghcr.io/org/charts/myapp:1.0.0 \
  --path="./charts/myapp" \
  --source="$(git config --get remote.origin.url)" \
  --revision="$(git rev-parse HEAD)"
```

## Signature Verification

### Using cosign

**Sign artifact**:
```bash
cosign sign ghcr.io/org/app-config:v1.0.0
```

**Verify in Flux**:
```yaml
spec:
  verify:
    provider: cosign
    secretRef:
      name: cosign-public-key
```

### Using notation

**Sign artifact**:
```bash
notation sign ghcr.io/org/app-config:v1.0.0
```

**Verify in Flux**:
```yaml
spec:
  verify:
    provider: notation
    secretRef:
      name: notation-config
```

## Workload Identity

**Instead of static credentials, use cloud provider workload identity**:

**AWS IRSA**:
```yaml
spec:
  provider: aws
  # No credentials needed - uses pod's IAM role
```

**GCP Workload Identity**:
```yaml
spec:
  provider: gcp
  # No credentials needed - uses service account binding
```

**Azure Workload Identity**:
```yaml
spec:
  provider: azure
  # No credentials needed - uses managed identity
```

## Best Practices (2025)

1. **Use digest pinning** for production:
   ```yaml
   ref:
     digest: sha256:abc123...
   ```

2. **Sign all artifacts**:
   ```bash
   flux push artifact ... | cosign sign
   ```

3. **Use semver for automated updates**:
   ```yaml
   ref:
     semver: ">=1.0.0 <2.0.0"
   ```

4. **Leverage workload identity** (no static credentials)

5. **Prefer OCI for generated configs** (Jsonnet, CUE, Helm output)

## When to Use OCI vs Git

**Use OCI Artifacts when**:
- ✅ Storing generated configurations (Jsonnet, CUE output)
- ✅ Need immutable, content-addressable storage
- ✅ Want signature verification
- ✅ Large repos (performance)
- ✅ Decoupling from Git

**Use Git when**:
- ✅ Source of truth for manifests
- ✅ Need Git workflow (PRs, reviews)
- ✅ Audit trail important
- ✅ Team collaboration

## Common Pattern: Hybrid Approach

```
Git (source of truth)
  ↓
CI builds/generates manifests
  ↓
Push to OCI registry (signed)
  ↓
Flux pulls from OCI (verified)
  ↓
Deploy to cluster
```

## Migration from Git to OCI

**Before (Git)**:
```yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: GitRepository
metadata:
  name: my-app
spec:
  url: https://github.com/org/repo
  ref:
    branch: main
```

**After (OCI)**:
```yaml
apiVersion: source.toolkit.fluxcd.io/v1beta2
kind: OCIRepository
metadata:
  name: my-app-oci
spec:
  url: oci://ghcr.io/org/app-config
  ref:
    tag: v1.0.0
```

**Update Kustomization/HelmRelease** sourceRef to point to OCIRepository

## Supported Registries

- ✅ GitHub Container Registry (ghcr.io)
- ✅ Docker Hub
- ✅ AWS ECR
- ✅ Google Artifact Registry
- ✅ Azure Container Registry
- ✅ Harbor
- ✅ GitLab Container Registry

## Troubleshooting

**Artifact not found**:
```bash
flux get sources oci
kubectl describe ocirepository <name>

# Verify artifact exists
crane digest ghcr.io/org/app:v1.0.0
```

**Authentication failures**:
```bash
# Check secret
kubectl get secret -n flux-system

# Test manually
crane manifest ghcr.io/org/app:v1.0.0
```

**Signature verification fails**:
```bash
# Verify locally
cosign verify ghcr.io/org/app:v1.0.0

# Check public key secret
kubectl get secret cosign-public-key -o yaml
```

## 2025 Recommendation

**Adopt OCI artifacts** for:
- Helm charts (already standard)
- Generated manifests (CI output)
- Multi-environment configs

**Keep Git for**:
- Source manifests
- Infrastructure definitions
- Team collaboration workflows
