# CI/CD Security

Comprehensive guide to securing CI/CD pipelines, secrets management, and supply chain security.

## Table of Contents

- [Secrets Management](#secrets-management)
- [OIDC Authentication](#oidc-authentication)
- [Supply Chain Security](#supply-chain-security)
- [Access Control](#access-control)
- [Secure Pipeline Patterns](#secure-pipeline-patterns)
- [Vulnerability Scanning](#vulnerability-scanning)

---

## Secrets Management

### Never Commit Secrets

**Prevention methods:**
- Use `.gitignore` for sensitive files
- Enable pre-commit hooks (git-secrets, gitleaks)
- Use secret scanning (GitHub, GitLab)

**If secrets are exposed:**
1. Rotate compromised credentials immediately
2. Remove from git history: `git filter-repo` or BFG Repo-Cleaner
3. Audit access logs for unauthorized usage

### Platform Secret Stores

**GitHub Secrets:**
```yaml
# Repository, Environment, or Organization secrets
steps:
  - name: Deploy
    env:
      API_KEY: ${{ secrets.API_KEY }}
      DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
    run: ./deploy.sh
```

**Secret hierarchy:**
1. Environment secrets (highest priority)
2. Repository secrets
3. Organization secrets (lowest priority)

**GitLab CI/CD Variables:**
```yaml
# Project > Settings > CI/CD > Variables
deploy:
  script:
    - echo $API_KEY
    - deploy --token $DEPLOY_TOKEN
  variables:
    ENVIRONMENT: "production"  # Non-secret variable
```

**Variable types:**
- **Protected:** Only available on protected branches
- **Masked:** Hidden in job logs
- **Environment scope:** Limit to specific environments

### External Secret Management

**HashiCorp Vault:**
```yaml
# GitHub Actions
- uses: hashicorp/vault-action@v3
  with:
    url: https://vault.example.com
    method: jwt
    role: cicd-role
    secrets: |
      secret/data/app api_key | API_KEY ;
      secret/data/db password | DB_PASSWORD
```

**AWS Secrets Manager:**
```yaml
- name: Get secrets
  run: |
    SECRET=$(aws secretsmanager get-secret-value \
      --secret-id prod/api/key \
      --query SecretString --output text)
    echo "::add-mask::$SECRET"
    echo "API_KEY=$SECRET" >> $GITHUB_ENV
```

**Azure Key Vault:**
```yaml
- uses: Azure/get-keyvault-secrets@v1
  with:
    keyvault: "my-keyvault"
    secrets: 'api-key, db-password'
```

### Secret Rotation

**Implement rotation policies:**
```yaml
check-secret-age:
  steps:
    - name: Check secret age
      run: |
        CREATED=$(aws secretsmanager describe-secret \
          --secret-id myapp/api-key \
          --query 'CreatedDate' --output text)
        AGE=$(( ($(date +%s) - $(date -d "$CREATED" +%s)) / 86400 ))
        if [ $AGE -gt 90 ]; then
          echo "Secret is $AGE days old, rotation required"
          exit 1
        fi
```

**Best practices:**
- Rotate secrets every 90 days
- Use short-lived credentials when possible
- Audit secret access logs
- Automate rotation where possible

---

## OIDC Authentication

### Why OIDC?

**Benefits over static credentials:**
- No long-lived secrets in CI/CD
- Automatic token expiration
- Fine-grained permissions
- Audit trail of authentication

### GitHub Actions OIDC

**AWS example:**
```yaml
permissions:
  id-token: write  # Required for OIDC
  contents: read

jobs:
  deploy:
    steps:
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789:role/GitHubActionsRole
          aws-region: us-east-1

      - run: aws s3 sync dist/ s3://my-bucket
```

**AWS IAM Trust Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::123456789:oidc-provider/token.actions.githubusercontent.com"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
        "token.actions.githubusercontent.com:sub": "repo:owner/repo:ref:refs/heads/main"
      }
    }
  }]
}
```

**GCP example:**
```yaml
- uses: google-github-actions/auth@v2
  with:
    workload_identity_provider: 'projects/123/locations/global/workloadIdentityPools/github/providers/github-provider'
    service_account: 'github-actions@project.iam.gserviceaccount.com'

- run: gcloud storage cp dist/* gs://my-bucket
```

**Azure example:**
```yaml
- uses: azure/login@v2
  with:
    client-id: ${{ secrets.AZURE_CLIENT_ID }}
    tenant-id: ${{ secrets.AZURE_TENANT_ID }}
    subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

- run: az storage blob upload-batch -d mycontainer -s dist/
```

### GitLab OIDC

**Configure ID token:**
```yaml
deploy:
  id_tokens:
    GITLAB_OIDC_TOKEN:
      aud: https://aws.amazonaws.com
  script:
    - |
      CREDENTIALS=$(aws sts assume-role-with-web-identity \
        --role-arn $AWS_ROLE_ARN \
        --role-session-name gitlab-ci \
        --web-identity-token $GITLAB_OIDC_TOKEN \
        --duration-seconds 3600)
```

**Vault integration:**
```yaml
deploy:
  id_tokens:
    VAULT_ID_TOKEN:
      aud: https://vault.example.com
  before_script:
    - export VAULT_TOKEN=$(vault write -field=token auth/jwt/login role=cicd-role jwt=$VAULT_ID_TOKEN)
```

---

## Supply Chain Security

### Dependency Verification

**Lock files:**
- Always commit lock files
- Use `npm ci`, not `npm install`
- Enable `--frozen-lockfile` (Yarn) or `--frozen-lockfile` (pnpm)

**Checksum verification:**
```yaml
- name: Verify dependencies
  run: |
    npm ci --audit=true
    npx lockfile-lint --path package-lock.json --validate-https
```

**SBOM generation:**
```yaml
- name: Generate SBOM
  run: |
    syft dir:. -o spdx-json > sbom.json

- uses: actions/upload-artifact@v4
  with:
    name: sbom
    path: sbom.json
```

### Action/Workflow Security

**Pin to commit SHA (GitHub):**
```yaml
# Bad - mutable tag
- uses: actions/checkout@v4

# Better - specific version
- uses: actions/checkout@v4.1.0

# Best - pinned to SHA
- uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11  # v4.1.0
```

**Verify action sources:**
- Only use actions from trusted sources
- Review action code before first use
- Monitor Dependabot alerts for actions
- Use verified creators when possible

**GitLab include verification:**
```yaml
include:
  - project: 'security/ci-templates'
    ref: 'v2.1.0'  # Pin to specific version
    file: '/security-scan.yml'
```

### Container Image Security

**Use specific tags:**
```yaml
# Bad
image: node:latest

# Good
image: node:20.11.0-alpine

# Best
image: node:20.11.0-alpine@sha256:abc123...
```

**Minimal base images:**
```dockerfile
# Prefer distroless or alpine
FROM gcr.io/distroless/node20-debian12

# Or alpine
FROM node:20-alpine
```

**Image scanning:**
```yaml
- name: Build image
  run: docker build -t myapp:${{ github.sha }} .

- name: Scan image
  run: |
    trivy image --severity HIGH,CRITICAL myapp:${{ github.sha }}
    grype myapp:${{ github.sha }}
```

### Code Signing

**Sign commits:**
```bash
git config --global user.signingkey <key-id>
git config --global commit.gpgsign true
```

**Verify signed commits (GitHub):**
```yaml
- name: Verify signatures
  run: |
    git verify-commit HEAD || exit 1
```

**Sign artifacts:**
```yaml
- name: Sign release
  run: |
    cosign sign myregistry/myapp:${{ github.sha }}
```

---

## Access Control

### Principle of Least Privilege

**GitHub permissions:**
```yaml
# Minimal permissions
permissions:
  contents: read  # Only read code
  pull-requests: write  # Comment on PRs

jobs:
  deploy:
    permissions:
      contents: read
      id-token: write  # For OIDC
```

**GitLab protected branches:**
- Configure in Settings > Repository > Protected branches
- Restrict who can push and merge
- Require approval before merge

### Branch Protection

**GitHub branch protection rules:**
- Require pull request reviews
- Require status checks to pass
- Require signed commits
- Require linear history
- Include administrators
- Restrict who can push

**GitLab merge request approval rules:**
```yaml
# .gitlab/CODEOWNERS
*       @senior-devs
/infra/ @devops-team
/security/ @security-team
```

### Environment Protection

**GitHub environment rules:**
- Required reviewers (up to 6)
- Wait timer before deployment
- Deployment branches (limit to specific branches)
- Custom deployment protection rules

**GitLab deployment protection:**
```yaml
production:
  environment:
    name: production
  rules:
    - if: '$CI_COMMIT_BRANCH == "main"'
      when: manual  # Require manual trigger
  only:
    variables:
      - $APPROVED == "true"
```

### Audit Logging

**Enable audit logs:**
- GitHub: Enterprise > Settings > Audit log
- GitLab: Admin Area > Monitoring > Audit Events

**Monitor for:**
- Secret access
- Permission changes
- Workflow modifications
- Deployment approvals

---

## Secure Pipeline Patterns

### Isolate Untrusted Code

**Separate test from deploy:**
```yaml
test:
  # Runs on PRs from forks
  permissions:
    contents: read
    pull-requests: write

deploy:
  if: github.event_name == 'push'  # Not on PR
  permissions:
    contents: read
    id-token: write
```

**GitLab fork protection:**
```yaml
deploy:
  rules:
    - if: '$CI_PROJECT_PATH == "myorg/myrepo"'  # Only from main repo
    - if: '$CI_COMMIT_BRANCH == "main"'
```

### Sanitize Inputs

**Avoid command injection:**
```yaml
# Bad - command injection risk
- run: echo "Title: ${{ github.event.issue.title }}"

# Good - use environment variable
- env:
    TITLE: ${{ github.event.issue.title }}
  run: echo "Title: $TITLE"
```

**Validate inputs:**
```yaml
- name: Validate version
  run: |
    if [[ ! "${{ inputs.version }}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
      echo "Invalid version format"
      exit 1
    fi
```

### Network Restrictions

**Limit egress:**
```yaml
# GitHub Actions with StepSecurity
- uses: step-security/harden-runner@v2
  with:
    egress-policy: block
    allowed-endpoints: |
      api.github.com:443
      npmjs.org:443
```

**GitLab network policy:**
```yaml
# Kubernetes NetworkPolicy for GitLab Runner pods
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: gitlab-runner-policy
spec:
  podSelector:
    matchLabels:
      app: gitlab-runner
  policyTypes:
    - Egress
  egress:
    - to:
        - namespaceSelector: {}
      ports:
        - protocol: TCP
          port: 443
```

---

## Vulnerability Scanning

### Dependency Scanning

**npm audit:**
```yaml
- run: npm audit --audit-level=high
```

**Snyk:**
```yaml
- uses: snyk/actions/node@master
  env:
    SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
  with:
    args: --severity-threshold=high
```

**GitLab Dependency Scanning:**
```yaml
include:
  - template: Security/Dependency-Scanning.gitlab-ci.yml
```

### Static Application Security Testing (SAST)

**CodeQL (GitHub):**
```yaml
- uses: github/codeql-action/init@v3
  with:
    languages: javascript, python

- uses: github/codeql-action/autobuild@v3

- uses: github/codeql-action/analyze@v3
```

**SonarQube:**
```yaml
- uses: sonarsource/sonarqube-scan-action@master
  env:
    SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
```

### Container Scanning

**Trivy:**
```yaml
- run: |
    docker build -t myapp .
    trivy image --severity HIGH,CRITICAL --exit-code 1 myapp
```

**Grype:**
```yaml
- uses: anchore/scan-action@v3
  with:
    image: myapp:latest
    fail-build: true
    severity-cutoff: high
```

### Dynamic Application Security Testing (DAST)

**OWASP ZAP:**
```yaml
dast:
  stage: test
  image: owasp/zap2docker-stable
  script:
    - zap-baseline.py -t https://staging.example.com -r report.html
  artifacts:
    paths:
      - report.html
```

---

## Security Checklist

### Repository Level
- [ ] Enable branch protection
- [ ] Require code review
- [ ] Enable secret scanning
- [ ] Configure CODEOWNERS
- [ ] Enable signed commits
- [ ] Audit third-party integrations

### Pipeline Level
- [ ] Use OIDC instead of static credentials
- [ ] Pin actions/includes to specific versions
- [ ] Minimize permissions
- [ ] Sanitize user inputs
- [ ] Enable vulnerability scanning
- [ ] Separate test from deploy workflows
- [ ] Add security gates

### Secrets Management
- [ ] Use platform secret stores
- [ ] Enable secret masking
- [ ] Rotate secrets regularly
- [ ] Use short-lived credentials
- [ ] Audit secret access
- [ ] Never log secrets

### Monitoring & Response
- [ ] Enable audit logging
- [ ] Monitor for security alerts
- [ ] Set up incident response plan
- [ ] Regular security reviews
- [ ] Dependency update automation
- [ ] Security training for team
