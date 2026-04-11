# GitOps Best Practices (2024-2025)

## CNCF GitOps Principles (OpenGitOps v1.0)

1. **Declarative**: System desired state expressed declaratively
2. **Versioned**: State stored in version control (Git)
3. **Automated**: Changes automatically applied
4. **Continuous Reconciliation**: Software agents ensure desired state
5. **Auditable**: All changes tracked in Git history

## Repository Organization

✅ **DO**:
- Separate infrastructure from applications
- Use clear directory structure (apps/, infrastructure/, clusters/)
- Implement environment promotion (dev → staging → prod)
- Use Kustomize overlays for environment differences

❌ **DON'T**:
- Commit secrets to Git (use SOPS/Sealed Secrets/ESO)
- Use `:latest` image tags (pin to specific versions)
- Make manual cluster changes (everything through Git)
- Skip testing in lower environments

## Security Best Practices

1. **Secrets**: Never plain text, use encryption or external stores
2. **RBAC**: Least privilege for GitOps controllers
3. **Image Security**: Pin to digests, scan for vulnerabilities
4. **Network Policies**: Restrict controller traffic
5. **Audit**: Enable audit logging

## ArgoCD 3.x Specific

**Fine-Grained RBAC** (new in 3.0):
```yaml
p, role:dev, applications, *, dev/*, allow
p, role:dev, applications/resources, *, dev/*/Deployment/*, allow
```

**Resource Exclusions** (default in 3.0):
- Reduces API load
- Excludes high-churn resources (Endpoints, Leases)

**Annotation Tracking** (default):
- More reliable than labels
- Auto-migrates on sync

## Flux 2.7 Specific

**OCI Artifacts** (GA in 2.6):
- Prefer OCI over Git for generated configs
- Use digest pinning for immutability
- Sign artifacts with cosign/notation

**Image Automation** (GA in 2.7):
- Automated image updates
- GitRepository write-back

**Source-Watcher** (new in 2.7):
- Improves reconciliation efficiency
- Enable with: `--components-extra=source-watcher`

## CI/CD Integration

**Git Workflow**:
```
1. Developer commits to feature branch
2. CI runs tests, builds image
3. CI updates Git manifest with new image tag
4. Developer creates PR to main
5. GitOps controller syncs after merge
```

**Don't**: Deploy directly from CI to cluster (breaks GitOps)
**Do**: Update Git from CI, let GitOps deploy

## Monitoring & Observability

**Track**:
- Sync success rate
- Reconciliation time
- Drift detection frequency
- Failed syncs/reconciliations

**Tools**:
- Prometheus metrics (both ArgoCD and Flux)
- Grafana dashboards
- Alert on sync failures

## Image Management

✅ **Good**:
```yaml
image: myapp:v1.2.3
image: myapp@sha256:abc123...
```

❌ **Bad**:
```yaml
image: myapp:latest
image: myapp:dev
```

**Strategy**: Semantic versioning + digest pinning

## Environment Promotion

**Recommended Flow**:
```
Dev (auto-sync) → Staging (auto-sync) → Production (manual approval)
```

**Implementation**:
- Separate directories or repos per environment
- PR-based promotion
- Automated tests before promotion
- Manual approval for production

## Disaster Recovery

1. **Git is Source of Truth**: Cluster can be rebuilt from Git
2. **Backup**: Git repo + cluster state
3. **Test Recovery**: Practice cluster rebuild
4. **Document Bootstrap**: How to restore from scratch

## Performance Optimization

**ArgoCD**:
- Use ApplicationSets for multi-cluster
- Enable resource exclusions (3.x default)
- Server-side diff for large apps

**Flux**:
- Use OCI artifacts for large repos
- Enable source-watcher (2.7)
- Tune reconciliation intervals

## Common Anti-Patterns to Avoid

1. **Manual kubectl apply**: Bypasses GitOps, creates drift
2. **Multiple sources of truth**: Git should be only source
3. **Secrets in Git**: Always encrypt
4. **Direct cluster modifications**: All changes through Git
5. **No testing**: Always test in dev/staging first
6. **Missing RBAC**: Controllers need minimal permissions

## 2025 Trends

✅ **Adopt**:
- OCI artifacts (Flux)
- Workload identity (no static credentials)
- SOPS + age (over PGP)
- External Secrets Operator (dynamic secrets)
- Multi-cluster with ApplicationSets/Flux

⚠️ **Avoid**:
- Label-based tracking (use annotations - ArgoCD 3.x default)
- PGP encryption (use age)
- Long-lived service account tokens (use workload identity)
