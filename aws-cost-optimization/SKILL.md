---
name: aws-cost-finops
description: AWS cost optimization and FinOps workflows. Use for finding unused resources, analyzing Reserved Instance opportunities, detecting cost anomalies, rightsizing instances, evaluating Spot instances, migrating to newer generation instances, implementing FinOps best practices, optimizing storage/network/database costs, and managing cloud financial operations. Includes automated analysis scripts and comprehensive reference documentation.
---

# AWS Cost Optimization & FinOps

Systematic workflows for AWS cost optimization and financial operations management.

## Cost Optimization Workflow

1. **Discover** — `find_unused_resources.py`, `cost_anomaly_detector.py`
2. **Analyze** — `rightsizing_analyzer.py`, `detect_old_generations.py`, `spot_recommendations.py`, `analyze_ri_recommendations.py`
3. **Prioritize** — Quick wins (low risk, high savings) → low-hanging fruit → strategic improvements
4. **Implement** — Delete unused resources, rightsize, purchase commitments, migrate generations
5. **Monitor** — Monthly cost reviews, tag compliance, budget variance tracking

---

## Core Workflows

### Workflow 1: Monthly Cost Optimization Review

**Frequency**: Run monthly (first week of each month)

**Step 1: Find Unused Resources**
```bash
# Scan for waste across all resources
python3 scripts/find_unused_resources.py

# Expected output:
# - Unattached EBS volumes
# - Old snapshots
# - Unused Elastic IPs
# - Idle NAT Gateways
# - Idle EC2 instances
# - Unused load balancers
# - Estimated monthly savings
```

**Step 2: Analyze Cost Anomalies**
```bash
# Detect unusual spending patterns
python3 scripts/cost_anomaly_detector.py --days 30

# Expected output:
# - Cost spikes and anomalies
# - Top cost drivers
# - Period-over-period comparison
# - 30-day forecast
```

**Step 3: Identify Rightsizing Opportunities**
```bash
# Find oversized instances
python3 scripts/rightsizing_analyzer.py --days 30

# Expected output:
# - EC2 instances with low utilization
# - RDS instances with low utilization
# - Recommended smaller instance types
# - Estimated savings
```

**Step 4: Generate Monthly Report**
```bash
# Use the template to compile findings
cp assets/templates/monthly_cost_report.md reports/$(date +%Y-%m)-cost-report.md

# Fill in:
# - Findings from scripts
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
# Identify workloads suitable for commitments
python3 scripts/analyze_ri_recommendations.py --days 60

# Looks for:
# - EC2 instances running consistently for 60+ days
# - RDS instances with stable usage
# - Calculates ROI for 1yr vs 3yr commitments
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
# Find outdated instance generations
python3 scripts/detect_old_generations.py

# Identifies:
# - t2 → t3 migrations (10% savings)
# - m4 → m5 → m6i migrations
# - Intel → Graviton opportunities (20% savings)
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
python3 scripts/spot_recommendations.py
```

**Step 2: Implementation Strategy**

**Option 1: Fargate Spot (Easiest)**
```yaml
# ECS task definition
requiresCompatibilities:
  - FARGATE
capacityProviderStrategy:
  - capacityProvider: FARGATE_SPOT
    weight: 70  # 70% Spot
  - capacityProvider: FARGATE
    weight: 30  # 30% On-Demand
```

**Option 2: EC2 Auto Scaling with Spot**
```yaml
# Mixed instances policy
MixedInstancesPolicy:
  InstancesDistribution:
    OnDemandBaseCapacity: 2
    OnDemandPercentageAboveBaseCapacity: 30
    SpotAllocationStrategy: capacity-optimized
  LaunchTemplate:
    Overrides:
      - InstanceType: m5.large
      - InstanceType: m5a.large
      - InstanceType: m5n.large
```

**Option 3: EC2 Spot Fleet**
```bash
# Create Spot Fleet with diverse instance types
aws ec2 request-spot-fleet --spot-fleet-request-config file://spot-fleet.json
```

**Step 4: Implement Interruption Handling**
```bash
# Handle 2-minute termination notice
# Instance metadata: /latest/meta-data/spot/instance-action

# In application:
1. Poll for termination notice
2. Gracefully shutdown (save state)
3. Drain connections
4. Exit
```

**Reference**: See `references/best_practices.md` → Compute Optimization → Spot Instances

---

---

## Service-Specific Optimization

| Category | Key Actions | Savings |
|----------|------------|---------|
| **Compute** | Graviton migration, Spot for fault-tolerant workloads, RIs for stable workloads, rightsizing | 20-70% |
| **Storage** | gp2→gp3, S3 lifecycle policies, delete old snapshots, Intelligent-Tiering | 20-95% |
| **Network** | VPC Endpoints instead of NAT Gateways, CloudFront, AZ colocation | $25-30/mo per NAT GW |
| **Database** | Rightsize RDS, gp3 storage, Aurora Serverless for variable loads, RDS RIs | 20-40% |

**→ Details**: `references/best_practices.md` · **Service selection**: `references/service_alternatives.md`

---

## FinOps Governance & Process

Three-phase rollout: Foundation (Cost Explorer, Budgets, tagging) → Visibility (enforcement, scripts, reviews) → Culture (KPIs, architecture reviews, optimization sprints).

**→ Full guide**: `references/finops_governance.md`

### Monthly Review Process

**Week 1**: Data Collection
- Run all optimization scripts
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

1. Run cost anomaly detection:
   ```bash
   python3 scripts/cost_anomaly_detector.py --days 30
   ```

2. Check Cost Explorer for service breakdown
3. Review CloudTrail for resource creation events
4. Check for AutoScaling events
5. Verify no Reserved Instances expired

### "I need to reduce costs by X%"

Follow the optimization workflow:
1. Run all discovery scripts
2. Calculate total potential savings
3. Prioritize by: Savings Amount × (1 / Effort)
4. Focus on quick wins first
5. Implement strategic changes for long-term

### "How do I know if Reserved Instances make sense?"

Run RI analysis:
```bash
python3 scripts/analyze_ri_recommendations.py --days 60
```

Look for:
- Instances running 60+ days consistently
- Workloads that won't change
- Savings > 30%

### "Which resources can I safely delete?"

Run unused resource finder:
```bash
python3 scripts/find_unused_resources.py
```

Safe to delete (usually):
- Unattached EBS volumes (after verifying)
- Snapshots > 90 days (if backups exist elsewhere)
- Unused Elastic IPs (after verifying not in DNS)
- Stopped EC2 instances > 30 days (after confirming abandoned)

Always verify with resource owner before deletion!

---

## Additional Resources

**References**: `references/best_practices.md` · `references/service_alternatives.md` · `references/finops_governance.md`

**Templates**: `assets/templates/monthly_cost_report.md`

**Scripts**: All scripts in `scripts/` support `--help`, `--region`, and `--profile` flags. Install deps: `pip install boto3 tabulate`
