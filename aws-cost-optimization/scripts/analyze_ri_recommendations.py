#!/usr/bin/env python3
"""
Analyze EC2 and RDS usage patterns to recommend Reserved Instances.

This script:
- Identifies consistently running EC2 instances
- Calculates potential savings with Reserved Instances
- Recommends RI types (Standard vs Convertible) and commitment levels (1yr vs 3yr)
- Analyzes RDS instances for RI opportunities

Usage:
    python3 analyze_ri_recommendations.py [--region REGION] [--profile PROFILE] [--days DAYS]

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


class RIAnalyzer:
    def __init__(self, profile: str = None, region: str = None, days: int = 30):
        self.session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        self.regions = [region] if region else self._get_all_regions()
        self.days = days
        self.recommendations = {
            'ec2': [],
            'rds': []
        }
        self.total_potential_savings = 0.0

        # Simplified RI discount rates (actual rates vary by region/instance type)
        self.ri_discounts = {
            '1yr_no_upfront': 0.40,      # ~40% savings
            '1yr_partial_upfront': 0.42,  # ~42% savings
            '1yr_all_upfront': 0.43,      # ~43% savings
            '3yr_no_upfront': 0.60,      # ~60% savings
            '3yr_partial_upfront': 0.62,  # ~62% savings
            '3yr_all_upfront': 0.63       # ~63% savings
        }

    def _get_all_regions(self) -> List[str]:
        """Get all enabled AWS regions."""
        ec2 = self.session.client('ec2', region_name='us-east-1')
        regions = ec2.describe_regions(AllRegions=False)
        return [region['RegionName'] for region in regions['Regions']]

    def _estimate_hourly_cost(self, instance_type: str) -> float:
        """Rough estimate of On-Demand hourly cost."""
        cost_map = {
            't2.micro': 0.0116, 't2.small': 0.023, 't2.medium': 0.0464,
            't3.micro': 0.0104, 't3.small': 0.0208, 't3.medium': 0.0416,
            't3.large': 0.0832, 't3.xlarge': 0.1664, 't3.2xlarge': 0.3328,
            'm5.large': 0.096, 'm5.xlarge': 0.192, 'm5.2xlarge': 0.384,
            'm5.4xlarge': 0.768, 'm5.8xlarge': 1.536, 'm5.12xlarge': 2.304,
            'c5.large': 0.085, 'c5.xlarge': 0.17, 'c5.2xlarge': 0.34,
            'c5.4xlarge': 0.68, 'c5.9xlarge': 1.53, 'c5.18xlarge': 3.06,
            'r5.large': 0.126, 'r5.xlarge': 0.252, 'r5.2xlarge': 0.504,
            'r5.4xlarge': 1.008, 'r5.8xlarge': 2.016, 'r5.12xlarge': 3.024,
        }

        # Default fallback based on instance family
        if instance_type not in cost_map:
            family = instance_type.split('.')[0]
            family_defaults = {'t2': 0.02, 't3': 0.02, 'm5': 0.10, 'c5': 0.09, 'r5': 0.13}
            return family_defaults.get(family, 0.10)

        return cost_map[instance_type]

    def _calculate_savings(self, hourly_cost: float, hours_running: float) -> Dict[str, float]:
        """Calculate potential savings with different RI options."""
        monthly_od_cost = hourly_cost * hours_running

        savings = {}
        for ri_type, discount in self.ri_discounts.items():
            monthly_ri_cost = monthly_od_cost * (1 - discount)
            monthly_savings = monthly_od_cost - monthly_ri_cost
            savings[ri_type] = {
                'monthly_cost': monthly_ri_cost,
                'monthly_savings': monthly_savings,
                'annual_savings': monthly_savings * 12
            }

        return savings

    def analyze_ec2_instances(self):
        """Analyze EC2 instances for RI opportunities."""
        print(f"\n[1/2] Analyzing EC2 instances (last {self.days} days)...")

        # Group instances by type and platform
        instance_groups = defaultdict(lambda: {'count': 0, 'instances': []})

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
                        platform = instance.get('Platform', 'Linux/UNIX')

                        # Check if instance has been running consistently
                        launch_time = instance['LaunchTime']
                        days_running = (datetime.now(launch_time.tzinfo) - launch_time).days

                        if days_running >= self.days:
                            # Check uptime via CloudWatch
                            end_time = datetime.now()
                            start_time = end_time - timedelta(days=self.days)

                            try:
                                metrics = cloudwatch.get_metric_statistics(
                                    Namespace='AWS/EC2',
                                    MetricName='StatusCheckFailed',
                                    Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                                    StartTime=start_time,
                                    EndTime=end_time,
                                    Period=3600,
                                    Statistics=['Sum']
                                )

                                # If we have metrics, the instance has been running
                                if metrics['Datapoints'] or days_running >= self.days:
                                    key = f"{instance_type}_{platform}_{region}"
                                    instance_groups[key]['count'] += 1
                                    instance_groups[key]['instances'].append({
                                        'id': instance_id,
                                        'type': instance_type,
                                        'platform': platform,
                                        'region': region,
                                        'days_running': days_running
                                    })
                            except Exception:
                                # If CloudWatch fails, still count long-running instances
                                if days_running >= self.days:
                                    key = f"{instance_type}_{platform}_{region}"
                                    instance_groups[key]['count'] += 1
                                    instance_groups[key]['instances'].append({
                                        'id': instance_id,
                                        'type': instance_type,
                                        'platform': platform,
                                        'region': region,
                                        'days_running': days_running
                                    })

            except Exception as e:
                print(f"  Error scanning {region}: {str(e)}")

        # Generate recommendations
        for key, data in instance_groups.items():
            if data['count'] > 0:
                sample = data['instances'][0]
                instance_type = sample['type']
                platform = sample['platform']
                region = sample['region']
                count = data['count']

                hourly_cost = self._estimate_hourly_cost(instance_type)
                hours_per_month = 730  # Average hours in a month
                savings = self._calculate_savings(hourly_cost, hours_per_month * count)

                # Recommend best option (3yr all upfront for max savings)
                best_option = savings['3yr_all_upfront']
                self.total_potential_savings += best_option['annual_savings']

                self.recommendations['ec2'].append({
                    'Region': region,
                    'Instance Type': instance_type,
                    'Platform': platform,
                    'Count': count,
                    'Current Monthly Cost': f"${hourly_cost * hours_per_month * count:.2f}",
                    '1yr Savings (monthly)': f"${savings['1yr_all_upfront']['monthly_savings']:.2f}",
                    '3yr Savings (monthly)': f"${savings['3yr_all_upfront']['monthly_savings']:.2f}",
                    'Annual Savings (3yr)': f"${best_option['annual_savings']:.2f}",
                    'Recommendation': '3yr Standard RI (All Upfront)'
                })

        print(f"  Found {len(self.recommendations['ec2'])} RI opportunities")

    def analyze_rds_instances(self):
        """Analyze RDS instances for RI opportunities."""
        print(f"\n[2/2] Analyzing RDS instances (last {self.days} days)...")

        instance_groups = defaultdict(lambda: {'count': 0, 'instances': []})

        for region in self.regions:
            try:
                rds = self.session.client('rds', region_name=region)
                instances = rds.describe_db_instances()

                for instance in instances['DBInstances']:
                    instance_id = instance['DBInstanceIdentifier']
                    instance_class = instance['DBInstanceClass']
                    engine = instance['Engine']
                    multi_az = instance['MultiAZ']

                    # Check if instance has been running for the analysis period
                    create_time = instance['InstanceCreateTime']
                    days_running = (datetime.now(create_time.tzinfo) - create_time).days

                    if days_running >= self.days:
                        key = f"{instance_class}_{engine}_{multi_az}_{region}"
                        instance_groups[key]['count'] += 1
                        instance_groups[key]['instances'].append({
                            'id': instance_id,
                            'class': instance_class,
                            'engine': engine,
                            'multi_az': multi_az,
                            'region': region,
                            'days_running': days_running
                        })

            except Exception as e:
                print(f"  Error scanning {region}: {str(e)}")

        # Generate recommendations
        for key, data in instance_groups.items():
            if data['count'] > 0:
                sample = data['instances'][0]
                instance_class = sample['class']
                engine = sample['engine']
                multi_az = sample['multi_az']
                region = sample['region']
                count = data['count']

                # RDS pricing is roughly 2x EC2 for same instance type
                # This is a rough approximation
                base_hourly = self._estimate_hourly_cost(instance_class.replace('db.', ''))
                hourly_cost = base_hourly * 2
                if multi_az:
                    hourly_cost *= 2  # Multi-AZ doubles the cost

                hours_per_month = 730
                savings = self._calculate_savings(hourly_cost, hours_per_month * count)

                best_option = savings['3yr_all_upfront']
                self.total_potential_savings += best_option['annual_savings']

                self.recommendations['rds'].append({
                    'Region': region,
                    'Instance Class': instance_class,
                    'Engine': engine,
                    'Multi-AZ': 'Yes' if multi_az else 'No',
                    'Count': count,
                    'Current Monthly Cost': f"${hourly_cost * hours_per_month * count:.2f}",
                    '1yr Savings (monthly)': f"${savings['1yr_all_upfront']['monthly_savings']:.2f}",
                    '3yr Savings (monthly)': f"${savings['3yr_all_upfront']['monthly_savings']:.2f}",
                    'Annual Savings (3yr)': f"${best_option['annual_savings']:.2f}",
                    'Recommendation': '3yr Standard RI (All Upfront)'
                })

        print(f"  Found {len(self.recommendations['rds'])} RI opportunities")

    def print_report(self):
        """Print RI recommendations report."""
        print("\n" + "="*100)
        print("RESERVED INSTANCE RECOMMENDATIONS")
        print("="*100)

        if self.recommendations['ec2']:
            print("\nEC2 RESERVED INSTANCE OPPORTUNITIES")
            print("-" * 100)
            print(tabulate(self.recommendations['ec2'], headers='keys', tablefmt='grid'))

        if self.recommendations['rds']:
            print("\nRDS RESERVED INSTANCE OPPORTUNITIES")
            print("-" * 100)
            print(tabulate(self.recommendations['rds'], headers='keys', tablefmt='grid'))

        print("\n" + "="*100)
        print(f"TOTAL ANNUAL SAVINGS POTENTIAL: ${self.total_potential_savings:.2f}")
        print("="*100)

        print("\n\nRECOMMENDATIONS:")
        print("- Standard RIs offer the highest discount but no flexibility to change instance type")
        print("- Consider Convertible RIs if you need flexibility (slightly lower discount)")
        print("- All Upfront payment offers maximum savings")
        print("- Partial Upfront balances savings with cash flow")
        print("- No Upfront minimizes initial cost but reduces savings")
        print("\nNEXT STEPS:")
        print("1. Review workload stability and growth projections")
        print("2. Compare RI costs with Savings Plans for additional flexibility")
        print("3. Purchase RIs through AWS Console or CLI")
        print("4. Monitor RI utilization to ensure maximum benefit")

    def run(self):
        """Run RI analysis."""
        print(f"Analyzing AWS resources for RI opportunities...")
        print(f"Looking at instances running for at least {self.days} days")
        print(f"Scanning {len(self.regions)} region(s)...\n")

        self.analyze_ec2_instances()
        self.analyze_rds_instances()

        self.print_report()


def main():
    parser = argparse.ArgumentParser(
        description='Analyze AWS resources for Reserved Instance opportunities',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze all regions with default profile
  python3 analyze_ri_recommendations.py

  # Analyze specific region for instances running 60+ days
  python3 analyze_ri_recommendations.py --region us-east-1 --days 60

  # Use named profile
  python3 analyze_ri_recommendations.py --profile production
        """
    )

    parser.add_argument('--region', help='AWS region (default: all regions)')
    parser.add_argument('--profile', help='AWS profile name (default: default profile)')
    parser.add_argument('--days', type=int, default=30,
                        help='Minimum days instance must be running (default: 30)')

    args = parser.parse_args()

    try:
        analyzer = RIAnalyzer(
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
