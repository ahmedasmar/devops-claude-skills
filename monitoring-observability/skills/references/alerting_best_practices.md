# Alerting Best Practices

## Core Principles

### 1. Every Alert Should Be Actionable
If you can't do something about it, don't alert on it.

❌ Bad: `Alert: CPU > 50%` (What action should be taken?)
✅ Good: `Alert: API latency p95 > 2s for 10m` (Investigate/scale up)

### 2. Alert on Symptoms, Not Causes
Alert on what users experience, not underlying components.

❌ Bad: `Database connection pool 80% full`
✅ Good: `Request latency p95 > 1s` (which might be caused by DB pool)

### 3. Alert on SLO Violations
Tie alerts to Service Level Objectives.

✅ `Error rate exceeds 0.1% (SLO: 99.9% availability)`

### 4. Reduce Noise
Alert fatigue is real. Only page for critical issues.

**Alert Severity Levels**:
- **Critical**: Page on-call immediately (user-facing issue)
- **Warning**: Create ticket, review during business hours
- **Info**: Log for awareness, no action needed

---

## Alert Design Patterns

### Pattern 1: Multi-Window Multi-Burn-Rate

Google's recommended SLO alerting approach.

**Concept**: Alert when error budget burn rate is high enough to exhaust the budget too quickly.

```yaml
# Fast burn (6% of budget in 1 hour)
- alert: FastBurnRate
  expr: |
    sum(rate(http_requests_total{status=~"5.."}[1h]))
      /
    sum(rate(http_requests_total[1h]))
    > (14.4 * 0.001)  # 14.4x burn rate for 99.9% SLO
  for: 2m
  labels:
    severity: critical

# Slow burn (6% of budget in 6 hours)
- alert: SlowBurnRate
  expr: |
    sum(rate(http_requests_total{status=~"5.."}[6h]))
      /
    sum(rate(http_requests_total[6h]))
    > (6 * 0.001)  # 6x burn rate for 99.9% SLO
  for: 30m
  labels:
    severity: warning
```

**Burn Rate Multipliers for 99.9% SLO (0.1% error budget)**:
- 1 hour window, 2m grace: 14.4x burn rate
- 6 hour window, 30m grace: 6x burn rate
- 3 day window, 6h grace: 1x burn rate

### Pattern 2: Rate of Change
Alert when metrics change rapidly.

```yaml
- alert: TrafficSpike
  expr: |
    sum(rate(http_requests_total[5m]))
      >
    1.5 * sum(rate(http_requests_total[5m] offset 1h))
  for: 10m
  annotations:
    summary: "Traffic increased by 50% compared to 1 hour ago"
```

### Pattern 3: Threshold with Hysteresis
Prevent flapping with different thresholds for firing and resolving.

```yaml
# Fire at 90%, resolve at 70%
- alert: HighCPU
  expr: cpu_usage > 90
  for: 5m

- alert: HighCPU_Resolved
  expr: cpu_usage < 70
  for: 5m
```

### Pattern 4: Absent Metrics
Alert when expected metrics stop being reported (service down).

```yaml
- alert: ServiceDown
  expr: absent(up{job="my-service"})
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "Service {{ $labels.job }} is not reporting metrics"
```

### Pattern 5: Aggregate Alerts
Alert on aggregate performance across multiple instances.

```yaml
- alert: HighOverallErrorRate
  expr: |
    sum(rate(http_requests_total{status=~"5.."}[5m]))
      /
    sum(rate(http_requests_total[5m]))
    > 0.05
  for: 10m
  annotations:
    summary: "Overall error rate is {{ $value | humanizePercentage }}"
```

---

## Alert Annotation Best Practices

### Required Fields

**summary**: One-line description of the issue
```yaml
summary: "High error rate on {{ $labels.service }}: {{ $value | humanizePercentage }}"
```

**description**: Detailed explanation with context
```yaml
description: |
  Error rate on {{ $labels.service }} is {{ $value | humanizePercentage }},
  which exceeds the threshold of 1% for more than 10 minutes.

  Current value: {{ $value }}
  Runbook: https://runbooks.example.com/high-error-rate
```

**runbook_url**: Link to investigation steps
```yaml
runbook_url: "https://runbooks.example.com/alerts/{{ $labels.alertname }}"
```

### Optional but Recommended

**dashboard**: Link to relevant dashboard
```yaml
dashboard: "https://grafana.example.com/d/service-dashboard?var-service={{ $labels.service }}"
```

**logs**: Link to logs
```yaml
logs: "https://kibana.example.com/app/discover#/?_a=(query:(query_string:(query:'service:{{ $labels.service }}')))"
```

---

## Alert Label Best Practices

### Required Labels

**severity**: Critical, warning, or info
```yaml
labels:
  severity: critical
```

**team**: Who should handle this alert
```yaml
labels:
  team: platform
  severity: critical
```

**component**: What part of the system
```yaml
labels:
  component: api-gateway
  severity: warning
```

### Example Complete Alert
```yaml
- alert: HighLatency
  expr: |
    histogram_quantile(0.95,
      sum(rate(http_request_duration_seconds_bucket[5m])) by (le, service)
    ) > 1
  for: 10m
  labels:
    severity: warning
    team: backend
    component: api
    environment: "{{ $labels.environment }}"
  annotations:
    summary: "High latency on {{ $labels.service }}"
    description: |
      P95 latency on {{ $labels.service }} is {{ $value }}s, exceeding 1s threshold.

      This may impact user experience. Check recent deployments and database performance.

      Current p95: {{ $value }}s
      Threshold: 1s
      Duration: 10m+
    runbook_url: "https://runbooks.example.com/high-latency"
    dashboard: "https://grafana.example.com/d/api-dashboard"
    logs: "https://kibana.example.com/app/discover#/?_a=(query:(query_string:(query:'service:{{ $labels.service }} AND level:error')))"
```

---

## Alert Thresholds

### General Guidelines

**Response Time / Latency**:
- Warning: p95 > 500ms or p99 > 1s
- Critical: p95 > 2s or p99 > 5s

**Error Rate**:
- Warning: > 1%
- Critical: > 5%

**Availability**:
- Warning: < 99.9%
- Critical: < 99.5%

**CPU Utilization**:
- Warning: > 70% for 15m
- Critical: > 90% for 5m

**Memory Utilization**:
- Warning: > 80% for 15m
- Critical: > 95% for 5m

**Disk Space**:
- Warning: > 80% full
- Critical: > 90% full

**Queue Depth**:
- Warning: > 70% of max capacity
- Critical: > 90% of max capacity

### Application-Specific Thresholds

Set thresholds based on:
1. **Historical performance**: Use p95 of last 30 days + 20%
2. **SLO requirements**: If SLO is 99.9%, alert at 99.5%
3. **Business impact**: What error rate causes user complaints?

---

## The "for" Clause

Prevent alert flapping by requiring the condition to be true for a duration.

### Guidelines

**Critical alerts**: Short duration (2-5m)
```yaml
- alert: ServiceDown
  expr: up == 0
  for: 2m  # Quick detection for critical issues
```

**Warning alerts**: Longer duration (10-30m)
```yaml
- alert: HighMemoryUsage
  expr: memory_usage > 80
  for: 15m  # Avoid noise from temporary spikes
```

**Resource saturation**: Medium duration (5-10m)
```yaml
- alert: HighCPU
  expr: cpu_usage > 90
  for: 5m
```

---

## Alert Routing

### Severity-Based Routing

```yaml
# alertmanager.yml
route:
  group_by: ['alertname', 'cluster']
  group_wait: 10s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'default'

  routes:
  # Critical alerts → PagerDuty
  - match:
      severity: critical
    receiver: pagerduty
    group_wait: 10s
    repeat_interval: 5m

  # Warning alerts → Slack
  - match:
      severity: warning
    receiver: slack
    group_wait: 30s
    repeat_interval: 12h

  # Info alerts → Email
  - match:
      severity: info
    receiver: email
    repeat_interval: 24h
```

### Team-Based Routing

```yaml
routes:
  # Platform team
  - match:
      team: platform
    receiver: platform-pagerduty

  # Backend team
  - match:
      team: backend
    receiver: backend-slack

  # Database team
  - match:
      component: database
    receiver: dba-pagerduty
```

### Time-Based Routing

```yaml
# Only page during business hours for non-critical
routes:
  - match:
      severity: warning
    receiver: slack
    active_time_intervals:
      - business_hours

time_intervals:
  - name: business_hours
    time_intervals:
      - weekdays: ['monday:friday']
        times:
          - start_time: '09:00'
            end_time: '17:00'
        location: 'America/New_York'
```

---

## Alert Grouping

### Intelligent Grouping

**Group by service and environment**:
```yaml
route:
  group_by: ['alertname', 'service', 'environment']
  group_wait: 30s
  group_interval: 5m
```

This prevents:
- 50 alerts for "HighCPU" on different pods → 1 grouped alert
- Mixing production and staging alerts

### Inhibition Rules

Suppress related alerts when a parent alert fires.

```yaml
inhibit_rules:
  # If service is down, suppress latency alerts
  - source_match:
      alertname: ServiceDown
    target_match:
      alertname: HighLatency
    equal: ['service']

  # If node is down, suppress all pod alerts on that node
  - source_match:
      alertname: NodeDown
    target_match_re:
      alertname: '(PodCrashLoop|HighCPU|HighMemory)'
    equal: ['node']
```

---

## Runbook Structure

Every alert should link to a runbook with:

### 1. Context
- What does this alert mean?
- What is the user impact?
- What is the urgency?

### 2. Investigation Steps
```markdown
## Investigation

1. Check service health dashboard
   https://grafana.example.com/d/service-dashboard

2. Check recent deployments
   kubectl rollout history deployment/myapp -n production

3. Check error logs
   kubectl logs deployment/myapp -n production --tail=100 | grep ERROR

4. Check dependencies
   - Database: Check slow query log
   - Redis: Check memory usage
   - External APIs: Check status pages
```

### 3. Common Causes
```markdown
## Common Causes

- **Recent deployment**: Check if alert started after deployment
- **Traffic spike**: Check request rate, might need to scale
- **Database issues**: Check query performance and connection pool
- **External API degradation**: Check third-party status pages
```

### 4. Resolution Steps
```markdown
## Resolution

### Immediate Actions (< 5 minutes)
1. Scale up if traffic spike: `kubectl scale deployment myapp --replicas=10`
2. Rollback if recent deployment: `kubectl rollout undo deployment/myapp`

### Short-term Actions (< 30 minutes)
1. Restart pods if memory leak: `kubectl rollout restart deployment/myapp`
2. Clear cache if stale data: `redis-cli -h cache.example.com FLUSHDB`

### Long-term Actions (post-incident)
1. Review and optimize slow queries
2. Implement circuit breakers
3. Add more capacity
4. Update alert thresholds if false positive
```

### 5. Escalation
```markdown
## Escalation

If issue persists after 30 minutes:
- Slack: #backend-oncall
- PagerDuty: Escalate to senior engineer
- Incident Commander: Jane Doe (jane@example.com)
```

---

## Anti-Patterns to Avoid

### 1. Alert on Everything
❌ Don't: Alert on every warning log
✅ Do: Alert on error rate exceeding threshold

### 2. Alert Without Context
❌ Don't: "Error rate high"
✅ Do: "Error rate 5.2% exceeds 1% threshold for 10m, impacting checkout flow"

### 3. Static Thresholds for Dynamic Systems
❌ Don't: `cpu_usage > 70` (fails during scale-up)
✅ Do: Alert on SLO violations or rate of change

### 4. No "for" Clause
❌ Don't: Alert immediately on threshold breach
✅ Do: Use `for: 5m` to avoid flapping

### 5. Too Many Recipients
❌ Don't: Page 10 people for every alert
✅ Do: Route to specific on-call rotation

### 6. Duplicate Alerts
❌ Don't: Alert on both cause and symptom
✅ Do: Alert on symptom, use inhibition for causes

### 7. No Runbook
❌ Don't: Alert without guidance
✅ Do: Include runbook_url in every alert

---

## Alert Testing

### Test Alert Firing
```bash
# Trigger test alert in Prometheus
amtool alert add alertname="TestAlert" \
  severity="warning" \
  summary="Test alert"

# Or use Alertmanager API
curl -X POST http://alertmanager:9093/api/v1/alerts \
  -d '[{
    "labels": {"alertname": "TestAlert", "severity": "critical"},
    "annotations": {"summary": "Test critical alert"}
  }]'
```

### Verify Alert Rules
```bash
# Check syntax
promtool check rules alerts.yml

# Test expression
promtool query instant http://prometheus:9090 \
  'sum(rate(http_requests_total{status=~"5.."}[5m]))'

# Unit test alerts
promtool test rules test.yml
```

### Test Alertmanager Routing
```bash
# Test which receiver an alert would go to
amtool config routes test \
  --config.file=alertmanager.yml \
  alertname="HighLatency" \
  severity="critical" \
  team="backend"
```

---

## On-Call Best Practices

### Rotation Schedule
- **Primary on-call**: First responder
- **Secondary on-call**: Escalation backup
- **Rotation length**: 1 week (balance load vs context)
- **Handoff**: Monday morning (not Friday evening)

### On-Call Checklist
```markdown
## Pre-shift
- [ ] Test pager/phone
- [ ] Review recent incidents
- [ ] Check upcoming deployments
- [ ] Update contact info

## During shift
- [ ] Respond to pages within 5 minutes
- [ ] Document all incidents
- [ ] Update runbooks if gaps found
- [ ] Communicate in #incidents channel

## Post-shift
- [ ] Hand off open incidents
- [ ] Complete incident reports
- [ ] Suggest improvements
- [ ] Update team documentation
```

### Escalation Policy
1. **Primary**: Responds within 5 minutes
2. **Secondary**: Auto-escalate after 15 minutes
3. **Manager**: Auto-escalate after 30 minutes
4. **Incident Commander**: Critical incidents only

---

## Metrics About Alerts

Monitor your monitoring system!

### Key Metrics
```promql
# Alert firing frequency
sum(ALERTS{alertstate="firing"}) by (alertname)

# Alert duration
ALERTS_FOR_STATE{alertstate="firing"}

# Alerts per severity
sum(ALERTS{alertstate="firing"}) by (severity)

# Time to acknowledge (from PagerDuty/etc)
pagerduty_incident_ack_duration_seconds
```

### Alert Quality Metrics
- **Mean Time to Acknowledge (MTTA)**: < 5 minutes
- **Mean Time to Resolve (MTTR)**: < 30 minutes
- **False Positive Rate**: < 10%
- **Alert Coverage**: % of incidents with preceding alert > 80%
