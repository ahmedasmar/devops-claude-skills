# Progressive Delivery with GitOps (2024-2025)

## Argo Rollouts (with ArgoCD)

**Current Focus**: Kubernetes-native progressive delivery

**Deployment Strategies**:

### 1. Canary
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
      - pause: {duration: 5m}
      - setWeight: 50
      - pause: {duration: 5m}
      - setWeight: 100
```

### 2. Blue-Green
```yaml
spec:
  strategy:
    blueGreen:
      activeService: my-app
      previewService: my-app-preview
      autoPromotionEnabled: false
```

### 3. Analysis with Metrics
```yaml
spec:
  strategy:
    canary:
      analysis:
        templates:
        - templateName: success-rate
        args:
        - name: service-name
          value: my-app
```

**Metric Providers**: Prometheus, Datadog, New Relic, CloudWatch

## Flagger (with Flux)

**Installation**:
```bash
flux install
kubectl apply -k github.com/fluxcd/flagger//kustomize/linkerd
```

**Canary with Flagger**:
```yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: my-app
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  service:
    port: 9898
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

## Best Practices

1. **Start with Manual Approval** (autoPromotionEnabled: false)
2. **Monitor Key Metrics** (error rate, latency, saturation)
3. **Set Conservative Steps** (10%, 25%, 50%, 100%)
4. **Define Rollback Criteria** (error rate > 1%)
5. **Test in Staging First**

## 2025 Recommendation

**For ArgoCD users**: Argo Rollouts (tight integration, UI support)
**For Flux users**: Flagger (CNCF project, modular design)
