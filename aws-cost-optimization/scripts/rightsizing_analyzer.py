#!/usr/bin/env python3
"""
Analyze EC2 and RDS instances for rightsizing opportunities.

This script identifies:
- Oversized EC2 instances (low CPU/memory utilization)
- Oversized RDS instances (low CPU/connection utilization)
- Recommended smaller instance types
- Potential cost savings

Usage:
    python3 rightsizing_analyzer.py [--region REGION] [--profile PROFILE] [--days DAYS]

Requirements:
    pip install boto3 tabulate
"""

import argparse
import boto3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from tabulate import tabulate
import sys


class RightsizingAnalyzer:
    def __init__(self, profile: str = None, region: str = None, days: int = 14):
        self.session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        self.regions = [region] if region else self._get_all_regions()
        self.days = days
        self.findings = {
            'ec2': [],
            'rds': []
        }
        self.total_savings = 0.0

        # CPU thresholds for rightsizing
        self.cpu_thresholds = {
            'underutilized': 15,  # < 15% avg CPU
            'low': 30,            # < 30% avg CPU
        }

    def _get_all_regions(self) -> List[str]:
        """Get all enabled AWS regions."""
        ec2 = self.session.client('ec2', region_name='us-east-1')
        regions = ec2.describe_regions(AllRegions=False)
        return [region['RegionName'] for region in regions['Regions']]

    def _estimate_hourly_cost(self, instance_type: str) -> float:
        """Rough estimate of hourly cost."""
        cost_map = {
            't3.micro': 0.0104, 't3.small': 0.0208, 't3.medium': 0.0416,
            't3.large': 0.0832, 't3.xlarge': 0.1664, 't3.2xlarge': 0.3328,
            'm5.large': 0.096, 'm5.xlarge': 0.192, 'm5.2xlarge': 0.384,
            'm5.4xlarge': 0.768, 'm5.8xlarge': 1.536, 'm5.12xlarge': 2.304,
            'm5.16xlarge': 3.072, 'm5.24xlarge': 4.608,
            'c5.large': 0.085, 'c5.xlarge': 0.17, 'c5.2xlarge': 0.34,
            'c5.4xlarge': 0.68, 'c5.9xlarge': 1.53, 'c5.12xlarge': 2.04,
            'c5.18xlarge': 3.06, 'c5.24xlarge': 4.08,
            'r5.large': 0.126, 'r5.xlarge': 0.252, 'r5.2xlarge': 0.504,
            'r5.4xlarge': 1.008, 'r5.8xlarge': 2.016, 'r5.12xlarge': 3.024,
            'r5.16xlarge': 4.032, 'r5.24xlarge': 6.048,
        }

        if instance_type not in cost_map:
            family = instance_type.split('.')[0]
            family_defaults = {'t3': 0.04, 'm5': 0.20, 'c5': 0.17, 'r5': 0.25}
            return family_defaults.get(family, 0.10)

        return cost_map[instance_type]

    def _get_smaller_instance_type(self, current_type: str) -> Optional[str]:
        """Suggest a smaller instance type."""
        # Size progression within families
        sizes = ['nano', 'micro', 'small', 'medium', 'large', 'xlarge', '2xlarge',
                 '3xlarge', '4xlarge', '8xlarge', '9xlarge', '12xlarge', '16xlarge',
                 '18xlarge', '24xlarge', '32xlarge']

        parts = current_type.split('.')
        if len(parts) != 2:
            return None

        family, size = parts

        if size not in sizes:
            return None

        current_idx = sizes.index(size)
        if current_idx <= 0:
            return None  # Already at smallest

        # Go down one size
        new_size = sizes[current_idx - 1]
        return f"{family}.{new_size}"

    def analyze_ec2_instances(self):
        """Analyze EC2 instances for rightsizing."""
        print(f"\n[1/2] Analyzing EC2 instances (last {self.days} days)...")

        for region in self.regions:
            try:
                ec2 = self.session.client('ec2', region_name=region)
                cloudwatch = self.session.client('cloudwatch', region_name=region)

                instances = ec2.describe_instances(
                    Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
                )

                for reservation in instances['Reservations']:
                    for instance in reservation['Instances']:
                        instance_id = instance['InstanceId']
                        instance_type = instance['InstanceType']

                        # Skip smallest instances (already optimized)
                        if any(size in instance_type for size in ['nano', 'micro', 'small']):
                            continue

                        name_tag = next((tag['Value'] for tag in instance.get('Tags', [])
                                       if tag['Key'] == 'Name'), 'N/A')

                        # Get CloudWatch metrics
                        end_time = datetime.now()
                        start_time = end_time - timedelta(days=self.days)

                        try:
                            # CPU Utilization
                            cpu_metrics = cloudwatch.get_metric_statistics(
                                Namespace='AWS/EC2',
                                MetricName='CPUUtilization',
                                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                                StartTime=start_time,
                                EndTime=end_time,
                                Period=3600,
                                Statistics=['Average', 'Maximum']
                            )

                            if not cpu_metrics['Datapoints']:
                                continue

                            avg_cpu = sum([p['Average'] for p in cpu_metrics['Datapoints']]) / len(cpu_metrics['Datapoints'])
                            max_cpu = max([p['Maximum'] for p in cpu_metrics['Datapoints']])

                            # Check if underutilized
                            if avg_cpu < self.cpu_thresholds['low'] and max_cpu < 60:
                                smaller_type = self._get_smaller_instance_type(instance_type)

                                if smaller_type:
                                    current_cost = self._estimate_hourly_cost(instance_type)
                                    new_cost = self._estimate_hourly_cost(smaller_type)
                                    monthly_savings = (current_cost - new_cost) * 730
                                    annual_savings = monthly_savings * 12

                                    self.total_savings += annual_savings

                                    # Determine severity
                                    if avg_cpu < self.cpu_thresholds['underutilized']:
                                        severity = "High"
                                    else:
                                        severity = "Medium"

                                    self.findings['ec2'].append({
                                        'Region': region,
                                        'Instance ID': instance_id,
                                        'Name': name_tag,
                                        'Current Type': instance_type,
                                        'Recommended Type': smaller_type,
                                        'Avg CPU (%)': f"{avg_cpu:.1f}",
                                        'Max CPU (%)': f"{max_cpu:.1f}",
                                        'Monthly Savings': f"${monthly_savings:.2f}",
                                        'Severity': severity
                                    })

                        except Exception as e:
                            pass  # Skip instances without metrics

            except Exception as e:
                print(f"  Error scanning {region}: {str(e)}")

        print(f"  Found {len(self.findings['ec2'])} rightsizing opportunities")

    def analyze_rds_instances(self):
        """Analyze RDS instances for rightsizing."""
        print(f"\n[2/2] Analyzing RDS instances (last {self.days} days)...")

        for region in self.regions:
            try:
                rds = self.session.client('rds', region_name=region)
                cloudwatch = self.session.client('cloudwatch', region_name=region)

                instances = rds.describe_db_instances()

                for instance in instances['DBInstances']:
                    instance_id = instance['DBInstanceIdentifier']
                    instance_class = instance['DBInstanceClass']
                    engine = instance['Engine']

                    # Skip smallest instances
                    if any(size in instance_class for size in ['micro', 'small']):
                        continue

                    # Get CloudWatch metrics
                    end_time = datetime.now()
                    start_time = end_time - timedelta(days=self.days)

                    try:
                        # CPU Utilization
                        cpu_metrics = cloudwatch.get_metric_statistics(
                            Namespace='AWS/RDS',
                            MetricName='CPUUtilization',
                            Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': instance_id}],
                            StartTime=start_time,
                            EndTime=end_time,
                            Period=3600,
                            Statistics=['Average', 'Maximum']
                        )

                        # Database Connections
                        conn_metrics = cloudwatch.get_metric_statistics(
                            Namespace='AWS/RDS',
                            MetricName='DatabaseConnections',
                            Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': instance_id}],
                            StartTime=start_time,
                            EndTime=end_time,
                            Period=3600,
                            Statistics=['Average', 'Maximum']
                        )

                        if not cpu_metrics['Datapoints']:
                            continue

                        avg_cpu = sum([p['Average'] for p in cpu_metrics['Datapoints']]) / len(cpu_metrics['Datapoints'])
                        max_cpu = max([p['Maximum'] for p in cpu_metrics['Datapoints']])

                        avg_conns = 0
                        max_conns = 0
                        if conn_metrics['Datapoints']:
                            avg_conns = sum([p['Average'] for p in conn_metrics['Datapoints']]) / len(conn_metrics['Datapoints'])
                            max_conns = max([p['Maximum'] for p in conn_metrics['Datapoints']])

                        # Check if underutilized
                        if avg_cpu < self.cpu_thresholds['low'] and max_cpu < 60:
                            smaller_class = self._get_smaller_instance_type(instance_class)

                            if smaller_class:
                                # RDS pricing is roughly 2x EC2
                                base_type = instance_class.replace('db.', '')
                                current_cost = self._estimate_hourly_cost(base_type) * 2
                                new_base = smaller_class.replace('db.', '')
                                new_cost = self._estimate_hourly_cost(new_base) * 2

                                monthly_savings = (current_cost - new_cost) * 730
                                annual_savings = monthly_savings * 12

                                self.total_savings += annual_savings

                                # Determine severity
                                if avg_cpu < self.cpu_thresholds['underutilized']:
                                    severity = "High"
                                else:
                                    severity = "Medium"

                                self.findings['rds'].append({
                                    'Region': region,
                                    'Instance ID': instance_id,
                                    'Engine': engine,
                                    'Current Class': instance_class,
                                    'Recommended Class': smaller_class,
                                    'Avg CPU (%)': f"{avg_cpu:.1f}",
                                    'Max CPU (%)': f"{max_cpu:.1f}",
                                    'Avg Connections': f"{avg_conns:.0f}",
                                    'Monthly Savings': f"${monthly_savings:.2f}",
                                    'Severity': severity
                                })

                    except Exception as e:
                        pass  # Skip instances without metrics

            except Exception as e:
                print(f"  Error scanning {region}: {str(e)}")

        print(f"  Found {len(self.findings['rds'])} rightsizing opportunities")

    def print_report(self):
        """Print rightsizing report."""
        print("\n" + "="*110)
        print("RIGHTSIZING RECOMMENDATIONS")
        print("="*110)

        if self.findings['ec2']:
            print("\nEC2 RIGHTSIZING OPPORTUNITIES")
            print("-" * 110)
            sorted_ec2 = sorted(self.findings['ec2'],
                              key=lambda x: float(x['Monthly Savings'].replace('$', '')),
                              reverse=True)
            print(tabulate(sorted_ec2, headers='keys', tablefmt='grid'))

        if self.findings['rds']:
            print("\nRDS RIGHTSIZING OPPORTUNITIES")
            print("-" * 110)
            sorted_rds = sorted(self.findings['rds'],
                              key=lambda x: float(x['Monthly Savings'].replace('$', '')),
                              reverse=True)
            print(tabulate(sorted_rds, headers='keys', tablefmt='grid'))

        print("\n" + "="*110)
        print(f"TOTAL ANNUAL SAVINGS: ${self.total_savings:.2f}")
        print("="*110)

        print("\n\nRIGHTSIZING BEST PRACTICES:")
        print("\n1. Before Rightsizing:")
        print("   - Review metrics over longer period (30+ days recommended)")
        print("   - Check for seasonal patterns or cyclical workloads")
        print("   - Verify that current size isn't required for burst capacity")
        print("   - Review application performance requirements")

        print("\n2. Rightsizing Process:")
        print("   - Test in non-production environment first")
        print("   - Schedule during maintenance window")
        print("   - EC2: Stop instance → Change type → Start")
        print("   - RDS: Modify instance (causes brief downtime)")
        print("   - Monitor performance after change")

        print("\n3. Important Considerations:")
        print("   - Some instance families can't be changed (requires new instance)")
        print("   - EBS-optimized settings may change with instance type")
        print("   - Network performance varies by instance size")
        print("   - Consider vertical scaling limits vs horizontal scaling")

        print("\n4. Alternative Approaches:")
        print("   - Consider serverless options (Lambda, Fargate, Aurora Serverless)")
        print("   - Use Auto Scaling to match capacity to demand")
        print("   - Implement horizontal scaling instead of larger instances")
        print("   - Evaluate containerization for better resource utilization")

    def run(self):
        """Run rightsizing analysis."""
        print(f"Analyzing AWS resources for rightsizing opportunities...")
        print(f"Metrics period: {self.days} days")
        print(f"Scanning {len(self.regions)} region(s)...\n")

        self.analyze_ec2_instances()
        self.analyze_rds_instances()

        self.print_report()


def main():
    parser = argparse.ArgumentParser(
        description='Analyze AWS resources for rightsizing opportunities',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze all regions (14 days of metrics)
  python3 rightsizing_analyzer.py

  # Analyze with 30 days of metrics for better accuracy
  python3 rightsizing_analyzer.py --days 30

  # Analyze specific region
  python3 rightsizing_analyzer.py --region us-east-1

  # Use named profile
  python3 rightsizing_analyzer.py --profile production
        """
    )

    parser.add_argument('--region', help='AWS region (default: all regions)')
    parser.add_argument('--profile', help='AWS profile name (default: default profile)')
    parser.add_argument('--days', type=int, default=14,
                        help='Days of metrics to analyze (default: 14)')

    args = parser.parse_args()

    try:
        analyzer = RightsizingAnalyzer(
            profile=args.profile,
            region=args.region,
            days=args.days
        )
        analyzer.run()
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
