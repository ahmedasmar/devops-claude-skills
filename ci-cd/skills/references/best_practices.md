# CI/CD Best Practices

Comprehensive guide to CI/CD pipeline design, testing strategies, and deployment patterns.

## Table of Contents

- [Pipeline Design Principles](#pipeline-design-principles)
- [Testing in CI/CD](#testing-in-cicd)
- [Deployment Strategies](#deployment-strategies)
- [Dependency Management](#dependency-management)
- [Artifact & Release Management](#artifact--release-management)
- [Platform Patterns](#platform-patterns)

---

## Pipeline Design Principles

### Fast Feedback Loops

Design pipelines to provide feedback quickly:

**Priority ordering:**
1. Linting and code formatting (seconds)
2. Unit tests (1-5 minutes)
3. Integration tests (5-15 minutes)
4. E2E tests (15-30 minutes)
5. Deployment (varies)

**Fail fast pattern:**
```yaml
# GitHub Actions
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - run: npm run lint

  test:
    needs: lint  # Only run if lint passes
    runs-on: ubuntu-latest
    steps:
      - run: npm test

  e2e:
    needs: [lint, test]  # Run after basic checks
```

### Job Parallelization

Run independent jobs concurrently:

**GitHub Actions:**
```yaml
jobs:
  lint:
    runs-on: ubuntu-latest

  test:
    runs-on: ubuntu-latest
    # No 'needs' - runs in parallel with lint

  build:
    needs: [lint, test]  # Wait for both
    runs-on: ubuntu-latest
```

**GitLab CI:**
```yaml
stages:
  - validate
  - test
  - build

# Jobs in same stage run in parallel
unit-test:
  stage: test

integration-test:
  stage: test

e2e-test:
  stage: test
```

### Monorepo Strategies

**Path-based triggers (GitHub):**
```yaml
on:
  push:
    paths:
      - 'services/api/**'
      - 'shared/**'

jobs:
  api-test:
    if: |
      contains(github.event.head_commit.modified, 'services/api/') ||
      contains(github.event.head_commit.modified, 'shared/')
```

**GitLab rules:**
```yaml
api-test:
  rules:
    - changes:
        - services/api/**/*
        - shared/**/*

frontend-test:
  rules:
    - changes:
        - services/frontend/**/*
        - shared/**/*
```

### Matrix Builds

Test across multiple versions/platforms:

**GitHub Actions:**
```yaml
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
    node: [18, 20, 22]
    include:
      - os: ubuntu-latest
        node: 22
        coverage: true
    exclude:
      - os: windows-latest
        node: 18
  fail-fast: false  # See all results
```

**GitLab parallel:**
```yaml
test:
  parallel:
    matrix:
      - NODE_VERSION: ['18', '20', '22']
        OS: ['ubuntu', 'alpine']
```

---

## Testing in CI/CD

### Test Pyramid Strategy

Maintain proper test distribution:

```
        /\
       /E2E\      10% - Slow, expensive, flaky
      /-----\
     /  Int  \    20% - Medium speed
    /--------\
   /   Unit   \   70% - Fast, reliable
  /------------\
```

**Implementation:**
```yaml
jobs:
  unit-test:
    runs-on: ubuntu-latest
    steps:
      - run: npm run test:unit  # Fast, runs on every commit

  integration-test:
    runs-on: ubuntu-latest
    needs: unit-test
    steps:
      - run: npm run test:integration  # Medium, after unit tests

  e2e-test:
    runs-on: ubuntu-latest
    needs: [unit-test, integration-test]
    if: github.ref == 'refs/heads/main'  # Only on main branch
    steps:
      - run: npm run test:e2e  # Slow, only on main
```

### Test Splitting & Parallelization

Split large test suites:

**GitHub Actions:**
```yaml
strategy:
  matrix:
    shard: [1, 2, 3, 4]
steps:
  - run: npm test -- --shard=${{ matrix.shard }}/4
```

**Playwright example:**
```yaml
strategy:
  matrix:
    shardIndex: [1, 2, 3, 4]
    shardTotal: [4]
steps:
  - run: npx playwright test --shard=${{ matrix.shardIndex }}/${{ matrix.shardTotal }}
```

### Code Coverage

**Track coverage trends:**
```yaml
- name: Run tests with coverage
  run: npm test -- --coverage

- name: Upload coverage
  uses: codecov/codecov-action@v4
  with:
    files: ./coverage/lcov.info
    fail_ci_if_error: true  # Fail if upload fails

- name: Coverage check
  run: |
    COVERAGE=$(jq -r '.total.lines.pct' coverage/coverage-summary.json)
    if (( $(echo "$COVERAGE < 80" | bc -l) )); then
      echo "Coverage $COVERAGE% is below 80%"
      exit 1
    fi
```

### Test Environment Management

**Docker Compose for services:**
```yaml
jobs:
  integration-test:
    runs-on: ubuntu-latest
    steps:
      - name: Start services
        run: docker-compose up -d postgres redis

      - name: Wait for services
        run: |
          timeout 30 bash -c 'until docker-compose exec -T postgres pg_isready; do sleep 1; done'

      - name: Run tests
        run: npm run test:integration

      - name: Cleanup
        if: always()
        run: docker-compose down
```

**GitLab services:**
```yaml
integration-test:
  services:
    - postgres:15
    - redis:7-alpine
  variables:
    POSTGRES_DB: testdb
    POSTGRES_PASSWORD: password
  script:
    - npm run test:integration
```

---

## Deployment Strategies

### Deployment Patterns

**1. Direct Deployment (Simple)**
```yaml
deploy:
  if: github.ref == 'refs/heads/main'
  steps:
    - run: |
        aws s3 sync dist/ s3://${{ secrets.S3_BUCKET }}
        aws cloudfront create-invalidation --distribution-id ${{ secrets.CF_DIST }}
```

**2. Blue-Green Deployment**
```yaml
deploy:
  steps:
    - name: Deploy to staging slot
      run: az webapp deployment slot swap --slot staging --resource-group $RG --name $APP

    - name: Health check
      run: |
        for i in {1..10}; do
          if curl -f https://$APP.azurewebsites.net/health; then
            echo "Health check passed"
            exit 0
          fi
          sleep 10
        done
        exit 1

    - name: Rollback on failure
      if: failure()
      run: az webapp deployment slot swap --slot staging --resource-group $RG --name $APP
```

**3. Canary Deployment**
```yaml
deploy-canary:
  steps:
    - run: kubectl set image deployment/app app=myapp:${{ github.sha }}
    - run: kubectl patch deployment app -p '{"spec":{"replicas":1}}'  # 1 pod
    - run: sleep 300  # Monitor for 5 minutes
    - run: kubectl scale deployment app --replicas=10  # Scale to full
```

### Environment Management

**GitHub Environments:**
```yaml
jobs:
  deploy-staging:
    environment:
      name: staging
      url: https://staging.example.com
    steps:
      - run: ./deploy.sh staging

  deploy-production:
    needs: deploy-staging
    environment:
      name: production
      url: https://example.com
    steps:
      - run: ./deploy.sh production
```

**Protection rules:**
- Require approval for production
- Restrict to specific branches
- Add deployment delay

**GitLab environments:**
```yaml
deploy:staging:
  stage: deploy
  environment:
    name: staging
    url: https://staging.example.com
    on_stop: stop:staging
  only:
    - develop

deploy:production:
  stage: deploy
  environment:
    name: production
    url: https://example.com
  when: manual  # Require manual trigger
  only:
    - main
```

### Deployment Gates

**Pre-deployment checks:**
```yaml
pre-deploy-checks:
  steps:
    - name: Check migration status
      run: ./scripts/check-migrations.sh

    - name: Verify dependencies
      run: npm audit --audit-level=high

    - name: Check service health
      run: curl -f https://api.example.com/health
```

**Post-deployment validation:**
```yaml
post-deploy-validation:
  needs: deploy
  steps:
    - name: Smoke tests
      run: npm run test:smoke

    - name: Monitor errors
      run: |
        ERROR_COUNT=$(datadog-api errors --since 5m)
        if [ $ERROR_COUNT -gt 10 ]; then
          echo "Error spike detected!"
          exit 1
        fi
```

---

## Dependency Management

### Lock Files

**Always commit lock files:**
- `package-lock.json` (npm)
- `yarn.lock` (Yarn)
- `pnpm-lock.yaml` (pnpm)
- `Cargo.lock` (Rust)
- `Gemfile.lock` (Ruby)
- `poetry.lock` (Python)

**Use deterministic install commands:**
```bash
# Good - uses lock file
npm ci           # Not npm install
yarn install --frozen-lockfile
pnpm install --frozen-lockfile
pip install -r requirements.txt

# Bad - updates lock file
npm install
```

### Dependency Caching

**See optimization.md for detailed caching strategies**

Quick reference:
- Hash lock files for cache keys
- Include OS/platform in cache key
- Use restore-keys for partial matches
- Separate cache for build artifacts vs dependencies

### Security Scanning

**Automated vulnerability checks:**
```yaml
security-scan:
  steps:
    - name: Dependency audit
      run: |
        npm audit --audit-level=high
        # Or: pip-audit, cargo audit, bundle audit

    - name: SAST scanning
      uses: github/codeql-action/analyze@v3

    - name: Container scanning
      run: trivy image myapp:${{ github.sha }}
```

### Dependency Updates

**Automated dependency updates:**
- Dependabot (GitHub)
- Renovate
- GitLab Dependency Scanning

**Configuration example (Dependabot):**
```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: npm
    directory: "/"
    schedule:
      interval: weekly
    open-pull-requests-limit: 5
    groups:
      dev-dependencies:
        dependency-type: development
```

---

## Artifact & Release Management

### Artifact Strategy

**Build once, deploy many:**
```yaml
build:
  steps:
    - run: npm run build
    - uses: actions/upload-artifact@v4
      with:
        name: dist-${{ github.sha }}
        path: dist/
        retention-days: 7

deploy-staging:
  needs: build
  steps:
    - uses: actions/download-artifact@v4
      with:
        name: dist-${{ github.sha }}
    - run: ./deploy.sh staging

deploy-production:
  needs: [build, deploy-staging]
  steps:
    - uses: actions/download-artifact@v4
      with:
        name: dist-${{ github.sha }}
    - run: ./deploy.sh production
```

### Container Image Management

**Multi-stage builds:**
```dockerfile
# Build stage
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

# Production stage
FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
USER node
CMD ["node", "dist/server.js"]
```

**Image tagging strategy:**
```yaml
- name: Build and tag images
  run: |
    docker build -t myapp:${{ github.sha }} .
    docker tag myapp:${{ github.sha }} myapp:latest
    docker tag myapp:${{ github.sha }} myapp:v1.2.3
```

### Release Automation

**Semantic versioning:**
```yaml
release:
  if: startsWith(github.ref, 'refs/tags/v')
  steps:
    - uses: actions/create-release@v1
      with:
        tag_name: ${{ github.ref }}
        release_name: Release ${{ github.ref }}
        body: |
          Changes in this release:
          ${{ github.event.head_commit.message }}
```

**Changelog generation:**
```yaml
- name: Generate changelog
  run: |
    git log $(git describe --tags --abbrev=0)..HEAD \
      --pretty=format:"- %s (%h)" > CHANGELOG.md
```

---

## Platform Patterns

### GitHub Actions

**Reusable workflows:**
```yaml
# .github/workflows/reusable-test.yml
on:
  workflow_call:
    inputs:
      node-version:
        required: true
        type: string

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ inputs.node-version }}
      - run: npm test
```

**Composite actions:**
```yaml
# .github/actions/setup-app/action.yml
name: Setup Application
runs:
  using: composite
  steps:
    - uses: actions/setup-node@v4
      with:
        node-version: 20
    - run: npm ci
      shell: bash
```

### GitLab CI

**Templates & extends:**
```yaml
.test_template:
  image: node:20
  before_script:
    - npm ci
  script:
    - npm test

unit-test:
  extends: .test_template
  script:
    - npm run test:unit

integration-test:
  extends: .test_template
  script:
    - npm run test:integration
```

**Dynamic child pipelines:**
```yaml
generate-pipeline:
  script:
    - ./generate-config.sh > pipeline.yml
  artifacts:
    paths:
      - pipeline.yml

trigger-pipeline:
  trigger:
    include:
      - artifact: pipeline.yml
        job: generate-pipeline
```

---

## Continuous Improvement

### Metrics to Track

- **Build duration:** Target < 10 minutes
- **Failure rate:** Target < 5%
- **Time to recovery:** Target < 1 hour
- **Deployment frequency:** Aim for multiple/day
- **Lead time:** Commit to production < 1 day

### Pipeline Optimization Checklist

- [ ] Jobs run in parallel where possible
- [ ] Dependencies are cached
- [ ] Test suite is properly split
- [ ] Linting fails fast
- [ ] Only necessary tests run on PRs
- [ ] Artifacts are reused across jobs
- [ ] Pipeline has appropriate timeouts
- [ ] Flaky tests are identified and fixed
- [ ] Security scanning is automated
- [ ] Deployment requires approval

### Regular Reviews

**Monthly:**
- Review build duration trends
- Analyze failure patterns
- Update dependencies
- Review security scan results

**Quarterly:**
- Audit pipeline efficiency
- Review deployment frequency
- Update CI/CD tools and actions
- Team retrospective on CI/CD pain points
