# Metrics Design Guide

## The Four Golden Signals

The Four Golden Signals from Google's SRE book provide a comprehensive view of system health:

### 1. Latency
**What**: Time to service a request

**Why Monitor**: Directly impacts user experience

**Key Metrics**:
- Request duration (p50, p95, p99, p99.9)
- Time to first byte (TTFB)
- Backend processing time
- Database query latency

**PromQL Examples**:
```promql
# P95 latency
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))

# Average latency by endpoint
avg(rate(http_request_duration_seconds_sum[5m])) by (endpoint)
  /
avg(rate(http_request_duration_seconds_count[5m])) by (endpoint)
```

**Alert Thresholds**:
- Warning: p95 > 500ms
- Critical: p99 > 2s

### 2. Traffic
**What**: Demand on your system

**Why Monitor**: Understand load patterns, capacity planning

**Key Metrics**:
- Requests per second (RPS)
- Transactions per second (TPS)
- Concurrent connections
- Network throughput

**PromQL Examples**:
```promql
# Requests per second
sum(rate(http_requests_total[5m]))

# Requests per second by status code
sum(rate(http_requests_total[5m])) by (status)

# Traffic growth rate (week over week)
sum(rate(http_requests_total[5m]))
  /
sum(rate(http_requests_total[5m] offset 7d))
```

**Alert Thresholds**:
- Warning: RPS > 80% of capacity
- Critical: RPS > 95% of capacity

### 3. Errors
**What**: Rate of requests that fail

**Why Monitor**: Direct indicator of user-facing problems

**Key Metrics**:
- Error rate (%)
- 5xx response codes
- Failed transactions
- Exception counts

**PromQL Examples**:
```promql
# Error rate percentage
sum(rate(http_requests_total{status=~"5.."}[5m]))
  /
sum(rate(http_requests_total[5m])) * 100

# Error count by type
sum(rate(http_requests_total{status=~"5.."}[5m])) by (status)

# Application errors
rate(application_errors_total[5m])
```

**Alert Thresholds**:
- Warning: Error rate > 1%
- Critical: Error rate > 5%

### 4. Saturation
**What**: How "full" your service is

**Why Monitor**: Predict capacity issues before they impact users

**Key Metrics**:
- CPU utilization
- Memory utilization
- Disk I/O
- Network bandwidth
- Queue depth
- Thread pool usage

**PromQL Examples**:
```promql
# CPU saturation
100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# Memory saturation
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100

# Disk saturation
rate(node_disk_io_time_seconds_total[5m]) * 100

# Queue depth
queue_depth_current / queue_depth_max * 100
```

**Alert Thresholds**:
- Warning: > 70% utilization
- Critical: > 90% utilization

---

## RED Method (for Services)

**R**ate, **E**rrors, **D**uration - a simplified approach for request-driven services

### Rate
Number of requests per second:
```promql
sum(rate(http_requests_total[5m]))
```

### Errors
Number of failed requests per second:
```promql
sum(rate(http_requests_total{status=~"5.."}[5m]))
```

### Duration
Time taken to process requests:
```promql
histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))
```

**When to Use**: Microservices, APIs, web applications

---

## USE Method (for Resources)

**U**tilization, **S**aturation, **E**rrors - for infrastructure resources

### Utilization
Percentage of time resource is busy:
```promql
# CPU utilization
100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# Disk utilization
(node_filesystem_size_bytes - node_filesystem_avail_bytes)
  / node_filesystem_size_bytes * 100
```

### Saturation
Amount of work the resource cannot service (queued):
```promql
# Load average (saturation indicator)
node_load15

# Disk I/O wait time
rate(node_disk_io_time_weighted_seconds_total[5m])
```

### Errors
Count of error events:
```promql
# Network errors
rate(node_network_receive_errs_total[5m])
rate(node_network_transmit_errs_total[5m])

# Disk errors
rate(node_disk_io_errors_total[5m])
```

**When to Use**: Servers, databases, network devices

---

## Metric Types

### Counter
Monotonically increasing value (never decreases)

**Examples**: Request count, error count, bytes sent

**Usage**:
```promql
# Always use rate() or increase() with counters
rate(http_requests_total[5m])  # Requests per second
increase(http_requests_total[1h])  # Total requests in 1 hour
```

### Gauge
Value that can go up and down

**Examples**: Memory usage, queue depth, concurrent connections

**Usage**:
```promql
# Use directly or with aggregations
avg(memory_usage_bytes)
max(queue_depth)
```

### Histogram
Samples observations and counts them in configurable buckets

**Examples**: Request duration, response size

**Usage**:
```promql
# Calculate percentiles
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))

# Average from histogram
rate(http_request_duration_seconds_sum[5m])
  /
rate(http_request_duration_seconds_count[5m])
```

### Summary
Similar to histogram but calculates quantiles on client side

**Usage**: Less flexible than histograms, avoid for new metrics

---

## Cardinality Best Practices

**Cardinality**: Number of unique time series

### High Cardinality Labels (AVOID)
❌ User ID
❌ Email address
❌ IP address
❌ Timestamp
❌ Random IDs

### Low Cardinality Labels (GOOD)
✅ Environment (prod, staging)
✅ Region (us-east-1, eu-west-1)
✅ Service name
✅ HTTP status code category (2xx, 4xx, 5xx)
✅ Endpoint/route

### Calculating Cardinality Impact
```
Time series = unique combinations of labels

Example:
service (5) × environment (3) × region (4) × status (5) = 300 time series ✅

service (5) × environment (3) × region (4) × user_id (1M) = 60M time series ❌
```

---

## Naming Conventions

### Prometheus Naming
```
<namespace>_<name>_<unit>_total

Examples:
http_requests_total
http_request_duration_seconds
process_cpu_seconds_total
node_memory_MemAvailable_bytes
```

**Rules**:
- Use snake_case
- Include unit in name (seconds, bytes, ratio)
- Use `_total` suffix for counters
- Namespace by application/component

### CloudWatch Naming
```
<Namespace>/<MetricName>

Examples:
AWS/EC2/CPUUtilization
MyApp/RequestCount
```

**Rules**:
- Use PascalCase
- Group by namespace
- No unit in name (specified separately)

---

## Dashboard Design

### Key Principles

1. **Top-Down Layout**: Most important metrics first
2. **Color Coding**: Red (critical), yellow (warning), green (healthy)
3. **Consistent Time Windows**: All panels use same time range
4. **Limit Panels**: 8-12 panels per dashboard maximum
5. **Include Context**: Show related metrics together

### Dashboard Structure

```
┌─────────────────────────────────────────────┐
│  Overall Health (Single Stats)              │
│  [Requests/s] [Error%] [P95 Latency]        │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│  Request Rate & Errors (Graphs)             │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│  Latency Distribution (Graphs)              │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│  Resource Usage (Graphs)                    │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│  Dependencies (Graphs)                      │
└─────────────────────────────────────────────┘
```

### Template Variables
Use variables for filtering:
- Environment: `$environment`
- Service: `$service`
- Region: `$region`
- Pod: `$pod`

---

## Common Pitfalls

### 1. Monitoring What You Build, Not What Users Experience
❌ `backend_processing_complete`
✅ `user_request_completed`

### 2. Too Many Metrics
- Start with Four Golden Signals
- Add metrics only when needed for specific issues
- Remove unused metrics

### 3. Incorrect Aggregations
❌ `avg(rate(...))` - averages rates incorrectly
✅ `sum(rate(...)) / count(...)` - correct average

### 4. Wrong Time Windows
- Too short (< 1m): Noisy data
- Too long (> 15m): Miss short-lived issues
- Sweet spot: 5m for most alerts

### 5. Missing Labels
❌ `http_requests_total`
✅ `http_requests_total{method="GET", status="200", endpoint="/api/users"}`

---

## Metric Collection Best Practices

### Application Instrumentation
```python
from prometheus_client import Counter, Histogram, Gauge

# Counter for requests
requests_total = Counter('http_requests_total',
                        'Total HTTP requests',
                        ['method', 'endpoint', 'status'])

# Histogram for latency
request_duration = Histogram('http_request_duration_seconds',
                            'HTTP request duration',
                            ['method', 'endpoint'])

# Gauge for in-progress requests
requests_in_progress = Gauge('http_requests_in_progress',
                            'HTTP requests currently being processed')
```

### Collection Intervals
- Application metrics: 15-30s
- Infrastructure metrics: 30-60s
- Billing/cost metrics: 5-15m
- External API checks: 1-5m

### Retention
- Raw metrics: 15-30 days
- 5m aggregates: 90 days
- 1h aggregates: 1 year
- Daily aggregates: 2+ years
