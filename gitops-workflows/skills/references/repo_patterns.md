# GitOps Repository Patterns (2024-2025)

## Monorepo vs Polyrepo

### Monorepo Pattern

**Structure**:
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

**Pros**:
- Single source of truth
- Atomic changes across apps
- Easier to start with
- Simpler CI/CD

**Cons**:
- Scaling issues (>100 apps)
- RBAC complexity
- Large repo size
- Blast radius concerns

**Best for**: Startups, small teams (< 20 apps), single team ownership

### Polyrepo Pattern

**Structure**:
```
infrastructure-repo/     (Platform team)
app-team-1-repo/        (Team 1)
app-team-2-repo/        (Team 2)
cluster-config-repo/    (Platform team)
```

**Pros**:
- Clear ownership boundaries
- Better RBAC (repo-level)
- Scales to 100s of apps
- Team autonomy

**Cons**:
- More complex setup
- Cross-repo dependencies
- Multiple CI/CD pipelines

**Best for**: Large orgs, multiple teams, clear separation of concerns

## Common Patterns

### 1. Repo Per Team
- Each team has own repo
- Platform team manages infra repo
- Hub cluster manages all

### 2. Repo Per App
- Each app in separate repo
- Good for microservices
- Maximum autonomy

### 3. Hybrid (Recommended)
- Infrastructure monorepo (platform team)
- Application polyrepo (dev teams)
- Best of both worlds

## App-of-Apps Pattern (ArgoCD)

**Root Application**:
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: root
spec:
  source:
    repoURL: https://github.com/org/gitops
    path: apps/
  destination:
    server: https://kubernetes.default.svc
```

**Apps Directory**:
```
apps/
├── app1.yaml    (Application manifest)
├── app2.yaml
└── app3.yaml
```

**Benefits**: Centralized management, single sync point

## Environment Structure

### Option 1: Directory Per Environment
```
apps/
├── base/
│   └── kustomization.yaml
└── overlays/
    ├── dev/
    ├── staging/
    └── production/
```

### Option 2: Branch Per Environment
```
main branch      → production
staging branch   → staging
dev branch       → development
```

**Don't Repeat YAML**: Use Kustomize bases + overlays

## Flux Repository Organization

**Recommended Structure**:
```
flux-repo/
├── clusters/
│   ├── production/
│   │   ├── flux-system/
│   │   ├── apps.yaml
│   │   └── infrastructure.yaml
│   └── staging/
├── apps/
│   └── podinfo/
│       ├── kustomization.yaml
│       └── release.yaml
└── infrastructure/
    └── sources/
        ├── gitrepositories.yaml
        └── ocirepositories.yaml
```

## Kustomize vs Helm in GitOps

**Kustomize** (recommended for GitOps):
- Native Kubernetes
- Declarative patches
- No templating language

**Helm** (when necessary):
- Third-party charts
- Complex applications
- Need parameterization

**Best Practice**: Kustomize for your apps, Helm for third-party

## Promotion Strategies

### 1. Manual PR-based
```
dev/ → (PR) → staging/ → (PR) → production/
```

### 2. Automated with CI
```
dev/ → (auto-promote on tests pass) → staging/ → (manual approval) → production/
```

### 3. Progressive with Canary
```
production/stable/ → canary deployment → production/all/
```

## 2024-2025 Recommendations

1. **Start with monorepo**, migrate to polyrepo when needed
2. **Use Kustomize bases + overlays** (don't repeat YAML)
3. **Separate infrastructure from applications**
4. **Implement promotion workflows** (dev → staging → prod)
5. **Never commit directly to production** (always PR)
