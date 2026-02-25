---
name: monitoring-observability
description: Monitoring and observability strategy, implementation, and troubleshooting. Use for designing metrics/logs/traces systems, setting up Prometheus/Grafana/Loki, creating alerts and dashboards, calculating SLOs and error budgets, analyzing performance issues, and comparing monitoring tools (Datadog, ELK, CloudWatch). Covers the Four Golden Signals, RED/USE methods, OpenTelemetry instrumentation, log aggregation patterns, and distributed tracing.
---

# Monitoring & Observability

## Core Workflow: Observability Implementation

Use this decision tree to determine your starting point:

```
Are you setting up monitoring from scratch?
├─ YES → Start with "1. Design Metrics Strategy"
└─ NO → Do you have an existing issue?
    ├─ YES → Go to "9. Troubleshooting & Analysis"
    └─ NO → Are you improving existing monitoring?
        ├─ Alerts → Go to "3. Alert Design"
        ├─ Dashboards → Go to "4. Dashboard & Visualization"
        ├─ SLOs → Go to "5. SLO & Error Budgets"
        ├─ Tool selection → Read references/tool_comparison.md
        └─ Using Datadog? High costs? → Go to "7. Datadog Cost Optimization & Migration"
```

---

## 1. Design Metrics Strategy

### Start with The Four Golden Signals

Every service should monitor:

1. **Latency**: Response time (p50, p95, p99)
2. **Traffic**: Requests per second
3. **Errors**: Failure rate
4. **Saturation**: Resource utilization

Use **RED** (Rate/Errors/Duration) for request-driven services, **USE** (Utilization/Saturation/Errors) for infrastructure.

**Quick Start - Web Application Example**:
```promql
# Rate (requests/sec)
sum(rate(http_requests_total[5m]))

# Errors (error rate %)
sum(rate(http_requests_total{status=~"5.."}[5m]))
  /
sum(rate(http_requests_total[5m])) * 100

# Duration (p95 latency)
histogram_quantile(0.95,
  sum(rate(http_request_duration_seconds_bucket[5m])) by (le)
)
```

**→ Deep dive**: [references/metrics_design.md](references/metrics_design.md) (metric types, cardinality, naming, dashboards)

### Automated Metric Analysis

Detect anomalies and trends in your metrics:

```bash
# Analyze Prometheus metrics for anomalies
python3 scripts/analyze_metrics.py prometheus \
  --endpoint http://localhost:9090 \
  --query 'rate(http_requests_total[5m])' \
  --hours 24

# Analyze CloudWatch metrics
python3 scripts/analyze_metrics.py cloudwatch \
  --namespace AWS/EC2 \
  --metric CPUUtilization \
  --dimensions InstanceId=i-1234567890abcdef0 \
  --hours 48
```

**→ Script**: [scripts/analyze_metrics.py](scripts/analyze_metrics.py)

---

## 2. Log Aggregation & Analysis

### Structured Logging Checklist

Every log entry should include:
- ✅ Timestamp (ISO 8601 format)
- ✅ Log level (DEBUG, INFO, WARN, ERROR, FATAL)
- ✅ Message (human-readable)
- ✅ Service name
- ✅ Request ID (for tracing)

**Example structured log (JSON)**:
```json
{
  "timestamp": "2024-10-28T14:32:15Z",
  "level": "error",
  "message": "Payment processing failed",
  "service": "payment-service",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user123",
  "order_id": "ORD-456",
  "error_type": "GatewayTimeout",
  "duration_ms": 5000
}
```

### Log Analysis

Analyze logs for errors, patterns, and anomalies:

```bash
# Analyze log file for patterns
python3 scripts/log_analyzer.py application.log

# Show error lines with context
python3 scripts/log_analyzer.py application.log --show-errors

# Extract stack traces
python3 scripts/log_analyzer.py application.log --show-traces
```

**→ Script**: [scripts/log_analyzer.py](scripts/log_analyzer.py)

**→ Deep dive**: [references/logging_guide.md](references/logging_guide.md) (structured logging examples, aggregation patterns, PII redaction)

---

## 3. Alert Design

### Alert Design Principles

1. **Every alert must be actionable** - If you can't do something, don't alert
2. **Alert on symptoms, not causes** - Alert on user experience, not components
3. **Tie alerts to SLOs** - Connect to business impact
4. **Reduce noise** - Only page for critical issues

### Alert Severity Levels

| Severity | Response Time | Example |
|----------|--------------|---------|
| **Critical** | Page immediately | Service down, SLO violation |
| **Warning** | Ticket, review in hours | Elevated error rate, resource warning |
| **Info** | Log for awareness | Deployment completed, scaling event |

### Multi-Window Burn Rate Alerting

Alert when error budget is consumed too quickly:

```yaml
# Fast burn (1h window) - Critical
- alert: ErrorBudgetFastBurn
  expr: |
    (error_rate / 0.001) > 14.4  # 99.9% SLO
  for: 2m
  labels:
    severity: critical

# Slow burn (6h window) - Warning
- alert: ErrorBudgetSlowBurn
  expr: |
    (error_rate / 0.001) > 6  # 99.9% SLO
  for: 30m
  labels:
    severity: warning
```

### Alert Quality Checker

Audit your alert rules against best practices:

```bash
# Check single file
python3 scripts/alert_quality_checker.py alerts.yml

# Check all rules in directory
python3 scripts/alert_quality_checker.py /path/to/prometheus/rules/
```

**Checks for**:
- Alert naming conventions
- Required labels (severity, team)
- Required annotations (summary, description, runbook_url)
- PromQL expression quality
- 'for' clause to prevent flapping

**→ Script**: [scripts/alert_quality_checker.py](scripts/alert_quality_checker.py)

### Alert Templates

Production-ready alert rule templates:

**→ Templates**:
- [assets/templates/prometheus-alerts/webapp-alerts.yml](assets/templates/prometheus-alerts/webapp-alerts.yml) - Web application alerts
- [assets/templates/prometheus-alerts/kubernetes-alerts.yml](assets/templates/prometheus-alerts/kubernetes-alerts.yml) - Kubernetes alerts

**→ Deep dive**: [references/alerting_best_practices.md](references/alerting_best_practices.md) (design patterns, routing, inhibition, runbooks, on-call)

### Runbook Template

Create comprehensive runbooks for your alerts:

**→ Template**: [assets/templates/runbooks/incident-runbook-template.md](assets/templates/runbooks/incident-runbook-template.md)

---

## 4. Dashboard & Visualization

### Dashboard Design Principles

1. **Top-down layout**: Most important metrics first
2. **Color coding**: Red (critical), yellow (warning), green (healthy)
3. **Consistent time windows**: All panels use same time range
4. **Limit panels**: 8-12 panels per dashboard maximum
5. **Include context**: Show related metrics together

### Recommended Dashboard Structure

```
┌─────────────────────────────────────┐
│  Overall Health (Single Stats)      │
│  [Requests/s] [Error%] [P95 Latency]│
└─────────────────────────────────────┘
┌─────────────────────────────────────┐
│  Request Rate & Errors (Graphs)     │
└─────────────────────────────────────┘
┌─────────────────────────────────────┐
│  Latency Distribution (Graphs)      │
└─────────────────────────────────────┘
┌─────────────────────────────────────┐
│  Resource Usage (Graphs)            │
└─────────────────────────────────────┘
```

### Generate Grafana Dashboards

Automatically generate dashboards from templates:

```bash
# Web application dashboard
python3 scripts/dashboard_generator.py webapp \
  --title "My API Dashboard" \
  --service my_api \
  --output dashboard.json

# Kubernetes dashboard
python3 scripts/dashboard_generator.py kubernetes \
  --title "K8s Production" \
  --namespace production \
  --output k8s-dashboard.json

# Database dashboard
python3 scripts/dashboard_generator.py database \
  --title "PostgreSQL" \
  --db-type postgres \
  --instance db.example.com:5432 \
  --output db-dashboard.json
```

**Supports**:
- Web applications (requests, errors, latency, resources)
- Kubernetes (pods, nodes, resources, network)
- Databases (PostgreSQL, MySQL)

**→ Script**: [scripts/dashboard_generator.py](scripts/dashboard_generator.py)

---

## 5. SLO & Error Budgets

### Common SLO Targets

| Availability | Downtime/Month | Use Case |
|--------------|----------------|----------|
| **99%** | 7.2 hours | Internal tools |
| **99.9%** | 43.2 minutes | Standard production |
| **99.95%** | 21.6 minutes | Critical services |
| **99.99%** | 4.3 minutes | High availability |

### SLO Calculator

Calculate compliance, error budgets, and burn rates:

```bash
# Show SLO reference table
python3 scripts/slo_calculator.py --table

# Calculate availability SLO
python3 scripts/slo_calculator.py availability \
  --slo 99.9 \
  --total-requests 1000000 \
  --failed-requests 1500 \
  --period-days 30

# Calculate burn rate
python3 scripts/slo_calculator.py burn-rate \
  --slo 99.9 \
  --errors 50 \
  --requests 10000 \
  --window-hours 1
```

**→ Script**: [scripts/slo_calculator.py](scripts/slo_calculator.py)

**→ Deep dive**: [references/slo_sla_guide.md](references/slo_sla_guide.md) (SLI selection, error budgets, burn rate alerting, SLA contracts)

---

## 6. Distributed Tracing

### When to Use Tracing

Use distributed tracing when you need to:
- Debug performance issues across services
- Understand request flow through microservices
- Identify bottlenecks in distributed systems
- Find N+1 query problems

### OpenTelemetry Implementation

**Python example**:
```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

@tracer.start_as_current_span("process_order")
def process_order(order_id):
    span = trace.get_current_span()
    span.set_attribute("order.id", order_id)

    try:
        result = payment_service.charge(order_id)
        span.set_attribute("payment.status", "success")
        return result
    except Exception as e:
        span.set_status(trace.Status(trace.StatusCode.ERROR))
        span.record_exception(e)
        raise
```

### Sampling Strategies

- **Development**: 100% (ALWAYS_ON)
- **Staging**: 50-100%
- **Production**: 1-10% (or error-based sampling)

**Error-based sampling** (always sample errors, 1% of successes):
```python
class ErrorSampler(Sampler):
    def should_sample(self, parent_context, trace_id, name, **kwargs):
        attributes = kwargs.get('attributes', {})

        if attributes.get('error', False):
            return Decision.RECORD_AND_SAMPLE

        if trace_id & 0xFF < 3:  # ~1%
            return Decision.RECORD_AND_SAMPLE

        return Decision.DROP
```

### OTel Collector Configuration

Production-ready OpenTelemetry Collector configuration:

**→ Template**: [assets/templates/otel-config/collector-config.yaml](assets/templates/otel-config/collector-config.yaml)

**Features**:
- Receives OTLP, Prometheus, and host metrics
- Batching and memory limiting
- Tail sampling (error-based, latency-based, probabilistic)
- Multiple exporters (Tempo, Jaeger, Loki, Prometheus, CloudWatch, Datadog)

**→ Deep dive**: [references/tracing_guide.md](references/tracing_guide.md) (OTel instrumentation, context propagation, backend comparison, N+1 detection)

---

## 7. Datadog Cost Optimization & Migration

### Scenario 1: I'm Using Datadog and Costs Are Too High

If your Datadog bill is growing out of control, start by identifying waste:

#### Cost Analysis Script

Automatically analyze your Datadog usage and find cost optimization opportunities:

```bash
# Analyze Datadog usage (requires API key and APP key)
python3 scripts/datadog_cost_analyzer.py \
  --api-key $DD_API_KEY \
  --app-key $DD_APP_KEY

# Show detailed breakdown by category
python3 scripts/datadog_cost_analyzer.py \
  --api-key $DD_API_KEY \
  --app-key $DD_APP_KEY \
  --show-details
```

**What it checks**:
- Infrastructure host count and cost
- Custom metrics usage and high-cardinality metrics
- Log ingestion volume and trends
- APM host usage
- Unused or noisy monitors
- Container vs VM optimization opportunities

**→ Script**: [scripts/datadog_cost_analyzer.py](scripts/datadog_cost_analyzer.py)

#### Common Cost Optimization Strategies

**1. Custom Metrics Optimization** (typical savings: 20-40%):
- Remove high-cardinality tags (user IDs, request IDs)
- Delete unused custom metrics
- Aggregate metrics before sending
- Use metric prefixes to identify teams/services

**2. Log Management** (typical savings: 30-50%):
- Implement log sampling for high-volume services
- Use exclusion filters for debug/trace logs in production
- Archive cold logs to S3/GCS after 7 days
- Set log retention policies (15 days instead of 30)

**3. APM Optimization** (typical savings: 15-25%):
- Reduce trace sampling rates (10% → 5% in prod)
- Use head-based sampling instead of complete sampling
- Remove APM from non-critical services
- Use trace search with lower retention

**4. Infrastructure Monitoring** (typical savings: 10-20%):
- Switch from VM-based to container-based pricing where possible
- Remove agents from ephemeral instances
- Use Datadog's host reduction strategies
- Consolidate staging environments

### Scenario 2: Migrating Away from Datadog

If you're considering migrating to a more cost-effective open-source stack:

#### Migration Overview

**From Datadog** → **To Open Source Stack**:
- Metrics: Datadog → **Prometheus + Grafana**
- Logs: Datadog Logs → **Grafana Loki**
- Traces: Datadog APM → **Tempo or Jaeger**
- Dashboards: Datadog → **Grafana**
- Alerts: Datadog Monitors → **Prometheus Alertmanager**

**Estimated Cost Savings**: 60-77% ($49.8k-61.8k/year for 100-host environment)

#### Migration Strategy

**Phase 1: Run Parallel** (Month 1-2):
- Deploy open-source stack alongside Datadog
- Migrate metrics first (lowest risk)
- Validate data accuracy

**Phase 2: Migrate Dashboards & Alerts** (Month 2-3):
- Convert Datadog dashboards to Grafana
- Translate alert rules (use DQL → PromQL guide below)
- Train team on new tools

**Phase 3: Migrate Logs & Traces** (Month 3-4):
- Set up Loki for log aggregation
- Deploy Tempo/Jaeger for tracing
- Update application instrumentation

**Phase 4: Decommission Datadog** (Month 4-5):
- Confirm all functionality migrated
- Cancel Datadog subscription

#### Query Translation: DQL → PromQL

When migrating dashboards and alerts, you'll need to translate Datadog queries to PromQL:

**Quick examples**:
```
# Average CPU
Datadog: avg:system.cpu.user{*}
Prometheus: avg(node_cpu_seconds_total{mode="user"})

# Request rate
Datadog: sum:requests.count{*}.as_rate()
Prometheus: sum(rate(http_requests_total[5m]))

# P95 latency
Datadog: p95:request.duration{*}
Prometheus: histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))

# Error rate percentage
Datadog: (sum:requests.errors{*}.as_rate() / sum:requests.count{*}.as_rate()) * 100
Prometheus: (sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))) * 100
```

**→ Full Translation Guide**: [references/dql_promql_translation.md](references/dql_promql_translation.md)

#### Cost Comparison

**Example: 100-host infrastructure**

| Component | Datadog (Annual) | Open Source (Annual) | Savings |
|-----------|-----------------|---------------------|---------|
| Infrastructure | $18,000 | $10,000 (self-hosted infra) | $8,000 |
| Custom Metrics | $600 | Included | $600 |
| Logs | $24,000 | $3,000 (storage) | $21,000 |
| APM/Traces | $37,200 | $5,000 (storage) | $32,200 |
| **Total** | **$79,800** | **$18,000** | **$61,800 (77%)** |

**→ Read**: [references/datadog_migration.md](references/datadog_migration.md)

---

## 8. Tool Selection & Comparison

| Solution | Monthly Cost (100 hosts) | Best For |
|----------|-------------------------|----------|
| Prometheus + Loki + Tempo | $1,500 | Kubernetes, budget-conscious, ops-capable teams |
| Grafana Cloud | $3,000 | Open-source stack, low ops overhead |
| Datadog | $8,000 | Ease of use, full observability out of the box |
| ELK Stack | $4,000 | Heavy log analysis, powerful search |
| CloudWatch | $2,000 | Single AWS provider, simple needs |

**→ Read**: [references/tool_comparison.md](references/tool_comparison.md)

---

## 9. Troubleshooting & Analysis

### Health Check Validation

Validate health check endpoints against best practices:

```bash
# Check single endpoint
python3 scripts/health_check_validator.py https://api.example.com/health

# Check multiple endpoints
python3 scripts/health_check_validator.py \
  https://api.example.com/health \
  https://api.example.com/readiness \
  --verbose
```

**Checks for**:
- ✓ Returns 200 status code
- ✓ Response time < 1 second
- ✓ Returns JSON format
- ✓ Contains 'status' field
- ✓ Includes version/build info
- ✓ Checks dependencies
- ✓ Disables caching

**→ Script**: [scripts/health_check_validator.py](scripts/health_check_validator.py)

### Common Troubleshooting Workflows

**High Latency Investigation**:
1. Check dashboards for latency spike
2. Query traces for slow operations
3. Check database slow query log
4. Check external API response times
5. Review recent deployments
6. Check resource utilization (CPU, memory)

**High Error Rate Investigation**:
1. Check error logs for patterns
2. Identify affected endpoints
3. Check dependency health
4. Review recent deployments
5. Check resource limits
6. Verify configuration

**Service Down Investigation**:
1. Check if pods/instances are running
2. Check health check endpoint
3. Review recent deployments
4. Check resource availability
5. Check network connectivity
6. Review logs for startup errors

---

## Quick Reference Commands

### Prometheus Queries

```promql
# Request rate
sum(rate(http_requests_total[5m]))

# Error rate
sum(rate(http_requests_total{status=~"5.."}[5m]))
  /
sum(rate(http_requests_total[5m])) * 100

# P95 latency
histogram_quantile(0.95,
  sum(rate(http_request_duration_seconds_bucket[5m])) by (le)
)

# CPU usage
100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# Memory usage
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100
```

### Kubernetes Commands

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

### Log Queries

**Elasticsearch**:
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

**Loki (LogQL)**:
```logql
{job="app", level="error"} |= "error" | json
```

**CloudWatch Insights**:
```
fields @timestamp, level, message
| filter level = "error"
| filter @timestamp > ago(1h)
```

---

## Resources Summary

**Scripts**: `analyze_metrics.py` · `alert_quality_checker.py` · `slo_calculator.py` · `log_analyzer.py` · `dashboard_generator.py` · `health_check_validator.py` · `datadog_cost_analyzer.py`

**References**: `metrics_design.md` · `alerting_best_practices.md` · `logging_guide.md` · `tracing_guide.md` · `slo_sla_guide.md` · `tool_comparison.md` · `datadog_migration.md` · `dql_promql_translation.md`

**Templates**: `prometheus-alerts/webapp-alerts.yml` · `prometheus-alerts/kubernetes-alerts.yml` · `otel-config/collector-config.yaml` · `runbooks/incident-runbook-template.md`
