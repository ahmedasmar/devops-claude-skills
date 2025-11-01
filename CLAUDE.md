# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a **Claude Code Skills Marketplace** repository containing DevOps-focused skills. It follows the Claude Code plugin/skill architecture where each skill is a self-contained directory with reference materials, scripts, and structured guidance.

## Repository Structure

```
devops-claude-skills/
├── .claude-plugin/
│   └── marketplace.json          # Marketplace registry (lists all available skills)
├── iac-terraform/                # Skill: Terraform & Terragrunt
│   ├── .claude-plugin/
│   │   └── plugin.json          # Skill metadata
│   └── skills/
│       ├── SKILL.md             # Main skill content (loaded when skill invoked)
│       ├── references/          # Supporting documentation
│       ├── scripts/             # Diagnostic/utility scripts
│       └── assets/              # Templates and resources
├── k8s-troubleshooter/          # Skill: Kubernetes troubleshooting
│   ├── .claude-plugin/
│   │   └── plugin.json
│   └── skills/
│       ├── SKILL.md
│       ├── references/
│       └── scripts/
├── aws-cost-optimization/       # Skill: AWS cost optimization & FinOps
│   ├── .claude-plugin/
│   │   └── plugin.json
│   ├── SKILL.md                 # Main skill content (at root level)
│   ├── scripts/                 # 6 automated analysis scripts
│   ├── references/              # Best practices and alternatives
│   └── assets/templates/        # Monthly report template
├── ci-cd/                       # Skill: CI/CD pipelines & DevSecOps
│   ├── .claude-plugin/
│   │   └── plugin.json
│   ├── SKILL.md
│   ├── scripts/
│   ├── references/
│   └── assets/
├── gitops-workflows/            # Skill: GitOps with ArgoCD & Flux
│   ├── .claude-plugin/
│   │   └── plugin.json
│   ├── SKILL.md                 # Main skill content (at root level)
│   ├── scripts/                 # 8 automated analysis scripts
│   ├── references/              # 8 comprehensive guides
│   └── assets/                  # ArgoCD, Flux, secrets templates
└── monitoring-observability/    # Skill: Monitoring & observability
    ├── .claude-plugin/
    │   └── plugin.json
    ├── SKILL.md                 # Main skill content (at root level)
    ├── scripts/                 # 6 automated analysis scripts
    ├── references/              # 6 comprehensive guides
    └── assets/templates/        # Prometheus alerts, OTel config, runbooks
```

## Architecture Principles

### 1. Skills as Self-Contained Modules
Each skill directory is completely independent and contains:
- **SKILL.md**: Main instructional content (the "brain" of the skill)
- **references/**: Detailed supporting documentation (troubleshooting guides, best practices)
- **scripts/**: Python automation scripts for diagnostics and validation
- **assets/**: Templates, examples, and reusable resources
- **.claude-plugin/plugin.json**: Metadata (name, description, version, author)

### 2. Two-Layer Documentation Pattern
Skills use a two-layer documentation approach:
- **SKILL.md**: Workflow-oriented guidance with decision trees, quick references, and "when to use" sections
- **references/*.md**: Deep-dive documentation for specific topics (e.g., `troubleshooting.md`, `best_practices.md`)

This pattern allows SKILL.md to stay focused on workflows while references provide comprehensive detail when needed.

### 3. Diagnostic Scripts Pattern
Each skill includes Python scripts that follow a common pattern:
- Accept relevant parameters (path, namespace/pod, etc.)
- Perform automated checks and analysis
- Provide structured output with actionable recommendations
- Can be run standalone or integrated into workflows

## Available Skills

### iac-terraform
**Purpose**: Terraform and Terragrunt infrastructure as code workflows

**Key Components**:
- `skills/SKILL.md`: Comprehensive Terraform/Terragrunt workflows including module development, state management, and troubleshooting
- `skills/references/best_practices.md`: Project structure, state management, module design, security practices, CI/CD patterns
- `skills/references/troubleshooting.md`: Common issues (state locks, drift, provider errors, resource issues, performance)
- `skills/scripts/inspect_state.py`: Terraform state inspection and drift detection
- `skills/scripts/validate_module.py`: Module validation against best practices
- `skills/assets/templates/MODULE_TEMPLATE.md`: Complete module structure template

**Workflow Pattern**: Decision-tree based (Is this reusable? → Module vs Environment Config)

### k8s-troubleshooter
**Purpose**: Systematic Kubernetes troubleshooting and incident response

**Key Components**:
- `skills/SKILL.md`: Systematic troubleshooting workflow from context gathering to post-incident
- `skills/references/common_issues.md`: Detailed issue library (ImagePullBackOff, CrashLoopBackOff, OOMKilled, node issues, networking, storage, RBAC)
- `skills/references/incident_response.md`: Structured incident response framework with severity levels and playbooks
- `skills/scripts/cluster_health.py`: Cluster-wide health check (nodes, system pods, failures)
- `skills/scripts/diagnose_pod.py`: Pod-level diagnostics with actionable recommendations

**Workflow Pattern**: Systematic triage (Gather Context → Initial Triage → Deep Dive → Root Cause → Remediation → Verify)

### aws-cost-optimization
**Purpose**: AWS cost optimization and FinOps workflows

**Key Components**:
- `SKILL.md`: Comprehensive cost optimization workflows (monthly reviews, RI analysis, instance migrations, Spot evaluation)
- `references/best_practices.md`: Cost optimization strategies across compute, storage, network, and database services
- `references/service_alternatives.md`: Cost-effective service selection guide (EC2 vs Lambda, S3 tiers, RDS vs Aurora, NAT alternatives)
- `references/finops_governance.md`: Organizational FinOps framework (tagging, budgets, monthly reviews, chargeback/showback)
- `scripts/find_unused_resources.py`: Find unattached volumes, old snapshots, unused IPs, idle NAT Gateways, idle instances, unused load balancers
- `scripts/analyze_ri_recommendations.py`: Analyze EC2/RDS usage patterns and recommend Reserved Instance purchases
- `scripts/detect_old_generations.py`: Identify old generation instances (t2→t3, Intel→Graviton) with migration recommendations
- `scripts/spot_recommendations.py`: Evaluate workloads for Spot instance suitability with savings estimates
- `scripts/rightsizing_analyzer.py`: Find oversized EC2/RDS instances using CloudWatch metrics
- `scripts/cost_anomaly_detector.py`: Detect cost spikes, identify top cost drivers, generate forecasts
- `assets/templates/monthly_cost_report.md`: Complete monthly cost optimization report template

**Workflow Pattern**: Systematic optimization (Discover → Analyze → Prioritize → Implement → Monitor)

### ci-cd
**Purpose**: CI/CD pipeline design, optimization, and DevSecOps integration

**Key Components**:
- `SKILL.md`: Comprehensive CI/CD workflows including GitHub Actions, GitLab CI, pipeline optimization, security scanning, and troubleshooting
- `references/best_practices.md`: Pipeline design patterns, caching strategies, security best practices
- `references/security.md`: DevSecOps practices, SAST/DAST/SCA integration, secret management
- `references/optimization.md`: Build performance optimization, parallel execution, artifact management
- `references/devsecops.md`: Security tooling integration (Snyk, Trivy, SonarQube)
- `references/troubleshooting.md`: Common pipeline issues and debugging strategies

**Workflow Pattern**: Task-based with security integration (Design → Optimize → Secure → Debug)

### gitops-workflows
**Purpose**: GitOps workflows with ArgoCD 3.x and Flux CD 2.7, multi-cluster management, and progressive delivery

**Key Components**:
- `SKILL.md`: Comprehensive GitOps workflows including ArgoCD/Flux setup, repository structure design, multi-cluster deployment, secrets management, progressive delivery, troubleshooting, and OCI artifacts
- `references/argocd_vs_flux.md`: Detailed comparison with decision matrix, ArgoCD 3.x breaking changes (annotation-based tracking, fine-grained RBAC), Flux 2.7 features (OCI artifacts GA, image automation, source-watcher)
- `references/repo_patterns.md`: Monorepo vs polyrepo patterns, app-of-apps, Kustomize vs Helm, environment promotion strategies
- `references/secret_management.md`: SOPS+age (2025 preferred), External Secrets Operator v0.20+, Sealed Secrets, key rotation, git pre-commit hooks
- `references/progressive_delivery.md`: Argo Rollouts canary/blue-green, Flagger integration, analysis with metrics providers
- `references/multi_cluster.md`: ApplicationSets (Cluster/Matrix generators), hub-and-spoke architecture, workload identity, 83% performance improvement patterns
- `references/oci_artifacts.md`: Flux v2.6+ OCI support, OCIRepository resource, cosign/notation signature verification, workload identity for AWS/GCP/Azure
- `references/best_practices.md`: CNCF GitOps principles (OpenGitOps v1.0), ArgoCD 3.x resource exclusions, Flux 2.7 source-watcher, 2025 security trends
- `references/troubleshooting.md`: ArgoCD OutOfSync/annotation tracking/sync failures, Flux GitRepository/Kustomization/HelmRelease/OCI issues, SOPS decryption, performance optimization
- `scripts/check_argocd_health.py`: Diagnose ArgoCD application health, detect sync issues, check annotation vs label tracking (ArgoCD 3.x compatible)
- `scripts/check_flux_health.py`: Diagnose Flux reconciliation issues across GitRepository, OCIRepository, Kustomization, HelmRelease, ImageUpdateAutomation
- `scripts/validate_gitops_repo.py`: Validate repository structure, detect deprecated Kustomize syntax, check YAML validity, audit secrets management
- `scripts/sync_drift_detector.py`: Detect configuration drift between Git and cluster for both ArgoCD and Flux
- `scripts/secret_audit.py`: Audit secrets management practices, detect plain secrets in Git (HIGH severity), verify SOPS/age/ESO configuration
- `scripts/applicationset_generator.py`: Generate ArgoCD ApplicationSet manifests (Cluster/List/Matrix generators) with goTemplate support
- `scripts/promotion_validator.py`: Validate environment promotion workflows (dev → staging → production)
- `scripts/oci_artifact_checker.py`: Validate Flux OCI artifacts, verify cosign/notation signatures
- `assets/argocd/install-argocd-3.x.yaml`: ArgoCD 3.x installation with annotation-based tracking, resource exclusions, LoadBalancer/Ingress
- `assets/applicationsets/cluster-generator.yaml`: ApplicationSet with Cluster generator, goTemplate, auto-sync
- `assets/flux/flux-bootstrap-github.sh`: Flux 2.7 bootstrap script with source-watcher component
- `assets/flux/oci-helmrelease.yaml`: OCIRepository + HelmRelease with semver and cosign verification
- `assets/secrets/sops-age-config.yaml`: .sops.yaml with age encryption for multiple environments
- `assets/progressive-delivery/argo-rollouts-canary.yaml`: Argo Rollouts canary with multi-step progression and Prometheus analysis

**Workflow Pattern**: Decision-tree based (Tool selection → Setup → Repository structure → Multi-cluster/Secrets/Progressive delivery → Troubleshooting) with 8 core workflows

### monitoring-observability
**Purpose**: Monitoring and observability strategy, implementation, and troubleshooting

**Key Components**:
- `SKILL.md`: Comprehensive observability workflows including metrics design, log aggregation, distributed tracing, alerting, SLOs, and tool selection
- `references/metrics_design.md`: Four Golden Signals, RED/USE methods, metric types, cardinality best practices, dashboard design
- `references/alerting_best_practices.md`: Alert design patterns, multi-window burn rate alerting, runbook structure, on-call practices
- `references/logging_guide.md`: Structured logging, log aggregation patterns (ELK, Loki, CloudWatch, Fluentd), query patterns, PII redaction
- `references/tracing_guide.md`: OpenTelemetry instrumentation (Python, Node.js, Go, Java), distributed tracing, sampling strategies, backend comparison
- `references/slo_sla_guide.md`: SLI/SLO/SLA definitions, error budget policies, burn rate alerting, monthly reporting
- `references/tool_comparison.md`: Comprehensive comparison of monitoring tools (Prometheus, Datadog, ELK, Loki, CloudWatch, Grafana, Jaeger, Tempo)
- `scripts/analyze_metrics.py`: Query Prometheus/CloudWatch metrics, detect anomalies, analyze trends
- `scripts/alert_quality_checker.py`: Audit Prometheus alert rules against best practices
- `scripts/slo_calculator.py`: Calculate SLO compliance, error budgets, and burn rates
- `scripts/log_analyzer.py`: Parse logs for errors, patterns, and stack traces
- `scripts/dashboard_generator.py`: Generate Grafana dashboards for web apps, Kubernetes, databases
- `scripts/health_check_validator.py`: Validate health check endpoints against best practices
- `assets/templates/prometheus-alerts/webapp-alerts.yml`: Production-ready web application alerts with SLO-based burn rate alerting
- `assets/templates/prometheus-alerts/kubernetes-alerts.yml`: Kubernetes monitoring alerts (pods, nodes, deployments, resources, jobs)
- `assets/templates/otel-config/collector-config.yaml`: OpenTelemetry Collector configuration with multiple exporters
- `assets/templates/runbooks/incident-runbook-template.md`: Comprehensive incident response runbook template

**Workflow Pattern**: Decision-tree based (Setup from scratch? → Existing issue? → Improving monitoring?) with 8 core workflows

## Contributing New Skills

When adding a new DevOps skill to this marketplace:

1. **Create skill directory structure**:
   ```
   new-skill-name/
   ├── .claude-plugin/
   │   └── plugin.json
   └── skills/
       ├── SKILL.md
       ├── references/
       ├── scripts/
       └── assets/
   ```

2. **Write plugin.json** with:
   ```json
   {
     "name": "skill-name",
     "description": "One-line description",
     "version": "1.0.0",
     "author": {
       "name": "Your Name"
     }
   }
   ```

3. **Structure SKILL.md** with:
   - YAML frontmatter (name, description)
   - "When to Use This Skill" section
   - Core workflows with decision trees or systematic processes
   - Quick reference commands
   - Links to reference documentation
   - Best practices summary

4. **Update .claude-plugin/marketplace.json** to register the new skill:
   ```json
   {
     "name": "skill-name",
     "source": "./skill-name",
     "description": "Brief description"
   }
   ```

5. **Update root README.md** to list the new skill under "Available Skills"

## Testing Skills

Skills can be tested by:

1. **Installing the marketplace locally**:
   ```bash
   /plugin marketplace add /path/to/devops-claude-skills
   ```

2. **Installing individual skills**:
   ```bash
   /plugin install iac-terraform@devops-skills
   /plugin install k8s-troubleshooter@devops-skills
   /plugin install aws-cost-optimization@devops-skills
   /plugin install ci-cd@devops-skills
   /plugin install gitops-workflows@devops-skills
   /plugin install monitoring-observability@devops-skills
   ```

3. **Testing script functionality**:
   ```bash
   # Terraform scripts
   python3 iac-terraform/skills/scripts/inspect_state.py /path/to/terraform
   python3 iac-terraform/skills/scripts/validate_module.py /path/to/module

   # Kubernetes scripts
   python3 k8s-troubleshooter/skills/scripts/cluster_health.py
   python3 k8s-troubleshooter/skills/scripts/diagnose_pod.py <namespace> <pod>

   # AWS cost optimization scripts
   python3 aws-cost-optimization/scripts/find_unused_resources.py
   python3 aws-cost-optimization/scripts/analyze_ri_recommendations.py --days 60
   python3 aws-cost-optimization/scripts/detect_old_generations.py --region us-east-1
   python3 aws-cost-optimization/scripts/spot_recommendations.py
   python3 aws-cost-optimization/scripts/rightsizing_analyzer.py --days 30
   python3 aws-cost-optimization/scripts/cost_anomaly_detector.py --days 30

   # GitOps workflows scripts
   python3 gitops-workflows/scripts/check_argocd_health.py --server argocd.example.com
   python3 gitops-workflows/scripts/check_flux_health.py --namespace flux-system
   python3 gitops-workflows/scripts/validate_gitops_repo.py /path/to/gitops-repo
   python3 gitops-workflows/scripts/sync_drift_detector.py --tool argocd
   python3 gitops-workflows/scripts/secret_audit.py /path/to/gitops-repo
   python3 gitops-workflows/scripts/applicationset_generator.py cluster --name my-apps --repo-url https://github.com/org/repo
   python3 gitops-workflows/scripts/promotion_validator.py --source dev --target staging
   python3 gitops-workflows/scripts/oci_artifact_checker.py --name my-chart --namespace flux-system

   # Monitoring & observability scripts
   python3 monitoring-observability/scripts/slo_calculator.py --table
   python3 monitoring-observability/scripts/alert_quality_checker.py alerts.yml
   python3 monitoring-observability/scripts/analyze_metrics.py prometheus --endpoint http://localhost:9090 --query 'rate(http_requests_total[5m])'
   python3 monitoring-observability/scripts/log_analyzer.py application.log
   python3 monitoring-observability/scripts/dashboard_generator.py webapp --title "My App" --service myapp --output dashboard.json
   python3 monitoring-observability/scripts/health_check_validator.py https://api.example.com/health
   python3 monitoring-observability/scripts/datadog_cost_analyzer.py --api-key $DD_API_KEY --app-key $DD_APP_KEY
   ```

## Design Philosophy

### For SKILL.md Files
- **Workflow-first**: Organize around "how to do X" rather than "what is X"
- **Decision trees**: Help users choose the right approach (see iac-terraform's "Is this reusable?" pattern)
- **Systematic processes**: Provide step-by-step frameworks (see k8s-troubleshooter's 6-phase workflow)
- **Quick references**: Include essential commands for rapid access
- **Link to depth**: Point to references/* for detailed information rather than duplicating

### For Reference Documentation
- **Comprehensive coverage**: Include all relevant details, causes, solutions
- **Searchable structure**: Use clear headings so specific issues can be found quickly
- **Actionable content**: Each issue includes symptoms, causes, diagnostics, remediation, and prevention
- **Real-world focus**: Based on actual production scenarios and common problems

### For Scripts
- **Automation over manual**: Automate repetitive diagnostic tasks
- **Structured output**: Provide clear, parseable results
- **Actionable recommendations**: Don't just report problems, suggest solutions
- **Safe defaults**: Never make destructive changes, only analyze and recommend

## File Conventions

- **Skill names**: lowercase, hyphenated (e.g., `iac-terraform`, `k8s-troubleshooter`)
- **Python scripts**: Descriptive verbs (e.g., `inspect_state.py`, `diagnose_pod.py`, `validate_module.py`)
- **Reference docs**: Noun phrases (e.g., `best_practices.md`, `common_issues.md`, `incident_response.md`)
- **Templates**: UPPERCASE suffix (e.g., `MODULE_TEMPLATE.md`)

## Important Notes

- The `.claude-plugin/marketplace.json` file at the root is the registry that makes skills discoverable
- Each skill's `plugin.json` must match its entry in `marketplace.json`
- SKILL.md files use YAML frontmatter with `name` and `description` fields
- Skills are invoked via `/plugin install` commands after marketplace is added
- Python scripts assume standard DevOps tooling is available (terraform, kubectl, aws cli, etc.)
- AWS cost optimization scripts require boto3 and tabulate: `pip install boto3 tabulate`
- Monitoring & observability scripts require requests, boto3, tabulate, and pyyaml: `pip install requests boto3 tabulate pyyaml`
