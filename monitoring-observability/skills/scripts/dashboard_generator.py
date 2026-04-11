#!/usr/bin/env python3
"""
Generate Grafana dashboards from templates.
Supports: web applications, Kubernetes, databases, Redis, and custom metrics.
"""

import argparse
import sys
import json
from typing import Dict, List, Any, Optional
from pathlib import Path


class DashboardGenerator:
    def __init__(self, title: str, datasource: str = "Prometheus"):
        self.title = title
        self.datasource = datasource
        self.dashboard = self._create_base_dashboard()
        self.panel_id = 1
        self.row_y = 0

    def _create_base_dashboard(self) -> Dict[str, Any]:
        """Create base dashboard structure."""
        return {
            "dashboard": {
                "title": self.title,
                "tags": [],
                "timezone": "browser",
                "schemaVersion": 16,
                "version": 0,
                "refresh": "30s",
                "panels": [],
                "templating": {
                    "list": []
                },
                "time": {
                    "from": "now-6h",
                    "to": "now"
                }
            },
            "overwrite": True
        }

    def add_variable(self, name: str, label: str, query: str):
        """Add a template variable."""
        variable = {
            "name": name,
            "label": label,
            "type": "query",
            "datasource": self.datasource,
            "query": query,
            "refresh": 1,
            "regex": "",
            "multi": False,
            "includeAll": False
        }
        self.dashboard["dashboard"]["templating"]["list"].append(variable)

    def add_row(self, title: str):
        """Add a row panel."""
        panel = {
            "id": self.panel_id,
            "type": "row",
            "title": title,
            "collapsed": False,
            "gridPos": {"h": 1, "w": 24, "x": 0, "y": self.row_y}
        }
        self.dashboard["dashboard"]["panels"].append(panel)
        self.panel_id += 1
        self.row_y += 1

    def add_graph(self, title: str, targets: List[Dict[str, str]], unit: str = "short",
                  width: int = 12, height: int = 8):
        """Add a graph panel."""
        panel = {
            "id": self.panel_id,
            "type": "graph",
            "title": title,
            "datasource": self.datasource,
            "targets": [
                {
                    "expr": target["query"],
                    "legendFormat": target.get("legend", ""),
                    "refId": chr(65 + i)  # A, B, C, etc.
                }
                for i, target in enumerate(targets)
            ],
            "gridPos": {"h": height, "w": width, "x": 0, "y": self.row_y},
            "yaxes": [
                {"format": unit, "label": None, "show": True},
                {"format": "short", "label": None, "show": True}
            ],
            "lines": True,
            "fill": 1,
            "linewidth": 2,
            "legend": {
                "show": True,
                "alignAsTable": True,
                "avg": True,
                "current": True,
                "max": True,
                "min": False,
                "total": False,
                "values": True
            }
        }
        self.dashboard["dashboard"]["panels"].append(panel)
        self.panel_id += 1
        self.row_y += height

    def add_stat(self, title: str, query: str, unit: str = "short",
                 width: int = 6, height: int = 4):
        """Add a stat panel (single value)."""
        panel = {
            "id": self.panel_id,
            "type": "stat",
            "title": title,
            "datasource": self.datasource,
            "targets": [
                {
                    "expr": query,
                    "refId": "A"
                }
            ],
            "gridPos": {"h": height, "w": width, "x": 0, "y": self.row_y},
            "options": {
                "graphMode": "area",
                "orientation": "auto",
                "reduceOptions": {
                    "values": False,
                    "calcs": ["lastNotNull"]
                }
            },
            "fieldConfig": {
                "defaults": {
                    "unit": unit,
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {"value": None, "color": "green"},
                            {"value": 80, "color": "red"}
                        ]
                    }
                }
            }
        }
        self.dashboard["dashboard"]["panels"].append(panel)
        self.panel_id += 1

    def generate_webapp_dashboard(self, service: str):
        """Generate dashboard for web application."""
        self.add_variable("service", "Service", f"label_values({service}_http_requests_total, service)")

        # Request metrics
        self.add_row("Request Metrics")

        self.add_graph(
            "Request Rate",
            [{"query": f'sum(rate({service}_http_requests_total[5m])) by (status)', "legend": "{{status}}"}],
            unit="reqps",
            width=12
        )

        self.add_graph(
            "Request Latency (p50, p95, p99)",
            [
                {"query": f'histogram_quantile(0.50, sum(rate({service}_http_request_duration_seconds_bucket[5m])) by (le))', "legend": "p50"},
                {"query": f'histogram_quantile(0.95, sum(rate({service}_http_request_duration_seconds_bucket[5m])) by (le))', "legend": "p95"},
                {"query": f'histogram_quantile(0.99, sum(rate({service}_http_request_duration_seconds_bucket[5m])) by (le))', "legend": "p99"}
            ],
            unit="s",
            width=12
        )

        # Error rate
        self.add_row("Errors")

        self.add_graph(
            "Error Rate (%)",
            [{"query": f'sum(rate({service}_http_requests_total{{status=~"5.."}}[5m])) / sum(rate({service}_http_requests_total[5m])) * 100', "legend": "Error Rate"}],
            unit="percent",
            width=12
        )

        # Resource usage
        self.add_row("Resource Usage")

        self.add_graph(
            "CPU Usage",
            [{"query": f'sum(rate(process_cpu_seconds_total{{job="{service}"}}[5m])) * 100', "legend": "CPU %"}],
            unit="percent",
            width=12
        )

        self.add_graph(
            "Memory Usage",
            [{"query": f'process_resident_memory_bytes{{job="{service}"}}', "legend": "Memory"}],
            unit="bytes",
            width=12
        )

    def generate_kubernetes_dashboard(self, namespace: str):
        """Generate dashboard for Kubernetes cluster."""
        self.add_variable("namespace", "Namespace", f"label_values(kube_pod_info, namespace)")

        # Cluster overview
        self.add_row("Cluster Overview")

        self.add_stat("Total Pods", f'count(kube_pod_info{{namespace="{namespace}"}})', width=6)
        self.add_stat("Running Pods", f'count(kube_pod_status_phase{{namespace="{namespace}", phase="Running"}})', width=6)
        self.add_stat("Pending Pods", f'count(kube_pod_status_phase{{namespace="{namespace}", phase="Pending"}})', width=6)
        self.add_stat("Failed Pods", f'count(kube_pod_status_phase{{namespace="{namespace}", phase="Failed"}})', width=6)

        # Resource usage
        self.add_row("Resource Usage")

        self.add_graph(
            "CPU Usage by Pod",
            [{"query": f'sum(rate(container_cpu_usage_seconds_total{{namespace="{namespace}"}}[5m])) by (pod)', "legend": "{{pod}}"}],
            unit="percent",
            width=12
        )

        self.add_graph(
            "Memory Usage by Pod",
            [{"query": f'sum(container_memory_usage_bytes{{namespace="{namespace}"}}) by (pod)', "legend": "{{pod}}"}],
            unit="bytes",
            width=12
        )

        # Network
        self.add_row("Network")

        self.add_graph(
            "Network I/O",
            [
                {"query": f'sum(rate(container_network_receive_bytes_total{{namespace="{namespace}"}}[5m])) by (pod)', "legend": "Receive - {{pod}}"},
                {"query": f'sum(rate(container_network_transmit_bytes_total{{namespace="{namespace}"}}[5m])) by (pod)', "legend": "Transmit - {{pod}}"}
            ],
            unit="Bps",
            width=12
        )

    def generate_database_dashboard(self, db_type: str, instance: str):
        """Generate dashboard for database (postgres/mysql)."""
        if db_type == "postgres":
            self._generate_postgres_dashboard(instance)
        elif db_type == "mysql":
            self._generate_mysql_dashboard(instance)

    def _generate_postgres_dashboard(self, instance: str):
        """Generate PostgreSQL dashboard."""
        self.add_row("PostgreSQL Metrics")

        self.add_graph(
            "Connections",
            [
                {"query": f'pg_stat_database_numbackends{{instance="{instance}"}}', "legend": "{{datname}}"}
            ],
            unit="short",
            width=12
        )

        self.add_graph(
            "Transactions per Second",
            [
                {"query": f'rate(pg_stat_database_xact_commit{{instance="{instance}"}}[5m])', "legend": "Commits"},
                {"query": f'rate(pg_stat_database_xact_rollback{{instance="{instance}"}}[5m])', "legend": "Rollbacks"}
            ],
            unit="tps",
            width=12
        )

        self.add_graph(
            "Query Duration (p95)",
            [
                {"query": f'histogram_quantile(0.95, rate(pg_stat_statements_total_time_bucket{{instance="{instance}"}}[5m]))', "legend": "p95"}
            ],
            unit="ms",
            width=12
        )

    def _generate_mysql_dashboard(self, instance: str):
        """Generate MySQL dashboard."""
        self.add_row("MySQL Metrics")

        self.add_graph(
            "Connections",
            [
                {"query": f'mysql_global_status_threads_connected{{instance="{instance}"}}', "legend": "Connected"},
                {"query": f'mysql_global_status_threads_running{{instance="{instance}"}}', "legend": "Running"}
            ],
            unit="short",
            width=12
        )

        self.add_graph(
            "Queries per Second",
            [
                {"query": f'rate(mysql_global_status_queries{{instance="{instance}"}}[5m])', "legend": "Queries"}
            ],
            unit="qps",
            width=12
        )

    def save(self, output_file: str):
        """Save dashboard to file."""
        try:
            with open(output_file, 'w') as f:
                json.dump(self.dashboard, f, indent=2)
            return True
        except Exception as e:
            print(f"❌ Error saving dashboard: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Generate Grafana dashboards from templates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Web application dashboard
  python3 dashboard_generator.py webapp \\
    --title "My API Dashboard" \\
    --service my_api \\
    --output dashboard.json

  # Kubernetes dashboard
  python3 dashboard_generator.py kubernetes \\
    --title "K8s Namespace" \\
    --namespace production \\
    --output k8s-dashboard.json

  # Database dashboard
  python3 dashboard_generator.py database \\
    --title "PostgreSQL" \\
    --db-type postgres \\
    --instance db.example.com:5432 \\
    --output db-dashboard.json
        """
    )

    parser.add_argument('type', choices=['webapp', 'kubernetes', 'database'],
                       help='Dashboard type')
    parser.add_argument('--title', required=True, help='Dashboard title')
    parser.add_argument('--output', required=True, help='Output file path')
    parser.add_argument('--datasource', default='Prometheus', help='Data source name')

    # Web app specific
    parser.add_argument('--service', help='Service name (for webapp)')

    # Kubernetes specific
    parser.add_argument('--namespace', help='Kubernetes namespace')

    # Database specific
    parser.add_argument('--db-type', choices=['postgres', 'mysql'], help='Database type')
    parser.add_argument('--instance', help='Database instance')

    args = parser.parse_args()

    print(f"🎨 Generating {args.type} dashboard: {args.title}")

    generator = DashboardGenerator(args.title, args.datasource)

    if args.type == 'webapp':
        if not args.service:
            print("❌ --service required for webapp dashboard")
            sys.exit(1)
        generator.generate_webapp_dashboard(args.service)

    elif args.type == 'kubernetes':
        if not args.namespace:
            print("❌ --namespace required for kubernetes dashboard")
            sys.exit(1)
        generator.generate_kubernetes_dashboard(args.namespace)

    elif args.type == 'database':
        if not args.db_type or not args.instance:
            print("❌ --db-type and --instance required for database dashboard")
            sys.exit(1)
        generator.generate_database_dashboard(args.db_type, args.instance)

    if generator.save(args.output):
        print(f"✅ Dashboard saved to: {args.output}")
        print(f"\n📝 Import to Grafana:")
        print(f"   1. Go to Grafana → Dashboards → Import")
        print(f"   2. Upload {args.output}")
        print(f"   3. Select datasource and save")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
