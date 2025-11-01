# DevOps Skills

Community repository of DevOps-focused skills for [Claude Code](https://claude.com/claude-code).

## Available Skills

### iac-terraform
**Infrastructure as Code with Terraform and Terragrunt**

Use for creating, validating, troubleshooting, and managing Terraform configurations, modules, and state. Includes state inspection tools, module validators, and comprehensive troubleshooting guides.

### k8s-troubleshooter
**Systematic Kubernetes troubleshooting and incident response**

Diagnose pod failures, cluster issues, performance problems, and production incidents. Features cluster health checks, pod diagnostics, and structured incident response playbooks.

### aws-cost-optimization
**AWS cost optimization and FinOps workflows**

Find unused resources, analyze Reserved Instance opportunities, detect cost anomalies, rightsize instances, evaluate Spot instances, and implement FinOps best practices.

**Features:**
- 🔍 6 automated analysis scripts (find waste, analyze RIs, detect old generations, evaluate Spot, rightsize resources, detect anomalies)
- 📊 Comprehensive reference guides (best practices, service alternatives, FinOps governance)
- 📝 Monthly cost report template
- 💰 Proven to find real cost savings on first run
- ⚡ Full integration with AWS APIs (EC2, RDS, EBS, S3, CloudWatch, Cost Explorer)

### ci-cd
**CI/CD pipeline design, optimization, security, and troubleshooting**

Create workflows, optimize build performance, implement caching, secure pipelines, and debug issues across GitHub Actions, GitLab CI, and other platforms.

### gitops-workflows
**GitOps workflows with ArgoCD and Flux CD**

Implement GitOps practices, deploy to multi-cluster environments, manage secrets securely, implement progressive delivery, and troubleshoot sync issues.

**Features:**
- 🚀 8 automated Python scripts (health checks for ArgoCD/Flux, repository validation, drift detection, secret auditing, ApplicationSet generation)
- 📚 8 comprehensive reference guides (ArgoCD vs Flux comparison, repo patterns, secrets management, multi-cluster, progressive delivery, OCI artifacts, best practices, troubleshooting)
- 📋 Production-ready templates (ArgoCD 3.x install, Flux bootstrap, ApplicationSets, SOPS+age config, Argo Rollouts canary, OCI artifacts)
- ✨ Updated for ArgoCD 3.x and Flux 2.7 (2024-2025)
- 🔐 Modern secrets management (SOPS+age, External Secrets Operator, Sealed Secrets)
- 🌐 Multi-cluster deployment patterns with ApplicationSets

### monitoring-observability
**Monitoring and observability strategy and implementation**

Design metrics systems, implement distributed tracing, create alerts and dashboards, calculate SLOs and error budgets, and choose the right monitoring tools for your needs.

**Features:**
- 📊 6 automated analysis scripts (analyze metrics, check alert quality, calculate SLOs, analyze logs, generate dashboards, validate health checks)
- 📚 Comprehensive reference guides (metrics design, alerting best practices, logging, tracing, SLO/SLA, tool comparison)
- 📋 Production-ready templates (Prometheus alerts for web apps and Kubernetes, OpenTelemetry collector config, incident runbooks)
- 🎯 Four Golden Signals, RED/USE methods, OpenTelemetry integration
- 🔍 Compare monitoring tools (Prometheus, Datadog, ELK, Loki, CloudWatch)

## Installation

Add the marketplace:
```bash
/plugin marketplace add https://github.com/ahmedasmar/devops-claude-skills
```

Install skills:
```bash
/plugin install iac-terraform@devops-skills
/plugin install k8s-troubleshooter@devops-skills
/plugin install aws-cost-optimization@devops-skills
/plugin install ci-cd@devops-skills
/plugin install gitops-workflows@devops-skills
/plugin install monitoring-observability@devops-skills
```

## Usage

Once installed, use these skills through Claude Code by describing what you need:

**Monitoring & Observability:**
- "Help me set up Prometheus monitoring for my web application"
- "Create alerts for my service based on SLO best practices"
- "Calculate my error budget consumption for 99.9% availability"
- "Design a Grafana dashboard for my Kubernetes cluster"
- "Should I use Prometheus or Datadog for my startup?"
- "Implement OpenTelemetry distributed tracing in my Node.js app"
- "Check the quality of my Prometheus alert rules"

**AWS Cost Optimization:**
- "Find unused AWS resources that are costing me money"
- "Analyze my EC2 instances for Reserved Instance opportunities"
- "What's the cheapest way to store infrequently accessed data in S3?"
- "Help me set up a monthly AWS cost review process"
- "Detect cost anomalies in my AWS spending"

**Terraform:**
- "Help me create a reusable Terraform module for VPC"
- "Review my Terraform state for drift"
- "Troubleshoot this Terraform error"

**Kubernetes:**
- "This pod is in CrashLoopBackOff, help me diagnose it"
- "Check the health of my Kubernetes cluster"
- "Help me troubleshoot this deployment"

**GitOps:**
- "Set up ArgoCD for my Kubernetes cluster"
- "Help me design a GitOps repository structure for multi-environment deployments"
- "My ArgoCD application is OutOfSync, help me troubleshoot"
- "Implement progressive delivery with canary deployments"
- "How should I manage secrets in GitOps?"
- "Set up multi-cluster deployment with Flux"
- "Should I use ArgoCD or Flux for my platform?"

## Contributing

To contribute a new DevOps skill:

1. Fork this repository
2. Create a new directory with your skill name (lowercase, hyphenated)
3. Add `.claude-plugin/plugin.json` manifest
4. Add `skills/SKILL.md` with proper frontmatter
5. Update `.claude-plugin/marketplace.json` to include your skill
6. Submit a pull request

## License

MIT
