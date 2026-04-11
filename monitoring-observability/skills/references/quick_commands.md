# Quick Reference Commands

## Kubernetes Commands

```bash
# Check pod status
kubectl get pods -n <namespace>

# View pod logs
kubectl logs -f <pod-name> -n <namespace>

# Check pod resources
kubectl top pods -n <namespace>

# Describe pod for events
kubectl describe pod <pod-name> -n <namespace>

# Check recent deployments
kubectl rollout history deployment/<name> -n <namespace>
```

## Log Queries

### Elasticsearch

```json
GET /logs-*/_search
{
  "query": {
    "bool": {
      "must": [
        { "match": { "level": "error" } },
        { "range": { "@timestamp": { "gte": "now-1h" } } }
      ]
    }
  }
}
```

### Loki (LogQL)

```logql
{job="app", level="error"} |= "error" | json
```

### CloudWatch Insights

```
fields @timestamp, level, message
| filter level = "error"
| filter @timestamp > ago(1h)
```
