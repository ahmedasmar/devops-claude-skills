# Logging Guide

## Structured Logging

### Why Structured Logs?

**Unstructured** (text):
```
2024-10-28 14:32:15 User john@example.com logged in from 192.168.1.1
```

**Structured** (JSON):
```json
{
  "timestamp": "2024-10-28T14:32:15Z",
  "level": "info",
  "message": "User logged in",
  "user": "john@example.com",
  "ip": "192.168.1.1",
  "event_type": "user_login"
}
```

**Benefits**:
- Easy to parse and query
- Consistent format
- Machine-readable
- Efficient storage and indexing

---

## Log Levels

Use appropriate log levels for better filtering and alerting.

### DEBUG
**When**: Development, troubleshooting
**Examples**:
- Function entry/exit
- Variable values
- Internal state changes

```python
logger.debug("Processing request", extra={
    "request_id": req_id,
    "params": params
})
```

### INFO
**When**: Important business events
**Examples**:
- User actions (login, purchase)
- System state changes (started, stopped)
- Significant milestones

```python
logger.info("Order placed", extra={
    "order_id": "12345",
    "user_id": "user123",
    "amount": 99.99
})
```

### WARN
**When**: Potentially problematic situations
**Examples**:
- Deprecated API usage
- Slow operations (but not failing)
- Retry attempts
- Resource usage approaching limits

```python
logger.warning("API response slow", extra={
    "endpoint": "/api/users",
    "duration_ms": 2500,
    "threshold_ms": 1000
})
```

### ERROR
**When**: Error conditions that need attention
**Examples**:
- Failed requests
- Exceptions caught and handled
- Integration failures
- Data validation errors

```python
logger.error("Payment processing failed", extra={
    "order_id": "12345",
    "error": str(e),
    "payment_gateway": "stripe"
}, exc_info=True)
```

### FATAL/CRITICAL
**When**: Severe errors causing shutdown
**Examples**:
- Database connection lost
- Out of memory
- Configuration errors preventing startup

```python
logger.critical("Database connection lost", extra={
    "database": "postgres",
    "host": "db.example.com",
    "attempt": 3
})
```

---

## Required Fields

Every log entry should include:

### 1. Timestamp
ISO 8601 format with timezone:
```json
{
  "timestamp": "2024-10-28T14:32:15.123Z"
}
```

### 2. Level
Standard levels: debug, info, warn, error, critical
```json
{
  "level": "error"
}
```

### 3. Message
Human-readable description:
```json
{
  "message": "User authentication failed"
}
```

### 4. Service/Application
What component logged this:
```json
{
  "service": "api-gateway",
  "version": "1.2.3"
}
```

### 5. Environment
```json
{
  "environment": "production"
}
```

---

## Recommended Fields

### Request Context
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user123",
  "session_id": "sess_abc",
  "ip_address": "192.168.1.1",
  "user_agent": "Mozilla/5.0..."
}
```

### Performance Metrics
```json
{
  "duration_ms": 245,
  "response_size_bytes": 1024
}
```

### Error Details
```json
{
  "error_type": "ValidationError",
  "error_message": "Invalid email format",
  "stack_trace": "...",
  "error_code": "VAL_001"
}
```

### Business Context
```json
{
  "order_id": "ORD-12345",
  "customer_id": "CUST-789",
  "transaction_amount": 99.99,
  "payment_method": "credit_card"
}
```

---

## Implementation Examples

### Python (using structlog)
```python
import structlog

logger = structlog.get_logger()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)

# Usage
logger.info(
    "user_logged_in",
    user_id="user123",
    ip_address="192.168.1.1",
    login_method="oauth"
)
```

### Node.js (using Winston)
```javascript
const winston = require('winston');

const logger = winston.createLogger({
  format: winston.format.json(),
  defaultMeta: { service: 'api-gateway' },
  transports: [
    new winston.transports.Console()
  ]
});

logger.info('User logged in', {
  userId: 'user123',
  ipAddress: '192.168.1.1',
  loginMethod: 'oauth'
});
```

### Go (using zap)
```go
import "go.uber.org/zap"

logger, _ := zap.NewProduction()
defer logger.Sync()

logger.Info("User logged in",
    zap.String("userId", "user123"),
    zap.String("ipAddress", "192.168.1.1"),
    zap.String("loginMethod", "oauth"),
)
```

### Java (using Logback with JSON)
```java
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import net.logstash.logback.argument.StructuredArguments;

Logger logger = LoggerFactory.getLogger(MyClass.class);

logger.info("User logged in",
    StructuredArguments.kv("userId", "user123"),
    StructuredArguments.kv("ipAddress", "192.168.1.1"),
    StructuredArguments.kv("loginMethod", "oauth")
);
```

---

## Log Aggregation Patterns

### Pattern 1: ELK Stack (Elasticsearch, Logstash, Kibana)

**Architecture**:
```
Application → Filebeat → Logstash → Elasticsearch → Kibana
```

**filebeat.yml**:
```yaml
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /var/log/app/*.log
    json.keys_under_root: true
    json.add_error_key: true

output.logstash:
  hosts: ["logstash:5044"]
```

**logstash.conf**:
```
input {
  beats {
    port => 5044
  }
}

filter {
  json {
    source => "message"
  }

  date {
    match => ["timestamp", "ISO8601"]
  }

  grok {
    match => { "message" => "%{COMBINEDAPACHELOG}" }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "app-logs-%{+YYYY.MM.dd}"
  }
}
```

### Pattern 2: Loki (Grafana Loki)

**Architecture**:
```
Application → Promtail → Loki → Grafana
```

**promtail-config.yml**:
```yaml
server:
  http_listen_port: 9080

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: app
    static_configs:
      - targets:
          - localhost
        labels:
          job: app
          __path__: /var/log/app/*.log
    pipeline_stages:
      - json:
          expressions:
            level: level
            timestamp: timestamp
      - labels:
          level:
          service:
      - timestamp:
          source: timestamp
          format: RFC3339
```

**Query in Grafana**:
```logql
{job="app"} |= "error" | json | level="error"
```

### Pattern 3: CloudWatch Logs

**Install CloudWatch agent**:
```json
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/app/*.log",
            "log_group_name": "/aws/app/production",
            "log_stream_name": "{instance_id}",
            "timezone": "UTC"
          }
        ]
      }
    }
  }
}
```

**Query with CloudWatch Insights**:
```
fields @timestamp, level, message, user_id
| filter level = "error"
| sort @timestamp desc
| limit 100
```

### Pattern 4: Fluentd/Fluent Bit

**fluent-bit.conf**:
```
[INPUT]
    Name              tail
    Path              /var/log/app/*.log
    Parser            json
    Tag               app.*

[FILTER]
    Name              record_modifier
    Match             *
    Record            hostname ${HOSTNAME}
    Record            cluster production

[OUTPUT]
    Name              es
    Match             *
    Host              elasticsearch
    Port              9200
    Index             app-logs
    Type              _doc
```

---

## Query Patterns

### Find Errors in Time Range
**Elasticsearch**:
```json
GET /app-logs-*/_search
{
  "query": {
    "bool": {
      "must": [
        { "match": { "level": "error" } },
        { "range": { "@timestamp": {
            "gte": "now-1h",
            "lte": "now"
        }}}
      ]
    }
  }
}
```

**Loki (LogQL)**:
```logql
{job="app", level="error"} |= "error"
```

**CloudWatch Insights**:
```
fields @timestamp, @message
| filter level = "error"
| filter @timestamp > ago(1h)
```

### Count Errors by Type
**Elasticsearch**:
```json
GET /app-logs-*/_search
{
  "size": 0,
  "query": { "match": { "level": "error" } },
  "aggs": {
    "error_types": {
      "terms": { "field": "error_type.keyword" }
    }
  }
}
```

**Loki**:
```logql
sum by (error_type) (count_over_time({job="app", level="error"}[1h]))
```

### Find Slow Requests
**Elasticsearch**:
```json
GET /app-logs-*/_search
{
  "query": {
    "range": { "duration_ms": { "gte": 1000 } }
  },
  "sort": [ { "duration_ms": "desc" } ]
}
```

### Trace Request Through Services
**Elasticsearch** (using request_id):
```json
GET /_search
{
  "query": {
    "match": { "request_id": "550e8400-e29b-41d4-a716-446655440000" }
  },
  "sort": [ { "@timestamp": "asc" } ]
}
```

---

## Sampling and Rate Limiting

### When to Sample
- **High volume services**: > 10,000 logs/second
- **Debug logs in production**: Sample 1-10%
- **Cost optimization**: Reduce storage costs

### Sampling Strategies

**1. Random Sampling**:
```python
import random

if random.random() < 0.1:  # Sample 10%
    logger.debug("Debug message", ...)
```

**2. Rate Limiting**:
```python
from rate_limiter import RateLimiter

limiter = RateLimiter(max_per_second=100)

if limiter.allow():
    logger.info("Rate limited log", ...)
```

**3. Error-Biased Sampling**:
```python
# Always log errors, sample successful requests
if level == "error" or random.random() < 0.01:
    logger.log(level, message, ...)
```

**4. Head-Based Sampling** (trace-aware):
```python
# If trace is sampled, log all related logs
if trace_context.is_sampled():
    logger.info("Traced log", trace_id=trace_context.trace_id)
```

---

## Log Retention

### Retention Strategy

**Hot tier** (fast SSD): 7-30 days
- Recent logs
- Full query performance
- High cost

**Warm tier** (regular disk): 30-90 days
- Older logs
- Slower queries acceptable
- Medium cost

**Cold tier** (object storage): 90+ days
- Archive logs
- Query via restore
- Low cost

### Example: Elasticsearch ILM Policy
```json
{
  "policy": {
    "phases": {
      "hot": {
        "actions": {
          "rollover": {
            "max_size": "50GB",
            "max_age": "1d"
          }
        }
      },
      "warm": {
        "min_age": "7d",
        "actions": {
          "allocate": { "number_of_replicas": 1 },
          "shrink": { "number_of_shards": 1 }
        }
      },
      "cold": {
        "min_age": "30d",
        "actions": {
          "allocate": { "require": { "box_type": "cold" } }
        }
      },
      "delete": {
        "min_age": "90d",
        "actions": {
          "delete": {}
        }
      }
    }
  }
}
```

---

## Security and Compliance

### PII Redaction

**Before logging**:
```python
import re

def redact_pii(data):
    # Redact email
    data = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                  '[EMAIL]', data)
    # Redact credit card
    data = re.sub(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
                  '[CARD]', data)
    # Redact SSN
    data = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', data)
    return data

logger.info("User data", user_input=redact_pii(user_input))
```

**In Logstash**:
```
filter {
  mutate {
    gsub => [
      "message", "\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL]",
      "message", "\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", "[CARD]"
    ]
  }
}
```

### Access Control

**Elasticsearch** (with Security):
```yaml
# Role for developers
dev_logs:
  indices:
    - names: ['app-logs-*']
      privileges: ['read']
      query: '{"match": {"environment": "development"}}'
```

**CloudWatch** (IAM Policy):
```json
{
  "Effect": "Allow",
  "Action": [
    "logs:DescribeLogGroups",
    "logs:GetLogEvents",
    "logs:FilterLogEvents"
  ],
  "Resource": "arn:aws:logs:*:*:log-group:/aws/app/production:*"
}
```

---

## Common Pitfalls

### 1. Logging Sensitive Data
❌ `logger.info("Login", password=password)`
✅ `logger.info("Login", user_id=user_id)`

### 2. Excessive Logging
❌ Logging every iteration of a loop
✅ Log aggregate results or sample

### 3. Not Including Context
❌ `logger.error("Failed")`
✅ `logger.error("Payment failed", order_id=order_id, error=str(e))`

### 4. Inconsistent Formats
❌ Mix of JSON and plain text
✅ Pick one format and stick to it

### 5. No Request IDs
❌ Can't trace request across services
✅ Generate and propagate request_id

### 6. Logging to Multiple Places
❌ Log to file AND stdout AND syslog
✅ Log to stdout, let agent handle routing

### 7. Blocking on Log Writes
❌ Synchronous writes to remote systems
✅ Asynchronous buffered writes

---

## Performance Optimization

### 1. Async Logging
```python
import logging
from logging.handlers import QueueHandler, QueueListener
import queue

# Create queue
log_queue = queue.Queue()

# Configure async handler
queue_handler = QueueHandler(log_queue)
logger.addHandler(queue_handler)

# Process logs in background thread
listener = QueueListener(log_queue, *handlers)
listener.start()
```

### 2. Conditional Logging
```python
# Avoid expensive operations if not logging
if logger.isEnabledFor(logging.DEBUG):
    logger.debug("Details", data=expensive_serialization(obj))
```

### 3. Batching
```python
# Batch logs before sending
batch = []
for log in logs:
    batch.append(log)
    if len(batch) >= 100:
        send_to_aggregator(batch)
        batch = []
```

### 4. Compression
```yaml
# Filebeat with compression
output.logstash:
  hosts: ["logstash:5044"]
  compression_level: 3
```

---

## Monitoring Log Pipeline

Track pipeline health with metrics:

```promql
# Log ingestion rate
rate(logs_ingested_total[5m])

# Pipeline lag
log_processing_lag_seconds

# Dropped logs
rate(logs_dropped_total[5m])

# Error parsing rate
rate(logs_parse_errors_total[5m])
```

Alert on:
- Sudden drop in log volume (service down?)
- High parse error rate (format changed?)
- Pipeline lag > 1 minute (capacity issue?)
