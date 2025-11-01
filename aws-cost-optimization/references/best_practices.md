# AWS Cost Optimization Best Practices

Comprehensive strategies for optimizing AWS costs across all major service categories.

## Table of Contents

1. [Compute Optimization](#compute-optimization)
2. [Storage Optimization](#storage-optimization)
3. [Network Optimization](#network-optimization)
4. [Database Optimization](#database-optimization)
5. [Container & Serverless Optimization](#container--serverless-optimization)
6. [General Principles](#general-principles)

---

## Compute Optimization

### EC2 Instance Optimization

**Right Instance Family**
- **General Purpose (T3, M5, M6i)**: Web servers, small-medium databases, dev environments
- **Compute Optimized (C5, C6i, C6g)**: CPU-intensive workloads, batch processing, HPC
- **Memory Optimized (R5, R6i, R6g)**: Databases, in-memory caches, big data
- **Storage Optimized (I3, D2)**: High IOPS, data warehousing, Hadoop

**Graviton Migration (ARM64)**
- Up to 20% cost savings with M6g, C6g, R6g, T4g instances
- Test compatibility first: Most modern languages/frameworks support ARM64
- Best for: Stateless applications, containerized workloads, open-source software

**Instance Sizing**
- Start small and scale up based on metrics
- Monitor CPU, memory, network for 2+ weeks before committing
- Use CloudWatch metrics to identify underutilized instances
- Consider burstable instances (T3) for variable workloads

**Purchase Options**
- **On-Demand**: Flexible, no commitment, highest cost
- **Reserved Instances**: 1-3 year commitment, up to 63% savings
  - Standard RI: Highest discount, no flexibility
  - Convertible RI: Moderate discount, can change instance types
- **Savings Plans**: Flexible commitment to compute spend, up to 66% savings
- **Spot Instances**: Up to 90% savings, suitable for fault-tolerant workloads

### Auto Scaling

**Horizontal Scaling**
- Scale out during peak, scale in during off-peak
- Use target tracking policies (CPU, ALB requests, custom metrics)
- Set minimum instances for high availability, maximum for cost control
- Consider scheduled scaling for predictable patterns

**Mixed Instances Policy**
- Combine instance types for better Spot availability
- Mix Spot and On-Demand for reliability
- Example: 70% Spot, 30% On-Demand for fault-tolerant apps

### Lambda Optimization

**Memory Configuration**
- Memory allocation determines CPU allocation
- More memory = faster execution = potentially lower cost
- Test different memory settings to find cost/performance sweet spot

**Cold Start Mitigation**
- Provisioned concurrency for critical functions (adds cost)
- Keep functions warm with scheduled invocations
- Minimize deployment package size
- Use Lambda layers for shared dependencies

**Execution Time**
- Optimize code to reduce execution duration
- Every 100ms of execution matters at scale
- Consider Graviton2 (arm64) for 20% better price/performance

---

## Storage Optimization

### S3 Cost Optimization

**Storage Classes**
- **S3 Standard**: Frequently accessed data
- **S3 Intelligent-Tiering**: Auto-moves between tiers, ideal for unknown patterns
- **S3 Standard-IA**: Infrequent access, 50% cheaper than Standard
- **S3 One Zone-IA**: Non-critical, infrequent access, 20% cheaper than Standard-IA
- **S3 Glacier Instant Retrieval**: Archive with instant access, 68% cheaper
- **S3 Glacier Flexible Retrieval**: Archive, retrieval in minutes-hours, 77% cheaper
- **S3 Glacier Deep Archive**: Long-term archive, retrieval in 12 hours, 83% cheaper

**Lifecycle Policies**
- Automatically transition objects between storage classes
- Delete incomplete multipart uploads after 7 days
- Example policy:
  - 0-30 days: S3 Standard
  - 30-90 days: S3 Standard-IA
  - 90-365 days: S3 Glacier Flexible Retrieval
  - 365+ days: S3 Glacier Deep Archive or Delete

**Request Optimization**
- Use CloudFront CDN to reduce S3 GET requests
- Batch operations instead of individual API calls
- Use S3 Select to retrieve subsets of data
- Enable S3 Transfer Acceleration for faster uploads (if needed)

**Cost Monitoring**
- Enable S3 Storage Lens for usage analytics
- Set up S3 Storage Class Analysis
- Monitor request costs (can exceed storage costs for small files)

### EBS Optimization

**Volume Types**
- **gp3**: General purpose, 20% cheaper than gp2, configurable IOPS/throughput
- **gp2**: Legacy general purpose (migrate to gp3)
- **io2**: High performance, mission-critical (only if needed)
- **st1**: Throughput-optimized HDD for big data (cheaper for sequential access)
- **sc1**: Cold HDD for infrequent access (cheapest)

**Snapshot Management**
- Delete old snapshots (they accumulate quickly)
- Use Lifecycle Manager for automated snapshot policies
- Snapshots are incremental but deletion is complex (use Data Lifecycle Manager)
- Consider cross-region replication costs

**Volume Cleanup**
- Delete unattached volumes
- Right-size oversized volumes
- Consider EBS Elastic Volumes to modify without downtime

---

## Network Optimization

### Data Transfer Costs

**General Rules**
- **Free**: Inbound from internet, same-AZ traffic (same subnet)
- **Cheap**: Same-region traffic across AZs
- **Expensive**: Cross-region, outbound to internet, CloudFront to origin

**Optimization Strategies**
- Colocate resources in same AZ when possible (consider HA trade-offs)
- Use VPC endpoints for AWS service access (avoids NAT/IGW costs)
- Implement caching with CloudFront, ElastiCache
- Compress data before transfer
- Use AWS PrivateLink instead of internet egress

### NAT Gateway Optimization

**Cost Structure**
- ~$32.85/month per NAT Gateway
- Data processing charges: $0.045/GB

**Alternatives**
- **VPC Endpoints**: Direct access to AWS services (S3, DynamoDB, etc.)
  - Interface endpoints: $7.20/month + $0.01/GB
  - Gateway endpoints: Free for S3 and DynamoDB
- **NAT Instance**: Cheaper but requires management
- **Single NAT Gateway**: Use one instead of one per AZ (reduces HA)
- **S3 Gateway Endpoint**: Free alternative for S3 access

**When to Use What**
- High traffic to AWS services → VPC Endpoints
- Low traffic, dev/test → Single NAT Gateway or NAT instance
- Production, HA required → NAT Gateway per AZ
- S3 access only → S3 Gateway Endpoint (free)

### CloudFront Optimization

**Use Cases for Savings**
- Reduce S3 data transfer costs (CloudFront egress is cheaper)
- Cache frequently accessed content
- Regional edge caches for less popular content

**Configuration**
- Use appropriate price class (exclude expensive regions if not needed)
- Set proper TTL to maximize cache hit ratio
- Use compression (gzip, brotli)
- Monitor cache hit ratio and adjust

---

## Database Optimization

### RDS Cost Optimization

**Instance Sizing**
- Right-size based on CloudWatch metrics (CPU, memory, connections)
- Consider burstable instances (db.t3) for variable workloads
- Graviton instances (db.m6g, db.r6g) offer 20% savings

**Storage Optimization**
- Use gp3 instead of gp2 (20% cheaper)
- Enable storage autoscaling with upper limit
- Delete old automated backups
- Reduce backup retention period if possible

**High Availability Trade-offs**
- Multi-AZ doubles cost (needed for production)
- Single-AZ acceptable for dev/test
- Read replicas for read scaling (cheaper than bigger instance)

**Aurora vs RDS**
- Aurora costs more but offers better scaling
- Aurora Serverless v2 for variable workloads
- Standard RDS for predictable workloads
- PostgreSQL/MySQL community for dev/test

### DynamoDB Optimization

**Capacity Modes**
- **On-Demand**: Pay per request, unpredictable traffic
- **Provisioned**: Cheaper for consistent traffic, requires capacity planning
- **Reserved Capacity**: 1-3 year commitment for provisioned capacity

**Table Design**
- Use single-table design to minimize costs
- Implement GSI/LSI carefully (they add cost)
- Enable point-in-time recovery only if needed
- Use TTL to auto-expire old data

**Read Optimization**
- Use eventually consistent reads (50% cheaper than strongly consistent)
- Implement caching (DAX or ElastiCache)
- Batch operations when possible

### ElastiCache Optimization

**Node Types**
- Graviton instances (cache.m6g, cache.r6g) for 20% savings
- Right-size based on memory usage and eviction rates

**Redis vs Memcached**
- Redis: More features, persistence, replication (more expensive)
- Memcached: Simpler, no persistence, multi-threaded (cheaper)

**Strategies**
- Reserved nodes for 30-55% savings
- Single-AZ for dev/test
- Monitor eviction rates to avoid over-provisioning

---

## Container & Serverless Optimization

### ECS/Fargate Optimization

**Compute Options**
- **EC2 Launch Type**: More control, cheaper for steady workloads
- **Fargate**: Serverless, easier management, better for variable loads
- **Fargate Spot**: Up to 70% savings for fault-tolerant tasks

**Graviton Support**
- Fargate ARM64 support available
- ECS on Graviton2 EC2 instances for 20% savings

**Right-sizing**
- Start with minimal CPU/memory, scale up based on metrics
- Use Container Insights for utilization data
- Consider task packing (multiple containers per task)

### EKS Optimization

**Control Plane**
- $73/month per cluster (consider consolidation)
- Use single cluster with namespaces when appropriate

**Worker Nodes**
- Use Spot instances for fault-tolerant pods (up to 90% savings)
- Managed node groups with Graviton instances
- Karpenter for intelligent autoscaling
- Mixed instance types for better Spot availability

**Cost Visibility**
- Kubecost or OpenCost for K8s cost attribution
- Resource requests/limits prevent waste
- Cluster autoscaler for automatic node scaling

---

## General Principles

### Tagging Strategy

**Cost Allocation Tags**
- Environment: prod, staging, dev, test
- Owner: team/person responsible
- Project: business initiative
- CostCenter: chargeback allocation
- Application: specific app name

**Tag Enforcement**
- Use AWS Organizations policies to enforce tagging
- Service Control Policies to prevent untagged resources
- AWS Config rules for compliance

### Monitoring and Governance

**Cost Monitoring Tools**
- AWS Cost Explorer: Historical analysis
- AWS Budgets: Proactive alerts
- Cost and Usage Reports: Detailed data export
- Cost Anomaly Detection: Automatic anomaly alerts

**Regular Reviews**
- Monthly cost review meetings
- Quarterly rightsizing exercises
- Annual Reserved Instance/Savings Plan optimization
- Automated reports to stakeholders

### Automation

**Infrastructure as Code**
- Define resource sizes in code (prevent oversizing)
- Automated cleanup of dev/test resources
- Scheduled shutdown of non-production resources

**Cost Optimization Tools**
- AWS Compute Optimizer: ML-based recommendations
- AWS Trusted Advisor: Best practice checks
- Third-party tools: CloudHealth, Cloudability, Spot.io

### Cultural Best Practices

**Engineering Ownership**
- Engineers should see cost impact of their changes
- Cost metrics in dashboards alongside performance
- Cost budgets for teams/projects

**Experiments and Cleanup**
- Tag experimental resources with expiration dates
- Automated cleanup of abandoned resources
- Regular audits of unused resources

**Cost-Aware Architecture**
- Design for cost from the beginning
- Choose appropriate service tiers
- Implement auto-scaling and right-sizing from day one
- Consider serverless and managed services

---

## Quick Wins Checklist

- [ ] Delete unattached EBS volumes
- [ ] Delete old EBS snapshots
- [ ] Release unused Elastic IPs
- [ ] Stop or terminate idle EC2 instances
- [ ] Right-size oversized instances
- [ ] Convert gp2 to gp3 volumes
- [ ] Enable S3 Intelligent-Tiering
- [ ] Set up S3 lifecycle policies
- [ ] Replace NAT Gateways with VPC Endpoints where possible
- [ ] Migrate to Graviton instances
- [ ] Purchase Reserved Instances/Savings Plans for stable workloads
- [ ] Use Spot instances for fault-tolerant workloads
- [ ] Delete old RDS snapshots
- [ ] Enable DynamoDB auto-scaling
- [ ] Set up cost allocation tags
- [ ] Enable AWS Budgets alerts
- [ ] Schedule shutdown of dev/test resources
