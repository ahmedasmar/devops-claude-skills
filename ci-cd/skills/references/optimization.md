# CI/CD Pipeline Optimization

Comprehensive guide to improving pipeline performance through caching, parallelization, and smart resource usage.

## Table of Contents

- [Caching Strategies](#caching-strategies)
- [Parallelization Techniques](#parallelization-techniques)
- [Build Optimization](#build-optimization)
- [Test Optimization](#test-optimization)
- [Resource Management](#resource-management)
- [Monitoring & Metrics](#monitoring--metrics)

---

## Caching Strategies

### Dependency Caching

**Impact:** Can reduce build times by 50-90%

#### GitHub Actions

**Node.js/npm:**
```yaml
- uses: actions/cache@v4
  with:
    path: ~/.npm
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
    restore-keys: |
      ${{ runner.os }}-node-

- run: npm ci
```

**Python/pip:**
```yaml
- uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
    restore-keys: |
      ${{ runner.os }}-pip-

- run: pip install -r requirements.txt
```

**Go modules:**
```yaml
- uses: actions/cache@v4
  with:
    path: |
      ~/.cache/go-build
      ~/go/pkg/mod
    key: ${{ runner.os }}-go-${{ hashFiles('**/go.sum') }}
    restore-keys: |
      ${{ runner.os }}-go-

- run: go build
```

**Rust/Cargo:**
```yaml
- uses: actions/cache@v4
  with:
    path: |
      ~/.cargo/bin/
      ~/.cargo/registry/index/
      ~/.cargo/registry/cache/
      ~/.cargo/git/db/
      target/
    key: ${{ runner.os }}-cargo-${{ hashFiles('**/Cargo.lock') }}
    restore-keys: |
      ${{ runner.os }}-cargo-

- run: cargo build --release
```

**Maven:**
```yaml
- uses: actions/cache@v4
  with:
    path: ~/.m2/repository
    key: ${{ runner.os }}-maven-${{ hashFiles('**/pom.xml') }}
    restore-keys: |
      ${{ runner.os }}-maven-

- run: mvn clean install
```

#### GitLab CI

**Global cache:**
```yaml
cache:
  key: ${CI_COMMIT_REF_SLUG}
  paths:
    - node_modules/
    - .npm/
    - vendor/
```

**Job-specific cache:**
```yaml
build:
  cache:
    key: build-${CI_COMMIT_REF_SLUG}
    paths:
      - target/
    policy: push  # Upload only

test:
  cache:
    key: build-${CI_COMMIT_REF_SLUG}
    paths:
      - target/
    policy: pull  # Download only
```

**Cache with files checksum:**
```yaml
cache:
  key:
    files:
      - package-lock.json
      - yarn.lock
  paths:
    - node_modules/
```

### Build Artifact Caching

**Docker layer caching (GitHub):**
```yaml
- uses: docker/setup-buildx-action@v3

- uses: docker/build-push-action@v5
  with:
    context: .
    cache-from: type=gha
    cache-to: type=gha,mode=max
    push: false
    tags: myapp:latest
```

**Docker layer caching (GitLab):**
```yaml
build:
  image: docker:latest
  services:
    - docker:dind
  variables:
    DOCKER_DRIVER: overlay2
  script:
    - docker pull $CI_REGISTRY_IMAGE:latest || true
    - docker build --cache-from $CI_REGISTRY_IMAGE:latest -t $CI_REGISTRY_IMAGE:latest .
    - docker push $CI_REGISTRY_IMAGE:latest
```

**Gradle build cache:**
```yaml
- uses: actions/cache@v4
  with:
    path: |
      ~/.gradle/caches
      ~/.gradle/wrapper
    key: ${{ runner.os }}-gradle-${{ hashFiles('**/*.gradle*', '**/gradle-wrapper.properties') }}

- run: ./gradlew build --build-cache
```

### Cache Best Practices

**Key strategies:**
- Include OS/platform: `${{ runner.os }}-` or `${CI_RUNNER_OS}`
- Hash lock files: `hashFiles('**/package-lock.json')`
- Use restore-keys for fallback matches
- Separate caches for different purposes

**Cache invalidation:**
```yaml
# Version in cache key
cache:
  key: v2-${CI_COMMIT_REF_SLUG}-${CI_PIPELINE_ID}
```

**Cache size management:**
- GitHub: 10GB per repository (LRU eviction after 7 days)
- GitLab: Configurable per runner

---

## Parallelization Techniques

### Job Parallelization

**Remove unnecessary dependencies:**
```yaml
# Before - Sequential
jobs:
  lint:
  test:
    needs: lint
  build:
    needs: test

# After - Parallel
jobs:
  lint:
  test:
  build:
    needs: [lint, test]  # Only wait for what's needed
```

### Matrix Builds

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
      - os: macos-latest
        node: 18
  fail-fast: false
  max-parallel: 10  # Limit concurrent jobs
```

**GitLab parallel:**
```yaml
test:
  parallel:
    matrix:
      - NODE_VERSION: ['18', '20', '22']
        TEST_SUITE: ['unit', 'integration']
  script:
    - nvm use $NODE_VERSION
    - npm run test:$TEST_SUITE
```

### Test Splitting

**Jest sharding:**
```yaml
strategy:
  matrix:
    shard: [1, 2, 3, 4]
steps:
  - run: npm test -- --shard=${{ matrix.shard }}/4
```

**Playwright sharding:**
```yaml
strategy:
  matrix:
    shardIndex: [1, 2, 3, 4]
    shardTotal: [4]
steps:
  - run: npx playwright test --shard=${{ matrix.shardIndex }}/${{ matrix.shardTotal }}
```

**Pytest splitting:**
```yaml
strategy:
  matrix:
    group: [1, 2, 3, 4]
steps:
  - run: pytest --splits 4 --group ${{ matrix.group }}
```

### Conditional Execution

**Path-based:**
```yaml
jobs:
  frontend-test:
    if: contains(github.event.head_commit.modified, 'frontend/')

  backend-test:
    if: contains(github.event.head_commit.modified, 'backend/')
```

**GitLab rules:**
```yaml
frontend-test:
  rules:
    - changes:
        - frontend/**/*

backend-test:
  rules:
    - changes:
        - backend/**/*
```

---

## Build Optimization

### Incremental Builds

**Turb

orepo (monorepo):**
```yaml
- run: npx turbo run build test lint --filter=[HEAD^1]
```

**Nx (monorepo):**
```yaml
- run: npx nx affected --target=build --base=origin/main
```

### Compiler Optimizations

**TypeScript incremental:**
```json
{
  "compilerOptions": {
    "incremental": true,
    "tsBuildInfoFile": ".tsbuildinfo"
  }
}
```

**Cache tsbuildinfo:**
```yaml
- uses: actions/cache@v4
  with:
    path: .tsbuildinfo
    key: ts-build-${{ hashFiles('**/*.ts') }}
```

### Multi-stage Docker Builds

```dockerfile
# Build stage
FROM node:20 AS builder
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
CMD ["node", "dist/server.js"]
```

### Build Tool Configuration

**Webpack production mode:**
```javascript
module.exports = {
  mode: 'production',
  optimization: {
    minimize: true,
    splitChunks: {
      chunks: 'all'
    }
  }
}
```

**Vite optimization:**
```javascript
export default {
  build: {
    minify: 'terser',
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules')) {
            return 'vendor';
          }
        }
      }
    }
  }
}
```

---

## Test Optimization

### Test Categorization

**Run fast tests first:**
```yaml
jobs:
  unit-test:
    runs-on: ubuntu-latest
    steps:
      - run: npm run test:unit  # Fast (1-5 min)

  integration-test:
    needs: unit-test
    runs-on: ubuntu-latest
    steps:
      - run: npm run test:integration  # Medium (5-15 min)

  e2e-test:
    needs: [unit-test, integration-test]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - run: npm run test:e2e  # Slow (15-30 min)
```

### Selective Test Execution

**Run only changed:**
```yaml
- name: Get changed files
  id: changed
  run: |
    if [ "${{ github.event_name }}" == "pull_request" ]; then
      echo "files=$(git diff --name-only origin/${{ github.base_ref }}...HEAD | tr '\n' ' ')" >> $GITHUB_OUTPUT
    fi

- name: Run affected tests
  if: steps.changed.outputs.files
  run: npm test -- --findRelatedTests ${{ steps.changed.outputs.files }}
```

### Test Fixtures & Data

**Reuse test databases:**
```yaml
services:
  postgres:
    image: postgres:15
    env:
      POSTGRES_DB: testdb
      POSTGRES_PASSWORD: testpass
    options: >-
      --health-cmd pg_isready
      --health-interval 10s
      --health-timeout 5s
      --health-retries 5

steps:
  - run: npm test  # All tests share same DB
```

**Snapshot testing:**
```javascript
// Faster than full rendering tests
expect(component).toMatchSnapshot();
```

### Mock External Services

```javascript
// Instead of hitting real APIs
jest.mock('./api', () => ({
  fetchData: jest.fn(() => Promise.resolve(mockData))
}));
```

---

## Resource Management

### Job Timeouts

**Prevent hung jobs:**
```yaml
jobs:
  test:
    timeout-minutes: 30  # Default: 360 (6 hours)

  build:
    timeout-minutes: 15
```

**GitLab:**
```yaml
test:
  timeout: 30m  # Default: 1h
```

### Concurrency Control

**GitHub Actions:**
```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true  # Cancel old runs
```

**GitLab:**
```yaml
workflow:
  auto_cancel:
    on_new_commit: interruptible

job:
  interruptible: true
```

### Resource Allocation

**GitLab runner tags:**
```yaml
build:
  tags:
    - high-memory
    - ssd
```

**Kubernetes resource limits:**
```yaml
# GitLab Runner config
[[runners]]
  [runners.kubernetes]
    cpu_request = "1"
    cpu_limit = "2"
    memory_request = "2Gi"
    memory_limit = "4Gi"
```

---

## Monitoring & Metrics

### Track Key Metrics

**Build duration:**
```yaml
- name: Track duration
  run: |
    START=$SECONDS
    npm run build
    DURATION=$((SECONDS - START))
    echo "Build took ${DURATION}s"
```

**Cache hit rate:**
```yaml
- uses: actions/cache@v4
  id: cache
  with:
    path: node_modules
    key: ${{ hashFiles('package-lock.json') }}

- name: Cache stats
  run: |
    if [ "${{ steps.cache.outputs.cache-hit }}" == "true" ]; then
      echo "Cache hit!"
    else
      echo "Cache miss"
    fi
```

### Performance Regression Detection

**Compare against baseline:**
```yaml
- name: Benchmark
  run: npm run benchmark > results.json

- name: Compare
  run: |
    CURRENT=$(jq '.duration' results.json)
    BASELINE=120
    if [ $CURRENT -gt $((BASELINE * 120 / 100)) ]; then
      echo "Performance regression: ${CURRENT}s vs ${BASELINE}s baseline"
      exit 1
    fi
```

### External Monitoring

**DataDog CI Visibility:**
```yaml
- run: datadog-ci junit upload --service myapp junit-results.xml
```

**BuildPulse (flaky test detection):**
```yaml
- uses: buildpulse/buildpulse-action@v0.11.0
  with:
    account: myaccount
    repository: myrepo
    path: test-results/*.xml
```

---

## Optimization Checklist

### Quick Wins
- [ ] Enable dependency caching
- [ ] Remove unnecessary job dependencies
- [ ] Add job timeouts
- [ ] Enable concurrency cancellation
- [ ] Use `npm ci` instead of `npm install`

### Medium Impact
- [ ] Implement test sharding
- [ ] Use Docker layer caching
- [ ] Add path-based triggers
- [ ] Split slow test suites
- [ ] Use matrix builds for parallel execution

### Advanced
- [ ] Implement incremental builds (Nx, Turborepo)
- [ ] Use remote caching
- [ ] Optimize Docker images (multi-stage, distroless)
- [ ] Implement test impact analysis
- [ ] Set up distributed test execution

### Monitoring
- [ ] Track build duration trends
- [ ] Monitor cache hit rates
- [ ] Identify flaky tests
- [ ] Measure test execution time
- [ ] Set up performance regression alerts

---

## Performance Targets

**Build times:**
- Lint: < 1 minute
- Unit tests: < 5 minutes
- Integration tests: < 15 minutes
- E2E tests: < 30 minutes
- Full pipeline: < 20 minutes

**Resource usage:**
- Cache hit rate: > 80%
- Job success rate: > 95%
- Concurrent jobs: Balanced across available runners
- Queue time: < 2 minutes

**Cost optimization:**
- Build minutes used: Monitor monthly trends
- Storage: Keep artifacts < 7 days unless needed
- Self-hosted runners: Monitor utilization (target 60-80%)
