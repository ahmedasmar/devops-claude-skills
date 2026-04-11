# DQL (Datadog Query Language) ↔ PromQL Translation Guide

## Quick Reference

| Concept | Datadog (DQL) | Prometheus (PromQL) |
|---------|---------------|---------------------|
| Aggregation | `avg:`, `sum:`, `min:`, `max:` | `avg()`, `sum()`, `min()`, `max()` |
| Rate | `.as_rate()`, `.as_count()` | `rate()`, `increase()` |
| Percentile | `p50:`, `p95:`, `p99:` | `histogram_quantile()` |
| Filtering | `{tag:value}` | `{label="value"}` |
| Time window | `last_5m`, `last_1h` | `[5m]`, `[1h]` |

---

## Basic Queries

### Simple Metric Query

**Datadog**:
```
system.cpu.user
```

**Prometheus**:
```promql
node_cpu_seconds_total{mode="user"}
```

---

### Metric with Filter

**Datadog**:
```
system.cpu.user{host:web-01}
```

**Prometheus**:
```promql
node_cpu_seconds_total{mode="user", instance="web-01"}
```

---

### Multiple Filters (AND)

**Datadog**:
```
system.cpu.user{host:web-01,env:production}
```

**Prometheus**:
```promql
node_cpu_seconds_total{mode="user", instance="web-01", env="production"}
```

---

### Wildcard Filters

**Datadog**:
```
system.cpu.user{host:web-*}
```

**Prometheus**:
```promql
node_cpu_seconds_total{mode="user", instance=~"web-.*"}
```

---

### OR Filters

**Datadog**:
```
system.cpu.user{host:web-01 OR host:web-02}
```

**Prometheus**:
```promql
node_cpu_seconds_total{mode="user", instance=~"web-01|web-02"}
```

---

## Aggregations

### Average

**Datadog**:
```
avg:system.cpu.user{*}
```

**Prometheus**:
```promql
avg(node_cpu_seconds_total{mode="user"})
```

---

### Sum

**Datadog**:
```
sum:requests.count{*}
```

**Prometheus**:
```promql
sum(http_requests_total)
```

---

### Min/Max

**Datadog**:
```
min:system.mem.free{*}
max:system.mem.free{*}
```

**Prometheus**:
```promql
min(node_memory_MemFree_bytes)
max(node_memory_MemFree_bytes)
```

---

### Aggregation by Tag/Label

**Datadog**:
```
avg:system.cpu.user{*} by {host}
```

**Prometheus**:
```promql
avg by (instance) (node_cpu_seconds_total{mode="user"})
```

---

## Rates and Counts

### Rate (per second)

**Datadog**:
```
sum:requests.count{*}.as_rate()
```

**Prometheus**:
```promql
sum(rate(http_requests_total[5m]))
```

Note: Prometheus requires explicit time window `[5m]`

---

### Count (total over time)

**Datadog**:
```
sum:requests.count{*}.as_count()
```

**Prometheus**:
```promql
sum(increase(http_requests_total[1h]))
```

---

### Derivative (change over time)

**Datadog**:
```
derivative(avg:system.disk.used{*})
```

**Prometheus**:
```promql
deriv(node_filesystem_size_bytes[5m])
```

---

## Percentiles

### P50 (Median)

**Datadog**:
```
p50:request.duration{*}
```

**Prometheus** (requires histogram):
```promql
histogram_quantile(0.50, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))
```

---

### P95

**Datadog**:
```
p95:request.duration{*}
```

**Prometheus**:
```promql
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))
```

---

### P99

**Datadog**:
```
p99:request.duration{*}
```

**Prometheus**:
```promql
histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))
```

---

## Time Windows

### Last 5 minutes

**Datadog**:
```
avg(last_5m):system.cpu.user{*}
```

**Prometheus**:
```promql
avg(node_cpu_seconds_total{mode="user"}[5m])
```

---

### Last 1 hour

**Datadog**:
```
avg(last_1h):system.cpu.user{*}
```

**Prometheus**:
```promql
avg_over_time(node_cpu_seconds_total{mode="user"}[1h])
```

---

## Math Operations

### Division

**Datadog**:
```
avg:system.mem.used{*} / avg:system.mem.total{*}
```

**Prometheus**:
```promql
node_memory_MemUsed_bytes / node_memory_MemTotal_bytes
```

---

### Multiplication

**Datadog**:
```
avg:system.cpu.user{*} * 100
```

**Prometheus**:
```promql
avg(node_cpu_seconds_total{mode="user"}) * 100
```

---

### Percentage Calculation

**Datadog**:
```
(sum:requests.errors{*} / sum:requests.count{*}) * 100
```

**Prometheus**:
```promql
(sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))) * 100
```

---

## Common Use Cases

### CPU Usage Percentage

**Datadog**:
```
100 - avg:system.cpu.idle{*}
```

**Prometheus**:
```promql
100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
```

---

### Memory Usage Percentage

**Datadog**:
```
(avg:system.mem.used{*} / avg:system.mem.total{*}) * 100
```

**Prometheus**:
```promql
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100
```

---

### Disk Usage Percentage

**Datadog**:
```
(avg:system.disk.used{*} / avg:system.disk.total{*}) * 100
```

**Prometheus**:
```promql
(node_filesystem_size_bytes - node_filesystem_free_bytes) / node_filesystem_size_bytes * 100
```

---

### Request Rate (requests/sec)

**Datadog**:
```
sum:requests.count{*}.as_rate()
```

**Prometheus**:
```promql
sum(rate(http_requests_total[5m]))
```

---

### Error Rate Percentage

**Datadog**:
```
(sum:requests.errors{*}.as_rate() / sum:requests.count{*}.as_rate()) * 100
```

**Prometheus**:
```promql
(sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))) * 100
```

---

### Request Latency (P95)

**Datadog**:
```
p95:request.duration{*}
```

**Prometheus**:
```promql
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))
```

---

### Top 5 Hosts by CPU

**Datadog**:
```
top(avg:system.cpu.user{*} by {host}, 5, 'mean', 'desc')
```

**Prometheus**:
```promql
topk(5, avg by (instance) (rate(node_cpu_seconds_total{mode="user"}[5m])))
```

---

## Functions

### Absolute Value

**Datadog**:
```
abs(diff(avg:system.cpu.user{*}))
```

**Prometheus**:
```promql
abs(delta(node_cpu_seconds_total{mode="user"}[5m]))
```

---

### Ceiling/Floor

**Datadog**:
```
ceil(avg:system.cpu.user{*})
floor(avg:system.cpu.user{*})
```

**Prometheus**:
```promql
ceil(avg(node_cpu_seconds_total{mode="user"}))
floor(avg(node_cpu_seconds_total{mode="user"}))
```

---

### Clamp (Limit Range)

**Datadog**:
```
clamp_min(avg:system.cpu.user{*}, 0)
clamp_max(avg:system.cpu.user{*}, 100)
```

**Prometheus**:
```promql
clamp_min(avg(node_cpu_seconds_total{mode="user"}), 0)
clamp_max(avg(node_cpu_seconds_total{mode="user"}), 100)
```

---

### Moving Average

**Datadog**:
```
moving_rollup(avg:system.cpu.user{*}, 60, 'avg')
```

**Prometheus**:
```promql
avg_over_time(node_cpu_seconds_total{mode="user"}[1h])
```

---

## Advanced Patterns

### Compare to Previous Period

**Datadog**:
```
sum:requests.count{*}.as_rate() / timeshift(sum:requests.count{*}.as_rate(), 3600)
```

**Prometheus**:
```promql
sum(rate(http_requests_total[5m])) / sum(rate(http_requests_total[5m] offset 1h))
```

---

### Forecast

**Datadog**:
```
forecast(avg:system.disk.used{*}, 'linear', 1)
```

**Prometheus**:
```promql
predict_linear(node_filesystem_size_bytes[1h], 3600)
```

Note: Predicts value 1 hour in future based on last 1 hour trend

---

### Anomaly Detection

**Datadog**:
```
anomalies(avg:system.cpu.user{*}, 'basic', 2)
```

**Prometheus**: No built-in function
- Use recording rules with stddev
- External tools like **Robust Perception's anomaly detector**
- Or use **Grafana ML** plugin

---

### Outlier Detection

**Datadog**:
```
outliers(avg:system.cpu.user{*} by {host}, 'mad')
```

**Prometheus**: No built-in function
- Calculate manually with stddev:
```promql
abs(metric - avg(metric)) > 2 * stddev(metric)
```

---

## Container & Kubernetes

### Container CPU Usage

**Datadog**:
```
avg:docker.cpu.usage{*} by {container_name}
```

**Prometheus**:
```promql
avg by (container) (rate(container_cpu_usage_seconds_total[5m]))
```

---

### Container Memory Usage

**Datadog**:
```
avg:docker.mem.rss{*} by {container_name}
```

**Prometheus**:
```promql
avg by (container) (container_memory_rss)
```

---

### Pod Count by Status

**Datadog**:
```
sum:kubernetes.pods.running{*} by {kube_namespace}
```

**Prometheus**:
```promql
sum by (namespace) (kube_pod_status_phase{phase="Running"})
```

---

## Database Queries

### MySQL Queries Per Second

**Datadog**:
```
sum:mysql.performance.queries{*}.as_rate()
```

**Prometheus**:
```promql
sum(rate(mysql_global_status_queries[5m]))
```

---

### PostgreSQL Active Connections

**Datadog**:
```
avg:postgresql.connections{*}
```

**Prometheus**:
```promql
avg(pg_stat_database_numbackends)
```

---

### Redis Memory Usage

**Datadog**:
```
avg:redis.mem.used{*}
```

**Prometheus**:
```promql
avg(redis_memory_used_bytes)
```

---

## Network Metrics

### Network Bytes Sent

**Datadog**:
```
sum:system.net.bytes_sent{*}.as_rate()
```

**Prometheus**:
```promql
sum(rate(node_network_transmit_bytes_total[5m]))
```

---

### Network Bytes Received

**Datadog**:
```
sum:system.net.bytes_rcvd{*}.as_rate()
```

**Prometheus**:
```promql
sum(rate(node_network_receive_bytes_total[5m]))
```

---

## Key Differences

### 1. Time Windows
- **Datadog**: Optional, defaults to query time range
- **Prometheus**: Always required for rate/increase functions

### 2. Histograms
- **Datadog**: Percentiles available directly
- **Prometheus**: Requires histogram buckets + `histogram_quantile()`

### 3. Default Aggregation
- **Datadog**: No default, must specify
- **Prometheus**: Returns all time series unless aggregated

### 4. Metric Types
- **Datadog**: All metrics treated similarly
- **Prometheus**: Explicit types (counter, gauge, histogram, summary)

### 5. Tag vs Label
- **Datadog**: Uses "tags" (key:value)
- **Prometheus**: Uses "labels" (key="value")

---

## Migration Tips

1. **Start with dashboards**: Convert most-used dashboards first
2. **Use recording rules**: Pre-calculate expensive PromQL queries
3. **Test in parallel**: Run both systems during migration
4. **Document mappings**: Create team-specific translation guide
5. **Train team**: PromQL has learning curve, invest in training

---

## Tools

- **Datadog Dashboard Exporter**: Export JSON dashboards
- **Grafana Dashboard Linter**: Validate converted dashboards
- **PromQL Learning Resources**: https://prometheus.io/docs/prometheus/latest/querying/basics/

---

## Common Gotchas

### Rate without Time Window

❌ **Wrong**:
```promql
rate(http_requests_total)
```

✅ **Correct**:
```promql
rate(http_requests_total[5m])
```

---

### Aggregating Before Rate

❌ **Wrong**:
```promql
rate(sum(http_requests_total)[5m])
```

✅ **Correct**:
```promql
sum(rate(http_requests_total[5m]))
```

---

### Histogram Quantile Without by (le)

❌ **Wrong**:
```promql
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

✅ **Correct**:
```promql
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))
```

---

## Quick Conversion Checklist

When converting a Datadog query to PromQL:

- [ ] Replace metric name (e.g., `system.cpu.user` → `node_cpu_seconds_total`)
- [ ] Convert tags to labels (`{tag:value}` → `{label="value"}`)
- [ ] Add time window for rate/increase (`[5m]`)
- [ ] Change aggregation syntax (`avg:` → `avg()`)
- [ ] Convert percentiles to histogram_quantile if needed
- [ ] Test query in Prometheus before adding to dashboard
- [ ] Add `by (label)` for grouped aggregations

---

## Need More Help?

- See `datadog_migration.md` for full migration guide
- PromQL documentation: https://prometheus.io/docs/prometheus/latest/querying/
- Practice at: https://demo.promlens.com/
