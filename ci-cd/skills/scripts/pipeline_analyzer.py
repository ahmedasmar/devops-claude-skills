#!/usr/bin/env python3
"""
CI/CD Pipeline Performance Analyzer

Analyzes CI/CD pipeline configuration and execution to identify performance
bottlenecks, caching opportunities, and optimization recommendations.

Usage:
    # Analyze GitHub Actions workflow
    python3 pipeline_analyzer.py --platform github --workflow .github/workflows/ci.yml

    # Analyze GitLab CI pipeline
    python3 pipeline_analyzer.py --platform gitlab --config .gitlab-ci.yml

    # Analyze recent workflow runs
    python3 pipeline_analyzer.py --platform github --repo owner/repo --analyze-runs 10
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import yaml

class PipelineAnalyzer:
    def __init__(self, platform: str, **kwargs):
        self.platform = platform.lower()
        self.config = kwargs
        self.findings = []
        self.optimizations = []
        self.metrics = {}

    def analyze_github_workflow(self, workflow_file: str) -> Dict:
        """Analyze GitHub Actions workflow file"""
        print(f"🔍 Analyzing GitHub Actions workflow: {workflow_file}")

        if not os.path.exists(workflow_file):
            return self._error(f"Workflow file not found: {workflow_file}")

        try:
            with open(workflow_file, 'r') as f:
                workflow = yaml.safe_load(f)

            # Analyze workflow structure
            self._check_workflow_triggers(workflow)
            self._check_caching_strategy(workflow, 'github')
            self._check_job_parallelization(workflow, 'github')
            self._check_dependency_management(workflow, 'github')
            self._check_matrix_strategy(workflow)
            self._check_artifact_usage(workflow)
            self._analyze_action_versions(workflow)

            return self._generate_report()

        except yaml.YAMLError as e:
            return self._error(f"Invalid YAML: {e}")
        except Exception as e:
            return self._error(f"Analysis failed: {e}")

    def analyze_gitlab_pipeline(self, config_file: str) -> Dict:
        """Analyze GitLab CI pipeline configuration"""
        print(f"🔍 Analyzing GitLab CI pipeline: {config_file}")

        if not os.path.exists(config_file):
            return self._error(f"Config file not found: {config_file}")

        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)

            # Analyze pipeline structure
            self._check_caching_strategy(config, 'gitlab')
            self._check_job_parallelization(config, 'gitlab')
            self._check_dependency_management(config, 'gitlab')
            self._check_gitlab_specific_features(config)

            return self._generate_report()

        except yaml.YAMLError as e:
            return self._error(f"Invalid YAML: {e}")
        except Exception as e:
            return self._error(f"Analysis failed: {e}")

    def _check_workflow_triggers(self, workflow: Dict):
        """Check workflow trigger configuration"""
        triggers = workflow.get('on', {})

        if isinstance(triggers, list):
            trigger_types = triggers
        elif isinstance(triggers, dict):
            trigger_types = list(triggers.keys())
        else:
            trigger_types = [triggers] if triggers else []

        # Check for overly broad triggers
        if 'push' in trigger_types:
            push_config = triggers.get('push', {}) if isinstance(triggers, dict) else {}
            if not push_config or not push_config.get('branches'):
                self.findings.append("Workflow triggers on all push events (no branch filter)")
                self.optimizations.append(
                    "Add branch filters to 'push' trigger to reduce unnecessary runs:\n"
                    "  on:\n"
                    "    push:\n"
                    "      branches: [main, develop]"
                )

        # Check for path filters
        if 'pull_request' in trigger_types:
            pr_config = triggers.get('pull_request', {}) if isinstance(triggers, dict) else {}
            if not pr_config.get('paths') and not pr_config.get('paths-ignore'):
                self.optimizations.append(
                    "Consider adding path filters to skip unnecessary PR runs:\n"
                    "  pull_request:\n"
                    "    paths-ignore:\n"
                    "      - 'docs/**'\n"
                    "      - '**.md'"
                )

    def _check_caching_strategy(self, config: Dict, platform: str):
        """Check for dependency caching"""
        has_cache = False

        if platform == 'github':
            jobs = config.get('jobs', {})
            for job_name, job in jobs.items():
                steps = job.get('steps', [])
                for step in steps:
                    if isinstance(step, dict) and step.get('uses', '').startswith('actions/cache'):
                        has_cache = True
                        break

            if not has_cache:
                self.findings.append("No dependency caching detected")
                self.optimizations.append(
                    "Add dependency caching to speed up builds:\n"
                    "  - uses: actions/cache@v4\n"
                    "    with:\n"
                    "      path: |\n"
                    "        ~/.cargo\n"
                    "        ~/.npm\n"
                    "        ~/.cache/pip\n"
                    "      key: ${{ runner.os }}-deps-${{ hashFiles('**/package-lock.json') }}"
                )

        elif platform == 'gitlab':
            cache_config = config.get('cache', {})
            job_has_cache = False

            # Check global cache
            if cache_config:
                has_cache = True

            # Check job-level cache
            for key, value in config.items():
                if isinstance(value, dict) and 'script' in value:
                    if value.get('cache'):
                        job_has_cache = True

            if not has_cache and not job_has_cache:
                self.findings.append("No caching configuration detected")
                self.optimizations.append(
                    "Add caching to speed up builds:\n"
                    "cache:\n"
                    "  key: ${CI_COMMIT_REF_SLUG}\n"
                    "  paths:\n"
                    "    - node_modules/\n"
                    "    - .npm/\n"
                    "    - vendor/"
                )

    def _check_job_parallelization(self, config: Dict, platform: str):
        """Check for job parallelization opportunities"""
        if platform == 'github':
            jobs = config.get('jobs', {})

            # Count jobs with dependencies
            jobs_with_needs = sum(1 for job in jobs.values()
                                 if isinstance(job, dict) and 'needs' in job)

            if len(jobs) > 1 and jobs_with_needs == 0:
                self.optimizations.append(
                    f"Found {len(jobs)} jobs with no dependencies - they will run in parallel (good!)"
                )
            elif len(jobs) > 3 and jobs_with_needs == len(jobs):
                self.findings.append("All jobs have 'needs' dependencies - may be unnecessarily sequential")
                self.optimizations.append(
                    "Review job dependencies - remove 'needs' where jobs can run in parallel"
                )

        elif platform == 'gitlab':
            stages = config.get('stages', [])
            if len(stages) > 5:
                self.findings.append(f"Pipeline has {len(stages)} stages - may be overly sequential")
                self.optimizations.append(
                    "Consider reducing stages to allow more parallel execution"
                )

    def _check_dependency_management(self, config: Dict, platform: str):
        """Check dependency installation patterns"""
        if platform == 'github':
            jobs = config.get('jobs', {})
            for job_name, job in jobs.items():
                steps = job.get('steps', [])
                for step in steps:
                    if isinstance(step, dict):
                        run_cmd = step.get('run', '')

                        # Check for npm ci vs npm install
                        if 'npm install' in run_cmd and 'npm ci' not in run_cmd:
                            self.findings.append(f"Job '{job_name}' uses 'npm install' instead of 'npm ci'")
                            self.optimizations.append(
                                f"Use 'npm ci' instead of 'npm install' for faster, reproducible installs"
                            )

                        # Check for pip install without cache
                        if 'pip install' in run_cmd:
                            has_pip_cache = any(
                                s.get('uses', '').startswith('actions/cache') and
                                'pip' in str(s.get('with', {}).get('path', ''))
                                for s in steps if isinstance(s, dict)
                            )
                            if not has_pip_cache:
                                self.optimizations.append(
                                    f"Add pip cache for job '{job_name}' to speed up Python dependency installation"
                                )

    def _check_matrix_strategy(self, workflow: Dict):
        """Check for matrix strategy usage"""
        jobs = workflow.get('jobs', {})

        for job_name, job in jobs.items():
            if isinstance(job, dict):
                strategy = job.get('strategy', {})
                matrix = strategy.get('matrix', {})

                if matrix:
                    # Check fail-fast
                    fail_fast = strategy.get('fail-fast', True)
                    if fail_fast:
                        self.optimizations.append(
                            f"Job '{job_name}' has fail-fast=true (default). "
                            f"Consider fail-fast=false to see all matrix results"
                        )

                    # Check for large matrices
                    matrix_size = 1
                    for key, values in matrix.items():
                        if isinstance(values, list):
                            matrix_size *= len(values)

                    if matrix_size > 20:
                        self.findings.append(
                            f"Job '{job_name}' has large matrix ({matrix_size} combinations)"
                        )
                        self.optimizations.append(
                            f"Consider reducing matrix size or using 'exclude' to skip unnecessary combinations"
                        )

    def _check_artifact_usage(self, workflow: Dict):
        """Check artifact upload/download patterns"""
        jobs = workflow.get('jobs', {})
        uploads = {}
        downloads = {}

        for job_name, job in jobs.items():
            if not isinstance(job, dict):
                continue

            steps = job.get('steps', [])
            for step in steps:
                if isinstance(step, dict):
                    uses = step.get('uses', '')

                    if 'actions/upload-artifact' in uses:
                        artifact_name = step.get('with', {}).get('name', 'unknown')
                        uploads[artifact_name] = job_name

                    if 'actions/download-artifact' in uses:
                        artifact_name = step.get('with', {}).get('name', 'unknown')
                        downloads.setdefault(artifact_name, []).append(job_name)

        # Check for unused artifacts
        for artifact, uploader in uploads.items():
            if artifact not in downloads:
                self.findings.append(f"Artifact '{artifact}' uploaded but never downloaded")
                self.optimizations.append(f"Remove unused artifact upload or add download step")

    def _analyze_action_versions(self, workflow: Dict):
        """Check for outdated action versions"""
        jobs = workflow.get('jobs', {})
        outdated_actions = []

        for job_name, job in jobs.items():
            if not isinstance(job, dict):
                continue

            steps = job.get('steps', [])
            for step in steps:
                if isinstance(step, dict):
                    uses = step.get('uses', '')

                    # Check for @v1, @v2 versions (likely outdated)
                    if '@v1' in uses or '@v2' in uses:
                        outdated_actions.append(uses)

        if outdated_actions:
            self.findings.append(f"Found {len(outdated_actions)} potentially outdated actions")
            self.optimizations.append(
                f"Update to latest action versions:\n" +
                "\n".join(f"  - {action}" for action in set(outdated_actions))
            )

    def _check_gitlab_specific_features(self, config: Dict):
        """Check GitLab-specific optimization opportunities"""
        # Check for interruptible jobs
        has_interruptible = any(
            isinstance(v, dict) and v.get('interruptible')
            for v in config.values()
        )

        if not has_interruptible:
            self.optimizations.append(
                "Consider marking jobs as 'interruptible: true' to cancel redundant pipeline runs:\n"
                "job_name:\n"
                "  interruptible: true"
            )

        # Check for DAG usage (needs keyword)
        has_needs = any(
            isinstance(v, dict) and 'needs' in v
            for v in config.values()
        )

        if not has_needs and config.get('stages') and len(config.get('stages', [])) > 2:
            self.optimizations.append(
                "Consider using 'needs' keyword for DAG pipelines to improve parallelization:\n"
                "test:\n"
                "  needs: [build]"
            )

    def _error(self, message: str) -> Dict:
        """Return error report"""
        return {
            'status': 'error',
            'error': message,
            'findings': [],
            'optimizations': []
        }

    def _generate_report(self) -> Dict:
        """Generate analysis report"""
        return {
            'status': 'success',
            'platform': self.platform,
            'findings': self.findings,
            'optimizations': self.optimizations,
            'metrics': self.metrics
        }

def print_report(report: Dict):
    """Print formatted analysis report"""
    if report['status'] == 'error':
        print(f"\n❌ Error: {report['error']}\n")
        return

    print("\n" + "="*60)
    print(f"📊 Pipeline Analysis Report - {report['platform'].upper()}")
    print("="*60)

    if report['findings']:
        print(f"\n🔍 Findings ({len(report['findings'])}):")
        for i, finding in enumerate(report['findings'], 1):
            print(f"\n  {i}. {finding}")

    if report['optimizations']:
        print(f"\n💡 Optimization Recommendations ({len(report['optimizations'])}):")
        for i, opt in enumerate(report['optimizations'], 1):
            print(f"\n  {i}. {opt}")

    if not report['findings'] and not report['optimizations']:
        print("\n✅ No issues found - pipeline looks well optimized!")

    print("\n" + "="*60 + "\n")

def main():
    parser = argparse.ArgumentParser(
        description='CI/CD Pipeline Performance Analyzer',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('--platform', required=True, choices=['github', 'gitlab'],
                       help='CI/CD platform')
    parser.add_argument('--workflow', help='Path to GitHub Actions workflow file')
    parser.add_argument('--config', help='Path to GitLab CI config file')
    parser.add_argument('--repo', help='Repository (owner/repo) for run analysis')
    parser.add_argument('--analyze-runs', type=int, help='Number of recent runs to analyze')

    args = parser.parse_args()

    # Create analyzer
    analyzer = PipelineAnalyzer(
        platform=args.platform,
        repo=args.repo
    )

    # Run analysis
    if args.platform == 'github':
        if args.workflow:
            report = analyzer.analyze_github_workflow(args.workflow)
        else:
            # Try to find workflow files
            workflow_dir = Path('.github/workflows')
            if workflow_dir.exists():
                workflows = list(workflow_dir.glob('*.yml')) + list(workflow_dir.glob('*.yaml'))
                if workflows:
                    print(f"Found {len(workflows)} workflow(s), analyzing first one...")
                    report = analyzer.analyze_github_workflow(str(workflows[0]))
                else:
                    print("❌ No workflow files found in .github/workflows/")
                    sys.exit(1)
            else:
                print("❌ No .github/workflows/ directory found")
                sys.exit(1)

    elif args.platform == 'gitlab':
        config_file = args.config or '.gitlab-ci.yml'
        report = analyzer.analyze_gitlab_pipeline(config_file)

    # Print report
    print_report(report)

    # Exit with appropriate code
    sys.exit(0 if report['status'] == 'success' else 1)

if __name__ == '__main__':
    main()
