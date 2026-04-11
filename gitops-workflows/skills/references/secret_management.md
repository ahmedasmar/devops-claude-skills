# Secrets Management in GitOps (2024-2025)

## Overview

**Never commit plain secrets to Git.** Use encryption or external secret stores.

## Solutions Comparison

| Solution | Type | Complexity | Best For | 2025 Trend |
|----------|------|------------|----------|------------|
| **Sealed Secrets** | Encrypted in Git | Low | Simple, GitOps-first | Stable |
| **External Secrets Operator** | External store | Medium | Cloud-native, dynamic | ↗️ Growing |
| **SOPS + age** | Encrypted in Git | Medium | Flexible, Git-friendly | ↗️ Preferred over PGP |

## 1. Sealed Secrets

**How it works**: Public key encryption, controller decrypts in-cluster

**Setup**:
```bash
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml
```

**Usage**:
```bash
# Create sealed secret
kubectl create secret generic my-secret --dry-run=client -o yaml --from-literal=password=supersecret | \
  kubeseal -o yaml > sealed-secret.yaml

# Commit to Git
git add sealed-secret.yaml
git commit -m "Add sealed secret"
```

**Pros**: Simple, GitOps-native, no external dependencies
**Cons**: Key rotation complexity, static secrets only

## 2. External Secrets Operator (ESO)

**Latest Version**: v0.20.2 (2024-2025)

**Supported Providers**:
- AWS Secrets Manager
- Azure Key Vault
- Google Secret Manager
- HashiCorp Vault
- 1Password
- Doppler

**Setup**:
```bash
helm install external-secrets external-secrets/external-secrets -n external-secrets-system --create-namespace
```

**Usage**:
```yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: aws-secret-store
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-east-1
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets-sa
---
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: my-secret
spec:
  secretStoreRef:
    name: aws-secret-store
  target:
    name: my-app-secret
  data:
  - secretKey: password
    remoteRef:
      key: prod/my-app/password
```

**Pros**: Dynamic secrets, cloud-native, automatic rotation
**Cons**: External dependency, requires cloud secret store

**2025 Recommendation**: Growing preference over Sealed Secrets

## 3. SOPS + age

**Recommended over PGP as of 2024-2025**

**Setup age**:
```bash
# Install age
brew install age  # macOS
apt install age   # Ubuntu

# Generate key
age-keygen -o key.txt
# Public key: age1...
```

**Setup SOPS**:
```bash
# Install SOPS
brew install sops

# Create .sops.yaml
cat <<EOF > .sops.yaml
creation_rules:
  - path_regex: .*.yaml
    encrypted_regex: ^(data|stringData)$
    age: age1ql3z7hjy54pw3hyww5ayyfg7zqgvc7w3j2elw8zmrj2kg5sfn9aqmcac8p
EOF
```

**Encrypt secrets**:
```bash
# Create secret
kubectl create secret generic my-secret --dry-run=client -o yaml --from-literal=password=supersecret > secret.yaml

# Encrypt with SOPS
sops -e secret.yaml > secret.enc.yaml

# Commit encrypted version
git add secret.enc.yaml .sops.yaml
```

**Flux Integration**:
```yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: app
spec:
  decryption:
    provider: sops
    secretRef:
      name: sops-age
```

**Pros**: Git-friendly, flexible, age is simpler than PGP
**Cons**: Manual encryption step, key management

## Best Practices (2024-2025)

### 1. Key Rotation
**Sealed Secrets**: Rotate annually, maintain old keys for decryption
**ESO**: Automatic with cloud providers
**SOPS**: Re-encrypt when rotating age keys

### 2. Access Control
- Never commit `.sops` age key to Git
- Use separate keys per environment
- Store age keys in CI/CD secrets
- Use RBAC for Secret access

### 3. Encryption Scope
**SOPS .sops.yaml**:
```yaml
creation_rules:
  - path_regex: production/.*
    encrypted_regex: ^(data|stringData)$
    age: age1prod...
  - path_regex: staging/.*
    encrypted_regex: ^(data|stringData)$
    age: age1staging...
```

### 4. Git Pre-commit Hook
Prevent committing plain secrets:
```bash
#!/bin/bash
# .git/hooks/pre-commit
if git diff --cached --name-only | grep -E 'secret.*\.yaml$'; then
  echo "⚠️  Potential secret file detected"
  echo "Ensure it's encrypted with SOPS"
  exit 1
fi
```

### 5. ArgoCD 3.0 Recommendation
**Use secrets operators** (ESO preferred), avoid config management plugins for secrets

## Decision Guide

**Choose Sealed Secrets if**:
- ✅ Simple GitOps workflow
- ✅ Static secrets
- ✅ No external dependencies wanted
- ✅ Small team

**Choose External Secrets Operator if**:
- ✅ Already using cloud secret stores
- ✅ Need secret rotation
- ✅ Dynamic secrets
- ✅ Enterprise compliance

**Choose SOPS + age if**:
- ✅ Git-centric workflow
- ✅ Want flexibility
- ✅ Multi-cloud
- ✅ Prefer open standards

## 2025 Trend Summary

**Growing**: External Secrets Operator, SOPS+age
**Stable**: Sealed Secrets (still widely used)
**Declining**: PGP encryption (age preferred)
**Emerging**: age encryption as standard (simpler than PGP)
