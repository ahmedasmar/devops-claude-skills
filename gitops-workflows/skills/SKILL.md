---
name: gitops-workflows
description: "GitOps deployment workflows with ArgoCD and Flux. Use this skill whenever the user mentions GitOps, ArgoCD, Flux, Flagger, Argo Rollouts, or continuous deployment to Kubernetes. Triggers include setting up ArgoCD or Flux from scratch, designing Git repository structures (monorepo vs polyrepo, app-of-apps), deploying to multiple clusters with ApplicationSets, managing secrets in Git (SOPS, Sealed Secrets, External Secrets Operator), implementing canary or blue-green deployments, troubleshooting sync or reconciliation issues, working with OCI artifacts, and comparing ArgoCD vs Flux."
---

# GitOps Workflows

## Core Workflow: GitOps Implementation

Use this decision tree to determine your starting point:

```
Do you have GitOps installed?
├─ NO → Need to choose a tool
│   └─ Want UI + easy onboarding? → ArgoCD (Workflow 1)
│   └─ Want modularity + platform engineering? → Flux (Workflow 2)
└─ YES → What's your goal?
    ├─ Sync issues / troubleshooting → Workflow 7
    ├─ Multi-cluster deployment → Workflow 4
    ├─ Secrets management → Workflow 5
    ├─ Progressive delivery → Workflow 6
    ├─ Repository structure → Workflow 3
    └─ Tool comparison → Read references/argocd_vs_flux.md
```

---

## 1. Initial Setup: ArgoCD 3.x

**Latest Version**: v3.1.9 (stable), v3.2.0-rc4 (October 2025)

### Quick Install

```bash
# Create namespace
kubectl create namespace argocd

# Install ArgoCD 3.x
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v3.1.9/manifests/install.yaml

# Get admin password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d

# Port forward to access UI
kubectl port-forward svc/argocd-server -n argocd 8080:443
# Access: https://localhost:8080
```

**→ Template**: [assets/argocd/install-argocd-3.x.yaml](assets/argocd/install-argocd-3.x.yaml)

### ArgoCD 3.x Key Changes

- **Breaking**: Annotation-based tracking (default, was labels), RBAC logs enforcement enabled, legacy metrics removed
- **New**: Fine-grained RBAC (per-resource permissions), better defaults (resource exclusions), secrets operators endorsement

### Deploy Your First Application

```bash
# CLI method
argocd app create guestbook \
  --repo https://github.com/argoproj/argocd-example-apps.git \
  --path guestbook \
  --dest-server https://kubernetes.default.svc \
  --dest-namespace default

# Sync application
argocd app sync guestbook
```

### Health Check

```bash
# List all applications and their sync/health status
argocd app list

# Get detailed status for a specific application
argocd app get <app-name>

# Check applications via kubectl (no ArgoCD CLI needed)
kubectl get applications.argoproj.io -A
```

---

## 2. Initial Setup: Flux 2.7

**Latest Version**: v2.7.1 (October 2025)

### Quick Install

```bash
# Install Flux CLI
brew install fluxcd/tap/flux  # macOS
# or: curl -s https://fluxcd.io/install.sh | sudo bash

# Check prerequisites
flux check --pre

# Bootstrap Flux (GitHub)
export GITHUB_TOKEN=<your-token>
flux bootstrap github \
  --owner=<org> \
  --repository=fleet-infra \
  --branch=main \
  --path=clusters/production \
  --personal

# Enable source-watcher (Flux 2.7+)
flux install --components-extra=source-watcher
```

**→ Template**: [assets/flux/flux-bootstrap-github.sh](assets/flux/flux-bootstrap-github.sh)

### Flux 2.7 New Features

- ✅ Image automation GA
- ✅ ExternalArtifact and ArtifactGenerator APIs
- ✅ Source-watcher component for better performance
- ✅ OpenTelemetry tracing support
- ✅ CEL expressions for readiness evaluation

### Deploy Your First Application

```yaml
# gitrepository.yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: GitRepository
metadata:
  name: podinfo
  namespace: flux-system
spec:
  interval: 1m
  url: https://github.com/stefanprodan/podinfo
  ref:
    branch: master
---
# kustomization.yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: podinfo
  namespace: flux-system
spec:
  interval: 5m
  path: "./kustomize"
  prune: true
  sourceRef:
    kind: GitRepository
    name: podinfo
```

### Health Check

```bash
# Check all Flux resources across namespaces
flux get all -A

# Check Git sources
flux get sources git

# Check kustomization status
flux get kustomizations
```

---

## 3. Repository Structure Design

**Decision: Monorepo or Polyrepo?**

### Monorepo Pattern

**Best for**: Startups, small teams (< 20 apps), single team

```
gitops-repo/
├── apps/
│   ├── frontend/
│   ├── backend/
│   └── database/
├── infrastructure/
│   ├── ingress/
│   ├── monitoring/
│   └── secrets/
└── clusters/
    ├── dev/
    ├── staging/
    └── production/
```

### Polyrepo Pattern

**Best for**: Large orgs, multiple teams, clear boundaries

```
infrastructure-repo/     (Platform team)
app-team-1-repo/        (Team 1)
app-team-2-repo/        (Team 2)
```

### Environment Structure (Kustomize)

```
app/
├── base/
│   ├── deployment.yaml
│   ├── service.yaml
│   └── kustomization.yaml
└── overlays/
    ├── dev/
    │   ├── kustomization.yaml
    │   └── replica-patch.yaml
    ├── staging/
    └── production/
```

**→ Reference**: [references/repo_patterns.md](references/repo_patterns.md) | **→ Script**: `python3 scripts/validate_gitops_repo.py /path/to/repo`

---

## 4. Multi-Cluster Deployments

### ArgoCD ApplicationSets

**Cluster Generator** (deploy to all clusters):

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: cluster-apps
spec:
  generators:
  - cluster:
      selector:
        matchLabels:
          environment: production
  template:
    metadata:
      name: '{{name}}-myapp'
    spec:
      source:
        repoURL: https://github.com/org/apps
        path: myapp
      destination:
        server: '{{server}}'
```

**→ Template**: [assets/applicationsets/cluster-generator.yaml](assets/applicationsets/cluster-generator.yaml)

**Performance Benefit**: 83% faster deployments (30min → 5min)

### Generate ApplicationSets

```bash
# Cluster generator
python3 scripts/applicationset_generator.py cluster \
  --name my-apps \
  --repo-url https://github.com/org/repo \
  --output appset.yaml

# Matrix generator (cluster x apps)
python3 scripts/applicationset_generator.py matrix \
  --name my-apps \
  --cluster-label production \
  --directories app1,app2,app3 \
  --output appset.yaml
```

**→ Script**: [scripts/applicationset_generator.py](scripts/applicationset_generator.py)

### Flux Multi-Cluster

**Hub-and-Spoke**: Management cluster manages all clusters

```bash
# Bootstrap each cluster
flux bootstrap github --context prod-cluster --path clusters/production
flux bootstrap github --context staging-cluster --path clusters/staging
```

**→ Reference**: [references/multi_cluster.md](references/multi_cluster.md)

---

## 5. Secrets Management

**Never commit plain secrets to Git.** Choose a solution:

### Decision Matrix

| Solution | Complexity | Best For | 2025 Trend |
|----------|-----------|----------|------------|
| **SOPS + age** | Medium | Git-centric, flexible | ↗️ Preferred |
| **External Secrets Operator** | Medium | Cloud-native, dynamic | ↗️ Growing |
| **Sealed Secrets** | Low | Simple, GitOps-first | → Stable |

### Option 1: SOPS + age (Recommended 2025)

**Setup**:
```bash
# Generate age key
age-keygen -o key.txt
# Public key: age1...

# Create .sops.yaml
cat <<EOF > .sops.yaml
creation_rules:
  - path_regex: .*.yaml
    encrypted_regex: ^(data|stringData)$
    age: age1ql3z7hjy54pw3hyww5ayyfg7zqgvc7w3j2elw8zmrj2kg5sfn9aqmcac8p
EOF

# Encrypt secret
kubectl create secret generic my-secret --dry-run=client -o yaml \
  --from-literal=password=supersecret > secret.yaml
sops -e secret.yaml > secret.enc.yaml

# Commit encrypted version
git add secret.enc.yaml .sops.yaml
```

**→ Template**: [assets/secrets/sops-age-config.yaml](assets/secrets/sops-age-config.yaml)

### Option 2: External Secrets Operator (v0.20+)

**Best for**: Cloud-native apps, dynamic secrets, automatic rotation

### Option 3: Sealed Secrets

**Best for**: Simple setup, static secrets, no external dependencies

**→ Reference**: [references/secret_management.md](references/secret_management.md)

### Audit Secrets

```bash
python3 scripts/secret_audit.py /path/to/repo
```

**→ Script**: [scripts/secret_audit.py](scripts/secret_audit.py)

---

## 6. Progressive Delivery

### Argo Rollouts (with ArgoCD)

**Canary Deployment**:
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: my-app
spec:
  strategy:
    canary:
      steps:
      - setWeight: 20
      - pause: {duration: 2m}
      - setWeight: 50
      - pause: {duration: 2m}
      - setWeight: 100
```

**→ Template**: [assets/progressive-delivery/argo-rollouts-canary.yaml](assets/progressive-delivery/argo-rollouts-canary.yaml)

### Flagger (with Flux)

**Canary with Metrics Analysis**:
```yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: my-app
spec:
  analysis:
    interval: 1m
    threshold: 5
    maxWeight: 50
    stepWeight: 10
    metrics:
    - name: request-success-rate
      thresholdRange:
        min: 99
```

**→ Reference**: [references/progressive_delivery.md](references/progressive_delivery.md)

---

## 7. Troubleshooting

### Common Issues

**ArgoCD OutOfSync**:
```bash
# Check differences
argocd app diff my-app

# Sync application
argocd app sync my-app

# Check health
argocd app list
argocd app get my-app
```

**Flux Not Reconciling**:
```bash
# Check resources
flux get all

# Check specific kustomization
flux get kustomizations
kubectl describe kustomization my-app -n flux-system

# Force reconcile
flux reconcile kustomization my-app
```

**Detect Drift**:
```bash
# ArgoCD drift detection
argocd app diff my-app

# Kubernetes manifest drift detection
kubectl diff -f <manifest.yaml>
```

**→ Reference**: [references/troubleshooting.md](references/troubleshooting.md)

---

## 8. OCI Artifacts (Flux 2.6+, GA June 2025)

### Use OCIRepository for Helm Charts

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
  verify:
    provider: cosign
```

**→ Template**: [assets/flux/oci-helmrelease.yaml](assets/flux/oci-helmrelease.yaml)

### Verify OCI Artifacts

```bash
# Check OCI sources managed by Flux
flux get sources oci

# Get detailed OCI repository status via kubectl
kubectl get ocirepository -A -o json
```

**→ Reference**: [references/oci_artifacts.md](references/oci_artifacts.md)

## Quick Reference Commands

### ArgoCD

```bash
argocd app list                    # List applications
argocd app get <app-name>          # Get application details
argocd app sync <app-name>         # Sync application
argocd app diff <app-name>         # View diff
argocd app delete <app-name>       # Delete application
```

### Flux

```bash
flux check                                    # Check Flux status
flux get all                                  # Get all resources
flux reconcile source git <name>              # Reconcile immediately
flux reconcile kustomization <name>           # Reconcile kustomization
flux suspend kustomization <name>             # Suspend
flux resume kustomization <name>              # Resume
flux export source git --all > sources.yaml   # Export resources
```

## Resources Summary

**Scripts**: `applicationset_generator.py` | `secret_audit.py` | `validate_gitops_repo.py`

**References**: `argocd_vs_flux.md` | `repo_patterns.md` | `secret_management.md` | `progressive_delivery.md` | `multi_cluster.md` | `troubleshooting.md` | `best_practices.md` | `oci_artifacts.md`

**Templates**: `argocd/install-argocd-3.x.yaml` | `applicationsets/cluster-generator.yaml` | `flux/flux-bootstrap-github.sh` | `flux/oci-helmrelease.yaml` | `secrets/sops-age-config.yaml` | `progressive-delivery/argo-rollouts-canary.yaml`
