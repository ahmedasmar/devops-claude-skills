# Distributed Tracing Guide

## What is Distributed Tracing?

Distributed tracing tracks a request as it flows through multiple services in a distributed system.

### Key Concepts

**Trace**: End-to-end journey of a request
**Span**: Single operation within a trace
**Context**: Metadata propagated between services (trace_id, span_id)

### Example Flow
```
User Request → API Gateway → Auth Service → User Service → Database
                    ↓              ↓             ↓
              [Trace ID: abc123]
              Span 1: gateway (50ms)
              Span 2: auth (20ms)
              Span 3: user_service (100ms)
              Span 4: db_query (80ms)

Total: 250ms with waterfall view showing dependencies
```

---

## OpenTelemetry (OTel)

OpenTelemetry is the industry standard for instrumentation.

### Components

**API**: Instrument code (create spans, add attributes)
**SDK**: Implement API, configure exporters
**Collector**: Receive, process, and export telemetry data
**Exporters**: Send data to backends (Jaeger, Tempo, Zipkin)

### Architecture
```
Application → OTel SDK → OTel Collector → Backend (Jaeger/Tempo)
                                              ↓
                                          Visualization
```

---

## Instrumentation Examples

### Python (using OpenTelemetry)

**Setup**:
```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Setup tracer
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Configure exporter
otlp_exporter = OTLPSpanExporter(endpoint="localhost:4317")
span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)
```

**Manual instrumentation**:
```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

@tracer.start_as_current_span("process_order")
def process_order(order_id):
    span = trace.get_current_span()
    span.set_attribute("order.id", order_id)
    span.set_attribute("order.amount", 99.99)

    try:
        result = payment_service.charge(order_id)
        span.set_attribute("payment.status", "success")
        return result
    except Exception as e:
        span.set_status(trace.Status(trace.StatusCode.ERROR))
        span.record_exception(e)
        raise
```

**Auto-instrumentation** (Flask example):
```python
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

# Auto-instrument Flask
FlaskInstrumentor().instrument_app(app)

# Auto-instrument requests library
RequestsInstrumentor().instrument()

# Auto-instrument SQLAlchemy
SQLAlchemyInstrumentor().instrument(engine=db.engine)
```

### Node.js (using OpenTelemetry)

**Setup**:
```javascript
const { NodeTracerProvider } = require('@opentelemetry/sdk-trace-node');
const { BatchSpanProcessor } = require('@opentelemetry/sdk-trace-base');
const { OTLPTraceExporter } = require('@opentelemetry/exporter-trace-otlp-grpc');

// Setup provider
const provider = new NodeTracerProvider();
const exporter = new OTLPTraceExporter({ url: 'localhost:4317' });
provider.addSpanProcessor(new BatchSpanProcessor(exporter));
provider.register();
```

**Manual instrumentation**:
```javascript
const tracer = provider.getTracer('my-service');

async function processOrder(orderId) {
  const span = tracer.startSpan('process_order');
  span.setAttribute('order.id', orderId);

  try {
    const result = await paymentService.charge(orderId);
    span.setAttribute('payment.status', 'success');
    return result;
  } catch (error) {
    span.setStatus({ code: SpanStatusCode.ERROR });
    span.recordException(error);
    throw error;
  } finally {
    span.end();
  }
}
```

**Auto-instrumentation**:
```javascript
const { registerInstrumentations } = require('@opentelemetry/instrumentation');
const { HttpInstrumentation } = require('@opentelemetry/instrumentation-http');
const { ExpressInstrumentation } = require('@opentelemetry/instrumentation-express');
const { MongoDBInstrumentation } = require('@opentelemetry/instrumentation-mongodb');

registerInstrumentations({
  instrumentations: [
    new HttpInstrumentation(),
    new ExpressInstrumentation(),
    new MongoDBInstrumentation()
  ]
});
```

### Go (using OpenTelemetry)

**Setup**:
```go
import (
    "go.opentelemetry.io/otel"
    "go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
    "go.opentelemetry.io/otel/sdk/trace"
)

func initTracer() {
    exporter, _ := otlptracegrpc.New(context.Background())
    tp := trace.NewTracerProvider(
        trace.WithBatcher(exporter),
    )
    otel.SetTracerProvider(tp)
}
```

**Manual instrumentation**:
```go
import (
    "go.opentelemetry.io/otel"
    "go.opentelemetry.io/otel/attribute"
)

func processOrder(ctx context.Context, orderID string) error {
    tracer := otel.Tracer("my-service")
    ctx, span := tracer.Start(ctx, "process_order")
    defer span.End()

    span.SetAttributes(
        attribute.String("order.id", orderID),
        attribute.Float64("order.amount", 99.99),
    )

    err := paymentService.Charge(ctx, orderID)
    if err != nil {
        span.RecordError(err)
        return err
    }

    span.SetAttributes(attribute.String("payment.status", "success"))
    return nil
}
```

---

## Span Attributes

### Semantic Conventions

Follow OpenTelemetry semantic conventions for consistency:

**HTTP**:
```python
span.set_attribute("http.method", "GET")
span.set_attribute("http.url", "https://api.example.com/users")
span.set_attribute("http.status_code", 200)
span.set_attribute("http.user_agent", "Mozilla/5.0...")
```

**Database**:
```python
span.set_attribute("db.system", "postgresql")
span.set_attribute("db.name", "users_db")
span.set_attribute("db.statement", "SELECT * FROM users WHERE id = ?")
span.set_attribute("db.operation", "SELECT")
```

**RPC/gRPC**:
```python
span.set_attribute("rpc.system", "grpc")
span.set_attribute("rpc.service", "UserService")
span.set_attribute("rpc.method", "GetUser")
span.set_attribute("rpc.grpc.status_code", 0)
```

**Messaging**:
```python
span.set_attribute("messaging.system", "kafka")
span.set_attribute("messaging.destination", "user-events")
span.set_attribute("messaging.operation", "publish")
span.set_attribute("messaging.message_id", "msg123")
```

### Custom Attributes

Add business context:
```python
span.set_attribute("user.id", "user123")
span.set_attribute("order.id", "ORD-456")
span.set_attribute("feature.flag.checkout_v2", True)
span.set_attribute("cache.hit", False)
```

---

## Context Propagation

### W3C Trace Context (Standard)

Headers propagated between services:
```
traceparent: 00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01
tracestate: vendor1=value1,vendor2=value2
```

**Format**: `version-trace_id-parent_span_id-trace_flags`

### Implementation

**Python**:
```python
from opentelemetry.propagate import inject, extract
import requests

# Inject context into outgoing request
headers = {}
inject(headers)
requests.get("https://api.example.com", headers=headers)

# Extract context from incoming request
from flask import request
ctx = extract(request.headers)
```

**Node.js**:
```javascript
const { propagation } = require('@opentelemetry/api');

// Inject
const headers = {};
propagation.inject(context.active(), headers);
axios.get('https://api.example.com', { headers });

// Extract
const ctx = propagation.extract(context.active(), req.headers);
```

**HTTP Example**:
```bash
curl -H "traceparent: 00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01" \
     https://api.example.com/users
```

---

## Sampling Strategies

### 1. Always On/Off
```python
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.sampling import ALWAYS_ON, ALWAYS_OFF

# Development: trace everything
provider = TracerProvider(sampler=ALWAYS_ON)

# Production: trace nothing (usually not desired)
provider = TracerProvider(sampler=ALWAYS_OFF)
```

### 2. Probability-Based
```python
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

# Sample 10% of traces
provider = TracerProvider(sampler=TraceIdRatioBased(0.1))
```

### 3. Rate Limiting
```python
from opentelemetry.sdk.trace.sampling import ParentBased, RateLimitingSampler

# Sample max 100 traces per second
sampler = ParentBased(root=RateLimitingSampler(100))
provider = TracerProvider(sampler=sampler)
```

### 4. Parent-Based (Default)
```python
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

# If parent span is sampled, sample child spans
sampler = ParentBased(root=TraceIdRatioBased(0.1))
provider = TracerProvider(sampler=sampler)
```

### 5. Custom Sampling
```python
from opentelemetry.sdk.trace.sampling import Sampler, Decision

class ErrorSampler(Sampler):
    """Always sample errors, sample 1% of successes"""

    def should_sample(self, parent_context, trace_id, name, **kwargs):
        attributes = kwargs.get('attributes', {})

        # Always sample if error
        if attributes.get('error', False):
            return Decision.RECORD_AND_SAMPLE

        # Sample 1% of successes
        if trace_id & 0xFF < 3:  # ~1%
            return Decision.RECORD_AND_SAMPLE

        return Decision.DROP

provider = TracerProvider(sampler=ErrorSampler())
```

---

## Backends

### Jaeger

**Docker Compose**:
```yaml
version: '3'
services:
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"  # UI
      - "4317:4317"    # OTLP gRPC
      - "4318:4318"    # OTLP HTTP
    environment:
      - COLLECTOR_OTLP_ENABLED=true
```

**Query traces**:
```bash
# UI: http://localhost:16686

# API: Get trace by ID
curl http://localhost:16686/api/traces/abc123

# Search traces
curl "http://localhost:16686/api/traces?service=my-service&limit=20"
```

### Grafana Tempo

**Docker Compose**:
```yaml
version: '3'
services:
  tempo:
    image: grafana/tempo:latest
    ports:
      - "3200:3200"   # Tempo
      - "4317:4317"   # OTLP gRPC
    volumes:
      - ./tempo.yaml:/etc/tempo.yaml
    command: ["-config.file=/etc/tempo.yaml"]
```

**tempo.yaml**:
```yaml
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
    backend: local
    local:
      path: /tmp/tempo/traces
```

**Query in Grafana**:
- Install Tempo data source
- Use TraceQL: `{ span.http.status_code = 500 }`

### AWS X-Ray

**Configuration**:
```python
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.ext.flask.middleware import XRayMiddleware

xray_recorder.configure(service='my-service')
XRayMiddleware(app, xray_recorder)
```

**Query**:
```bash
aws xray get-trace-summaries \
  --start-time 2024-10-28T00:00:00 \
  --end-time 2024-10-28T23:59:59 \
  --filter-expression 'error = true'
```

---

## Analysis Patterns

### Find Slow Traces
```
# Jaeger UI
- Filter by service
- Set min duration: 1000ms
- Sort by duration

# TraceQL (Tempo)
{ duration > 1s }
```

### Find Error Traces
```
# Jaeger UI
- Filter by tag: error=true
- Or by HTTP status: http.status_code=500

# TraceQL (Tempo)
{ span.http.status_code >= 500 }
```

### Find Traces by User
```
# Jaeger UI
- Filter by tag: user.id=user123

# TraceQL (Tempo)
{ span.user.id = "user123" }
```

### Find N+1 Query Problems
Look for:
- Many sequential database spans
- Same query repeated multiple times
- Pattern: API call → DB query → DB query → DB query...

### Find Service Bottlenecks
- Identify spans with longest duration
- Check if time is spent in service logic or waiting for dependencies
- Look at span relationships (parallel vs sequential)

---

## Integration with Logs

### Trace ID in Logs

**Python**:
```python
from opentelemetry import trace

def add_trace_context():
    span = trace.get_current_span()
    trace_id = span.get_span_context().trace_id
    span_id = span.get_span_context().span_id

    return {
        "trace_id": format(trace_id, '032x'),
        "span_id": format(span_id, '016x')
    }

logger.info("Processing order", **add_trace_context(), order_id=order_id)
```

**Query logs for trace**:
```
# Elasticsearch
GET /logs/_search
{
  "query": {
    "match": { "trace_id": "0af7651916cd43dd8448eb211c80319c" }
  }
}

# Loki (LogQL)
{job="app"} |= "0af7651916cd43dd8448eb211c80319c"
```

### Trace from Log (Grafana)

Configure derived fields in Grafana:
```yaml
datasources:
  - name: Loki
    type: loki
    jsonData:
      derivedFields:
        - name: TraceID
          matcherRegex: "trace_id=([\\w]+)"
          url: "http://tempo:3200/trace/$${__value.raw}"
          datasourceUid: tempo_uid
```

---

## Best Practices

### 1. Span Naming
✅ Use operation names, not IDs
- Good: `GET /api/users`, `UserService.GetUser`, `db.query.users`
- Bad: `/api/users/123`, `span_abc`, `query_1`

### 2. Span Granularity
✅ One span per logical operation
- Too coarse: One span for entire request
- Too fine: Span for every variable assignment
- Just right: Span per service call, database query, external API

### 3. Add Context
Always include:
- Operation name
- Service name
- Error status
- Business identifiers (user_id, order_id)

### 4. Handle Errors
```python
try:
    result = operation()
except Exception as e:
    span.set_status(trace.Status(trace.StatusCode.ERROR))
    span.record_exception(e)
    raise
```

### 5. Sampling Strategy
- Development: 100%
- Staging: 50-100%
- Production: 1-10% (or error-based)

### 6. Performance Impact
- Overhead: ~1-5% CPU
- Use async exporters
- Batch span exports
- Sample appropriately

### 7. Cardinality
Avoid high-cardinality attributes:
- ❌ Email addresses
- ❌ Full URLs with unique IDs
- ❌ Timestamps
- ✅ User ID
- ✅ Endpoint pattern
- ✅ Status code

---

## Common Issues

### Missing Traces
**Cause**: Context not propagated
**Solution**: Verify headers are injected/extracted

### Incomplete Traces
**Cause**: Spans not closed properly
**Solution**: Always use `defer span.End()` or context managers

### High Overhead
**Cause**: Too many spans or synchronous export
**Solution**: Reduce span count, use batch processor

### No Error Traces
**Cause**: Errors not recorded on spans
**Solution**: Call `span.record_exception()` and set error status

---

## Metrics from Traces

Generate RED metrics from trace data:

**Rate**: Traces per second
**Errors**: Traces with error status
**Duration**: Span duration percentiles

**Example** (using Tempo + Prometheus):
```yaml
# Generate metrics from spans
metrics_generator:
  processor:
    span_metrics:
      dimensions:
        - http.method
        - http.status_code
```

**Query**:
```promql
# Request rate
rate(traces_spanmetrics_calls_total[5m])

# Error rate
rate(traces_spanmetrics_calls_total{status_code="STATUS_CODE_ERROR"}[5m])
  /
rate(traces_spanmetrics_calls_total[5m])

# P95 latency
histogram_quantile(0.95, traces_spanmetrics_latency_bucket)
```
