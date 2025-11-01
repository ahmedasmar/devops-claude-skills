#!/usr/bin/env python3
"""
Detect cost anomalies and unusual spending patterns in AWS.

This script:
- Analyzes Cost Explorer data for spending trends
- Detects anomalies and unexpected cost increases
- Identifies top cost drivers
- Compares period-over-period spending

Usage:
    python3 cost_anomaly_detector.py [--profile PROFILE] [--days DAYS]

Requirements:
    pip install boto3 tabulate
"""

import argparse
import boto3
from datetime import datetime, timedelta
from typing import List, Dict, Any
from collections import defaultdict
from tabulate import tabulate
import sys


class CostAnomalyDetector:
    def __init__(self, profile: str = None, days: int = 30):
        self.session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        self.days = days
        self.ce = self.session.client('ce', region_name='us-east-1')  # Cost Explorer is global

        self.findings = {
            'anomalies': [],
            'top_services': [],
            'trend_analysis': []
        }

        # Anomaly detection threshold
        self.anomaly_threshold = 1.5  # 50% increase triggers alert

    def _get_date_range(self, days: int) -> tuple:
        """Get start and end dates for analysis."""
        end = datetime.now().date()
        start = end - timedelta(days=days)
        return start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')

    def analyze_daily_costs(self):
        """Analyze daily cost trends."""
        print(f"\n[1/4] Analyzing daily costs (last {self.days} days)...")

        start_date, end_date = self._get_date_range(self.days)

        try:
            response = self.ce.get_cost_and_usage(
                TimePeriod={'Start': start_date, 'End': end_date},
                Granularity='DAILY',
                Metrics=['UnblendedCost'],
                GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
            )

            # Aggregate daily costs
            daily_totals = defaultdict(float)
            service_costs = defaultdict(lambda: defaultdict(float))

            for result in response['ResultsByTime']:
                date = result['TimePeriod']['Start']
                for group in result['Groups']:
                    service = group['Keys'][0]
                    cost = float(group['Metrics']['UnblendedCost']['Amount'])

                    daily_totals[date] += cost
                    service_costs[service][date] = cost

            # Detect daily anomalies
            dates = sorted(daily_totals.keys())
            if len(dates) > 7:
                # Calculate baseline (average of first week)
                baseline = sum(daily_totals[d] for d in dates[:7]) / 7

                for date in dates[7:]:
                    daily_cost = daily_totals[date]
                    if daily_cost > baseline * self.anomaly_threshold:
                        increase_pct = ((daily_cost - baseline) / baseline) * 100

                        # Find which service caused the spike
                        top_service = max(
                            ((svc, service_costs[svc][date]) for svc in service_costs),
                            key=lambda x: x[1]
                        )

                        self.findings['anomalies'].append({
                            'Date': date,
                            'Daily Cost': f"${daily_cost:.2f}",
                            'Baseline': f"${baseline:.2f}",
                            'Increase': f"+{increase_pct:.1f}%",
                            'Top Service': top_service[0],
                            'Service Cost': f"${top_service[1]:.2f}",
                            'Severity': 'High' if increase_pct > 100 else 'Medium'
                        })

            print(f"  Detected {len(self.findings['anomalies'])} cost anomalies")

        except Exception as e:
            print(f"  Error analyzing daily costs: {str(e)}")

    def analyze_top_services(self):
        """Identify top cost drivers."""
        print(f"\n[2/4] Analyzing top cost drivers...")

        start_date, end_date = self._get_date_range(self.days)

        try:
            response = self.ce.get_cost_and_usage(
                TimePeriod={'Start': start_date, 'End': end_date},
                Granularity='MONTHLY',
                Metrics=['UnblendedCost'],
                GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
            )

            service_totals = {}
            for result in response['ResultsByTime']:
                for group in result['Groups']:
                    service = group['Keys'][0]
                    cost = float(group['Metrics']['UnblendedCost']['Amount'])
                    service_totals[service] = service_totals.get(service, 0) + cost

            # Get top 10 services
            sorted_services = sorted(service_totals.items(), key=lambda x: x[1], reverse=True)[:10]

            total_cost = sum(service_totals.values())

            for service, cost in sorted_services:
                percentage = (cost / total_cost * 100) if total_cost > 0 else 0

                self.findings['top_services'].append({
                    'Service': service,
                    'Cost': f"${cost:.2f}",
                    'Percentage': f"{percentage:.1f}%",
                    'Daily Average': f"${cost/self.days:.2f}"
                })

            print(f"  Identified top {len(self.findings['top_services'])} cost drivers")

        except Exception as e:
            print(f"  Error analyzing top services: {str(e)}")

    def compare_periods(self):
        """Compare current period with previous period."""
        print(f"\n[3/4] Comparing cost trends...")

        # Current period
        current_end = datetime.now().date()
        current_start = current_end - timedelta(days=self.days)

        # Previous period
        previous_end = current_start - timedelta(days=1)
        previous_start = previous_end - timedelta(days=self.days)

        try:
            # Get current period costs
            current_response = self.ce.get_cost_and_usage(
                TimePeriod={
                    'Start': current_start.strftime('%Y-%m-%d'),
                    'End': current_end.strftime('%Y-%m-%d')
                },
                Granularity='MONTHLY',
                Metrics=['UnblendedCost'],
                GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
            )

            # Get previous period costs
            previous_response = self.ce.get_cost_and_usage(
                TimePeriod={
                    'Start': previous_start.strftime('%Y-%m-%d'),
                    'End': previous_end.strftime('%Y-%m-%d')
                },
                Granularity='MONTHLY',
                Metrics=['UnblendedCost'],
                GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
            )

            # Aggregate by service
            current_costs = {}
            for result in current_response['ResultsByTime']:
                for group in result['Groups']:
                    service = group['Keys'][0]
                    cost = float(group['Metrics']['UnblendedCost']['Amount'])
                    current_costs[service] = current_costs.get(service, 0) + cost

            previous_costs = {}
            for result in previous_response['ResultsByTime']:
                for group in result['Groups']:
                    service = group['Keys'][0]
                    cost = float(group['Metrics']['UnblendedCost']['Amount'])
                    previous_costs[service] = previous_costs.get(service, 0) + cost

            # Compare services
            all_services = set(current_costs.keys()) | set(previous_costs.keys())

            for service in all_services:
                current = current_costs.get(service, 0)
                previous = previous_costs.get(service, 0)

                if previous > 0:
                    change_pct = ((current - previous) / previous) * 100
                    change_amount = current - previous
                elif current > 0:
                    change_pct = 100
                    change_amount = current
                else:
                    continue

                # Only report significant changes (> 10% or > $10)
                if abs(change_pct) > 10 or abs(change_amount) > 10:
                    trend = "↑ Increase" if change_amount > 0 else "↓ Decrease"

                    self.findings['trend_analysis'].append({
                        'Service': service,
                        'Previous Period': f"${previous:.2f}",
                        'Current Period': f"${current:.2f}",
                        'Change': f"${change_amount:+.2f}",
                        'Change %': f"{change_pct:+.1f}%",
                        'Trend': trend
                    })

            # Sort by absolute change
            self.findings['trend_analysis'].sort(
                key=lambda x: abs(float(x['Change'].replace('$', '').replace('+', '').replace('-', ''))),
                reverse=True
            )

            print(f"  Compared {len(self.findings['trend_analysis'])} services")

        except Exception as e:
            print(f"  Error comparing periods: {str(e)}")

    def get_forecast(self):
        """Get AWS cost forecast."""
        print(f"\n[4/4] Getting cost forecast...")

        try:
            # Get 30-day forecast
            start_date = datetime.now().date()
            end_date = start_date + timedelta(days=30)

            response = self.ce.get_cost_forecast(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Metric='UNBLENDED_COST',
                Granularity='MONTHLY'
            )

            forecast_amount = float(response['Total']['Amount'])
            print(f"  30-day forecast: ${forecast_amount:.2f}")

            return forecast_amount

        except Exception as e:
            print(f"  Error getting forecast: {str(e)}")
            return None

    def print_report(self, forecast_amount: float = None):
        """Print cost anomaly report."""
        print("\n" + "="*110)
        print("AWS COST ANOMALY DETECTION REPORT")
        print("="*110)

        # Anomalies
        if self.findings['anomalies']:
            print("\nCOST ANOMALIES DETECTED")
            print("-" * 110)
            print(tabulate(self.findings['anomalies'], headers='keys', tablefmt='grid'))
            print("\n⚠️  These dates show unusual cost spikes. Investigate immediately.")

        # Top Services
        if self.findings['top_services']:
            print("\nTOP COST DRIVERS")
            print("-" * 110)
            print(tabulate(self.findings['top_services'], headers='keys', tablefmt='grid'))

        # Trend Analysis
        if self.findings['trend_analysis']:
            print("\nPERIOD-OVER-PERIOD COMPARISON")
            print(f"(Current {self.days} days vs Previous {self.days} days)")
            print("-" * 110)
            # Show top 15 changes
            print(tabulate(self.findings['trend_analysis'][:15], headers='keys', tablefmt='grid'))

        # Forecast
        if forecast_amount:
            print("\nCOST FORECAST")
            print("-" * 110)
            print(f"Projected 30-day cost: ${forecast_amount:.2f}")
            print(f"Projected monthly run rate: ${forecast_amount:.2f}")

        print("\n" + "="*110)

        print("\n\nRECOMMENDED ACTIONS:")
        print("\n1. For Cost Anomalies:")
        print("   - Review CloudWatch Logs for the affected service on anomaly dates")
        print("   - Check for configuration changes or deployments")
        print("   - Verify no unauthorized resource creation")
        print("   - Set up billing alerts to catch future anomalies")

        print("\n2. For Top Cost Drivers:")
        print("   - Review each service for optimization opportunities")
        print("   - Consider Reserved Instances for consistent workloads")
        print("   - Implement auto-scaling to match demand")
        print("   - Archive or delete unused resources")

        print("\n3. Cost Monitoring Best Practices:")
        print("   - Set up AWS Budgets with email/SNS alerts")
        print("   - Enable Cost Anomaly Detection in AWS Console")
        print("   - Tag resources for cost allocation and tracking")
        print("   - Run this script weekly to track trends")
        print("   - Review Cost Explorer monthly for detailed analysis")

        print("\n4. Immediate Actions:")
        print("   - aws budgets create-budget (set spending alerts)")
        print("   - aws ce get-anomaly-subscriptions (enable anomaly detection)")
        print("   - Review IAM policies to prevent unauthorized spending")
        print("   - Implement cost allocation tags across all resources")

    def run(self):
        """Run cost anomaly detection."""
        print("="*80)
        print("AWS COST ANOMALY DETECTOR")
        print("="*80)
        print(f"Analysis period: {self.days} days")

        self.analyze_daily_costs()
        self.analyze_top_services()
        self.compare_periods()
        forecast = self.get_forecast()

        self.print_report(forecast)


def main():
    parser = argparse.ArgumentParser(
        description='Detect AWS cost anomalies and analyze spending trends',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze last 30 days (default)
  python3 cost_anomaly_detector.py

  # Analyze last 60 days
  python3 cost_anomaly_detector.py --days 60

  # Use named profile
  python3 cost_anomaly_detector.py --profile production

Note: This script requires Cost Explorer API access, which may incur small charges.
        """
    )

    parser.add_argument('--profile', help='AWS profile name (default: default profile)')
    parser.add_argument('--days', type=int, default=30,
                        help='Days of cost data to analyze (default: 30)')

    args = parser.parse_args()

    try:
        detector = CostAnomalyDetector(
            profile=args.profile,
            days=args.days
        )
        detector.run()
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        print("\nNote: Cost Explorer API access is required. Ensure:", file=sys.stderr)
        print("1. Cost Explorer is enabled in AWS Console", file=sys.stderr)
        print("2. IAM user has 'ce:GetCostAndUsage' and 'ce:GetCostForecast' permissions", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
