# AWS Cost Optimization Report - [Month Year]

**Report Date**: [Date]
**Reporting Period**: [Start Date] - [End Date]
**Prepared By**: [Your Name/Team]

---

## Executive Summary

| Metric | Value | vs Budget | vs Last Month |
|--------|-------|-----------|---------------|
| **Total AWS Spend** | $XX,XXX | ±X% | ±X% |
| **Largest Service** | Service Name ($X,XXX) | - | - |
| **Optimization Savings** | $X,XXX | - | - |
| **Projected Next Month** | $XX,XXX | - | - |

### Key Highlights
- ✅ [Positive highlight, e.g., "Reduced compute costs by 15%"]
- ⚠️  [Area of concern, e.g., "Storage costs increased 25% due to new backups"]
- 🎯 [Action taken, e.g., "Purchased Reserved Instances for $X,XXX annual savings"]

---

## Cost Breakdown by Service

| Service | Current Month | Last Month | Change | % of Total |
|---------|--------------|------------|--------|-----------|
| EC2 | $XX,XXX | $XX,XXX | +/-X% | XX% |
| RDS | $XX,XXX | $XX,XXX | +/-X% | XX% |
| S3 | $XX,XXX | $XX,XXX | +/-X% | XX% |
| Data Transfer | $XX,XXX | $XX,XXX | +/-X% | XX% |
| Lambda | $XX,XXX | $XX,XXX | +/-X% | XX% |
| Other | $XX,XXX | $XX,XXX | +/-X% | XX% |
| **Total** | **$XX,XXX** | **$XX,XXX** | **+/-X%** | **100%** |

---

## Cost by Environment

| Environment | Cost | % of Total | Budget | Variance |
|-------------|------|-----------|--------|----------|
| Production | $XX,XXX | XX% | $XX,XXX | +/-X% |
| Staging | $XX,XXX | XX% | $XX,XXX | +/-X% |
| Development | $XX,XXX | XX% | $XX,XXX | +/-X% |
| Test | $XX,XXX | XX% | $XX,XXX | +/-X% |
| **Total** | **$XX,XXX** | **100%** | **$XX,XXX** | **+/-X%** |

---

## Cost by Team/Project

| Team/Project | Cost | % of Total | vs Last Month |
|--------------|------|-----------|---------------|
| Team Alpha | $XX,XXX | XX% | +/-X% |
| Team Beta | $XX,XXX | XX% | +/-X% |
| Team Gamma | $XX,XXX | XX% | +/-X% |
| Platform/Shared | $XX,XXX | XX% | +/-X% |
| Untagged | $XX,XXX | XX% | +/-X% |
| **Total** | **$XX,XXX** | **100%** | **+/-X%** |

---

## Cost Anomalies Detected

### Significant Cost Increases

| Date | Service | Cost | Baseline | Increase | Root Cause | Action Taken |
|------|---------|------|----------|----------|------------|--------------|
| [Date] | [Service] | $XXX | $XXX | +XX% | [Explanation] | [Action] |

### Unusual Spending Patterns

- **[Service/Resource]**: [Description of anomaly and investigation findings]

---

## Optimization Activities This Month

### Actions Completed

1. **[Optimization Action 1]**
   - **Description**: [What was done]
   - **Monthly Savings**: $XXX
   - **Annual Savings**: $XXX
   - **Effort**: [Hours/Days]

2. **[Optimization Action 2]**
   - **Description**: [What was done]
   - **Monthly Savings**: $XXX
   - **Annual Savings**: $XXX
   - **Effort**: [Hours/Days]

3. **[Optimization Action 3]**
   - **Description**: [What was done]
   - **Monthly Savings**: $XXX
   - **Annual Savings**: $XXX
   - **Effort**: [Hours/Days]

### Total Savings Achieved
- **Monthly**: $XXX
- **Annual**: $XXX

---

## Optimization Opportunities Identified

### High Priority (Recommended This Month)

1. **[Opportunity 1]**
   - **Issue**: [Description of waste/inefficiency]
   - **Recommendation**: [What to do]
   - **Estimated Monthly Savings**: $XXX
   - **Effort**: [Low/Medium/High]
   - **Risk**: [Low/Medium/High]
   - **Owner**: [Team/Person]
   - **Deadline**: [Date]

2. **[Opportunity 2]**
   - **Issue**: [Description]
   - **Recommendation**: [Action]
   - **Estimated Monthly Savings**: $XXX
   - **Effort**: [Low/Medium/High]
   - **Risk**: [Low/Medium/High]
   - **Owner**: [Team/Person]
   - **Deadline**: [Date]

### Medium Priority (Next Quarter)

1. **[Opportunity 3]**
   - **Details**: [Brief description]
   - **Estimated Monthly Savings**: $XXX

2. **[Opportunity 4]**
   - **Details**: [Brief description]
   - **Estimated Monthly Savings**: $XXX

---

## Resource Inventory

### Unused Resources Found

| Resource Type | Count | Total Monthly Cost | Action |
|---------------|-------|-------------------|--------|
| Unattached EBS Volumes | XX | $XXX | Delete after review |
| Old Snapshots (>90 days) | XX | $XXX | Delete after review |
| Unused Elastic IPs | XX | $XXX | Release |
| Idle NAT Gateways | XX | $XXX | Review and consolidate |
| Idle Load Balancers | XX | $XXX | Delete |
| Stopped EC2 (>30 days) | XX | $XXX | Terminate |

**Total Potential Savings**: $XXX/month

### Rightsizing Recommendations

| Instance ID | Current Type | Recommended Type | Monthly Savings | Utilization |
|-------------|--------------|------------------|-----------------|-------------|
| i-xxxxx | m5.2xlarge | m5.xlarge | $XXX | Avg CPU: XX% |
| i-xxxxx | c5.4xlarge | c5.2xlarge | $XXX | Avg CPU: XX% |
| i-xxxxx | r5.8xlarge | r5.4xlarge | $XXX | Avg CPU: XX% |

**Total Potential Savings**: $XXX/month

### Reserved Instance/Savings Plan Opportunities

| Service | Instance Type | Quantity | Commitment | Monthly Savings | Annual Savings |
|---------|--------------|----------|------------|-----------------|----------------|
| EC2 | m5.xlarge | 10 | 1yr Standard RI | $XXX | $XXX |
| RDS | db.r5.large | 5 | 3yr Standard RI | $XXX | $XXX |

**Total Potential Annual Savings**: $XXX

---

## Commitment Utilization

### Reserved Instances

| Instance Type | Purchased | Utilized | Utilization % | Status |
|---------------|-----------|----------|---------------|--------|
| m5.xlarge | 20 | 19.2 | 96% | ✅ Good |
| c5.2xlarge | 10 | 7.5 | 75% | ⚠️  Review |
| r5.large | 5 | 5.0 | 100% | ✅ Good |

### Savings Plans

| Commitment Type | Commitment | Used | Utilization % | Status |
|----------------|------------|------|---------------|--------|
| Compute SP | $5,000/month | $4,950 | 99% | ✅ Good |
| EC2 Instance SP | $2,000/month | $1,800 | 90% | ✅ Good |

---

## Tag Compliance

| Tag | Compliance Rate | Resources Missing Tags | Trend |
|-----|----------------|------------------------|-------|
| Environment | 95% | 120 | ↗️ Improving |
| Owner | 88% | 280 | → Stable |
| Project | 92% | 180 | ↗️ Improving |
| CostCenter | 85% | 350 | ↘️ Declining |

**Action Required**: [Teams/resources that need to improve tagging]

---

## Forecast & Projections

### Next Month Forecast

- **AWS Cost Explorer Forecast**: $XX,XXX
- **Confidence Level**: [High/Medium/Low]
- **Known Variables**:
  - ✅ [Factor that will decrease costs]
  - ⚠️  [Factor that will increase costs]

### Quarterly Projection

| Quarter | Projected Cost | vs Previous Quarter | Notes |
|---------|---------------|---------------------|-------|
| Q[X] [Year] | $XXX,XXX | +/-X% | [Notes] |

---

## Upcoming Changes & Impact

### New Projects/Initiatives

1. **[Project Name]**
   - **Launch Date**: [Date]
   - **Expected Monthly Cost**: $XXX
   - **Budget Allocated**: $XXX

2. **[Project Name]**
   - **Launch Date**: [Date]
   - **Expected Monthly Cost**: $XXX
   - **Budget Allocated**: $XXX

### Planned Optimizations

1. **[Planned Activity]**
   - **Scheduled**: [Date]
   - **Expected Savings**: $XXX/month

---

## Action Items from Last Month

| Item | Owner | Status | Notes |
|------|-------|--------|-------|
| [Action item 1] | [Name] | ✅ Complete | [Notes] |
| [Action item 2] | [Name] | 🔄 In Progress | [Notes] |
| [Action item 3] | [Name] | ❌ Blocked | [Notes] |

---

## Action Items for Next Month

| Priority | Item | Owner | Deadline | Expected Savings |
|----------|------|-------|----------|------------------|
| 🔴 High | [Action 1] | [Name] | [Date] | $XXX/month |
| 🔴 High | [Action 2] | [Name] | [Date] | $XXX/month |
| 🟡 Medium | [Action 3] | [Name] | [Date] | $XXX/month |
| 🟡 Medium | [Action 4] | [Name] | [Date] | $XXX/month |
| 🟢 Low | [Action 5] | [Name] | [Date] | $XXX/month |

---

## Appendix

### Methodology

- **Data Source**: AWS Cost Explorer, Cost & Usage Reports
- **Scripts Used**:
  - `find_unused_resources.py`
  - `analyze_ri_recommendations.py`
  - `rightsizing_analyzer.py`
  - `cost_anomaly_detector.py`
- **Analysis Period**: [Days] days of data
- **Cost Estimation**: Based on [region] pricing, [assumptions]

### Definitions

- **Untagged Resources**: Resources missing one or more required tags
- **Idle Resources**: Resources with <5% avg utilization over analysis period
- **Optimization Savings**: Actual realized savings from completed optimizations
- **Potential Savings**: Estimated savings from recommended actions

### Contact

For questions about this report, contact:
- **FinOps Team**: [email]
- **Report Author**: [name, email]

---

**Next Review Date**: [Date]
