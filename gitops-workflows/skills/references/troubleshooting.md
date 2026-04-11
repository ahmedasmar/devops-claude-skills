# GitOps Troubleshooting Guide (2024-2025)

## Common ArgoCD Issues

### 1. Application OutOfSync
**Symptoms**: Application shows OutOfSync status
**Causes**: Git changes not applied, manual cluster changes
**Fix**:
```bash
argocd app sync my-app
argocd app diff my-app  # See differences
```

### 2. Annotation Tracking Migration (ArgoCD 3.x)
**Symptoms**: Resources not tracked after upgrade to 3.x
**Cause**: Default changed from labels to annotations
**Fix**: Resources auto-migrate on next sync, or force:
```bash
argocd app sync my-app --force
```

### 3. Sync Fails with "Resource is Invalid"
**Cause**: YAML validation error, CRD mismatch
**Fix**:
```bash
argocd app get my-app --show-operation
kubectl apply --dry-run=client -f manifest.yaml  # Test locally
```

### 4. Image Pull Errors
**Cause**: Registry credentials, network issues
**Fix**:
```bash
kubectl get events -n <namespace>
kubectl describe pod <pod-name> -n <namespace>
# Check image pull secret
kubectl get secret -n <namespace>
```

## Common Flux Issues

### 1. GitRepository Not Ready
**Symptoms**: source not ready, no artifact
**Causes**: Auth failure, branch doesn't exist
**Fix**:
```bash
flux get sources git
flux reconcile source git <name> -n flux-system
kubectl describe gitrepository <name> -n flux-system
```

### 2. Kustomization Build Failed
**Cause**: Invalid kustomization.yaml, missing resources
**Fix**:
```bash
flux get kustomizations
kubectl describe kustomization <name> -n flux-system
# Test locally
kustomize build <path>
```

### 3. HelmRelease Install Failed
**Cause**: Values error, chart incompatibility
**Fix**:
```bash
flux get helmreleases
kubectl logs -n flux-system -l app=helm-controller
# Test locally
helm template <chart> -f values.yaml
```

### 4. OCI Repository Issues (Flux 2.6+)
**Cause**: Registry auth, OCI artifact not found
**Fix**:
```bash
flux get sources oci
kubectl describe ocirepository <name>
# Verify artifact exists
crane digest ghcr.io/org/app:v1.0.0
```

## SOPS Decryption Failures

**Symptom**: Secret not decrypted
**Fix**:
```bash
# Check age secret exists
kubectl get secret sops-age -n flux-system

# Test decryption locally
export SOPS_AGE_KEY_FILE=key.txt
sops -d secret.enc.yaml
```

## Performance Issues

### ArgoCD Slow Syncs
**Cause**: Too many resources, inefficient queries
**Fix** (ArgoCD 3.x):
- Use default resource exclusions
- Enable server-side diff
- Increase controller replicas

### Flux Slow Reconciliation
**Cause**: Large monorepos, many sources
**Fix** (Flux 2.7+):
- Enable source-watcher
- Increase interval
- Use OCI artifacts instead of Git

## Debugging Commands

**ArgoCD**:
```bash
argocd app get <app> --refresh
argocd app logs <app>
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller
```

**Flux**:
```bash
flux logs --all-namespaces
flux check
flux get all
kubectl -n flux-system get events --sort-by='.lastTimestamp'
```

## Quick Wins

1. **Use `--dry-run`** before applying
2. **Check controller logs** first
3. **Verify RBAC** permissions
4. **Test manifests locally** (kubectl apply --dry-run, kustomize build)
5. **Check Git connectivity** (credentials, network)
