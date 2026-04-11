---
name: aws-cost-optimization
description: "AWS cost optimization and FinOps workflows. Use this skill whenever the user mentions AWS costs, cloud spending, FinOps, Reserved Instances, Savings Plans, or cost reduction. Triggers include finding unused resources, analyzing the AWS bill, rightsizing EC2 or RDS instances, evaluating Spot instances, detecting cost anomalies, migrating to Graviton or newer instance generations, implementing tagging for cost allocation, setting up AWS Budgets, conducting monthly cost reviews, comparing RI vs Savings Plans, and optimizing storage, network, or database costs."
---

# AWS Cost Optimization & FinOps

Systematic workflows for AWS cost optimization and financial operations management.

## Cost Optimization Workflow

1. **Discover** — Find waste using `aws ec2` and `aws ce` CLI commands to identify unused resources and cost anomalies
2. **Analyze** — Find opportunities with `aws compute-optimizer`, `aws cloudwatch`, and `aws ce` for rightsizing, generation upgrades, Spot, and RI recommendations
3. **Prioritize** — Quick wins (low risk, high savings) first, then low-hanging fruit, then strategic improvements
4. **Implement** — Delete unused resources, rightsize instances, purchase commitments, migrate generations
5. **Monitor** — Monthly cost reviews, tag compliance, budget variance tracking

---

## Core Workflows

### Workflow 1: Monthly Cost Optimization Review

**Frequency**: Run monthly (first week of each month)

**Step 1: Find Unused Resources**
```bash
# Find unattached EBS volumes
aws ec2 describe-volumes --filters Name=status,Values=available \
  --query 'Volumes[].{ID:VolumeId,Size:Size,Created:CreateTime}' --output table

# Find unused Elastic IPs
aws ec2 describe-addresses --filters Name=domain,Values=vpc \
  --query 'Addresses[?AssociationId==null].{IP:PublicIp,AllocationId:AllocationId}' --output table

# Find idle EC2 instances (low CPU over 14 days)
aws cloudwatch get-metric-statistics --namespace AWS/EC2 \
  --metric-name CPUUtilization --period 86400 --statistics Average \
  --start-time $(date -u -v-14d +%Y-%m-%dT%H:%M:%S) --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --dimensions Name=InstanceId,Value=INSTANCE_ID

# Find old snapshots (>90 days)
aws ec2 describe-snapshots --owner-ids self \
  --query 'Snapshots[?StartTime<=`2025-01-01`].{ID:SnapshotId,Size:VolumeSize,Date:StartTime}' --output table

# Find unused load balancers (no healthy targets)
aws elbv2 describe-target-health --target-group-arn TARGET_GROUP_ARN
```

**Step 2: Analyze Cost Anomalies**
```bash
# Get daily costs for the past 30 days
aws ce get-cost-and-usage \
  --time-period Start=$(date -u -v-30d +%Y-%m-%d),End=$(date -u +%Y-%m-%d) \
  --granularity DAILY --metrics BlendedCost \
  --group-by Type=DIMENSION,Key=SERVICE

# Get cost forecast for the next 30 days
aws ce get-cost-forecast \
  --time-period Start=$(date -u +%Y-%m-%d),End=$(date -u -v+30d +%Y-%m-%d) \
  --granularity MONTHLY --metric BLENDED_COST

# Compare month-over-month costs
aws ce get-cost-and-usage \
  --time-period Start=$(date -u -v-60d +%Y-%m-01),End=$(date -u +%Y-%m-%d) \
  --granularity MONTHLY --metrics BlendedCost
```

**Step 3: Identify Rightsizing Opportunities**
```bash
# Get Compute Optimizer rightsizing recommendations
aws compute-optimizer get-ec2-instance-recommendations \
  --query 'instanceRecommendations[].{Instance:instanceArn,Finding:finding,Current:currentInstanceType,Recommended:recommendationOptions[0].instanceType}'

# Check CPU utilization for a specific instance (past 30 days)
aws cloudwatch get-metric-statistics --namespace AWS/EC2 \
  --metric-name CPUUtilization --period 3600 --statistics Average Maximum \
  --start-time $(date -u -v-30d +%Y-%m-%dT%H:%M:%S) --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --dimensions Name=InstanceId,Value=INSTANCE_ID

# Get RDS rightsizing recommendations
aws compute-optimizer get-ecs-service-recommendations 2>/dev/null || \
  echo "Check RDS CPU/memory in CloudWatch manually"
```

**Step 4: Generate Monthly Report**
```bash
# Use the template to compile findings
cp assets/templates/monthly_cost_report.md reports/$(date +%Y-%m)-cost-report.md

# Fill in:
# - Findings from AWS CLI analysis
# - Action items
# - Team cost breakdowns
# - Optimization wins
```

**Step 5: Team Review Meeting**
- Present findings to engineering teams
- Assign optimization tasks
- Track action items to completion

---

### Workflow 2: Commitment Purchase Analysis (RI/Savings Plans)

**When**: Quarterly or when usage patterns stabilize

**Step 1: Analyze Current Usage**
```bash
# Get EC2 RI purchase recommendations
aws ce get-reservation-purchase-recommendation --service "Amazon Elastic Compute Cloud - Compute" \
  --lookback-period-in-days SIXTY_DAYS --term-in-years ONE_YEAR --payment-option NO_UPFRONT

# Get RDS RI purchase recommendations
aws ce get-reservation-purchase-recommendation --service "Amazon Relational Database Service" \
  --lookback-period-in-days SIXTY_DAYS --term-in-years ONE_YEAR --payment-option NO_UPFRONT

# Get Savings Plans recommendations
aws ce get-savings-plans-purchase-recommendation \
  --savings-plans-type COMPUTE_SP --lookback-period-in-days SIXTY_DAYS \
  --term-in-years ONE_YEAR --payment-option NO_UPFRONT
```

**Step 2: Review Recommendations**

Evaluate each recommendation:
```
✅ Good candidate if:
  - Running 24/7 for 60+ days
  - Workload is stable and predictable
  - No plans to change architecture
  - Savings > 30%

❌ Poor candidate if:
  - Workload is variable or experimental
  - Architecture changes planned
  - Instance type may change
  - Dev/test environment
```

**Step 3: Choose Commitment Type**

**Reserved Instances**:
- Standard RI: Highest discount (63%), no flexibility
- Convertible RI: Moderate discount (54%), can change instance type
- Best for: Specific instance types, stable workloads

**Savings Plans**:
- Compute SP: Flexible across instance types, regions (66% savings)
- EC2 Instance SP: Flexible across sizes in same family (72% savings)
- Best for: Variable workloads within constraints

**Decision Matrix**:
```
Known instance type, won't change → Standard RI
May need to change types → Convertible RI or Compute SP
Variable workloads → Compute Savings Plan
Maximum flexibility → Compute Savings Plan
```

**Step 4: Purchase and Track**
- Purchase through AWS Console or CLI
- Tag commitments with purchase date and owner
- Monitor utilization monthly
- Aim for >90% utilization

**Reference**: See `references/best_practices.md` for detailed commitment strategies

---

### Workflow 3: Instance Generation Migration

**When**: During architecture reviews or optimization sprints

**Step 1: Detect Old Instances**
```bash
# Find old-generation instances (t2, m4, c4, r4, etc.)
aws ec2 describe-instances --filters Name=instance-state-name,Values=running \
  --query 'Reservations[].Instances[?starts_with(InstanceType, `t2.`) || starts_with(InstanceType, `m4.`) || starts_with(InstanceType, `c4.`) || starts_with(InstanceType, `r4.`)].{ID:InstanceId,Type:InstanceType,Name:Tags[?Key==`Name`]|[0].Value}' \
  --output table

# Find all running instance types to review generations
aws ec2 describe-instances --filters Name=instance-state-name,Values=running \
  --query 'Reservations[].Instances[].{ID:InstanceId,Type:InstanceType,Name:Tags[?Key==`Name`]|[0].Value}' \
  --output table
# Look for: t2→t3, m4→m6i, c4→c6i, r4→r6i, Intel→Graviton (20% savings)
```

**Step 2: Prioritize Migrations**

**Quick Wins (Low Risk)**:
```
t2 → t3: Drop-in replacement, 10% savings
m4 → m5: Better performance, 5% savings
gp2 → gp3: No downtime, 20% savings
```

**Medium Effort (Test Required)**:
```
x86 → Graviton (ARM64): 20% savings
- Requires ARM64 compatibility testing
- Most modern frameworks support ARM64
- Test in staging first
```

**Step 3: Execute Migration**

**For EC2 (x86 to x86)**:
1. Stop instance
2. Change instance type
3. Start instance
4. Verify application

**For Graviton Migration**:
1. Create ARM64 AMI or Docker image
2. Launch new Graviton instance
3. Test thoroughly
4. Cut over traffic
5. Terminate old instance

**Step 4: Validate Savings**
- Monitor new costs in Cost Explorer
- Verify performance is acceptable
- Document migration for other teams

**Reference**: See `references/best_practices.md` → Compute Optimization

---

### Workflow 4: Spot Instance Evaluation

**When**: For fault-tolerant workloads or Auto Scaling Groups

**Step 1: Identify Candidates**
```bash
# Check current Spot pricing vs On-Demand for target instance types
aws ec2 describe-spot-price-history --instance-types m5.large m5.xlarge m6i.large \
  --product-descriptions "Linux/UNIX" --start-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --query 'SpotPriceHistory[].{Type:InstanceType,AZ:AvailabilityZone,Price:SpotPrice}' --output table

# List Auto Scaling Groups (good Spot candidates)
aws autoscaling describe-auto-scaling-groups \
  --query 'AutoScalingGroups[].{Name:AutoScalingGroupName,Min:MinSize,Max:MaxSize,Desired:DesiredCapacity}' --output table

# Check which ASGs already use mixed instances (Spot)
aws autoscaling describe-auto-scaling-groups \
  --query 'AutoScalingGroups[?MixedInstancesPolicy!=null].AutoScalingGroupName'
```

**Spot candidates**: instances in ASGs, dev/test/staging environments, batch processing, CI/CD servers.

**Step 2: Assess Suitability**

**Excellent for Spot**:
- Stateless applications
- Batch jobs
- CI/CD pipelines
- Data processing
- Auto Scaling Groups

**NOT suitable for Spot**:
- Databases (without replicas)
- Stateful applications
- Real-time services
- Mission-critical workloads

**Step 3: Implementation Strategy**

**Option 1: Fargate Spot** -- Set `capacityProviderStrategy` with `FARGATE_SPOT` weight 70, `FARGATE` weight 30.

**Option 2: EC2 Auto Scaling with Spot** -- Use `MixedInstancesPolicy` with `OnDemandBaseCapacity: 2`, `OnDemandPercentageAboveBaseCapacity: 30`, `SpotAllocationStrategy: capacity-optimized`, and multiple instance type overrides (m5.large, m5a.large, m5n.large).

**Option 3: EC2 Spot Fleet** -- `aws ec2 request-spot-fleet --spot-fleet-request-config file://spot-fleet.json`

**Step 4: Implement Interruption Handling** -- Poll instance metadata at `/latest/meta-data/spot/instance-action` for the 2-minute termination notice. On notice: gracefully shutdown, save state, drain connections, exit.

**Reference**: See `references/best_practices.md` → Compute Optimization → Spot Instances

---

## Quick Reference

Use AWS CLI commands directly -- Claude Code can run `aws ce`, `aws ec2`, `aws cloudwatch`, and `aws compute-optimizer` commands to perform cost analysis.

**Monthly review commands**:
- `aws ec2 describe-volumes --filters Name=status,Values=available` (unused volumes)
- `aws ce get-cost-and-usage --granularity DAILY --metrics BlendedCost` (cost trends)
- `aws compute-optimizer get-ec2-instance-recommendations` (rightsizing)

**Quarterly optimization commands**:
- `aws ce get-reservation-purchase-recommendation --service EC2` (RI analysis)
- `aws ec2 describe-instances` with instance type filters (old generations)
- `aws ec2 describe-spot-price-history` (Spot pricing)

Add `--region REGION` and `--profile PROFILE` to any AWS CLI command as needed.

---

## Service-Specific Optimization

### Compute Optimization
**Key Actions**:
- Migrate to Graviton (20% savings)
- Use Spot for fault-tolerant workloads (70% savings)
- Purchase RIs for stable workloads (40-65% savings)
- Right-size oversized instances

**Reference**: `references/best_practices.md` → Compute Optimization

### Storage Optimization
**Key Actions**:
- Convert gp2 → gp3 (20% savings)
- Implement S3 lifecycle policies (50-95% savings)
- Delete old snapshots
- Use S3 Intelligent-Tiering

**Reference**: `references/best_practices.md` → Storage Optimization

### Network Optimization
**Key Actions**:
- Replace NAT Gateways with VPC Endpoints (save $25-30/month each)
- Use CloudFront to reduce data transfer costs
- Colocate resources in same AZ when possible

**Reference**: `references/best_practices.md` → Network Optimization

### Database Optimization
**Key Actions**:
- Right-size RDS instances
- Use gp3 storage (20% cheaper than gp2)
- Evaluate Aurora Serverless for variable workloads
- Purchase RDS Reserved Instances

**Reference**: `references/best_practices.md` → Database Optimization

---

## Service Alternatives Decision Guide

Need help choosing between services?

**Question**: "Should I use EC2, Lambda, or Fargate?"
**Answer**: See `references/service_alternatives.md` → Compute Alternatives

**Question**: "Which S3 storage class should I use?"
**Answer**: See `references/service_alternatives.md` → Storage Alternatives

**Question**: "Should I use RDS or Aurora?"
**Answer**: See `references/service_alternatives.md` → Database Alternatives

**Question**: "NAT Gateway vs VPC Endpoint vs NAT Instance?"
**Answer**: See `references/service_alternatives.md` → Networking Alternatives

---

## FinOps Governance & Process

Three-phase rollout: (1) Foundation -- Enable Cost Explorer, set up Budgets, define tagging strategy. (2) Visibility -- Enforce tags, run AWS CLI cost analysis commands, set up monthly reviews. (3) Culture -- Cost metrics in engineering KPIs, architecture reviews, optimization sprints.

Full guide: `references/finops_governance.md`

### Monthly Review Process

**Week 1**: Data Collection
- Run AWS CLI cost analysis commands (see Workflow 1)
- Export Cost & Usage Reports
- Compile findings

**Week 2**: Analysis
- Identify trends
- Find opportunities
- Prioritize actions

**Week 3**: Team Reviews
- Present to engineering teams
- Discuss optimizations
- Assign action items

**Week 4**: Executive Reporting
- Create executive summary
- Forecast next quarter
- Report optimization wins

**Template**: See `assets/templates/monthly_cost_report.md`

**Detailed Process**: See `references/finops_governance.md` → Monthly Review Process

---

## Cost Optimization Checklist

### Quick Wins (Do First)
- [ ] Delete unattached EBS volumes
- [ ] Delete old EBS snapshots (>90 days)
- [ ] Release unused Elastic IPs
- [ ] Convert gp2 → gp3 volumes
- [ ] Stop/terminate idle EC2 instances
- [ ] Enable S3 Intelligent-Tiering
- [ ] Set up AWS Budgets and alerts

### Medium Effort (This Quarter)
- [ ] Right-size oversized instances
- [ ] Migrate to newer instance generations
- [ ] Purchase Reserved Instances for stable workloads
- [ ] Implement S3 lifecycle policies
- [ ] Replace NAT Gateways with VPC Endpoints (where applicable)
- [ ] Enable automated resource scheduling (dev/test)
- [ ] Implement tagging strategy and enforcement

### Strategic Initiatives (Ongoing)
- [ ] Migrate to Graviton instances
- [ ] Implement Spot for fault-tolerant workloads
- [ ] Establish monthly cost review process
- [ ] Set up cost allocation by team
- [ ] Implement chargeback/showback model
- [ ] Create FinOps culture and practices

---

## Troubleshooting Cost Issues

### "My bill suddenly increased"

1. Check daily cost breakdown by service:
   ```bash
   aws ce get-cost-and-usage \
     --time-period Start=$(date -u -v-30d +%Y-%m-%d),End=$(date -u +%Y-%m-%d) \
     --granularity DAILY --metrics BlendedCost \
     --group-by Type=DIMENSION,Key=SERVICE
   ```

2. Check Cost Explorer in the AWS Console for visual breakdown
3. Review CloudTrail for resource creation events
4. Check for AutoScaling events
5. Verify no Reserved Instances expired

### "I need to reduce costs by X%"

Follow the optimization workflow:
1. Run the discovery commands from Workflow 1 above (unused resources, cost anomalies, rightsizing)
2. Calculate total potential savings
3. Prioritize by: Savings Amount x (1 / Effort)
4. Focus on quick wins first
5. Implement strategic changes for long-term

### "How do I know if Reserved Instances make sense?"

Run RI analysis:
```bash
aws ce get-reservation-purchase-recommendation \
  --service "Amazon Elastic Compute Cloud - Compute" \
  --lookback-period-in-days SIXTY_DAYS --term-in-years ONE_YEAR --payment-option NO_UPFRONT
```

Look for:
- Instances running 60+ days consistently
- Workloads that won't change
- Savings > 30%

### "Which resources can I safely delete?"

Find unused resources:
```bash
aws ec2 describe-volumes --filters Name=status,Values=available --output table
aws ec2 describe-addresses --query 'Addresses[?AssociationId==null]' --output table
aws ec2 describe-snapshots --owner-ids self \
  --query 'Snapshots[?StartTime<=`2025-01-01`]' --output table
```

Safe to delete (usually):
- Unattached EBS volumes (after verifying)
- Snapshots > 90 days (if backups exist elsewhere)
- Unused Elastic IPs (after verifying not in DNS)
- Stopped EC2 instances > 30 days (after confirming abandoned)

Always verify with resource owner before deletion!

---

## Additional Resources

**References**: `references/best_practices.md` | `references/service_alternatives.md` | `references/finops_governance.md`

**Templates**: `assets/templates/monthly_cost_report.md`

**CLI Tools**: Use AWS CLI commands directly -- Claude Code can run `aws ce`, `aws ec2`, `aws cloudwatch`, and `aws compute-optimizer` commands to perform cost analysis. No additional dependencies required.
