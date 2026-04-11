#!/usr/bin/env python3
"""
Audit secrets management in GitOps repositories.
Checks for plain secrets, SOPS, Sealed Secrets, and External Secrets Operator.
"""

import argparse
import sys
from pathlib import Path
from typing import List, Dict

try:
    import yaml
except ImportError:
    print("⚠️  'pyyaml' not found. Install with: pip install pyyaml")
    sys.exit(1)


class SecretAuditor:
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.findings = []

    def audit(self) -> Dict:
        """Run all secret audits."""
        print(f"🔐 Auditing secrets in: {self.repo_path}\n")

        self._check_plain_secrets()
        self._check_sops_config()
        self._check_sealed_secrets()
        self._check_external_secrets()

        return self._generate_report()

    def _check_plain_secrets(self):
        """Check for plain Kubernetes secrets."""
        secret_files = list(self.repo_path.rglob('*.yaml')) + list(self.repo_path.rglob('*.yml'))
        plain_secrets = []

        for sfile in secret_files:
            if '.git' in sfile.parts:
                continue

            try:
                with open(sfile) as f:
                    for doc in yaml.safe_load_all(f):
                        if doc and doc.get('kind') == 'Secret':
                            # Skip service account tokens
                            if doc.get('type') == 'kubernetes.io/service-account-token':
                                continue
                            # Check if it's encrypted
                            if 'sops' not in str(doc) and doc.get('kind') != 'SealedSecret':
                                plain_secrets.append(sfile.relative_to(self.repo_path))
            except:
                pass

        if plain_secrets:
            self.findings.append({
                'severity': 'HIGH',
                'type': 'Plain Secrets',
                'count': len(plain_secrets),
                'message': f"Found {len(plain_secrets)} plain Kubernetes Secret manifests",
                'recommendation': 'Encrypt with SOPS, Sealed Secrets, or use External Secrets Operator',
                'files': [str(f) for f in plain_secrets[:5]]
            })
        else:
            print("✅ No plain secrets found in Git")

    def _check_sops_config(self):
        """Check SOPS configuration."""
        sops_config = self.repo_path / '.sops.yaml'

        if sops_config.exists():
            print("✅ SOPS config found (.sops.yaml)")
            with open(sops_config) as f:
                config = yaml.safe_load(f)

            # Check for age keys
            if 'age' in str(config):
                print("  ✓ Using age encryption (recommended)")
            elif 'pgp' in str(config):
                print("  ⚠️  Using PGP (consider migrating to age)")
                self.findings.append({
                    'severity': 'LOW',
                    'type': 'SOPS Configuration',
                    'message': 'Using PGP encryption',
                    'recommendation': 'Migrate to age for better security and simplicity'
                })
        else:
            encrypted_files = list(self.repo_path.rglob('*.enc.yaml'))
            if encrypted_files:
                print("⚠️  SOPS encrypted files found but no .sops.yaml config")
                self.findings.append({
                    'severity': 'MEDIUM',
                    'type': 'SOPS Configuration',
                    'message': 'Encrypted files without .sops.yaml',
                    'recommendation': 'Add .sops.yaml for consistent encryption settings'
                })

    def _check_sealed_secrets(self):
        """Check Sealed Secrets usage."""
        sealed_secrets = list(self.repo_path.rglob('*sealedsecret*.yaml'))

        if sealed_secrets:
            print(f"✅ Found {len(sealed_secrets)} Sealed Secrets")

    def _check_external_secrets(self):
        """Check External Secrets Operator usage."""
        eso_files = list(self.repo_path.rglob('*externalsecret*.yaml')) + \
                   list(self.repo_path.rglob('*secretstore*.yaml'))

        if eso_files:
            print(f"✅ Found {len(eso_files)} External Secrets manifests")

    def _generate_report(self) -> Dict:
        """Generate audit report."""
        return {
            'findings': self.findings,
            'total_issues': len(self.findings),
            'high_severity': len([f for f in self.findings if f['severity'] == 'HIGH']),
            'medium_severity': len([f for f in self.findings if f['severity'] == 'MEDIUM']),
            'low_severity': len([f for f in self.findings if f['severity'] == 'LOW'])
        }


def main():
    parser = argparse.ArgumentParser(
        description='Audit secrets management in GitOps repositories',
        epilog="""
Examples:
  # Audit current directory
  python3 secret_audit.py .

  # Audit specific repo
  python3 secret_audit.py /path/to/gitops-repo

Checks:
  - Plain Kubernetes Secrets in Git (HIGH risk)
  - SOPS configuration and encryption method
  - Sealed Secrets usage
  - External Secrets Operator usage
        """
    )

    parser.add_argument('repo_path', help='Path to GitOps repository')

    args = parser.parse_args()

    auditor = SecretAuditor(args.repo_path)
    report = auditor.audit()

    # Print summary
    print("\n" + "="*60)
    print("📊 Audit Summary")
    print("="*60)

    if report['findings']:
        print(f"\n🔴 HIGH: {report['high_severity']}")
        print(f"🟡 MEDIUM: {report['medium_severity']}")
        print(f"🟢 LOW: {report['low_severity']}")

        print("\n📋 Findings:\n")
        for f in report['findings']:
            icon = {'HIGH': '🔴', 'MEDIUM': '🟡', 'LOW': '🟢'}[f['severity']]
            print(f"{icon} [{f['severity']}] {f['type']}")
            print(f"   {f['message']}")
            print(f"   → {f['recommendation']}")
            if 'files' in f and f['files']:
                print(f"   Files: {', '.join(f['files'][:3])}")
            print()
    else:
        print("\n✅ No security issues found!")

    sys.exit(1 if report['high_severity'] > 0 else 0)


if __name__ == '__main__':
    main()
