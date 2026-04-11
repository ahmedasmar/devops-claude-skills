#!/usr/bin/env python3
"""
Generate ArgoCD ApplicationSet manifests for multi-cluster deployments.
Supports Cluster, List, and Matrix generators (ArgoCD 3.x).
"""

import argparse
import sys
import yaml


APPLICATIONSET_TEMPLATE = """---
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: {name}
  namespace: argocd
spec:
  goTemplate: true
  goTemplateOptions: ["missingkey=error"]
  generators:
{generators}
  template:
    metadata:
      name: '{{{{.name}}}}-{name}'
      labels:
        environment: '{{{{.environment}}}}'
    spec:
      project: default
      source:
        repoURL: {repo_url}
        targetRevision: {target_revision}
        path: '{path}'
      destination:
        server: '{{{{.server}}}}'
        namespace: {namespace}
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
        syncOptions:
          - CreateNamespace=true
"""


def generate_cluster_generator(label_selector: str = "") -> str:
    """Generate Cluster generator."""
    selector = f"\n      selector:\n        matchLabels:\n          {label_selector}" if label_selector else ""
    return f"""  - cluster: {{{selector}}}"""


def generate_list_generator(clusters: list) -> str:
    """Generate List generator."""
    elements = "\n".join([f"      - name: {c['name']}\n        server: {c['server']}\n        environment: {c.get('environment', 'production')}"
                          for c in clusters])
    return f"""  - list:
      elements:
{elements}"""


def generate_matrix_generator(cluster_label: str, git_directories: list) -> str:
    """Generate Matrix generator (Cluster x Git directories)."""
    git_list = "\n".join([f"          - path: {d}" for d in git_directories])
    return f"""  - matrix:
      generators:
      - cluster:
          selector:
            matchLabels:
              environment: {cluster_label}
      - git:
          repoURL: https://github.com/example/apps
          revision: HEAD
          directories:
{git_list}"""


def main():
    parser = argparse.ArgumentParser(
        description='Generate ArgoCD ApplicationSet manifests',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Cluster generator (all clusters)
  python3 applicationset_generator.py cluster \\
    --name my-apps \\
    --repo-url https://github.com/org/repo \\
    --path apps/

  # List generator (specific clusters)
  python3 applicationset_generator.py list \\
    --name my-apps \\
    --clusters prod=https://prod.k8s.local,staging=https://staging.k8s.local

  # Matrix generator (cluster x directories)
  python3 applicationset_generator.py matrix \\
    --name my-apps \\
    --cluster-label production \\
    --directories app1,app2,app3
        """
    )

    parser.add_argument('generator_type', choices=['cluster', 'list', 'matrix'],
                       help='Generator type')
    parser.add_argument('--name', required=True, help='ApplicationSet name')
    parser.add_argument('--repo-url', default='https://github.com/example/repo',
                       help='Git repository URL')
    parser.add_argument('--path', default='apps/', help='Path in repository')
    parser.add_argument('--namespace', default='default', help='Target namespace')
    parser.add_argument('--target-revision', default='main', help='Git branch/tag')
    parser.add_argument('--cluster-label', help='Cluster label selector')
    parser.add_argument('--clusters', help='Cluster list (name=server,name=server)')
    parser.add_argument('--directories', help='Git directories (comma-separated)')
    parser.add_argument('--output', help='Output file')

    args = parser.parse_args()

    # Generate based on type
    if args.generator_type == 'cluster':
        generators = generate_cluster_generator(args.cluster_label or "")
    elif args.generator_type == 'list':
        if not args.clusters:
            print("❌ --clusters required for list generator")
            sys.exit(1)
        cluster_list = []
        for c in args.clusters.split(','):
            name, server = c.split('=')
            cluster_list.append({'name': name, 'server': server})
        generators = generate_list_generator(cluster_list)
    elif args.generator_type == 'matrix':
        if not args.cluster_label or not args.directories:
            print("❌ --cluster-label and --directories required for matrix generator")
            sys.exit(1)
        directories = args.directories.split(',')
        generators = generate_matrix_generator(args.cluster_label, directories)

    # Create ApplicationSet
    appset = APPLICATIONSET_TEMPLATE.format(
        name=args.name,
        generators=generators,
        repo_url=args.repo_url,
        target_revision=args.target_revision,
        path=args.path,
        namespace=args.namespace
    )

    # Output
    if args.output:
        with open(args.output, 'w') as f:
            f.write(appset)
        print(f"✅ ApplicationSet written to: {args.output}")
    else:
        print(appset)


if __name__ == '__main__':
    main()
