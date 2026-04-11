# Runbook: [Alert Name]

## Overview

**Alert Name**: [e.g., HighLatency, ServiceDown, ErrorBudgetBurn]

**Severity**: [Critical | Warning | Info]

**Team**: [e.g., Backend, Platform, Database]

**Component**: [e.g., API Gateway, User Service, PostgreSQL]

**What it means**: [One-line description of what this alert indicates]

**User impact**: [How does this affect users? High/Medium/Low]

**Urgency**: [How quickly must this be addressed? Immediate/Hours/Days]

---

## Alert Details

### When This Alert Fires

This alert fires when:
- [Specific condition, e.g., "P95 latency exceeds 500ms for 10 minutes"]
- [Any additional conditions]

### Symptoms

Users will experience:
- [ ] Slow response times
- [ ] Errors or failures
- [ ] Service unavailable
- [ ] [Other symptoms]

### Probable Causes

Common causes include:
1. **[Cause 1]**: [Description]
   - Example: Database overload due to slow queries
2. **[Cause 2]**: [Description]
   - Example: Memory leak causing OOM errors
3. **[Cause 3]**: [Description]
   - Example: Upstream service degradation

---

## Investigation Steps

### 1. Check Service Health

**Dashboard**: [Link to primary dashboard]

**Key metrics to check**:
```bash
# Request rate
sum(rate(http_requests_total[5m]))

# Error rate
sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))

# Latency (p95, p99)
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))
```

**What to look for**:
- [ ] Has traffic spiked recently?
- [ ] Is error rate elevated?
- [ ] Are any endpoints particularly slow?

### 2. Check Recent Changes

**Deployments**:
```bash
# Kubernetes
kubectl rollout history deployment/[service-name] -n [namespace]

# Check when last deployed
kubectl get pods -n [namespace] -o wide | grep [service-name]
```

**What to look for**:
- [ ] Was there a recent deployment?
- [ ] Did alert start after deployment?
- [ ] Any configuration changes?

### 3. Check Logs

**Log query** (adjust for your log system):
```bash
# Kubernetes
kubectl logs deployment/[service-name] -n [namespace] --tail=100 | grep ERROR

# Elasticsearch/Kibana
GET /logs-*/_search
{
  "query": {
    "bool": {
      "must": [
        { "match": { "service": "[service-name]" } },
        { "match": { "level": "error" } },
        { "range": { "@timestamp": { "gte": "now-30m" } } }
      ]
    }
  }
}

# Loki/LogQL
{job="[service-name]"} |= "error" | json | level="error"
```

**What to look for**:
- [ ] Repeated error messages
- [ ] Stack traces
- [ ] Connection errors
- [ ] Timeout errors

### 4. Check Dependencies

**Database**:
```bash
# Check active connections
SELECT count(*) FROM pg_stat_activity WHERE state = 'active';

# Check slow queries
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE state = 'active' AND now() - pg_stat_activity.query_start > interval '5 seconds';
```

**External APIs**:
- [ ] Check status pages: [Link to status pages]
- [ ] Check API error rates in dashboard
- [ ] Test API endpoints manually

**Cache** (Redis/Memcached):
```bash
# Redis info
redis-cli -h [host] INFO stats

# Check memory usage
redis-cli -h [host] INFO memory
```

### 5. Check Resource Usage

**CPU and Memory**:
```bash
# Kubernetes
kubectl top pods -n [namespace] | grep [service-name]

# Node metrics
kubectl top nodes
```

**Prometheus queries**:
```promql
# CPU usage by pod
sum(rate(container_cpu_usage_seconds_total{pod=~"[service-name].*"}[5m])) by (pod)

# Memory usage by pod
sum(container_memory_usage_bytes{pod=~"[service-name].*"}) by (pod)
```

**What to look for**:
- [ ] CPU throttling
- [ ] Memory approaching limits
- [ ] Disk space issues

### 6. Check Traces (if available)

**Trace query**:
```bash
# Jaeger
# Search for slow traces (> 1s) in last 30 minutes

# Tempo/TraceQL
{ duration > 1s && resource.service.name = "[service-name]" }
```

**What to look for**:
- [ ] Which operation is slow?
- [ ] Where is time spent? (DB, external API, service logic)
- [ ] Any N+1 query patterns?

---

## Common Scenarios and Solutions

### Scenario 1: Recent Deployment Caused Issue

**Symptoms**:
- Alert started immediately after deployment
- Error logs correlate with new code

**Solution**:
```bash
# Rollback deployment
kubectl rollout undo deployment/[service-name] -n [namespace]

# Verify rollback succeeded
kubectl rollout status deployment/[service-name] -n [namespace]

# Monitor for alert resolution
```

**Follow-up**:
- [ ] Create incident report
- [ ] Review deployment process
- [ ] Add pre-deployment checks

### Scenario 2: Database Performance Issue

**Symptoms**:
- Slow query logs show problematic queries
- Database CPU or connection pool exhausted

**Solution**:
```bash
# Identify slow query
# Kill long-running query (use with caution)
SELECT pg_cancel_backend([pid]);

# Or terminate if cancel doesn't work
SELECT pg_terminate_backend([pid]);

# Add index if missing (in maintenance window)
CREATE INDEX CONCURRENTLY idx_name ON table_name (column_name);
```

**Follow-up**:
- [ ] Add query performance test
- [ ] Review and optimize query
- [ ] Consider read replicas

### Scenario 3: Memory Leak

**Symptoms**:
- Memory usage gradually increasing
- Eventually OOMKilled
- Restarts temporarily fix issue

**Solution**:
```bash
# Immediate: Restart pods
kubectl rollout restart deployment/[service-name] -n [namespace]

# Increase memory limits (temporary)
kubectl set resources deployment/[service-name] -n [namespace] \
  --limits=memory=2Gi
```

**Follow-up**:
- [ ] Profile application for memory leaks
- [ ] Add memory usage alerts
- [ ] Fix root cause

### Scenario 4: Traffic Spike / DDoS

**Symptoms**:
- Sudden traffic increase
- Traffic from unusual sources
- High CPU/memory across all instances

**Solution**:
```bash
# Scale up immediately
kubectl scale deployment/[service-name] -n [namespace] --replicas=10

# Enable rate limiting at load balancer level
# (Specific steps depend on LB)

# Block suspicious IPs if confirmed DDoS
# (Use WAF or network policies)
```

**Follow-up**:
- [ ] Implement rate limiting
- [ ] Add DDoS protection (CloudFlare, WAF)
- [ ] Set up auto-scaling

### Scenario 5: Upstream Service Degradation

**Symptoms**:
- Errors calling external API
- Timeouts to upstream service
- Upstream status page shows issues

**Solution**:
```bash
# Enable circuit breaker (if available)
# Adjust timeout configuration
# Switch to backup service/cached data

# Monitor external service
# Check status page: [Link]
```

**Follow-up**:
- [ ] Implement circuit breaker pattern
- [ ] Add fallback mechanisms
- [ ] Set up external service monitoring

---

## Immediate Actions (< 5 minutes)

These should be done first to mitigate impact:

1. **[Action 1]**: [e.g., "Scale up service"]
   ```bash
   kubectl scale deployment/[service] --replicas=10
   ```

2. **[Action 2]**: [e.g., "Rollback deployment"]
   ```bash
   kubectl rollout undo deployment/[service]
   ```

3. **[Action 3]**: [e.g., "Enable circuit breaker"]

---

## Short-term Actions (< 30 minutes)

After immediate mitigation:

1. **[Action 1]**: [e.g., "Investigate root cause"]
2. **[Action 2]**: [e.g., "Optimize slow query"]
3. **[Action 3]**: [e.g., "Clear cache if stale"]

---

## Long-term Actions (Post-Incident)

Preventive measures:

1. **[Action 1]**: [e.g., "Add circuit breaker"]
2. **[Action 2]**: [e.g., "Implement auto-scaling"]
3. **[Action 3]**: [e.g., "Add query performance tests"]
4. **[Action 4]**: [e.g., "Update alert thresholds"]

---

## Escalation

If issue persists after 30 minutes:

**Escalation Path**:
1. **Primary oncall**: @[username] ([slack/email])
2. **Team lead**: @[username] ([slack/email])
3. **Engineering manager**: @[username] ([slack/email])
4. **Incident commander**: @[username] ([slack/email])

**Communication**:
- **Slack channel**: #[incidents-channel]
- **Status page**: [Link]
- **Incident tracking**: [Link to incident management tool]

---

## Related Runbooks

- [Related Runbook 1]
- [Related Runbook 2]
- [Related Runbook 3]

## Related Dashboards

- [Main Service Dashboard]
- [Resource Usage Dashboard]
- [Dependency Dashboard]

## Related Documentation

- [Architecture Diagram]
- [Service Documentation]
- [API Documentation]

---

## Recent Incidents

| Date | Duration | Root Cause | Resolution | Ticket |
|------|----------|------------|------------|--------|
| 2024-10-15 | 23 min | Database pool exhausted | Increased pool size | INC-123 |
| 2024-09-30 | 45 min | Memory leak | Fixed code, restarted | INC-120 |

---

## Runbook Metadata

**Last Updated**: [Date]

**Owner**: [Team name]

**Reviewers**: [Names]

**Next Review**: [Date]

---

## Notes

- This runbook should be reviewed quarterly
- Update after each incident to capture new learnings
- Keep investigation steps concise and actionable
- Include actual commands that can be copy-pasted
