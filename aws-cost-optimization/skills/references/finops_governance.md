# FinOps Governance Framework

Organizational practices, processes, and governance for AWS cost optimization.

## Table of Contents

1. [FinOps Principles](#finops-principles)
2. [Cost Allocation & Tagging](#cost-allocation--tagging)
3. [Budget Management](#budget-management)
4. [Monthly Review Process](#monthly-review-process)
5. [Roles & Responsibilities](#roles--responsibilities)
6. [Chargeback & Showback](#chargeback--showback)
7. [Policy & Governance](#policy--governance)
8. [Metrics & KPIs](#metrics--kpis)

---

## FinOps Principles

### The FinOps Framework

FinOps is the practice of bringing financial accountability to cloud spending through collaboration between engineering, finance, and business teams.

**Core Principles:**

1. **Teams Need to Collaborate**
   - Engineering makes technical decisions
   - Finance provides visibility and reporting
   - Business sets priorities and budgets
   - Cross-functional cost optimization

2. **Everyone Takes Ownership**
   - Engineers see cost impact of their decisions
   - Teams have cost budgets and accountability
   - Cost is a efficiency metric, not just finance

3. **Decisions Driven by Business Value**
   - Speed, quality, and cost trade-offs
   - Investment vs optimization decisions
   - ROI-based prioritization

4. **Take Advantage of Variable Cost Model**
   - Scale resources up and down as needed
   - Use different pricing models strategically
   - Optimize for actual usage patterns

5. **Centralized Team Drives FinOps**
   - Central FinOps team enables
   - Distributed execution by product teams
   - Share best practices and tools

### FinOps Maturity Model

**Crawl Phase (Getting Started)**
- Basic cost visibility
- Manual reporting
- Ad-hoc optimization
- Initial tagging strategy
- Basic budget alerts

**Walk Phase (Improving)**
- Automated cost reporting
- Regular optimization reviews
- Systematic tagging enforcement
- Team cost allocation
- Reserved Instance planning
- Monthly optimization meetings

**Run Phase (Optimized)**
- Real-time cost visibility
- Automated optimization
- Cost-aware engineering culture
- Predictive forecasting
- Automated guardrails
- FinOps integrated in SDLC

---

## Cost Allocation & Tagging

### Tagging Strategy

**Required Tags (Enforce via Policy)**

```yaml
Required Tags:
  Environment:
    values: [prod, staging, dev, test]
    purpose: Separate production from non-production costs

  Owner:
    values: [email or team name]
    purpose: Contact for resource questions

  Project:
    values: [project code]
    purpose: Track project spending

  CostCenter:
    values: [department code]
    purpose: Chargeback allocation

  Application:
    values: [app name]
    purpose: Application-level cost tracking
```

**Optional but Recommended Tags**

```yaml
Optional Tags:
  ExpirationDate:
    format: YYYY-MM-DD
    purpose: Auto-cleanup scheduling

  DataClassification:
    values: [public, internal, confidential, restricted]
    purpose: Security and compliance

  BackupRequired:
    values: [true, false]
    purpose: Backup policy enforcement

  Criticality:
    values: [critical, high, medium, low]
    purpose: Priority and SLA determination
```

### Tag Enforcement

**Using AWS Organizations Service Control Policies (SCP)**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyEC2CreationWithoutTags",
      "Effect": "Deny",
      "Action": [
        "ec2:RunInstances"
      ],
      "Resource": [
        "arn:aws:ec2:*:*:instance/*"
      ],
      "Condition": {
        "StringNotLike": {
          "aws:RequestTag/Environment": ["prod", "staging", "dev", "test"],
          "aws:RequestTag/Owner": "*",
          "aws:RequestTag/Project": "*"
        }
      }
    }
  ]
}
```

**Using AWS Config Rules**

- **required-tags**: Enforce tags on all resources
- **ec2-instance-no-public-ip**: Prevent public IPs unless tagged
- Custom Lambda-based rules for complex logic

**Tag Compliance Monitoring**

```python
# Example: Check tag compliance
# Run weekly to find untagged resources

aws resourcegroupstaggingapi get-resources \
  --query 'ResourceTagMappingList[?length(Tags) == `0`]' \
  --output table

# Or use Tag Editor in AWS Console
```

### Cost Allocation Tags

**Activating Cost Allocation Tags**

1. Go to AWS Billing → Cost Allocation Tags
2. Select user-defined tags to activate
3. Wait 24 hours for tags to appear in Cost Explorer
4. Tags only apply to charges after activation

**Best Practices**

- Activate tags before using them
- Use consistent naming (e.g., `Environment` not `Env` or `environment`)
- Document tag values in wiki/runbook
- Review and update tag strategy quarterly

---

## Budget Management

### AWS Budgets Setup

**Budget Types**

1. **Cost Budget**: Track spending against threshold
2. **Usage Budget**: Track service usage (e.g., EC2 hours)
3. **Savings Plans Budget**: Track commitment utilization
4. **Reservation Budget**: Track RI utilization

**Recommended Budgets**

**1. Overall Monthly Budget**
```yaml
Budget Name: Company-Wide-Monthly-Budget
Amount: $50,000/month
Alerts:
  - 50% actual: Email CFO, FinOps team
  - 80% actual: Email CFO, CTO, FinOps team
  - 100% forecasted: Email CFO, CTO, all team leads
  - 100% actual: Email everyone + Slack alert
```

**2. Per-Environment Budgets**
```yaml
Budget Name: Production-Environment-Budget
Amount: $30,000/month
Filter: Environment=prod
Alerts:
  - 80% actual: Email engineering leads
  - 100% forecasted: Email CTO + FinOps

Budget Name: Dev-Environment-Budget
Amount: $5,000/month
Filter: Environment=dev
Alerts:
  - 100% actual: Email dev team leads
  - 120% actual: Automated shutdown (if possible)
```

**3. Per-Team Budgets**
```yaml
Budget Name: Team-Platform-Budget
Amount: $15,000/month
Filter: Owner=platform-team
Alerts:
  - 90% actual: Email platform team
  - 100% forecasted: Email platform team + manager
```

**4. Per-Project Budgets**
```yaml
Budget Name: Project-Phoenix-Budget
Amount: $8,000/month
Filter: Project=phoenix
Alerts:
  - 75% actual: Email project owner
  - 100% actual: Email project owner + sponsor
```

### Budget Alert Actions

**Automated Responses to Budget Alerts**

```python
# Lambda function triggered by Budget alert SNS topic

def lambda_handler(event, context):
    # Parse budget alert
    budget_name = event['budgetName']
    threshold = event['threshold']

    if threshold >= 100:
        # Stop non-production instances
        stop_dev_instances()

        # Send Slack alert
        send_slack_alert(f"🚨 Budget {budget_name} exceeded!")

        # Create JIRA ticket
        create_cost_investigation_ticket()

    elif threshold >= 80:
        # Send warning
        send_slack_alert(f"⚠️  Budget {budget_name} at 80%")
```

---

## Monthly Review Process

### FinOps Monthly Cadence

**Week 1: Data Collection**
- Export Cost & Usage Reports
- Run cost optimization scripts
- Gather CloudWatch metrics
- Compile anomaly reports

**Week 2: Analysis**
- Identify cost trends
- Find optimization opportunities
- Compare to previous months
- Analyze tag compliance

**Week 3: Team Review Meetings**
- Present findings to engineering teams
- Discuss optimization opportunities
- Assign action items
- Review upcoming projects

**Week 4: Executive Reporting**
- Create executive summary
- Present cost trends to leadership
- Report on optimization wins
- Forecast next quarter

### Monthly Review Meeting Agenda

**Attendees**: Engineering Leads, FinOps Team, Finance Rep, Product Manager

**Agenda (1 hour)**

1. **Previous Month Recap (10 min)**
   - Total spend vs budget
   - Top 5 services by cost
   - Month-over-month comparison
   - Budget variance explanation

2. **Cost Anomalies (10 min)**
   - Unusual spending spikes
   - Root cause analysis
   - Prevention measures

3. **Optimization Opportunities (15 min)**
   - Unused resources found
   - Rightsizing recommendations
   - Reserved Instance opportunities
   - Estimated savings

4. **Team Cost Breakdown (10 min)**
   - Per-team spending
   - Top spenders
   - Tag compliance status

5. **Upcoming Changes (10 min)**
   - New projects launching
   - Expected cost impact
   - Budget adjustments needed

6. **Action Items Review (5 min)**
   - Follow-up on previous items
   - Assign new action items
   - Set deadlines

**Deliverable**: Monthly FinOps Report (template provided)

### Monthly Report Template

```markdown
# AWS Cost Report - [Month Year]

## Executive Summary
- Total spend: $XX,XXX
- vs Budget: X% (under/over)
- vs Last month: +/-X%
- Optimization savings: $X,XXX

## Cost Breakdown
| Service | Cost | % of Total | MoM Change |
|---------|------|-----------|-----------|
| EC2     | $XX  | XX%       | +/-X%     |
| RDS     | $XX  | XX%       | +/-X%     |

## Optimization Actions Taken
1. Migrated 20 instances to Graviton (saved $X/month)
2. Purchased Reserved Instances (saved $X/month)
3. Deleted unused resources (saved $X/month)

## Recommendations for Next Month
1. Right-size 15 oversized instances (potential $X/month savings)
2. Implement S3 lifecycle policies (potential $X/month savings)

## Action Items
- [ ] [Owner] Task description (Deadline)
```

---

## Roles & Responsibilities

### FinOps Team Structure

**FinOps Lead**
- Owns overall cloud financial management
- Reports to CFO and CTO
- Sets FinOps strategy and goals
- Manages budget process

**Cloud Cost Analyst**
- Analyzes spending trends
- Generates reports and dashboards
- Identifies optimization opportunities
- Runs monthly review process

**Cloud Architect (FinOps focus)**
- Advises on cost-optimized architectures
- Implements cost optimization tools
- Trains engineers on FinOps practices
- Reviews architectural designs for cost impact

### Engineering Team Responsibilities

**Engineering Manager**
- Owns team budget
- Reviews monthly cost reports
- Prioritizes optimization work
- Ensures tagging compliance

**Engineers**
- Tag all resources they create
- Consider cost in design decisions
- Implement optimization recommendations
- Delete unused resources

**Platform/SRE Team**
- Implements cost optimization tooling
- Automates cost monitoring
- Provides cost visibility dashboards
- Enforces tagging policies

---

## Chargeback & Showback

### Showback (Visibility Only)

**Purpose**: Show teams their costs without charging them
**Goal**: Raise cost awareness

**Implementation**:
- Monthly cost reports per team
- Dashboard showing team spending
- Highlight cost trends
- No budget enforcement

**Best for**: Organizations new to FinOps

### Chargeback (Financial Accountability)

**Purpose**: Allocate costs back to business units
**Goal**: Financial accountability

**Implementation**:
- Tag-based cost allocation
- Transfer costs between cost centers
- Teams have hard budgets
- Overspending requires justification

**Best for**: Mature FinOps organizations

### Hybrid Model (Recommended)

**Shared Costs**: Charged to central IT
- VPC resources
- Security tools
- Monitoring infrastructure
- Shared services

**Team Costs**: Charged to teams
- Compute resources (EC2, Lambda)
- Databases
- Storage
- Application-specific services

**Implementation**:
```
Total AWS Bill: $100,000

Shared Costs (30%): $30,000
  → Charged to IT/Platform budget

Team Costs (70%): $70,000
  → Allocated by tags:
    - Team A (Project=alpha): $20,000
    - Team B (Project=beta): $25,000
    - Team C (Project=gamma): $15,000
    - Untagged (alert!): $10,000 → Needs investigation
```

---

## Policy & Governance

### Cost Governance Policies

**1. Resource Creation Policies**

```yaml
Policy: All resources must be tagged
Enforcement: Service Control Policy (SCP)
Exception process: Request via FinOps team

Policy: Dev/test resources must auto-stop nights/weekends
Enforcement: AWS Instance Scheduler
Exception process: Tag with NoAutoStop=true (requires approval)

Policy: S3 buckets must have lifecycle policies
Enforcement: AWS Config rule
Exception process: Document justification in bucket tags
```

**2. Approval Workflows**

```yaml
# Spending thresholds requiring approval

< $1,000/month:
  - Auto-approved
  - Must be tagged

$1,000 - $5,000/month:
  - Engineering manager approval
  - Documented in JIRA

$5,000 - $20,000/month:
  - Director approval
  - Budget impact assessment
  - FinOps team review

> $20,000/month:
  - VP approval
  - Business case required
  - Quarterly review checkpoint
```

**3. Reserved Instance / Savings Plans Policy**

```yaml
Policy: All commitments require FinOps review

Process:
  1. Team identifies workload suitable for commitment
  2. Submit request to FinOps with:
     - Resource details
     - Usage history (30+ days)
     - Business justification
  3. FinOps analyzes and recommends
  4. Finance approves commitment
  5. FinOps purchases and tracks utilization
```

### Automation & Guardrails

**Automated Actions**

```yaml
# Non-production resource scheduling
Schedule: Instance Scheduler
  - Stop all dev/test EC2/RDS instances at 7pm weekdays
  - Stop all dev/test instances all weekend
  - Start at 7am weekdays
  - Exception tag: NoAutoStop=true

# Untagged resource alerts
Trigger: AWS Config rule violation
Action:
  - Send Slack alert to team
  - Create JIRA ticket
  - Escalate if not tagged in 48 hours

# Old snapshot cleanup
Schedule: Weekly Lambda function
Action:
  - Delete snapshots older than 90 days (unless tagged KeepForever=true)
  - Notify teams of deletions
  - Estimate savings

# Budget breach response
Trigger: Budget > 100%
Action:
  - Email alerts to stakeholders
  - Create incident ticket
  - Stop non-production resources (optional)
```

---

## Metrics & KPIs

### Key FinOps Metrics

**1. Cost Metrics**
```yaml
Total Monthly Cloud Spend:
  Target: Within budget
  Trend: Track month-over-month

Cost per Customer:
  Calculation: Total AWS Cost / Active Customers
  Target: Decreasing over time

Cost per Transaction:
  Calculation: Total AWS Cost / Transactions Processed
  Target: Optimize for efficiency

Unit Economics:
  Calculation: Revenue per Customer - Cost per Customer
  Target: Positive and growing
```

**2. Efficiency Metrics**
```yaml
Compute Utilization:
  Metric: Average CPU utilization
  Target: 40-60% (room for burst, not over-provisioned)

Storage Utilization:
  Metric: % of S3 in cost-optimized tiers
  Target: >60% in IA or Glacier tiers

Reserved Instance Coverage:
  Metric: % of On-Demand usage covered by RIs/SPs
  Target: >70% for stable workloads

RI/SP Utilization:
  Metric: % of RIs/SPs actually used
  Target: >90%
```

**3. Operational Metrics**
```yaml
Tag Compliance:
  Metric: % of resources with required tags
  Target: >95%

Budget Variance:
  Metric: Actual vs Budget %
  Target: ±5%

Optimization Savings:
  Metric: $ saved per month from optimizations
  Target: Growing

Mean Time to Optimize (MTTO):
  Metric: Days from finding opportunity to implementing
  Target: <30 days
```

**4. Organizational Metrics**
```yaml
FinOps Engagement:
  Metric: % of teams attending monthly reviews
  Target: 100%

Cost Awareness:
  Survey: Do engineers know their team's monthly cost?
  Target: >80% aware

Optimization Velocity:
  Metric: # optimization tasks completed per quarter
  Target: Growing trend
```

### Dashboard Requirements

**Executive Dashboard (Monthly)**
- Total spend vs budget
- Spend by service (top 10)
- Month-over-month trend
- Forecast for next quarter
- Optimization savings achieved

**Engineering Dashboard (Real-time)**
- Per-team costs (daily)
- Cost anomaly alerts
- Untagged resources count
- Budget utilization %
- Top cost drivers

**FinOps Dashboard (Daily)**
- Detailed service costs
- Tag compliance metrics
- RI/SP utilization
- Rightsizing opportunities
- Unused resource counts

---

## Getting Started Checklist

### Phase 1: Foundation (Month 1)
- [ ] Enable Cost Explorer
- [ ] Set up AWS Budgets
- [ ] Define tagging strategy
- [ ] Activate cost allocation tags
- [ ] Set up Cost and Usage Reports (CUR)
- [ ] Create basic cost dashboard

### Phase 2: Visibility (Months 2-3)
- [ ] Implement tagging enforcement
- [ ] Run first optimization scripts
- [ ] Set up monthly review meeting
- [ ] Create team cost reports
- [ ] Assign team cost owners
- [ ] Document FinOps processes

### Phase 3: Optimization (Months 4-6)
- [ ] Implement automated resource scheduling
- [ ] Purchase first Reserved Instances
- [ ] Set up cost anomaly detection
- [ ] Automate reporting
- [ ] Train engineering teams
- [ ] Implement showback/chargeback

### Phase 4: Culture (Ongoing)
- [ ] Cost metrics in engineering KPIs
- [ ] Cost review in architecture reviews
- [ ] Regular optimization sprints
- [ ] FinOps champions in each team
- [ ] Cost-aware development practices
- [ ] Continuous improvement

---

## Resources

**AWS Native Tools**
- AWS Cost Explorer
- AWS Budgets
- AWS Cost Anomaly Detection
- AWS Compute Optimizer
- AWS Trusted Advisor
- AWS Cost & Usage Reports

**Third-Party Tools**
- CloudHealth (VMware)
- Cloudability (Apptio)
- Kubecost (Kubernetes cost monitoring)
- Spot.io (Cost optimization platform)

**FinOps Foundation**
- https://www.finops.org
- FinOps Certified Practitioner certification
- FinOps community and best practices
