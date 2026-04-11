#!/usr/bin/env python3
"""
Validate GitOps repository structure, manifests, and best practices.
Supports both monorepo and polyrepo patterns with Kustomize and Helm.
"""

import argparse
import sys
import os
import glob
from typing import Dict, List, Any, Tuple
from pathlib import Path

try:
    import yaml
except ImportError:
    print("⚠️  Warning: 'pyyaml' library not found. Install with: pip install pyyaml")
    sys.exit(1)


class GitOpsRepoValidator:
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path).resolve()
        if not self.repo_path.exists():
            raise ValueError(f"Path does not exist: {repo_path}")

        self.issues = []
        self.warnings = []
        self.recommendations = []

    def validate(self) -> Dict[str, List[str]]:
        """Run all validations."""
        print(f"🔍 Validating GitOps repository: {self.repo_path}\n")

        # Structure validations
        self._check_repository_structure()
        self._check_kustomization_files()
        self._check_yaml_syntax()
        self._check_best_practices()
        self._check_secrets_management()

        return {
            'issues': self.issues,
            'warnings': self.warnings,
            'recommendations': self.recommendations
        }

    def _check_repository_structure(self):
        """Check repository structure and organization."""
        print("📁 Checking repository structure...")

        # Check for common patterns
        has_apps = (self.repo_path / 'apps').exists()
        has_clusters = (self.repo_path / 'clusters').exists()
        has_infrastructure = (self.repo_path / 'infrastructure').exists()
        has_base = (self.repo_path / 'base').exists()
        has_overlays = (self.repo_path / 'overlays').exists()

        if not any([has_apps, has_clusters, has_infrastructure, has_base]):
            self.warnings.append("No standard directory structure detected (apps/, clusters/, infrastructure/, base/)")
            self.recommendations.append("Consider organizing with: apps/ (applications), infrastructure/ (cluster config), clusters/ (per-cluster)")

        # Check for Flux bootstrap (if Flux)
        flux_system = self.repo_path / 'clusters' / 'flux-system'
        if flux_system.exists():
            print("  ✓ Flux bootstrap detected")
            if not (flux_system / 'gotk-components.yaml').exists():
                self.warnings.append("Flux bootstrap directory exists but gotk-components.yaml not found")

        # Check for ArgoCD bootstrap (if ArgoCD)
        argocd_patterns = list(self.repo_path.rglob('*argocd-*.yaml'))
        if argocd_patterns:
            print("  ✓ ArgoCD manifests detected")

    def _check_kustomization_files(self):
        """Check Kustomization files for validity."""
        print("\n🔧 Checking Kustomization files...")

        kustomization_files = list(self.repo_path.rglob('kustomization.yaml')) + \
                             list(self.repo_path.rglob('kustomization.yml'))

        if not kustomization_files:
            self.warnings.append("No kustomization.yaml files found")
            return

        print(f"  Found {len(kustomization_files)} kustomization files")

        for kfile in kustomization_files:
            try:
                with open(kfile, 'r') as f:
                    content = yaml.safe_load(f)

                if not content:
                    self.issues.append(f"Empty kustomization file: {kfile.relative_to(self.repo_path)}")
                    continue

                # Check for required fields
                if 'resources' not in content and 'bases' not in content and 'components' not in content:
                    self.warnings.append(f"Kustomization has no resources/bases: {kfile.relative_to(self.repo_path)}")

                # Check for deprecated 'bases' (Kustomize 5.7+)
                if 'bases' in content:
                    self.warnings.append(f"Using deprecated 'bases' field: {kfile.relative_to(self.repo_path)}")
                    self.recommendations.append("Migrate 'bases:' to 'resources:' (Kustomize 5.0+)")

            except yaml.YAMLError as e:
                self.issues.append(f"Invalid YAML in {kfile.relative_to(self.repo_path)}: {e}")
            except Exception as e:
                self.issues.append(f"Error reading {kfile.relative_to(self.repo_path)}: {e}")

    def _check_yaml_syntax(self):
        """Check YAML files for syntax errors."""
        print("\n📝 Checking YAML syntax...")

        yaml_files = list(self.repo_path.rglob('*.yaml')) + list(self.repo_path.rglob('*.yml'))

        # Exclude certain directories
        exclude_dirs = {'.git', 'node_modules', 'vendor', '.github'}
        yaml_files = [f for f in yaml_files if not any(ex in f.parts for ex in exclude_dirs)]

        syntax_errors = 0
        for yfile in yaml_files:
            try:
                with open(yfile, 'r') as f:
                    yaml.safe_load_all(f)
            except yaml.YAMLError as e:
                self.issues.append(f"YAML syntax error in {yfile.relative_to(self.repo_path)}: {e}")
                syntax_errors += 1

        if syntax_errors == 0:
            print(f"  ✓ All {len(yaml_files)} YAML files are valid")
        else:
            print(f"  ✗ {syntax_errors} YAML files have syntax errors")

    def _check_best_practices(self):
        """Check GitOps best practices."""
        print("\n✨ Checking best practices...")

        # Check for namespace definitions
        namespace_files = list(self.repo_path.rglob('*namespace*.yaml'))
        if not namespace_files:
            self.recommendations.append("No namespace definitions found. Consider explicitly defining namespaces.")

        # Check for image tags (not 'latest')
        all_yamls = list(self.repo_path.rglob('*.yaml')) + list(self.repo_path.rglob('*.yml'))
        latest_tag_count = 0

        for yfile in all_yamls:
            try:
                with open(yfile, 'r') as f:
                    content = f.read()
                    if ':latest' in content or 'image: latest' in content:
                        latest_tag_count += 1
            except:
                pass

        if latest_tag_count > 0:
            self.warnings.append(f"Found {latest_tag_count} files using ':latest' image tag")
            self.recommendations.append("Pin image tags to specific versions or digests for reproducibility")

        # Check for resource limits
        deployment_files = [f for f in all_yamls if 'deployment' in str(f).lower() or 'statefulset' in str(f).lower()]
        missing_limits = 0

        for dfile in deployment_files:
            try:
                with open(dfile, 'r') as f:
                    content = yaml.safe_load_all(f)
                    for doc in content:
                        if not doc or doc.get('kind') not in ['Deployment', 'StatefulSet']:
                            continue

                        containers = doc.get('spec', {}).get('template', {}).get('spec', {}).get('containers', [])
                        for container in containers:
                            if 'resources' not in container or 'limits' not in container.get('resources', {}):
                                missing_limits += 1
                                break
            except:
                pass

        if missing_limits > 0:
            self.recommendations.append(f"{missing_limits} Deployments/StatefulSets missing resource limits")

    def _check_secrets_management(self):
        """Check for secrets management practices."""
        print("\n🔐 Checking secrets management...")

        # Check for plain Kubernetes secrets
        secret_files = list(self.repo_path.rglob('*secret*.yaml'))
        plain_secrets = []

        for sfile in secret_files:
            try:
                with open(sfile, 'r') as f:
                    for doc in yaml.safe_load_all(f):
                        if doc and doc.get('kind') == 'Secret' and doc.get('type') != 'kubernetes.io/service-account-token':
                            # Check if it's a SealedSecret or ExternalSecret
                            if doc.get('kind') not in ['SealedSecret'] and 'external-secrets.io' not in doc.get('apiVersion', ''):
                                plain_secrets.append(sfile.relative_to(self.repo_path))
            except:
                pass

        if plain_secrets:
            self.issues.append(f"Found {len(plain_secrets)} plain Kubernetes Secret manifests in Git")
            self.recommendations.append("Use Sealed Secrets, External Secrets Operator, or SOPS for secrets management")
            for s in plain_secrets[:3]:  # Show first 3
                self.issues.append(f"  - {s}")

        # Check for SOPS configuration
        sops_config = self.repo_path / '.sops.yaml'
        if sops_config.exists():
            print("  ✓ SOPS configuration found (.sops.yaml)")

        # Check for Sealed Secrets
        sealed_secrets = list(self.repo_path.rglob('*sealedsecret*.yaml'))
        if sealed_secrets:
            print(f"  ✓ Found {len(sealed_secrets)} SealedSecret manifests")

        # Check for External Secrets
        external_secrets = [f for f in self.repo_path.rglob('*.yaml')
                           if 'externalsecret' in str(f).lower() or 'secretstore' in str(f).lower()]
        if external_secrets:
            print(f"  ✓ Found {len(external_secrets)} External Secrets manifests")

        if not sops_config.exists() and not sealed_secrets and not external_secrets and plain_secrets:
            self.recommendations.append("No secrets management solution detected. Consider implementing Sealed Secrets, ESO, or SOPS+age")


def main():
    parser = argparse.ArgumentParser(
        description='Validate GitOps repository structure and manifests',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate current directory
  python3 validate_gitops_repo.py .

  # Validate specific repository
  python3 validate_gitops_repo.py /path/to/gitops-repo

  # Show only issues (no warnings)
  python3 validate_gitops_repo.py . --errors-only

Checks:
  - Repository structure (monorepo/polyrepo patterns)
  - Kustomization file validity
  - YAML syntax errors
  - Best practices (image tags, resource limits, namespaces)
  - Secrets management (detect plain secrets, check for SOPS/Sealed Secrets/ESO)
        """
    )

    parser.add_argument('repo_path', help='Path to GitOps repository')
    parser.add_argument('--errors-only', action='store_true', help='Show only errors, not warnings')

    args = parser.parse_args()

    try:
        validator = GitOpsRepoValidator(args.repo_path)
        results = validator.validate()

        # Print summary
        print("\n" + "="*60)
        print("📊 Validation Summary")
        print("="*60)

        if results['issues']:
            print(f"\n❌ Issues ({len(results['issues'])}):")
            for issue in results['issues']:
                print(f"  • {issue}")

        if results['warnings'] and not args.errors_only:
            print(f"\n⚠️  Warnings ({len(results['warnings'])}):")
            for warning in results['warnings']:
                print(f"  • {warning}")

        if results['recommendations'] and not args.errors_only:
            print(f"\n💡 Recommendations ({len(results['recommendations'])}):")
            for rec in results['recommendations']:
                print(f"  → {rec}")

        if not results['issues'] and not results['warnings']:
            print("\n✅ No issues found! Repository structure looks good.")

        # Exit code
        sys.exit(1 if results['issues'] else 0)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
