# SLI, SLO, and SLA Guide

## Definitions

### SLI (Service Level Indicator)
**What**: A quantitative measure of service quality

**Examples**:
- Request latency (ms)
- Error rate (%)
- Availability (%)
- Throughput (requests/sec)

### SLO (Service Level Objective)
**What**: Target value or range for an SLI

**Examples**:
- "99.9% of requests return in < 500ms"
- "99.95% availability"
- "Error rate < 0.1%"

### SLA (Service Level Agreement)
**What**: Business contract with consequences for SLO violations

**Examples**:
- "99.9% uptime or 10% monthly credit"
- "p95 latency < 1s or refund"

### Relationship
```
SLI = Measurement
SLO = Target (internal goal)
SLA = Promise (customer contract with penalties)

Example:
SLI: Actual availability this month = 99.92%
SLO: Target availability = 99.9%
SLA: Guaranteed availability = 99.5% (with penalties)
```

---

## Choosing SLIs

### The Four Golden Signals as SLIs

1. **Latency SLIs**
   - Request duration (p50, p95, p99)
   - Time to first byte
   - Page load time

2. **Availability/Success SLIs**
   - % of successful requests
   - % uptime
   - % of requests completing

3. **Throughput SLIs** (less common)
   - Requests per second
   - Transactions per second

4. **Saturation SLIs** (internal only)
   - Resource utilization
   - Queue depth

### SLI Selection Criteria

✅ **Good SLIs**:
- Measured from user perspective
- Directly impact user experience
- Aggregatable across instances
- Proportional to user happiness

❌ **Bad SLIs**:
- Internal metrics only
- Not user-facing
- Hard to measure consistently

### Examples by Service Type

**Web Application**:
```
SLI 1: Request Success Rate
  = successful_requests / total_requests

SLI 2: Request Latency (p95)
  = 95th percentile of response times

SLI 3: Availability
  = time_service_responding / total_time
```

**API Service**:
```
SLI 1: Error Rate
  = (4xx_errors + 5xx_errors) / total_requests

SLI 2: Response Time (p99)
  = 99th percentile latency

SLI 3: Throughput
  = requests_per_second
```

**Batch Processing**:
```
SLI 1: Job Success Rate
  = successful_jobs / total_jobs

SLI 2: Processing Latency
  = time_from_submission_to_completion

SLI 3: Freshness
  = age_of_oldest_unprocessed_item
```

**Storage Service**:
```
SLI 1: Durability
  = data_not_lost / total_data

SLI 2: Read Latency (p99)
  = 99th percentile read time

SLI 3: Write Success Rate
  = successful_writes / total_writes
```

---

## Setting SLO Targets

### Start with Current Performance

1. **Measure baseline**: Collect 30 days of data
2. **Analyze distribution**: Look at p50, p95, p99, p99.9
3. **Set initial SLO**: Slightly better than worst performer
4. **Iterate**: Tighten or loosen based on feasibility

### Example Process

**Current Performance** (30 days):
```
p50 latency: 120ms
p95 latency: 450ms
p99 latency: 1200ms
p99.9 latency: 3500ms

Error rate: 0.05%
Availability: 99.95%
```

**Initial SLOs**:
```
Latency: p95 < 500ms (slightly worse than current p95)
Error rate: < 0.1% (double current rate)
Availability: 99.9% (slightly worse than current)
```

**Rationale**: Start loose, prevent false alarms, tighten over time

### Common SLO Targets

**Availability**:
- **99%** (3.65 days downtime/year): Internal tools
- **99.5%** (1.83 days/year): Non-critical services
- **99.9%** (8.76 hours/year): Standard production
- **99.95%** (4.38 hours/year): Critical services
- **99.99%** (52 minutes/year): High availability
- **99.999%** (5 minutes/year): Mission critical

**Latency**:
- **p50 < 100ms**: Excellent responsiveness
- **p95 < 500ms**: Standard web applications
- **p99 < 1s**: Acceptable for most users
- **p99.9 < 5s**: Acceptable for rare edge cases

**Error Rate**:
- **< 0.01%** (99.99% success): Critical operations
- **< 0.1%** (99.9% success): Standard production
- **< 1%** (99% success): Non-critical services

---

## Error Budgets

### Concept

Error budget = (100% - SLO target)

If SLO is 99.9%, error budget is 0.1%

**Purpose**: Balance reliability with feature velocity

### Calculation

**For availability**:
```
Monthly error budget = (1 - SLO) × time_period

Example (99.9% SLO, 30 days):
Error budget = 0.001 × 30 days = 0.03 days = 43.2 minutes
```

**For request-based SLIs**:
```
Error budget = (1 - SLO) × total_requests

Example (99.9% SLO, 10M requests/month):
Error budget = 0.001 × 10,000,000 = 10,000 failed requests
```

### Error Budget Consumption

**Formula**:
```
Budget consumed = actual_errors / allowed_errors × 100%

Example:
SLO: 99.9% (0.1% error budget)
Total requests: 1,000,000
Failed requests: 500
Allowed failures: 1,000

Budget consumed = 500 / 1,000 × 100% = 50%
Budget remaining = 50%
```

### Error Budget Policy

**Example policy**:

```markdown
## Error Budget Policy

### If error budget > 50%
- Deploy frequently (multiple times per day)
- Take calculated risks
- Experiment with new features
- Acceptable to have some incidents

### If error budget 20-50%
- Deploy normally (once per day)
- Increase testing
- Review recent changes
- Monitor closely

### If error budget < 20%
- Freeze non-critical deploys
- Focus on reliability improvements
- Postmortem all incidents
- Reduce change velocity

### If error budget exhausted (< 0%)
- Complete deploy freeze except rollbacks
- All hands on reliability
- Mandatory postmortems
- Executive escalation
```

---

## Error Budget Burn Rate

### Concept

Burn rate = rate of error budget consumption

**Example**:
- Monthly budget: 43.2 minutes (99.9% SLO)
- If consuming at 2x rate: Budget exhausted in 15 days
- If consuming at 10x rate: Budget exhausted in 3 days

### Burn Rate Calculation

```
Burn rate = (actual_error_rate / allowed_error_rate)

Example:
SLO: 99.9% (0.1% allowed error rate)
Current error rate: 0.5%

Burn rate = 0.5% / 0.1% = 5x
Time to exhaust = 30 days / 5 = 6 days
```

### Multi-Window Alerting

Alert on burn rate across multiple time windows:

**Fast burn** (1 hour window):
```
Burn rate > 14.4x → Exhausts budget in 2 days
Alert after 2 minutes
Severity: Critical (page immediately)
```

**Moderate burn** (6 hour window):
```
Burn rate > 6x → Exhausts budget in 5 days
Alert after 30 minutes
Severity: Warning (create ticket)
```

**Slow burn** (3 day window):
```
Burn rate > 1x → Exhausts budget by end of month
Alert after 6 hours
Severity: Info (monitor)
```

### Implementation

**Prometheus**:
```yaml
# Fast burn alert (1h window, 2m grace period)
- alert: ErrorBudgetFastBurn
  expr: |
    (
      sum(rate(http_requests_total{status=~"5.."}[1h]))
      /
      sum(rate(http_requests_total[1h]))
    ) > (14.4 * 0.001)  # 14.4x burn rate for 99.9% SLO
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "Fast error budget burn detected"
    description: "Error budget will be exhausted in 2 days at current rate"

# Slow burn alert (6h window, 30m grace period)
- alert: ErrorBudgetSlowBurn
  expr: |
    (
      sum(rate(http_requests_total{status=~"5.."}[6h]))
      /
      sum(rate(http_requests_total[6h]))
    ) > (6 * 0.001)  # 6x burn rate for 99.9% SLO
  for: 30m
  labels:
    severity: warning
  annotations:
    summary: "Elevated error budget burn detected"
```

---

## SLO Reporting

### Dashboard Structure

**Overall Health**:
```
┌─────────────────────────────────────────┐
│  SLO Compliance: 99.92% ✅              │
│  Error Budget Remaining: 73% 🟢         │
│  Burn Rate: 0.8x 🟢                     │
└─────────────────────────────────────────┘
```

**SLI Performance**:
```
Latency p95: 420ms (Target: 500ms) ✅
Error Rate: 0.08% (Target: < 0.1%) ✅
Availability: 99.95% (Target: > 99.9%) ✅
```

**Error Budget Trend**:
```
Graph showing:
- Error budget consumption over time
- Burn rate spikes
- Incidents marked
- Deploy events overlaid
```

### Monthly SLO Report

**Template**:
```markdown
# SLO Report: March 2026

## Executive Summary
- ✅ All SLOs met this month
- 🟡 Latency SLO came close to violation (99.1% compliance)
- 3 incidents consumed 47% of error budget
- Error budget remaining: 53%

## SLO Performance

### Availability SLO: 99.9%
- Actual: 99.92%
- Status: ✅ Met
- Error budget consumed: 33%
- Downtime: 23 minutes (allowed: 43.2 minutes)

### Latency SLO: p95 < 500ms
- Actual p95: 445ms
- Status: ✅ Met
- Compliance: 99.1% (target: 99%)
- 0.9% of requests exceeded threshold

### Error Rate SLO: < 0.1%
- Actual: 0.05%
- Status: ✅ Met
- Error budget consumed: 50%

## Incidents

### Incident #1: Database Overload (Mar 5)
- Duration: 15 minutes
- Error budget consumed: 35%
- Root cause: Slow query after schema change
- Prevention: Added query review to deploy checklist

### Incident #2: API Gateway Timeout (Mar 12)
- Duration: 5 minutes
- Error budget consumed: 10%
- Root cause: Configuration error in load balancer
- Prevention: Automated configuration validation

### Incident #3: Upstream Service Degradation (Mar 20)
- Duration: 3 minutes
- Error budget consumed: 2%
- Root cause: Third-party API outage
- Prevention: Implemented circuit breaker

## Recommendations
1. Investigate latency near-miss (Mar 15-17)
2. Add automated rollback for database changes
3. Increase circuit breaker thresholds for third-party APIs
4. Consider tightening availability SLO to 99.95%

## Next Month's Focus
- Reduce p95 latency to 400ms
- Implement automated canary deployments
- Add synthetic monitoring for critical paths
```

---

## SLA Structure

### Components

**Service Description**:
```
The API Service provides RESTful endpoints for user management,
authentication, and data retrieval.
```

**Covered Metrics**:
```
- Availability: Service is reachable and returns valid responses
- Latency: Time from request to response
- Error Rate: Percentage of requests returning errors
```

**SLA Targets**:
```
Service commits to:
1. 99.9% monthly uptime
2. p95 API response time < 1 second
3. Error rate < 0.5%
```

**Measurement**:
```
Metrics calculated from server-side monitoring:
- Uptime: Successful health check probes / total probes
- Latency: Server-side request duration (p95)
- Errors: HTTP 5xx responses / total responses

Calculated monthly (first of month for previous month).
```

**Exclusions**:
```
SLA does not cover:
- Scheduled maintenance (with 7 days notice)
- Client-side network issues
- DDoS attacks or force majeure
- Beta/preview features
- Issues caused by customer misuse
```

**Service Credits**:
```
Monthly Uptime    | Service Credit
----------------  | --------------
< 99.9% (SLA)     | 10%
< 99.0%           | 25%
< 95.0%           | 50%
```

**Claiming Credits**:
```
Customer must:
1. Report violation within 30 days
2. Provide ticket numbers for support requests
3. Credits applied to next month's invoice
4. Credits do not exceed monthly fee
```

### Example SLAs by Industry

**E-commerce**:
```
- 99.95% availability
- p95 page load < 2s
- p99 checkout < 5s
- Credits: 5% per 0.1% below target
```

**Financial Services**:
```
- 99.99% availability
- p99 transaction < 500ms
- Zero data loss
- Penalties: $10,000 per hour of downtime
```

**Media/Content**:
```
- 99.9% availability
- p95 video start < 3s
- No credit system (best effort latency)
```

---

## Best Practices

### 1. SLOs Should Be User-Centric
❌ "Database queries < 100ms"
✅ "API response time p95 < 500ms"

### 2. Start Loose, Tighten Over Time
- Begin with achievable targets
- Build reliability culture
- Gradually raise bar

### 3. Fewer, Better SLOs
- 1-3 SLOs per service
- Focus on user impact
- Avoid SLO sprawl

### 4. SLAs More Conservative Than SLOs
```
Internal SLO: 99.95%
Customer SLA: 99.9%
Margin: 0.05% buffer
```

### 5. Make Error Budgets Actionable
- Define policies at different thresholds
- Empower teams to make tradeoffs
- Review in planning meetings

### 6. Document Everything
- How SLIs are measured
- Why targets were chosen
- Who owns each SLO
- How to interpret metrics

### 7. Review Regularly
- Monthly SLO reviews
- Quarterly SLO adjustments
- Annual SLA renegotiation

---

## Common Pitfalls

### 1. Too Many SLOs
❌ 20 different SLOs per service
✅ 2-3 critical SLOs

### 2. Unrealistic Targets
❌ 99.999% for non-critical service
✅ 99.9% with room to improve

### 3. SLOs Without Error Budgets
❌ "Must always be 99.9%"
✅ "Budget for 0.1% errors"

### 4. No Consequences
❌ Missing SLO has no impact
✅ Deploy freeze when budget exhausted

### 5. SLA Equals SLO
❌ Promise exactly what you target
✅ SLA more conservative than SLO

### 6. Ignoring User Experience
❌ "Our servers are up 99.99%"
✅ "Users can complete actions 99.9% of the time"

### 7. Static Targets
❌ Set once, never revisit
✅ Quarterly reviews and adjustments

---

## Tools and Automation

### SLO Tracking Tools

**Prometheus + Grafana**:
- Use recording rules for SLIs
- Alert on burn rates
- Dashboard for compliance

**Google Cloud SLO Monitoring**:
- Built-in SLO tracking
- Automatic error budget calculation
- Integration with alerting

**Datadog SLOs**:
- UI for SLO definition
- Automatic burn rate alerts
- Status pages

**Custom Tools**:
- sloth: Generate Prometheus rules from SLO definitions
- slo-libsonnet: Jsonnet library for SLO monitoring

### Example: Prometheus Recording Rules

```yaml
groups:
  - name: sli_recording
    interval: 30s
    rules:
      # SLI: Request success rate
      - record: sli:request_success:ratio
        expr: |
          sum(rate(http_requests_total{status!~"5.."}[5m]))
          /
          sum(rate(http_requests_total[5m]))

      # SLI: Request latency (p95)
      - record: sli:request_latency:p95
        expr: |
          histogram_quantile(0.95,
            sum(rate(http_request_duration_seconds_bucket[5m])) by (le)
          )

      # Error budget burn rate (1h window)
      - record: slo:error_budget_burn_rate:1h
        expr: |
          (1 - sli:request_success:ratio) / 0.001
```
