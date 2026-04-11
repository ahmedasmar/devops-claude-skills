# CI/CD Troubleshooting

Comprehensive guide to diagnosing and resolving common CI/CD pipeline issues.

## Table of Contents

- [Pipeline Failures](#pipeline-failures)
- [Dependency Issues](#dependency-issues)
- [Docker & Container Problems](#docker--container-problems)
- [Authentication & Permissions](#authentication--permissions)
- [Performance Issues](#performance-issues)
- [Platform-Specific Issues](#platform-specific-issues)

---

## Pipeline Failures

### Workflow Not Triggering

**GitHub Actions:**

**Symptoms:** Workflow doesn't run on push/PR

**Common causes:**
1. Workflow file in wrong location (must be `.github/workflows/`)
2. Invalid YAML syntax
3. Branch/path filters excluding the changes
4. Workflow disabled in repository settings

**Diagnostics:**
```bash
# Validate YAML
yamllint .github/workflows/ci.yml

# Check if workflow is disabled
gh workflow list --repo owner/repo
```

**Solutions:**
```yaml
# Check trigger configuration
on:
  push:
    branches: [main]  # Ensure your branch matches
    paths-ignore:
      - 'docs/**'  # May be excluding your changes

# Enable workflow
gh workflow enable ci.yml --repo owner/repo
```

**GitLab CI:**

**Symptoms:** Pipeline doesn't start

**Diagnostics:**
```bash
# Validate .gitlab-ci.yml
gl-ci-lint < .gitlab-ci.yml

# Check CI/CD settings
# Project > Settings > CI/CD > General pipelines
```

**Solutions:**
- Check if CI/CD is enabled for the project
- Verify `.gitlab-ci.yml` is in repository root
- Check pipeline must succeed setting isn't blocking
- Review `only`/`except` or `rules` configuration

### Jobs Failing Intermittently

**Symptoms:** Same job passes sometimes, fails others

**Common causes:**
1. Flaky tests
2. Race conditions
3. Network timeouts
4. Resource constraints
5. Time-dependent tests

**Identify flaky tests:**
```yaml
# GitHub Actions - Run multiple times
strategy:
  matrix:
    attempt: [1, 2, 3, 4, 5]
steps:
  - run: npm test
```

**Solutions:**
```javascript
// Add retries to flaky tests
jest.retryTimes(3);

// Increase timeouts
jest.setTimeout(30000);

// Fix race conditions
await waitFor(() => expect(element).toBeInDocument(), {
  timeout: 5000
});
```

**Network retry pattern:**
```yaml
- name: Install with retry
  uses: nick-invision/retry@v2
  with:
    timeout_minutes: 10
    max_attempts: 3
    command: npm ci
```

### Timeout Errors

**Symptoms:** "Job exceeded maximum time" or similar

**Solutions:**
```yaml
# GitHub Actions - Increase timeout
jobs:
  build:
    timeout-minutes: 60  # Default: 360

# GitLab CI
test:
  timeout: 2h  # Default: 1h
```

**Optimize long-running jobs:**
- Add caching for dependencies
- Split tests into parallel jobs
- Use faster runners
- Identify and optimize slow tests

### Exit Code Errors

**Symptoms:** "Process completed with exit code 1"

**Diagnostics:**
```yaml
# Add verbose logging
- run: npm test -- --verbose

# Check specific exit codes
- run: |
    npm test
    EXIT_CODE=$?
    echo "Exit code: $EXIT_CODE"
    if [ $EXIT_CODE -eq 127 ]; then
      echo "Command not found"
    elif [ $EXIT_CODE -eq 1 ]; then
      echo "General error"
    fi
    exit $EXIT_CODE
```

**Common exit codes:**
- `1`: General error
- `2`: Misuse of shell command
- `126`: Command cannot execute
- `127`: Command not found
- `130`: Terminated by Ctrl+C
- `137`: Killed (OOM)
- `143`: Terminated (SIGTERM)

---

## Dependency Issues

### "Module not found" or "Cannot find package"

**Symptoms:** Build fails with missing dependency error

**Causes:**
1. Missing dependency in `package.json`
2. Cache corruption
3. Lock file out of sync
4. Private package access issues

**Solutions:**
```yaml
# Clear cache and reinstall
- run: rm -rf node_modules package-lock.json
- run: npm install

# Use npm ci for clean install
- run: npm ci

# Clear GitHub Actions cache
# Settings > Actions > Caches > Delete specific cache

# GitLab - clear cache
cache:
  key: $CI_COMMIT_REF_SLUG
  policy: push  # Force new cache
```

### Version Conflicts

**Symptoms:** Dependency resolution errors, peer dependency warnings

**Diagnostics:**
```bash
# Check for conflicts
npm ls
npm outdated

# View dependency tree
npm list --depth=1
```

**Solutions:**
```json
// Use overrides (package.json)
{
  "overrides": {
    "problematic-package": "2.0.0"
  }
}

// Or resolutions (Yarn)
{
  "resolutions": {
    "problematic-package": "2.0.0"
  }
}
```

### Private Package Access

**Symptoms:** "401 Unauthorized" or "404 Not Found" for private packages

**GitHub Packages:**
```yaml
- run: |
    echo "@myorg:registry=https://npm.pkg.github.com" >> .npmrc
    echo "//npm.pkg.github.com/:_authToken=${{ secrets.GITHUB_TOKEN }}" >> .npmrc
- run: npm ci
```

**npm Registry:**
```yaml
- run: echo "//registry.npmjs.org/:_authToken=${{ secrets.NPM_TOKEN }}" >> .npmrc
- run: npm ci
```

**GitLab Package Registry:**
```yaml
before_script:
  - echo "@mygroup:registry=${CI_API_V4_URL}/projects/${CI_PROJECT_ID}/packages/npm/" >> .npmrc
  - echo "${CI_API_V4_URL#https?}/projects/${CI_PROJECT_ID}/packages/npm/:_authToken=${CI_JOB_TOKEN}" >> .npmrc
```

---

## Docker & Container Problems

### "Cannot connect to Docker daemon"

**Symptoms:** Docker commands fail with connection error

**GitHub Actions:**
```yaml
# Ensure Docker is available
runs-on: ubuntu-latest  # Has Docker pre-installed

steps:
  - run: docker ps  # Test Docker access
```

**GitLab CI:**
```yaml
# Use Docker-in-Docker
image: docker:latest
services:
  - docker:dind

variables:
  DOCKER_HOST: tcp://docker:2376
  DOCKER_TLS_CERTDIR: "/certs"
  DOCKER_TLS_VERIFY: 1
  DOCKER_CERT_PATH: "$DOCKER_TLS_CERTDIR/client"
```

### Image Pull Errors

**Symptoms:** "Error response from daemon: pull access denied" or timeout

**Solutions:**
```yaml
# GitHub Actions - Login to registry
- uses: docker/login-action@v3
  with:
    registry: ghcr.io
    username: ${{ github.actor }}
    password: ${{ secrets.GITHUB_TOKEN }}

# Or for Docker Hub
- uses: docker/login-action@v3
  with:
    username: ${{ secrets.DOCKERHUB_USERNAME }}
    password: ${{ secrets.DOCKERHUB_TOKEN }}

# Add retry logic
- run: |
    for i in {1..3}; do
      docker pull myimage:latest && break
      sleep 5
    done
```

### "No space left on device"

**Symptoms:** Docker build fails with disk space error

**Solutions:**
```yaml
# GitHub Actions - Clean up space
- run: docker system prune -af --volumes

# Or use built-in action
- uses: jlumbroso/free-disk-space@main
  with:
    tool-cache: true
    android: true
    dotnet: true

# GitLab - configure runner
[[runners]]
  [runners.docker]
    volumes = ["/var/run/docker.sock:/var/run/docker.sock", "/cache"]
  [runners.docker.tmpfs]
    "/tmp" = "rw,noexec"
```

### Multi-platform Build Issues

**Symptoms:** Build fails for ARM/different architecture

**Solution:**
```yaml
- uses: docker/setup-qemu-action@v3

- uses: docker/setup-buildx-action@v3

- uses: docker/build-push-action@v5
  with:
    platforms: linux/amd64,linux/arm64
    context: .
    push: false
```

---

## Authentication & Permissions

### "Permission denied" or "403 Forbidden"

**GitHub Actions:**

**Symptoms:** Cannot push, create release, or access API

**Solutions:**
```yaml
# Add necessary permissions
permissions:
  contents: write  # For pushing tags/releases
  pull-requests: write  # For commenting on PRs
  packages: write  # For pushing packages
  id-token: write  # For OIDC

# Check GITHUB_TOKEN permissions
- run: |
    curl -H "Authorization: token ${{ secrets.GITHUB_TOKEN }}" \
      https://api.github.com/repos/${{ github.repository }}
```

**GitLab CI:**

**Symptoms:** Cannot push to repository or access API

**Solutions:**
```yaml
# Use CI_JOB_TOKEN for API access
script:
  - 'curl --header "JOB-TOKEN: $CI_JOB_TOKEN" "${CI_API_V4_URL}/projects"'

# Or use personal/project access token
variables:
  GIT_STRATEGY: clone
before_script:
  - git config --global user.email "ci@example.com"
  - git config --global user.name "CI Bot"
```

### Git Push Failures

**Symptoms:** "failed to push some refs" or "protected branch"

**Solutions:**
```yaml
# GitHub Actions - Check branch protection
# Settings > Branches > Branch protection rules

# Allow bypass
permissions:
  contents: write

# Or use PAT with admin access
- uses: actions/checkout@v4
  with:
    token: ${{ secrets.ADMIN_PAT }}

# GitLab - Grant permissions
# Settings > Repository > Protected Branches
# Add CI/CD role with push permission
```

### AWS Credentials Issues

**Symptoms:** "Unable to locate credentials"

**Solutions:**
```yaml
# Using OIDC (recommended)
- uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::123456789:role/GitHubActionsRole
    aws-region: us-east-1

# Using secrets (legacy)
- uses: aws-actions/configure-aws-credentials@v4
  with:
    aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
    aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
    aws-region: us-east-1

# Test credentials
- run: aws sts get-caller-identity
```

---

## Performance Issues

### Slow Pipeline Execution

**Diagnostics:**
```bash
# GitHub - View timing
gh run view <run-id> --log

# Identify slow steps
# Each step shows duration in UI
```

**Solutions:**
- See [optimization.md](optimization.md) for comprehensive guide
- Add dependency caching
- Parallelize independent jobs
- Use faster runners
- Reduce test scope on PRs

### Cache Not Working

**Symptoms:** Cache always misses, builds still slow

**Diagnostics:**
```yaml
- uses: actions/cache@v4
  id: cache
  with:
    path: node_modules
    key: ${{ hashFiles('**/package-lock.json') }}

- run: echo "Cache hit: ${{ steps.cache.outputs.cache-hit }}"
```

**Common issues:**
1. Key changes every time
2. Path doesn't exist
3. Cache size exceeds limit
4. Cache evicted (LRU after 7 days on GitHub)

**Solutions:**
```yaml
# Use consistent key
key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}

# Add restore-keys for partial match
restore-keys: |
  ${{ runner.os }}-node-

# Check cache size
- run: du -sh node_modules
```

---

## Platform-Specific Issues

### GitHub Actions

**"Resource not accessible by integration":**
```yaml
# Add required permission
permissions:
  issues: write  # Or whatever resource you're accessing
```

**"Workflow is not shared":**
- Reusable workflows must be in `.github/workflows/`
- Repository must be public or org member
- Check workflow access settings

**"No runner available":**
- Self-hosted: Check runner is online and has matching labels
- GitHub-hosted: May hit concurrent job limit (check usage)

### GitLab CI

**"This job is stuck":**
- No runner available with matching tags
- All runners are busy
- Runner not configured for this project

**Solutions:**
```yaml
# Remove tags to use any available runner
job:
  tags: []

# Or check runner configuration
# Settings > CI/CD > Runners
```

**"Job failed (system failure)":**
- Runner disconnected
- Resource limits exceeded
- Infrastructure issue

**Check runner logs:**
```bash
# On runner host
journalctl -u gitlab-runner -f
```

---

## Debugging Techniques

### Enable Debug Logging

**GitHub Actions:**
```yaml
# Repository > Settings > Secrets > Add:
# ACTIONS_RUNNER_DEBUG = true
# ACTIONS_STEP_DEBUG = true
```

**GitLab CI:**
```yaml
variables:
  CI_DEBUG_TRACE: "true"  # Caution: May expose secrets!
```

### Interactive Debugging

**GitHub Actions:**
```yaml
# Add tmate for SSH access
- uses: mxschmitt/action-tmate@v3
  if: failure()
```

**Local reproduction:**
```bash
# Use act to run GitHub Actions locally
act -j build

# Or nektos/act for Docker
docker run -v $(pwd):/workspace -it nektos/act -j build
```

### Reproduce Locally

```bash
# GitHub Actions - Use same Docker image
docker run -it ubuntu:latest bash

# Install dependencies and test
apt-get update && apt-get install -y nodejs npm
npm ci
npm test
```

---

## Prevention Strategies

### Pre-commit Checks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: check-yaml
      - id: check-added-large-files

  - repo: local
    hooks:
      - id: tests
        name: Run tests
        entry: npm test
        language: system
        pass_filenames: false
```

### CI/CD Health Monitoring

Use the `gh` CLI to check pipeline health:
```bash
gh run list --limit 20
gh workflow list
```

### Regular Maintenance

- [ ] Monthly: Review failed job patterns
- [ ] Monthly: Update actions/dependencies
- [ ] Quarterly: Audit pipeline efficiency
- [ ] Quarterly: Review and clean old caches
- [ ] Yearly: Major version updates

---

## Getting Help

**GitHub Actions:**
- Community Forum: https://github.community
- Documentation: https://docs.github.com/actions
- Status: https://www.githubstatus.com

**GitLab CI:**
- Forum: https://forum.gitlab.com
- Documentation: https://docs.gitlab.com/ee/ci
- Status: https://status.gitlab.com

**General CI/CD:**
- Stack Overflow: Tag [github-actions] or [gitlab-ci]
- Reddit: r/devops, r/cicd
