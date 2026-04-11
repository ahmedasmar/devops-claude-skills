# Migrating from Datadog to Open-Source Stack

## Overview

This guide helps you migrate from Datadog to a cost-effective open-source observability stack:
- **Metrics**: Datadog → Prometheus + Grafana
- **Logs**: Datadog → Loki + Grafana
- **Traces**: Datadog APM → Tempo/Jaeger + Grafana
- **Dashboards**: Datadog → Grafana
- **Alerts**: Datadog Monitors → Prometheus Alertmanager

**Estimated Cost Savings**: 60-80% for similar functionality

---

## Cost Comparison

### Example: 100-host infrastructure

**Datadog** (billed annually, 2026 pricing):
- Infrastructure Pro: $1,500/month (100 hosts × $15/host/month)
  - Or Enterprise: $2,300/month (100 hosts × $23/host/month)
- Custom Metrics: $50/month (5,000 extra metrics beyond included 10,000)
- Logs: $2,000/month (20GB/day × $0.10/GB × 30 days)
- APM: $3,100/month (100 hosts × $31/host/month)
- **Total**: ~$6,650-7,450/month ($79,800-89,400/year)
- **Note**: Actual costs vary significantly with custom metrics volume, log ingestion rates, and add-ons (RUM, Synthetics, CSPM, etc.)

**Open-Source Stack** (self-hosted):
- Infrastructure: $1,200/month (EC2/GKE for Prometheus, Grafana, Loki, Tempo)
- Storage: $300/month (S3/GCS for long-term metrics and traces)
- Operations time: Variable
- **Total**: ~$1,500-2,500/month ($18,000-30,000/year)

**Savings**: $49,800-61,800/year

---

## Migration Strategy

### Phase 1: Run Parallel (Month 1-2)
- Deploy open-source stack alongside Datadog
- Migrate metrics first (lowest risk)
- Validate data accuracy
- Build confidence

### Phase 2: Migrate Dashboards & Alerts (Month 2-3)
- Convert Datadog dashboards to Grafana
- Translate alert rules
- Train team on new tools

### Phase 3: Migrate Logs & Traces (Month 3-4)
- Set up Loki for log aggregation
- Deploy Tempo/Jaeger for tracing
- Update application instrumentation

### Phase 4: Decommission Datadog (Month 4-5)
- Confirm all functionality migrated
- Cancel Datadog subscription
- Archive Datadog dashboards/alerts for reference

---

## 1. Metrics Migration (Datadog → Prometheus)

### Step 1: Deploy Prometheus

**Kubernetes** (recommended):
```yaml
# prometheus-values.yaml
prometheus:
  prometheusSpec:
    retention: 30d
    storageSpec:
      volumeClaimTemplate:
        spec:
          resources:
            requests:
              storage: 100Gi

    # Scrape configs
    additionalScrapeConfigs:
      - job_name: 'kubernetes-pods'
        kubernetes_sd_configs:
          - role: pod
```

**Install**:
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack -f prometheus-values.yaml
```

**Docker Compose**:
```yaml
version: '3'
services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.retention.time=30d'

volumes:
  prometheus-data:
```

### Step 2: Replace DogStatsD with Prometheus Exporters

**Before (DogStatsD)**:
```python
from datadog import statsd

statsd.increment('page.views')
statsd.histogram('request.duration', 0.5)
statsd.gauge('active_users', 100)
```

**After (Prometheus Python client)**:
```python
from prometheus_client import Counter, Histogram, Gauge

page_views = Counter('page_views_total', 'Page views')
request_duration = Histogram('request_duration_seconds', 'Request duration')
active_users = Gauge('active_users', 'Active users')

# Usage
page_views.inc()
request_duration.observe(0.5)
active_users.set(100)
```

### Step 3: Metric Name Translation

| Datadog Metric | Prometheus Equivalent |
|----------------|----------------------|
| `system.cpu.idle` | `node_cpu_seconds_total{mode="idle"}` |
| `system.mem.free` | `node_memory_MemFree_bytes` |
| `system.disk.used` | `node_filesystem_size_bytes - node_filesystem_free_bytes` |
| `docker.cpu.usage` | `container_cpu_usage_seconds_total` |
| `kubernetes.pods.running` | `kube_pod_status_phase{phase="Running"}` |

### Step 4: Export Existing Datadog Metrics (Optional)

Use Datadog API to export historical data:

```python
from datadog import api, initialize

options = {
    'api_key': 'YOUR_API_KEY',
    'app_key': 'YOUR_APP_KEY'
}
initialize(**options)

# Query metric
result = api.Metric.query(
    start=int(time.time() - 86400),  # Last 24h
    end=int(time.time()),
    query='avg:system.cpu.user{*}'
)

# Convert to Prometheus format and import
```

---

## 2. Dashboard Migration (Datadog → Grafana)

### Step 1: Export Datadog Dashboards

```python
import requests
import json

api_key = "YOUR_API_KEY"
app_key = "YOUR_APP_KEY"

headers = {
    'DD-API-KEY': api_key,
    'DD-APPLICATION-KEY': app_key
}

# Get all dashboards
response = requests.get(
    'https://api.datadoghq.com/api/v1/dashboard',
    headers=headers
)

dashboards = response.json()

# Export each dashboard
for dashboard in dashboards['dashboards']:
    dash_id = dashboard['id']
    detail = requests.get(
        f'https://api.datadoghq.com/api/v1/dashboard/{dash_id}',
        headers=headers
    ).json()

    with open(f'datadog_{dash_id}.json', 'w') as f:
        json.dump(detail, f, indent=2)
```

### Step 2: Convert to Grafana Format

**Manual Conversion Template**:

| Datadog Widget | Grafana Panel Type |
|----------------|-------------------|
| Timeseries | Graph / Time series |
| Query Value | Stat |
| Toplist | Table / Bar gauge |
| Heatmap | Heatmap |
| Distribution | Histogram |

**Automated Conversion** (basic example):
```python
def convert_datadog_to_grafana(datadog_dashboard):
    grafana_dashboard = {
        "title": datadog_dashboard['title'],
        "panels": []
    }

    for widget in datadog_dashboard['widgets']:
        panel = {
            "title": widget['definition'].get('title', ''),
            "type": map_widget_type(widget['definition']['type']),
            "targets": convert_queries(widget['definition']['requests'])
        }
        grafana_dashboard['panels'].append(panel)

    return grafana_dashboard
```

### Step 3: Common Query Translations

See `dql_promql_translation.md` for comprehensive query mappings.

**Example conversions**:

```
Datadog: avg:system.cpu.user{*}
Prometheus: avg(rate(node_cpu_seconds_total{mode="user"}[5m])) * 100

Datadog: sum:requests.count{status:200}.as_rate()
Prometheus: sum(rate(http_requests_total{status="200"}[5m]))

Datadog: p95:request.duration{*}
Prometheus: histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))
```

---

## 3. Alert Migration (Datadog Monitors → Prometheus Alerts)

### Step 1: Export Datadog Monitors

```python
import requests

api_key = "YOUR_API_KEY"
app_key = "YOUR_APP_KEY"

headers = {
    'DD-API-KEY': api_key,
    'DD-APPLICATION-KEY': app_key
}

response = requests.get(
    'https://api.datadoghq.com/api/v1/monitor',
    headers=headers
)

monitors = response.json()

# Save each monitor
for monitor in monitors:
    with open(f'monitor_{monitor["id"]}.json', 'w') as f:
        json.dump(monitor, f, indent=2)
```

### Step 2: Convert to Prometheus Alert Rules

**Datadog Monitor**:
```json
{
  "name": "High CPU Usage",
  "type": "metric alert",
  "query": "avg(last_5m):avg:system.cpu.user{*} > 80",
  "message": "CPU usage is high on {{host.name}}"
}
```

**Prometheus Alert**:
```yaml
groups:
  - name: infrastructure
    rules:
      - alert: HighCPUUsage
        expr: |
          100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage on {{ $labels.instance }}"
          description: "CPU usage is {{ $value }}%"
```

### Step 3: Alert Routing (Datadog → Alertmanager)

**Datadog notification channels** → **Alertmanager receivers**

```yaml
# alertmanager.yml
route:
  group_by: ['alertname', 'severity']
  receiver: 'slack-notifications'

receivers:
  - name: 'slack-notifications'
    slack_configs:
      - api_url: 'YOUR_SLACK_WEBHOOK'
        channel: '#alerts'

  - name: 'pagerduty-critical'
    pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_KEY'
```

---

## 4. Log Migration (Datadog → Loki)

### Step 1: Deploy Loki

**Kubernetes**:
```bash
helm repo add grafana https://grafana.github.io/helm-charts
helm install loki grafana/loki-stack \
  --set loki.persistence.enabled=true \
  --set loki.persistence.size=100Gi \
  --set promtail.enabled=true
```

**Docker Compose**:
```yaml
version: '3'
services:
  loki:
    image: grafana/loki:latest
    ports:
      - "3100:3100"
    volumes:
      - ./loki-config.yaml:/etc/loki/local-config.yaml
      - loki-data:/loki

  promtail:
    image: grafana/promtail:latest
    volumes:
      - /var/log:/var/log
      - ./promtail-config.yaml:/etc/promtail/config.yml

volumes:
  loki-data:
```

### Step 2: Replace Datadog Log Forwarder

**Before (Datadog Agent)**:
```yaml
# datadog.yaml
logs_enabled: true

logs_config:
  container_collect_all: true
```

**After (Promtail)**:
```yaml
# promtail-config.yaml
server:
  http_listen_port: 9080

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: system
    static_configs:
      - targets:
          - localhost
        labels:
          job: varlogs
          __path__: /var/log/*.log
```

### Step 3: Query Translation

**Datadog Logs Query**:
```
service:my-app status:error
```

**Loki LogQL**:
```logql
{job="my-app", level="error"}
```

**More examples**:
```
Datadog: service:api-gateway status:error @http.status_code:>=500
Loki: {service="api-gateway", level="error"} | json | http_status_code >= 500

Datadog: source:nginx "404"
Loki: {source="nginx"} |= "404"
```

---

## 5. APM Migration (Datadog APM → Tempo/Jaeger)

### Step 1: Choose Tracing Backend

- **Tempo**: Better for high volume, cheaper storage (object storage)
- **Jaeger**: More mature, better UI, requires separate storage

### Step 2: Replace Datadog Tracer with OpenTelemetry

**Before (Datadog Python)**:
```python
from ddtrace import tracer

@tracer.wrap()
def my_function():
    pass
```

**After (OpenTelemetry)**:
```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Setup
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)
exporter = OTLPSpanExporter(endpoint="tempo:4317")

@tracer.start_as_current_span("my_function")
def my_function():
    pass
```

### Step 3: Deploy Tempo

```yaml
# tempo.yaml
server:
  http_listen_port: 3200

distributor:
  receivers:
    otlp:
      protocols:
        grpc:
          endpoint: 0.0.0.0:4317

storage:
  trace:
    backend: s3
    s3:
      bucket: tempo-traces
      endpoint: s3.amazonaws.com
```

---

## 6. Infrastructure Migration

### Recommended Architecture

```
┌─────────────────────────────────────────┐
│  Grafana (Visualization)                │
│  - Dashboards                           │
│  - Unified view                         │
└─────────────────────────────────────────┘
         ↓           ↓           ↓
┌──────────────┐ ┌──────────┐ ┌──────────┐
│  Prometheus  │ │   Loki   │ │  Tempo   │
│  (Metrics)   │ │  (Logs)  │ │ (Traces) │
└──────────────┘ └──────────┘ └──────────┘
         ↓           ↓           ↓
┌─────────────────────────────────────────┐
│  Applications (OpenTelemetry)           │
└─────────────────────────────────────────┘
```

### Sizing Recommendations

**100-host environment**:

- **Prometheus**: 2-4 CPU, 8-16GB RAM, 100GB SSD
- **Grafana**: 1 CPU, 2GB RAM
- **Loki**: 2-4 CPU, 8GB RAM, 100GB SSD
- **Tempo**: 2-4 CPU, 8GB RAM, S3 for storage
- **Alertmanager**: 1 CPU, 1GB RAM

**Total**: ~8-16 CPU, 32-64GB RAM, 200GB SSD + object storage

---

## 7. Migration Checklist

### Pre-Migration
- [ ] Calculate current Datadog costs
- [ ] Identify all Datadog integrations
- [ ] Export all dashboards
- [ ] Export all monitors
- [ ] Document custom metrics
- [ ] Get stakeholder approval

### During Migration
- [ ] Deploy Prometheus + Grafana
- [ ] Deploy Loki + Promtail
- [ ] Deploy Tempo/Jaeger (if using APM)
- [ ] Migrate metrics instrumentation
- [ ] Convert dashboards (top 10 critical first)
- [ ] Convert alerts (critical alerts first)
- [ ] Update application logging
- [ ] Replace APM instrumentation
- [ ] Run parallel for 2-4 weeks
- [ ] Validate data accuracy
- [ ] Train team on new tools

### Post-Migration
- [ ] Decommission Datadog agent from all hosts
- [ ] Cancel Datadog subscription
- [ ] Archive Datadog configs
- [ ] Document new workflows
- [ ] Create runbooks for common tasks

---

## 8. Common Challenges & Solutions

### Challenge: Missing Datadog Features

**Datadog Synthetic Monitoring**:
- Solution: Use **Blackbox Exporter** (Prometheus) or **Grafana Synthetic Monitoring**

**Datadog Network Performance Monitoring**:
- Solution: Use **Cilium Hubble** (Kubernetes) or **eBPF-based tools**

**Datadog RUM (Real User Monitoring)**:
- Solution: Use **Grafana Faro** or **OpenTelemetry Browser SDK**

### Challenge: Team Learning Curve

**Solution**:
- Provide training sessions (2-3 hours per tool)
- Create internal documentation with examples
- Set up sandbox environment for practice
- Assign champions for each tool

### Challenge: Query Performance

**Prometheus too slow**:
- Use **Thanos** or **Cortex** for scaling
- Implement recording rules for expensive queries
- Increase retention only where needed

**Loki too slow**:
- Add more labels for better filtering
- Use chunk caching
- Consider **parallel query execution**

---

## 9. Maintenance Comparison

### Datadog (Managed)
- **Ops burden**: Low (fully managed)
- **Upgrades**: Automatic
- **Scaling**: Automatic
- **Cost**: High ($7k-10k+/month, varies significantly with add-ons)

### Open-Source Stack (Self-hosted)
- **Ops burden**: Medium (requires ops team)
- **Upgrades**: Manual (quarterly)
- **Scaling**: Manual planning required
- **Cost**: Low ($1.5k-3k/month infrastructure)

**Hybrid Option**: Use **Grafana Cloud** (managed Prometheus/Loki/Tempo)
- Cost: ~$3k/month for 100 hosts
- Ops burden: Low
- Savings: ~50% vs Datadog

---

## 10. ROI Calculation

### Example Scenario

**Before (Datadog, Pro tier, billed annually)**:
- Monthly cost: $7,000 (higher with Enterprise tier or add-ons)
- Annual cost: $84,000

**After (Self-hosted OSS)**:
- Infrastructure: $1,800/month
- Operations (0.5 FTE): $4,000/month
- Annual cost: $69,600

**Savings**: $14,400/year

**After (Grafana Cloud)**:
- Monthly cost: $3,500
- Annual cost: $42,000

**Savings**: $42,000/year (50%)

**Break-even**: Immediate (no migration costs beyond engineering time)

---

## Resources

- **Prometheus**: https://prometheus.io/docs/
- **Grafana**: https://grafana.com/docs/
- **Loki**: https://grafana.com/docs/loki/
- **Tempo**: https://grafana.com/docs/tempo/
- **OpenTelemetry**: https://opentelemetry.io/
- **Migration Tools**: https://github.com/grafana/dashboard-linter

---

## Support

If you need help with migration:
- Grafana Labs offers migration consulting
- Many SRE consulting firms specialize in this
- Community support via Slack/Discord channels
