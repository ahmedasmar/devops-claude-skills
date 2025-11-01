# AWS Service Alternatives - Cost Optimization Guide

When to use cheaper alternatives and cost-effective service options for common AWS services.

## Table of Contents

1. [Compute Alternatives](#compute-alternatives)
2. [Storage Alternatives](#storage-alternatives)
3. [Database Alternatives](#database-alternatives)
4. [Networking Alternatives](#networking-alternatives)
5. [Application Services](#application-services)

---

## Compute Alternatives

### EC2 vs Lambda vs Fargate

**EC2 (Most Economical for Consistent Workloads)**
- **When to use**: 24/7 workloads, predictable traffic, need full OS control
- **Cost model**: Hourly charges, cheaper with Reserved Instances
- **Best for**: Always-on applications, legacy apps, specific OS/kernel requirements
- **Example**: Web server handling steady traffic → EC2 with Reserved Instance

**Lambda (Most Economical for Intermittent Work)**
- **When to use**: Event-driven, sporadic usage, < 15 minute executions
- **Cost model**: Pay per execution and duration (GB-seconds)
- **Best for**: APIs with sporadic traffic, scheduled tasks, event processing
- **Example**: Image processing triggered by S3 upload → Lambda
- **Break-even**: ~20-30 hours/month execution time vs equivalent EC2

**Fargate (Middle Ground)**
- **When to use**: Containerized apps, variable traffic, don't want to manage servers
- **Cost model**: Pay for vCPU and memory allocated
- **Best for**: Microservices, batch jobs, variable load applications
- **Example**: Background worker that scales 0-10 containers → Fargate
- **Tip**: Fargate Spot offers up to 70% savings for fault-tolerant tasks

**Decision Matrix**
```
Consistent 24/7 load → EC2 with Reserved Instances
Variable load, containerized → Fargate (or Fargate Spot)
Event-driven, < 15 min → Lambda
Batch processing → Fargate Spot or EC2 Spot
```

### EC2 Instance Alternatives

**Standard vs Graviton (ARM64)**
- **Graviton Savings**: 20% cheaper for same performance
- **When to use**: Modern applications, ARM-compatible workloads
- **Alternatives**:
  - t3.large → t4g.large (20% cheaper)
  - m5.xlarge → m6g.xlarge (20% cheaper)
  - c5.2xlarge → c6g.2xlarge (20% cheaper)
- **Considerations**: Test application compatibility first

**Current vs Previous Generation**
- **Migration Savings**: 5-10% cheaper, better performance
- **Examples**:
  - t2 → t3 (10% cheaper, better performance)
  - m4 → m5 → m6i (progressive improvements)
  - c4 → c5 → c6i (better price/performance)
- **Action**: Check `detect_old_generations.py` script

**On-Demand vs Spot vs Reserved**
- **On-Demand**: $X/hour, highest cost, full flexibility
- **Spot**: 60-90% discount, can be interrupted
- **Reserved (1yr)**: 30-40% discount
- **Reserved (3yr)**: 50-65% discount
- **Decision**: Use Spot for fault-tolerant, RI for predictable, On-Demand for rest

---

## Storage Alternatives

### S3 Storage Classes

**Frequently Accessed Data**
```
S3 Standard → $0.023/GB/month
Use when: Accessing files multiple times per month
```

**Infrequently Accessed Data**
```
S3 Standard → S3 Standard-IA
$0.023/GB/month → $0.0125/GB/month (46% cheaper)
Retrieval cost: $0.01/GB
Break-even: < 1 access per month
Use when: Backups, disaster recovery, infrequently accessed files
```

**Unknown Access Patterns**
```
S3 Standard → S3 Intelligent-Tiering
$0.023/GB/month → Automatic optimization
Extra cost: $0.0025 per 1000 objects monitored
Use when: Unclear access patterns, don't want to manage lifecycle
Best for: Mixed workloads, analytics datasets
```

**Archive Storage**
```
S3 Standard → S3 Glacier Instant Retrieval
$0.023/GB → $0.004/GB (83% cheaper)
Retrieval: Milliseconds, $0.03/GB
Use when: Archive with immediate access needs (e.g., medical records)

S3 Standard → S3 Glacier Flexible Retrieval
$0.023/GB → $0.0036/GB (84% cheaper)
Retrieval: Minutes to hours, $0.01/GB
Use when: Archive data, acceptable retrieval delay

S3 Standard → S3 Glacier Deep Archive
$0.023/GB → $0.00099/GB (96% cheaper)
Retrieval: 12 hours, $0.02/GB
Use when: Long-term archive, regulatory compliance, rarely accessed
```

**Decision Tree**
```
Accessed daily → S3 Standard
Accessed monthly → S3 Standard-IA
Unknown pattern → S3 Intelligent-Tiering
Archive, instant access → Glacier Instant Retrieval
Archive, can wait hours → Glacier Flexible Retrieval
Archive, can wait 12 hours → Glacier Deep Archive
```

### EBS Volume Types

**General Purpose Volumes**
```
gp2 → gp3
$0.10/GB → $0.08/GB (20% cheaper)
Additional benefits: Configurable IOPS/throughput independent of size
Action: Convert all gp2 to gp3 (no downtime required)
```

**High Performance Workloads**
```
io1 → io2
Same price, better durability and IOPS
io2 Block Express: For highest performance needs

Consider: Do you really need provisioned IOPS?
Many workloads perform fine on gp3 (up to 16,000 IOPS)
Test gp3 before committing to io2
```

**Throughput-Optimized Workloads**
```
gp3 → st1 (Throughput Optimized HDD)
$0.08/GB → $0.045/GB (44% cheaper)
Use when: Big data, data warehouses, log processing
Sequential access patterns, throughput more important than IOPS
```

**Cold Data**
```
gp3 → sc1 (Cold HDD)
$0.08/GB → $0.015/GB (81% cheaper)
Use when: Infrequently accessed data, lowest cost priority
Example: Archive storage, cold backups
```

### EFS vs S3 vs EBS

**S3 (Cheapest for Object Storage)**
- **Cost**: $0.023/GB/month (Standard)
- **When to use**: Object storage, static files, backups
- **Pros**: Unlimited scale, integrates with everything
- **Cons**: Not a file system, higher latency

**EBS (Best for Single-Instance Block Storage)**
- **Cost**: $0.08/GB/month (gp3)
- **When to use**: Boot volumes, database storage, single EC2 instance
- **Pros**: High performance, low latency
- **Cons**: Single-AZ, attached to one instance

**EFS (File System Across Multiple Instances)**
- **Cost**: $0.30/GB/month (Standard), $0.016/GB/month (IA)
- **When to use**: Shared file storage across multiple instances
- **Pros**: Multi-AZ, grows automatically, NFSv4
- **Cons**: More expensive than EBS
- **Optimization**: Use EFS Intelligent-Tiering to auto-move to IA class

**Decision Matrix**
```
Single instance, block storage → EBS
Multiple instances, shared files → EFS (with Intelligent-Tiering)
Object storage, static files → S3
Large data, high throughput → FSx for Lustre
Windows file shares → FSx for Windows
```

---

## Database Alternatives

### RDS vs Aurora vs Self-Managed

**RDS PostgreSQL/MySQL (Baseline)**
- **Cost**: Instance + storage
- **When to use**: Standard relational DB needs
- **Example**: db.t3.medium = ~$60/month + storage

**Aurora PostgreSQL/MySQL (2-3x RDS Cost)**
- **Cost**: Instance + storage + I/O charges
- **When to use**: Need high availability, auto-scaling storage, read replicas
- **Pros**: Better performance, automatic failover, up to 15 read replicas
- **Cons**: More expensive
- **Break-even**: High read traffic, need fast replication

**Aurora Serverless v2 (Variable Workloads)**
- **Cost**: Pay per ACU (Aurora Capacity Unit) per second
- **When to use**: Variable load, dev/test, infrequent usage
- **Example**: Dev database used 8 hours/day → 67% savings vs always-on
- **Limitation**: Min capacity charges apply

**Self-Managed on EC2 (Cheapest for Experts)**
- **Cost**: Just EC2 + EBS costs
- **When to use**: Full control needed, specific configuration, cost-sensitive
- **Pros**: Can be 50-70% cheaper than RDS
- **Cons**: You manage backups, patching, HA, monitoring
- **Consideration**: Factor in operational overhead

**Decision Matrix**
```
Standard workload, managed preferred → RDS
High availability, many reads → Aurora
Variable workload → Aurora Serverless v2
Cost-sensitive, have DBA expertise → Self-managed on EC2
Dev/test, intermittent use → Aurora Serverless v2
```

### DynamoDB Pricing Models

**On-Demand (Unpredictable Traffic)**
- **Cost**: $1.25 per million writes, $0.25 per million reads
- **When to use**: Variable traffic, new applications, spiky workloads
- **Pros**: No capacity planning, scales automatically
- **Example**: New API with unknown traffic pattern

**Provisioned Capacity (Predictable Traffic)**
- **Cost**: $0.00065 per WCU/hour, $0.00013 per RCU/hour
- **When to use**: Predictable traffic patterns
- **Savings**: 60-80% cheaper than on-demand at consistent usage
- **Example**: Application with steady 100 req/sec

**Reserved Capacity (Long-term Commitment)**
- **Cost**: Additional 30-50% discount on provisioned capacity
- **When to use**: Known long-term capacity needs
- **Commitment**: 1-3 years

**Break-Even Calculation**
```
On-Demand: $1.25 per million writes
Provisioned: ~$0.47 per million writes (at capacity)
Break-even: ~65% consistent utilization

Action: Start with on-demand, switch to provisioned once patterns clear
```

### Database Migration Options

**From Commercial to Open Source**
```
Oracle → Aurora PostgreSQL or RDS PostgreSQL
Savings: 90% on licensing costs
Consider: PostgreSQL compatibility, migration effort

SQL Server → Aurora PostgreSQL or RDS PostgreSQL/MySQL
Savings: 50-90% on licensing costs
Consider: Application compatibility, migration effort
```

**From RDS to Aurora**
```
Only if: High availability requirements, many read replicas needed
Cost increase: 20-50% more
Benefit: Better performance, automatic failover, scaling
```

**From Aurora to RDS**
```
When: Don't need Aurora features, cost-conscious
Savings: 20-50%
Downgrade if: Single-AZ sufficient, limited read replicas needed
```

---

## Networking Alternatives

### NAT Gateway Alternatives

**NAT Gateway (Default, Expensive)**
- **Cost**: $32.85/month + $0.045/GB processed
- **When to use**: Production, high availability, easy management

**VPC Endpoints (Cheaper for AWS Services)**
- **Gateway Endpoint (S3, DynamoDB)**: FREE
- **Interface Endpoint**: $7.20/month + $0.01/GB
- **When to use**: Accessing S3, DynamoDB, or other AWS services
- **Savings**: $25-30/month vs NAT Gateway
- **Example**: Lambda accessing S3 → Use S3 Gateway Endpoint

**NAT Instance (Cheapest, More Work)**
- **Cost**: Just EC2 cost (e.g., t3.micro = $7.50/month)
- **When to use**: Dev/test, cost-sensitive, low traffic
- **Cons**: Must manage, less resilient, manual HA setup
- **Savings**: 75% vs NAT Gateway

**Decision Matrix**
```
S3 or DynamoDB only → Gateway Endpoint (FREE)
Other AWS services → Interface Endpoint
Production, high availability → NAT Gateway
Dev/test, low traffic → NAT Instance or single NAT Gateway
```

### Load Balancer Alternatives

**Application Load Balancer (ALB)**
- **Cost**: $16.20/month + LCU charges
- **When to use**: HTTP/HTTPS, path-based routing, microservices
- **Features**: Layer 7, content-based routing, Lambda targets

**Network Load Balancer (NLB)**
- **Cost**: $22.35/month + LCU charges
- **When to use**: TCP/UDP, extreme performance, static IPs
- **Use case**: Non-HTTP protocols, high throughput

**Classic Load Balancer (Legacy)**
- **Cost**: $18/month + data charges
- **Recommendation**: Migrate to ALB or NLB (better features, often cheaper)

**CloudFront + S3 (Static Content)**
- **Cost**: Much cheaper for static content
- **When to use**: Static website, single-page app
- **Setup**: S3 static hosting + CloudFront distribution
- **Savings**: 90% vs ALB for static content

**API Gateway (REST APIs)**
- **Cost**: Pay per request
- **When to use**: REST API, need API management features
- **Alternative to**: ALB for simple APIs

---

## Application Services

### Message Queue Alternatives

**SQS vs SNS vs EventBridge vs Kinesis**

**SQS (Point-to-Point, Cheapest)**
- **Cost**: $0.40 per million requests (Standard), $0.50 (FIFO)
- **When to use**: Work queues, decoupling services
- **Best for**: Job processing, task queues

**SNS (Pub/Sub, Cheap)**
- **Cost**: $0.50 per million publishes
- **When to use**: Fan-out notifications, multiple subscribers
- **Best for**: Notifications, multiple consumers

**EventBridge (Event Router)**
- **Cost**: $1.00 per million events
- **When to use**: Event-driven architecture, complex routing
- **Best for**: Cross-account events, SaaS integrations

**Kinesis (Streaming, Expensive)**
- **Cost**: $0.015 per shard-hour + PUT charges
- **When to use**: Real-time streaming, ordered processing
- **Best for**: Logs, analytics, real-time processing
- **Alternative**: Kinesis Data Firehose (simpler, cheaper for basic needs)

**Decision Matrix**
```
Simple queue → SQS
Multiple consumers → SNS
Complex event routing → EventBridge
Real-time streaming → Kinesis
Log aggregation → Kinesis Firehose
```

### Container Orchestration

**ECS vs EKS vs Fargate**

**ECS on EC2 (Cheapest)**
- **Cost**: Just EC2 costs (no ECS fee)
- **When to use**: AWS-native, simpler workloads
- **Best for**: Cost-sensitive, AWS-specific deployments

**ECS on Fargate (Serverless, Easy)**
- **Cost**: Pay per task (vCPU + memory)
- **When to use**: Variable load, don't want to manage servers
- **Best for**: Variable workloads, simpler operations

**EKS (Kubernetes, Expensive)**
- **Cost**: $73/month per cluster + node costs
- **When to use**: Need Kubernetes, multi-cloud, complex deployments
- **Best for**: Kubernetes expertise, need K8s ecosystem
- **Tip**: Consolidate workloads to fewer clusters

**Decision Matrix**
```
AWS-native, cost-sensitive → ECS on EC2
Variable load, easy management → ECS on Fargate
Need Kubernetes → EKS
Multiple environments → Consider single EKS cluster with namespaces
```

---

## Quick Reference: When to Switch

### Immediate Actions (Low Risk)
- [ ] gp2 → gp3 (20% savings, no downtime)
- [ ] S3 Standard → Intelligent-Tiering (auto-optimization)
- [ ] NAT Gateway → VPC Endpoints for S3/DynamoDB (free)
- [ ] Old generation instances → New generation (10-20% savings)
- [ ] Intel → Graviton (20% savings, test first)

### Medium Effort Actions
- [ ] On-Demand → Reserved Instances/Savings Plans (40-65% savings)
- [ ] Always-on EC2 → Lambda for intermittent work
- [ ] S3 Standard → Lifecycle policies (50-95% savings on old data)
- [ ] RDS On-Demand → Reserved Instances (40-65% savings)
- [ ] DynamoDB On-Demand → Provisioned (60-80% savings if predictable)

### High Effort Actions (Evaluate Carefully)
- [ ] RDS → Aurora (usually more expensive, only if need features)
- [ ] Aurora → RDS (20-50% savings if don't need Aurora features)
- [ ] Commercial DB → PostgreSQL (90% savings, migration effort)
- [ ] EC2 → Lambda (case-by-case, break-even analysis needed)
- [ ] ECS → EKS (usually more expensive, only if need K8s)

---

## Cost Comparison Tool

Use this mental model when evaluating alternatives:

```
1. Calculate current monthly cost
2. Calculate alternative monthly cost
3. Estimate migration effort (hours × $cost)
4. Calculate payback period: Migration Cost / Monthly Savings
5. Decide: Payback < 3 months → Likely worth it
           Payback > 6 months → Evaluate carefully
```

**Example:**
```
Current: ALB for static site = $20/month
Alternative: CloudFront + S3 = $2/month
Savings: $18/month
Migration: 4 hours × $100/hour = $400
Payback: $400 / $18 = 22 months → Maybe not worth it

But if: Multiple sites, reusable pattern → Worth the investment
```
