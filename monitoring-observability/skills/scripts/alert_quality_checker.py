#!/usr/bin/env python3
"""
Audit Prometheus alert rules against best practices.
Checks for: alert naming, severity labels, runbook links, expression quality.
"""

import argparse
import sys
import os
import re
from typing import Dict, List, Any
from pathlib import Path

try:
    import yaml
except ImportError:
    print("⚠️  Warning: 'PyYAML' library not found. Install with: pip install pyyaml")
    sys.exit(1)


class AlertQualityChecker:
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.recommendations = []

    def check_alert_name(self, alert_name: str) -> List[str]:
        """Check alert naming conventions."""
        issues = []

        # Should be PascalCase or camelCase
        if not re.match(r'^[A-Z][a-zA-Z0-9]*$', alert_name):
            issues.append(f"Alert name '{alert_name}' should use PascalCase (e.g., HighCPUUsage)")

        # Should be descriptive
        if len(alert_name) < 5:
            issues.append(f"Alert name '{alert_name}' is too short, use descriptive names")

        # Avoid generic names
        generic_names = ['Alert', 'Test', 'Warning', 'Error']
        if alert_name in generic_names:
            issues.append(f"Alert name '{alert_name}' is too generic")

        return issues

    def check_labels(self, alert: Dict[str, Any]) -> List[str]:
        """Check required and recommended labels."""
        issues = []
        labels = alert.get('labels', {})

        # Required labels
        if 'severity' not in labels:
            issues.append("Missing required 'severity' label (critical/warning/info)")
        elif labels['severity'] not in ['critical', 'warning', 'info']:
            issues.append(f"Severity '{labels['severity']}' should be one of: critical, warning, info")

        # Recommended labels
        if 'team' not in labels:
            self.recommendations.append("Consider adding 'team' label for routing")

        if 'component' not in labels and 'service' not in labels:
            self.recommendations.append("Consider adding 'component' or 'service' label")

        return issues

    def check_annotations(self, alert: Dict[str, Any]) -> List[str]:
        """Check annotations quality."""
        issues = []
        annotations = alert.get('annotations', {})

        # Required annotations
        if 'summary' not in annotations:
            issues.append("Missing 'summary' annotation")
        elif len(annotations['summary']) < 10:
            issues.append("Summary annotation is too short, provide clear description")

        if 'description' not in annotations:
            issues.append("Missing 'description' annotation")

        # Runbook
        if 'runbook_url' not in annotations and 'runbook' not in annotations:
            self.recommendations.append("Consider adding 'runbook_url' for incident response")

        # Check for templating
        if 'summary' in annotations:
            if '{{ $value }}' not in annotations['summary'] and '{{' not in annotations['summary']:
                self.recommendations.append("Consider using template variables in summary (e.g., {{ $value }})")

        return issues

    def check_expression(self, expr: str, alert_name: str) -> List[str]:
        """Check PromQL expression quality."""
        issues = []

        # Should have a threshold
        if '>' not in expr and '<' not in expr and '==' not in expr and '!=' not in expr:
            issues.append("Expression should include a comparison operator")

        # Should use rate() for counters
        if '_total' in expr and 'rate(' not in expr and 'increase(' not in expr:
            self.recommendations.append("Consider using rate() or increase() for counter metrics (*_total)")

        # Avoid instant queries without aggregation
        if not any(agg in expr for agg in ['sum(', 'avg(', 'min(', 'max(', 'count(']):
            if expr.count('{') > 1:  # Multiple metrics without aggregation
                self.recommendations.append("Consider aggregating metrics with sum(), avg(), etc.")

        # Check for proper time windows
        if '[' not in expr and 'rate(' in expr:
            issues.append("rate() requires a time window (e.g., rate(metric[5m]))")

        return issues

    def check_for_duration(self, rule: Dict[str, Any]) -> List[str]:
        """Check for 'for' clause to prevent flapping."""
        issues = []
        severity = rule.get('labels', {}).get('severity', 'unknown')

        if 'for' not in rule:
            if severity == 'critical':
                issues.append("Critical alerts should have 'for' clause to prevent flapping")
            else:
                self.warnings.append("Consider adding 'for' clause to prevent alert flapping")
        else:
            # Parse duration
            duration = rule['for']
            if severity == 'critical' and any(x in duration for x in ['0s', '30s', '1m']):
                self.warnings.append(f"'for' duration ({duration}) might be too short for critical alerts")

        return issues

    def check_alert_rule(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Check a single alert rule."""
        alert_name = rule.get('alert', 'Unknown')
        issues = []

        # Check alert name
        issues.extend(self.check_alert_name(alert_name))

        # Check expression
        if 'expr' not in rule:
            issues.append("Missing 'expr' field")
        else:
            issues.extend(self.check_expression(rule['expr'], alert_name))

        # Check labels
        issues.extend(self.check_labels(rule))

        # Check annotations
        issues.extend(self.check_annotations(rule))

        # Check for duration
        issues.extend(self.check_for_duration(rule))

        return {
            "alert": alert_name,
            "issues": issues,
            "severity": rule.get('labels', {}).get('severity', 'unknown')
        }

    def analyze_file(self, filepath: str) -> Dict[str, Any]:
        """Analyze a Prometheus rules file."""
        try:
            with open(filepath, 'r') as f:
                data = yaml.safe_load(f)

            if not data:
                return {"error": "Empty or invalid YAML file"}

            results = []
            groups = data.get('groups', [])

            for group in groups:
                group_name = group.get('name', 'Unknown')
                rules = group.get('rules', [])

                for rule in rules:
                    # Only check alerting rules, not recording rules
                    if 'alert' in rule:
                        result = self.check_alert_rule(rule)
                        result['group'] = group_name
                        results.append(result)

            return {
                "file": filepath,
                "groups": len(groups),
                "alerts_checked": len(results),
                "results": results
            }

        except Exception as e:
            return {"error": f"Failed to parse file: {e}"}


def print_results(analysis: Dict[str, Any], checker: AlertQualityChecker):
    """Pretty print analysis results."""
    print("\n" + "="*60)
    print("🚨 ALERT QUALITY CHECK RESULTS")
    print("="*60)

    if "error" in analysis:
        print(f"\n❌ Error: {analysis['error']}")
        return

    print(f"\n📁 File: {analysis['file']}")
    print(f"📊 Groups: {analysis['groups']}")
    print(f"🔔 Alerts Checked: {analysis['alerts_checked']}")

    # Count issues by severity
    critical_count = 0
    warning_count = 0

    for result in analysis['results']:
        if result['issues']:
            critical_count += 1

    print(f"\n{'='*60}")
    print(f"📈 Summary:")
    print(f"   ❌ Alerts with Issues: {critical_count}")
    print(f"   ⚠️  Warnings: {len(checker.warnings)}")
    print(f"   💡 Recommendations: {len(checker.recommendations)}")

    # Print detailed results
    if critical_count > 0:
        print(f"\n{'='*60}")
        print("❌ ALERTS WITH ISSUES:")
        print(f"{'='*60}")

        for result in analysis['results']:
            if result['issues']:
                print(f"\n🔔 Alert: {result['alert']} (Group: {result['group']})")
                print(f"   Severity: {result['severity']}")
                print("   Issues:")
                for issue in result['issues']:
                    print(f"   • {issue}")

    # Print warnings
    if checker.warnings:
        print(f"\n{'='*60}")
        print("⚠️  WARNINGS:")
        print(f"{'='*60}")
        for warning in set(checker.warnings):  # Remove duplicates
            print(f"• {warning}")

    # Print recommendations
    if checker.recommendations:
        print(f"\n{'='*60}")
        print("💡 RECOMMENDATIONS:")
        print(f"{'='*60}")
        for rec in list(set(checker.recommendations))[:10]:  # Top 10 unique recommendations
            print(f"• {rec}")

    # Overall score
    total_alerts = analysis['alerts_checked']
    if total_alerts > 0:
        quality_score = ((total_alerts - critical_count) / total_alerts) * 100
        print(f"\n{'='*60}")
        print(f"📊 Quality Score: {quality_score:.1f}% ({total_alerts - critical_count}/{total_alerts} alerts passing)")
        print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Audit Prometheus alert rules for quality and best practices",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check a single file
  python3 alert_quality_checker.py alerts.yml

  # Check all YAML files in a directory
  python3 alert_quality_checker.py /path/to/prometheus/rules/

Best Practices Checked:
  ✓ Alert naming conventions (PascalCase, descriptive)
  ✓ Required labels (severity)
  ✓ Required annotations (summary, description)
  ✓ Runbook URL presence
  ✓ PromQL expression quality
  ✓ 'for' clause to prevent flapping
  ✓ Template variable usage
        """
    )

    parser.add_argument('path', help='Path to alert rules file or directory')
    parser.add_argument('--verbose', action='store_true', help='Show all recommendations')

    args = parser.parse_args()

    checker = AlertQualityChecker()

    # Check if path is file or directory
    path = Path(args.path)

    if path.is_file():
        files = [str(path)]
    elif path.is_dir():
        files = [str(f) for f in path.rglob('*.yml')] + [str(f) for f in path.rglob('*.yaml')]
    else:
        print(f"❌ Path not found: {args.path}")
        sys.exit(1)

    if not files:
        print(f"❌ No YAML files found in: {args.path}")
        sys.exit(1)

    print(f"🔍 Checking {len(files)} file(s)...")

    for filepath in files:
        analysis = checker.analyze_file(filepath)
        print_results(analysis, checker)


if __name__ == "__main__":
    main()
