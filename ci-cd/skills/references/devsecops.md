# DevSecOps in CI/CD

Comprehensive guide to integrating security into CI/CD pipelines with SAST, DAST, SCA, and security gates.

## Table of Contents

- [Shift-Left Security](#shift-left-security)
- [SAST (Static Application Security Testing)](#sast-static-application-security-testing)
- [DAST (Dynamic Application Security Testing)](#dast-dynamic-application-security-testing)
- [SCA (Software Composition Analysis)](#sca-software-composition-analysis)
- [Container Security](#container-security)
- [Secret Scanning](#secret-scanning)
- [Security Gates & Quality Gates](#security-gates--quality-gates)
- [Compliance & License Scanning](#compliance--license-scanning)

---

## Shift-Left Security

**Core principle:** Integrate security testing early in the development lifecycle, not just before production.

**Security testing stages in CI/CD:**

```
Commit → SAST → Unit Tests → SCA → Build → Container Scan → Deploy to Test → DAST → Production
  ↓         ↓                    ↓              ↓                               ↓
Secret   Code        Dependency  Docker      Dynamic        Security
Scan     Analysis    Vuln Check  Image Scan  App Testing    Gates
```

**Benefits:**
- Find vulnerabilities early (cheaper to fix)
- Faster feedback to developers
- Reduce security debt
- Prevent vulnerable code from reaching production

---

## SAST (Static Application Security Testing)

Analyzes source code, bytecode, or binaries for security vulnerabilities without executing the application.

### Tools by Language

| Language | Tools | GitHub Actions | GitLab CI |
|----------|-------|----------------|-----------|
| **Multi-language** | CodeQL, Semgrep, SonarQube | ✅ | ✅ |
| **JavaScript/TypeScript** | ESLint (security plugins), NodeJsScan | ✅ | ✅ |
| **Python** | Bandit, Pylint, Safety | ✅ | ✅ |
| **Go** | Gosec, GoSec Scanner | ✅ | ✅ |
| **Java** | SpotBugs, FindSecBugs, PMD | ✅ | ✅ |
| **C#/.NET** | Security Code Scan, Roslyn Analyzers | ✅ | ✅ |

### CodeQL (GitHub)

**GitHub Actions:**
```yaml
name: CodeQL Analysis

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * 1'  # Weekly scan

jobs:
  analyze:
    name: Analyze Code
    runs-on: ubuntu-latest
    timeout-minutes: 30

    permissions:
      actions: read
      contents: read
      security-events: write

    strategy:
      fail-fast: false
      matrix:
        language: ['javascript', 'python']

    steps:
      - uses: actions/checkout@v4

      - name: Initialize CodeQL
        uses: github/codeql-action/init@v3
        with:
          languages: ${{ matrix.language }}
          queries: security-extended

      - name: Autobuild
        uses: github/codeql-action/autobuild@v3

      - name: Perform CodeQL Analysis
        uses: github/codeql-action/analyze@v3
        with:
          category: "/language:${{matrix.language}}"
```

**Key features:**
- Supports 10+ languages
- Deep semantic analysis
- Low false positive rate
- Integrates with GitHub Security tab
- Custom query support

### Semgrep

**GitHub Actions:**
```yaml
- name: Run Semgrep
  uses: returntocorp/semgrep-action@v1
  with:
    config: >-
      p/security-audit
      p/owasp-top-ten
      p/cwe-top-25
```

**GitLab CI:**
```yaml
semgrep:
  stage: test
  image: returntocorp/semgrep
  script:
    - semgrep --config=auto --sarif --output=semgrep.sarif .
  artifacts:
    reports:
      sast: semgrep.sarif
```

**Benefits:**
- Fast (runs in seconds)
- Highly customizable rules
- Multi-language support
- CI-native design

### Language-Specific SAST

**Python - Bandit:**
```yaml
# GitHub Actions
- name: Run Bandit
  run: |
    pip install bandit
    bandit -r src/ -f json -o bandit-report.json
    bandit -r src/ --exit-zero -ll  # Only high severity fails build

# GitLab CI
bandit:
  stage: test
  image: python:3.11
  script:
    - pip install bandit
    - bandit -r src/ -ll -f gitlab > bandit-report.json
  artifacts:
    reports:
      sast: bandit-report.json
```

**JavaScript - ESLint Security Plugin:**
```yaml
# GitHub Actions
- name: Run ESLint Security
  run: |
    npm install eslint-plugin-security
    npx eslint . --plugin=security --format=json --output-file=eslint-security.json
```

**Go - Gosec:**
```yaml
# GitHub Actions
- name: Run Gosec
  uses: securego/gosec@master
  with:
    args: '-fmt sarif -out gosec.sarif ./...'

# GitLab CI
gosec:
  stage: test
  image: securego/gosec:latest
  script:
    - gosec -fmt json -out gosec-report.json ./...
  artifacts:
    reports:
      sast: gosec-report.json
```

### SonarQube/SonarCloud

**GitHub Actions:**
```yaml
- name: SonarCloud Scan
  uses: SonarSource/sonarcloud-github-action@master
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
  with:
    args: >
      -Dsonar.projectKey=my-project
      -Dsonar.organization=my-org
      -Dsonar.sources=src
      -Dsonar.tests=tests
      -Dsonar.python.coverage.reportPaths=coverage.xml
```

**GitLab CI:**
```yaml
sonarqube:
  stage: test
  image: sonarsource/sonar-scanner-cli:latest
  script:
    - sonar-scanner
      -Dsonar.projectKey=$CI_PROJECT_NAME
      -Dsonar.sources=src
      -Dsonar.host.url=$SONAR_HOST_URL
      -Dsonar.login=$SONAR_TOKEN
```

---

## DAST (Dynamic Application Security Testing)

Tests running applications for vulnerabilities by simulating attacks.

### OWASP ZAP

**Full scan workflow (GitHub Actions):**
```yaml
name: DAST Scan

on:
  schedule:
    - cron: '0 3 * * 1'  # Weekly scan
  workflow_dispatch:

jobs:
  dast:
    runs-on: ubuntu-latest

    services:
      app:
        image: myapp:latest
        ports:
          - 8080:8080

    steps:
      - name: Wait for app to start
        run: |
          timeout 60 bash -c 'until curl -f http://localhost:8080/health; do sleep 2; done'

      - name: ZAP Baseline Scan
        uses: zaproxy/action-baseline@v2.17.0
        with:
          target: 'http://localhost:8080'
          rules_file_name: '.zap/rules.tsv'
          fail_action: true

      - name: Upload ZAP report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: zap-report
          path: report_html.html
```

**GitLab CI:**
```yaml
dast:
  stage: test
  image: owasp/zap2docker-stable
  services:
    - name: $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
      alias: testapp
  script:
    # Baseline scan
    - zap-baseline.py -t http://testapp:8080 -r zap-report.html -J zap-report.json
  artifacts:
    when: always
    paths:
      - zap-report.html
      - zap-report.json
    reports:
      dast: zap-report.json
  only:
    - schedules
    - main
```

**ZAP scan types:**

1. **Baseline Scan** (Fast, ~1-2 min)
```bash
zap-baseline.py -t https://staging.example.com -r report.html
```
- Passive scanning only
- No active attacks
- Good for PR checks

2. **Full Scan** (Comprehensive, 10-60 min)
```bash
zap-full-scan.py -t https://staging.example.com -r report.html
```
- Active + Passive scanning
- Attempts exploits
- Use on staging only

3. **API Scan**
```bash
zap-api-scan.py -t https://api.example.com/openapi.json -f openapi -r report.html
```
- For REST APIs
- OpenAPI/Swagger support

### Other DAST Tools

**Nuclei:**
```yaml
- name: Run Nuclei
  uses: projectdiscovery/nuclei-action@main
  with:
    target: https://staging.example.com
    templates: cves,vulnerabilities,exposures
```

**Nikto (Web server scanner):**
```yaml
nikto:
  stage: dast
  image: sullo/nikto
  script:
    - nikto -h http://testapp:8080 -Format json -output nikto-report.json
```

---

## SCA (Software Composition Analysis)

Identifies vulnerabilities in third-party dependencies and libraries.

### Dependency Scanning

**GitHub Dependabot (Built-in):**
```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10

  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
```

**GitHub Actions - Dependency Review:**
```yaml
- name: Dependency Review
  uses: actions/dependency-review-action@v4
  with:
    fail-on-severity: high
```

**npm audit:**
```yaml
- name: npm audit
  run: |
    npm audit --audit-level=high
    # Or with audit-ci for better control
    npx audit-ci --high
```

**pip-audit (Python):**
```yaml
- name: Python Security Check
  run: |
    pip install pip-audit
    pip-audit --requirement requirements.txt --format json --output pip-audit.json
```

**Snyk:**
```yaml
# GitHub Actions
- name: Run Snyk
  uses: snyk/actions/node@master
  env:
    SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
  with:
    args: --severity-threshold=high --fail-on=all

# GitLab CI
snyk:
  stage: test
  image: snyk/snyk:node
  script:
    - snyk test --severity-threshold=high --json-file-output=snyk-report.json
  artifacts:
    reports:
      dependency_scanning: snyk-report.json
```

**OWASP Dependency-Check:**
```yaml
- name: OWASP Dependency Check
  run: |
    wget https://github.com/jeremylong/DependencyCheck/releases/download/v9.2.0/dependency-check-9.2.0-release.zip
    unzip dependency-check-9.2.0-release.zip
    ./dependency-check/bin/dependency-check.sh \
      --scan . \
      --format JSON \
      --out dependency-check-report.json \
      --failOnCVSS 7
```

### GitLab Dependency Scanning (Built-in)

```yaml
include:
  - template: Security/Dependency-Scanning.gitlab-ci.yml

dependency_scanning:
  variables:
    DS_EXCLUDED_PATHS: "test/,tests/,spec/,vendor/"
```

---

## Container Security

### Image Scanning

**Trivy (Comprehensive):**
```yaml
# GitHub Actions
- name: Run Trivy
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: myapp:${{ github.sha }}
    format: 'sarif'
    output: 'trivy-results.sarif'
    severity: 'CRITICAL,HIGH'
    exit-code: '1'

- name: Upload to Security tab
  uses: github/codeql-action/upload-sarif@v3
  if: always()
  with:
    sarif_file: 'trivy-results.sarif'

# GitLab CI
trivy:
  stage: test
  image: aquasec/trivy:latest
  script:
    - trivy image --severity HIGH,CRITICAL --format json --output trivy-report.json $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
    - trivy image --severity HIGH,CRITICAL --exit-code 1 $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
  artifacts:
    reports:
      container_scanning: trivy-report.json
```

**Grype:**
```yaml
- name: Scan with Grype
  uses: anchore/scan-action@v3
  with:
    image: myapp:latest
    fail-build: true
    severity-cutoff: high
    output-format: sarif

- name: Upload Grype results
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: ${{ steps.scan.outputs.sarif }}
```

**Clair:**
```yaml
clair:
  stage: scan
  image: arminc/clair-scanner:latest
  script:
    - clair-scanner --ip $(hostname -i) myapp:latest
```

### SBOM (Software Bill of Materials)

**Syft:**
```yaml
- name: Generate SBOM
  uses: anchore/sbom-action@v0
  with:
    image: myapp:${{ github.sha }}
    format: spdx-json
    output-file: sbom.spdx.json

- name: Upload SBOM
  uses: actions/upload-artifact@v4
  with:
    name: sbom
    path: sbom.spdx.json
```

**CycloneDX:**
```yaml
- name: Generate CycloneDX SBOM
  run: |
    npm install -g @cyclonedx/cyclonedx-npm
    cyclonedx-npm --output-file sbom.json
```

---

## Secret Scanning

### Pre-commit Prevention

**TruffleHog:**
```yaml
# GitHub Actions
- name: TruffleHog Scan
  uses: trufflesecurity/trufflehog@main
  with:
    path: ./
    base: ${{ github.event.repository.default_branch }}
    head: HEAD

# GitLab CI
trufflehog:
  stage: test
  image: trufflesecurity/trufflehog:latest
  script:
    - trufflehog filesystem . --json --fail > trufflehog-report.json
```

**Gitleaks:**
```yaml
# GitHub Actions
- name: Gitleaks
  uses: gitleaks/gitleaks-action@v2
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

# GitLab CI
gitleaks:
  stage: test
  image: zricethezav/gitleaks:latest
  script:
    - gitleaks detect --source . --report-format json --report-path gitleaks-report.json
```

**GitGuardian:**
```yaml
- name: GitGuardian scan
  uses: GitGuardian/ggshield-action@master
  env:
    GITGUARDIAN_API_KEY: ${{ secrets.GITGUARDIAN_API_KEY }}
```

### GitHub Secret Scanning (Native)

Enable in: **Settings → Code security and analysis → Secret scanning**

- Automatic detection
- Partner patterns (AWS, Azure, GCP, etc.)
- Push protection (prevents commits with secrets)

---

## Security Gates & Quality Gates

### Fail Pipeline on Security Issues

**Threshold-based gates:**
```yaml
security-gate:
  stage: gate
  script:
    # Check vulnerability count
    - |
      CRITICAL=$(jq '.vulnerabilities | map(select(.severity=="CRITICAL")) | length' trivy-report.json)
      HIGH=$(jq '.vulnerabilities | map(select(.severity=="HIGH")) | length' trivy-report.json)

      echo "Critical: $CRITICAL, High: $HIGH"

      if [ "$CRITICAL" -gt 0 ]; then
        echo "❌ CRITICAL vulnerabilities found!"
        exit 1
      fi

      if [ "$HIGH" -gt 5 ]; then
        echo "❌ Too many HIGH vulnerabilities: $HIGH"
        exit 1
      fi
```

**SonarQube Quality Gate:**
```yaml
- name: Check Quality Gate
  run: |
    STATUS=$(curl -u $SONAR_TOKEN: "$SONAR_HOST/api/qualitygates/project_status?projectKey=$PROJECT_KEY" | jq -r '.projectStatus.status')
    if [ "$STATUS" != "OK" ]; then
      echo "Quality gate failed: $STATUS"
      exit 1
    fi
```

### Manual Approval for Production

**GitHub Actions:**
```yaml
deploy-production:
  runs-on: ubuntu-latest
  needs: [sast, dast, container-scan]
  environment:
    name: production
    # Requires manual approval in Settings → Environments
  steps:
    - run: echo "Deploying to production"
```

**GitLab CI:**
```yaml
deploy:production:
  stage: deploy
  needs: [sast, dast, container_scanning]
  script:
    - ./deploy.sh production
  when: manual
  only:
    - main
```

---

## Compliance & License Scanning

### License Compliance

**FOSSology:**
```yaml
license-scan:
  stage: compliance
  image: fossology/fossology:latest
  script:
    - fossology --scan ./src
```

**License Finder:**
```yaml
- name: Check Licenses
  run: |
    gem install license_finder
    license_finder --decisions-file .license_finder.yml
```

**npm license checker:**
```yaml
- name: License Check
  run: |
    npx license-checker --production --onlyAllow "MIT;Apache-2.0;BSD-3-Clause;ISC"
```

### Policy as Code

**Open Policy Agent (OPA):**
```yaml
policy-check:
  stage: gate
  image: openpolicyagent/opa:latest
  script:
    - opa test policies/
    - opa eval --data policies/ --input violations.json "data.security.allow"
```

---

## Complete DevSecOps Pipeline

**Comprehensive example (GitHub Actions):**
```yaml
name: DevSecOps Pipeline

on: [push, pull_request]

jobs:
  # Stage 1: Secret Scanning
  secret-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: trufflesecurity/trufflehog@main

  # Stage 2: SAST
  sast:
    runs-on: ubuntu-latest
    needs: secret-scan
    steps:
      - uses: actions/checkout@v4
      - uses: github/codeql-action/init@v3
      - uses: github/codeql-action/autobuild@v3
      - uses: github/codeql-action/analyze@v3

  # Stage 3: SCA
  sca:
    runs-on: ubuntu-latest
    needs: secret-scan
    steps:
      - uses: actions/checkout@v4
      - run: npm audit --audit-level=high
      - uses: snyk/actions/node@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}

  # Stage 4: Build & Container Scan
  build-scan:
    runs-on: ubuntu-latest
    needs: [sast, sca]
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t myapp:${{ github.sha }} .
      - uses: aquasecurity/trivy-action@master
        with:
          image-ref: myapp:${{ github.sha }}
          exit-code: '1'

  # Stage 5: DAST
  dast:
    runs-on: ubuntu-latest
    needs: build-scan
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: zaproxy/action-baseline@v2.17.0
        with:
          target: 'https://staging.example.com'

  # Stage 6: Security Gate
  security-gate:
    runs-on: ubuntu-latest
    needs: [sast, sca, build-scan, dast]
    steps:
      - run: echo "All security checks passed!"
      - run: echo "Ready for deployment"

  # Stage 7: Deploy
  deploy:
    runs-on: ubuntu-latest
    needs: security-gate
    environment: production
    steps:
      - run: echo "Deploying to production"
```

---

## Best Practices

### 1. Fail Fast
- Run secret scanning first
- Run SAST early in pipeline
- Block PRs with critical vulnerabilities

### 2. Balance Speed vs Security
- SAST/SCA on every PR (fast)
- Container scanning after build
- DAST on schedules or staging only (slow)

### 3. Prioritize Findings
**Focus on:**
- Critical/High severity
- Exploitable vulnerabilities
- Direct dependencies (not transitive)
- Public-facing components

### 4. Developer Experience
- Clear error messages
- Link to remediation guidance
- Don't overwhelm with noise
- Use quality gates, not just fail/pass

### 5. Continuous Improvement
- Track security debt over time
- Set SLAs for vulnerability remediation
- Regular tool evaluation
- Security training for developers

### 6. Reporting & Metrics

**Track:**
- Mean Time to Remediate (MTTR)
- Vulnerability backlog
- False positive rate
- Coverage (% of code scanned)

```yaml
- name: Generate Security Report
  run: |
    echo "## Security Scan Summary" >> $GITHUB_STEP_SUMMARY
    echo "- SAST: ✅ Passed" >> $GITHUB_STEP_SUMMARY
    echo "- SCA: ⚠️ 3 vulnerabilities" >> $GITHUB_STEP_SUMMARY
    echo "- Container: ✅ Passed" >> $GITHUB_STEP_SUMMARY
    echo "- DAST: 🔄 Scheduled" >> $GITHUB_STEP_SUMMARY
```

---

## Tool Comparison

| Category | Tool | Speed | Accuracy | Cost | Best For |
|----------|------|-------|----------|------|----------|
| **SAST** | CodeQL | Medium | High | Free (GH) | Deep analysis |
| | Semgrep | Fast | Medium | Free/Paid | Custom rules |
| | SonarQube | Medium | High | Free/Paid | Quality + Security |
| **DAST** | OWASP ZAP | Medium | High | Free | Web apps |
| | Burp Suite | Slow | High | Paid | Professional |
| **SCA** | Snyk | Fast | High | Free/Paid | Easy integration |
| | Dependabot | Fast | Medium | Free (GH) | Auto PRs |
| **Container** | Trivy | Fast | High | Free | Fast scans |
| | Grype | Fast | High | Free | SBOM support |
| **Secrets** | TruffleHog | Fast | High | Free/Paid | Git history |
| | GitGuardian | Fast | High | Paid | Real-time |

---

## Security Scanning Schedule

**Recommended frequency:**

| Scan Type | PR | Main Branch | Schedule | Notes |
|-----------|----|-----------|-----------| ------|
| Secret Scanning | ✅ Every | ✅ Every | - | Fast, critical |
| SAST | ✅ Every | ✅ Every | - | Fast, essential |
| SCA | ✅ Every | ✅ Every | Weekly | Check dependencies |
| Linting | ✅ Every | ✅ Every | - | Very fast |
| Container Scan | ❌ No | ✅ Every | - | After build |
| DAST Baseline | ❌ No | ✅ Every | - | Medium speed |
| DAST Full | ❌ No | ❌ No | Weekly | Very slow |
| Penetration Test | ❌ No | ❌ No | Quarterly | Manual |

---

## Security Checklist

- [ ] Secret scanning enabled and running
- [ ] SAST configured for all languages used
- [ ] Dependency scanning (SCA) enabled
- [ ] Container images scanned before deployment
- [ ] DAST running on staging environment
- [ ] Security findings triaged in issue tracker
- [ ] Quality gates prevent vulnerable deployments
- [ ] SBOM generated for releases
- [ ] Security scan results tracked over time
- [ ] Vulnerability remediation SLAs defined
- [ ] Security training for developers
- [ ] Incident response plan documented
