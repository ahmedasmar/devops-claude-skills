# Multi-Cluster GitOps Management (2024-2025)

## ArgoCD ApplicationSets

**Cluster Generator** (auto-discover clusters):
```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: my-apps
spec:
  generators:
  - cluster:
      selector:
        matchLabels:
          environment: production
  template:
    spec:
      source:
        repoURL: https://github.com/org/repo
        path: apps/{{name}}
      destination:
        server: '{{server}}'
```

**Matrix Generator** (Cluster x Apps):
```yaml
generators:
- matrix:
    generators:
    - cluster: {}
    - git:
        directories:
        - path: apps/*
```

**Performance**: 83% faster than manual (30min → 5min)

## Flux Multi-Cluster

**Option 1: Flux Per Cluster**
```
cluster-1/ → Flux instance 1
cluster-2/ → Flux instance 2
```

**Option 2: Hub-and-Spoke**
```
management-cluster/
└── flux manages → cluster-1, cluster-2
```

**Setup**:
```bash
flux bootstrap github --owner=org --repository=fleet \
  --path=clusters/production --context=prod-cluster
```

## Hub-and-Spoke Pattern

**Benefits**: Centralized management, single source of truth
**Cons**: Single point of failure
**Best for**: < 50 clusters

## Workload Identity (2025 Best Practice)

**Instead of service account tokens, use**:
- AWS IRSA
- GCP Workload Identity
- Azure AD Workload Identity

No more long-lived credentials!

## Best Practices

1. **Cluster labeling** for organization
2. **Progressive rollout** (dev → staging → prod clusters)
3. **Separate repos** for cluster config vs apps
4. **Monitor sync status** across all clusters
5. **Use workload identity** (no static credentials)
