#!/usr/bin/env python3
"""
Find unused AWS resources that are costing money.

This script identifies:
- Unattached EBS volumes
- Old EBS snapshots
- Unused Elastic IPs
- Idle NAT Gateways
- Idle EC2 instances (low utilization)
- Unattached load balancers

Usage:
    python3 find_unused_resources.py [--region REGION] [--profile PROFILE] [--snapshot-age-days DAYS]

Requirements:
    pip install boto3 tabulate
"""

import argparse
import boto3
from datetime import datetime, timedelta
from typing import List, Dict, Any
from tabulate import tabulate
import sys


class UnusedResourceFinder:
    def __init__(self, profile: str = None, region: str = None, snapshot_age_days: int = 90):
        self.session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        self.regions = [region] if region else self._get_all_regions()
        self.snapshot_age_days = snapshot_age_days
        self.findings = {
            'ebs_volumes': [],
            'snapshots': [],
            'elastic_ips': [],
            'nat_gateways': [],
            'idle_instances': [],
            'load_balancers': []
        }
        self.total_cost_estimate = 0.0

    def _get_all_regions(self) -> List[str]:
        """Get all enabled AWS regions."""
        ec2 = self.session.client('ec2', region_name='us-east-1')
        regions = ec2.describe_regions(AllRegions=False)
        return [region['RegionName'] for region in regions['Regions']]

    def find_unattached_volumes(self):
        """Find unattached EBS volumes."""
        print("\n[1/6] Scanning for unattached EBS volumes...")

        for region in self.regions:
            try:
                ec2 = self.session.client('ec2', region_name=region)
                volumes = ec2.describe_volumes(
                    Filters=[{'Name': 'status', 'Values': ['available']}]
                )

                for volume in volumes['Volumes']:
                    # Rough cost estimate: gp3 $0.08/GB/month
                    monthly_cost = volume['Size'] * 0.08
                    self.total_cost_estimate += monthly_cost

                    self.findings['ebs_volumes'].append({
                        'Region': region,
                        'Volume ID': volume['VolumeId'],
                        'Size (GB)': volume['Size'],
                        'Type': volume['VolumeType'],
                        'Created': volume['CreateTime'].strftime('%Y-%m-%d'),
                        'Est. Monthly Cost': f"${monthly_cost:.2f}"
                    })
            except Exception as e:
                print(f"  Error scanning {region}: {str(e)}")

        print(f"  Found {len(self.findings['ebs_volumes'])} unattached volumes")

    def find_old_snapshots(self):
        """Find old EBS snapshots."""
        print(f"\n[2/6] Scanning for snapshots older than {self.snapshot_age_days} days...")

        cutoff_date = datetime.now(datetime.now().astimezone().tzinfo) - timedelta(days=self.snapshot_age_days)

        for region in self.regions:
            try:
                ec2 = self.session.client('ec2', region_name=region)

                # Get account ID
                sts = self.session.client('sts')
                account_id = sts.get_caller_identity()['Account']

                snapshots = ec2.describe_snapshots(OwnerIds=[account_id])

                for snapshot in snapshots['Snapshots']:
                    if snapshot['StartTime'] < cutoff_date:
                        # Snapshot cost: $0.05/GB/month
                        monthly_cost = snapshot['VolumeSize'] * 0.05
                        self.total_cost_estimate += monthly_cost

                        age_days = (datetime.now(datetime.now().astimezone().tzinfo) - snapshot['StartTime']).days

                        self.findings['snapshots'].append({
                            'Region': region,
                            'Snapshot ID': snapshot['SnapshotId'],
                            'Size (GB)': snapshot['VolumeSize'],
                            'Age (days)': age_days,
                            'Created': snapshot['StartTime'].strftime('%Y-%m-%d'),
                            'Est. Monthly Cost': f"${monthly_cost:.2f}"
                        })
            except Exception as e:
                print(f"  Error scanning {region}: {str(e)}")

        print(f"  Found {len(self.findings['snapshots'])} old snapshots")

    def find_unused_elastic_ips(self):
        """Find unassociated Elastic IPs."""
        print("\n[3/6] Scanning for unused Elastic IPs...")

        for region in self.regions:
            try:
                ec2 = self.session.client('ec2', region_name=region)
                addresses = ec2.describe_addresses()

                for address in addresses['Addresses']:
                    if 'AssociationId' not in address:
                        # Unassociated EIP: ~$3.65/month
                        monthly_cost = 3.65
                        self.total_cost_estimate += monthly_cost

                        self.findings['elastic_ips'].append({
                            'Region': region,
                            'Allocation ID': address['AllocationId'],
                            'Public IP': address.get('PublicIp', 'N/A'),
                            'Status': 'Unassociated',
                            'Est. Monthly Cost': f"${monthly_cost:.2f}"
                        })
            except Exception as e:
                print(f"  Error scanning {region}: {str(e)}")

        print(f"  Found {len(self.findings['elastic_ips'])} unused Elastic IPs")

    def find_idle_nat_gateways(self):
        """Find NAT Gateways with low traffic."""
        print("\n[4/6] Scanning for idle NAT Gateways...")

        for region in self.regions:
            try:
                ec2 = self.session.client('ec2', region_name=region)
                nat_gateways = ec2.describe_nat_gateways(
                    Filters=[{'Name': 'state', 'Values': ['available']}]
                )

                cloudwatch = self.session.client('cloudwatch', region_name=region)

                for nat in nat_gateways['NatGateways']:
                    nat_id = nat['NatGatewayId']

                    # Check CloudWatch metrics for the last 7 days
                    end_time = datetime.now()
                    start_time = end_time - timedelta(days=7)

                    try:
                        metrics = cloudwatch.get_metric_statistics(
                            Namespace='AWS/NATGateway',
                            MetricName='BytesOutToSource',
                            Dimensions=[{'Name': 'NatGatewayId', 'Value': nat_id}],
                            StartTime=start_time,
                            EndTime=end_time,
                            Period=86400,  # 1 day
                            Statistics=['Sum']
                        )

                        total_bytes = sum([point['Sum'] for point in metrics['Datapoints']])
                        avg_gb_per_day = (total_bytes / (1024**3)) / 7

                        # NAT Gateway: ~$32.85/month + data processing
                        monthly_cost = 32.85
                        self.total_cost_estimate += monthly_cost

                        # Flag as idle if less than 1GB/day average
                        if avg_gb_per_day < 1:
                            self.findings['nat_gateways'].append({
                                'Region': region,
                                'NAT Gateway ID': nat_id,
                                'VPC': nat.get('VpcId', 'N/A'),
                                'Avg Traffic (GB/day)': f"{avg_gb_per_day:.2f}",
                                'Status': 'Low Traffic',
                                'Est. Monthly Cost': f"${monthly_cost:.2f}"
                            })
                    except Exception:
                        # If we can't get metrics, still report the NAT Gateway
                        self.findings['nat_gateways'].append({
                            'Region': region,
                            'NAT Gateway ID': nat_id,
                            'VPC': nat.get('VpcId', 'N/A'),
                            'Avg Traffic (GB/day)': 'N/A',
                            'Status': 'Metrics Unavailable',
                            'Est. Monthly Cost': f"${monthly_cost:.2f}"
                        })

            except Exception as e:
                print(f"  Error scanning {region}: {str(e)}")

        print(f"  Found {len(self.findings['nat_gateways'])} idle NAT Gateways")

    def find_idle_instances(self):
        """Find EC2 instances with low CPU utilization."""
        print("\n[5/6] Scanning for idle EC2 instances...")

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

                        # Check CPU utilization for the last 7 days
                        end_time = datetime.now()
                        start_time = end_time - timedelta(days=7)

                        try:
                            metrics = cloudwatch.get_metric_statistics(
                                Namespace='AWS/EC2',
                                MetricName='CPUUtilization',
                                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                                StartTime=start_time,
                                EndTime=end_time,
                                Period=3600,  # 1 hour
                                Statistics=['Average']
                            )

                            if metrics['Datapoints']:
                                avg_cpu = sum([point['Average'] for point in metrics['Datapoints']]) / len(metrics['Datapoints'])
                                max_cpu = max([point['Average'] for point in metrics['Datapoints']])

                                # Flag instances with avg CPU < 5% and max < 15%
                                if avg_cpu < 5 and max_cpu < 15:
                                    # Rough cost estimate (varies by instance type)
                                    # This is approximate - you'd need pricing API for accuracy
                                    monthly_cost = self._estimate_instance_cost(instance_type)
                                    self.total_cost_estimate += monthly_cost

                                    name_tag = next((tag['Value'] for tag in instance.get('Tags', []) if tag['Key'] == 'Name'), 'N/A')

                                    self.findings['idle_instances'].append({
                                        'Region': region,
                                        'Instance ID': instance_id,
                                        'Name': name_tag,
                                        'Type': instance_type,
                                        'Avg CPU (%)': f"{avg_cpu:.2f}",
                                        'Max CPU (%)': f"{max_cpu:.2f}",
                                        'Est. Monthly Cost': f"${monthly_cost:.2f}"
                                    })
                        except Exception:
                            pass

            except Exception as e:
                print(f"  Error scanning {region}: {str(e)}")

        print(f"  Found {len(self.findings['idle_instances'])} idle instances")

    def find_unused_load_balancers(self):
        """Find load balancers with no targets."""
        print("\n[6/6] Scanning for unused load balancers...")

        for region in self.regions:
            try:
                # Check Application/Network Load Balancers
                elbv2 = self.session.client('elbv2', region_name=region)
                load_balancers = elbv2.describe_load_balancers()

                for lb in load_balancers['LoadBalancers']:
                    lb_arn = lb['LoadBalancerArn']
                    lb_name = lb['LoadBalancerName']
                    lb_type = lb['Type']

                    # Check target groups
                    target_groups = elbv2.describe_target_groups(LoadBalancerArn=lb_arn)

                    has_healthy_targets = False
                    for tg in target_groups['TargetGroups']:
                        health = elbv2.describe_target_health(TargetGroupArn=tg['TargetGroupArn'])
                        if any(target['TargetHealth']['State'] == 'healthy' for target in health['TargetHealthDescriptions']):
                            has_healthy_targets = True
                            break

                    if not has_healthy_targets:
                        # ALB: ~$16.20/month, NLB: ~$22.35/month
                        monthly_cost = 22.35 if lb_type == 'network' else 16.20
                        self.total_cost_estimate += monthly_cost

                        self.findings['load_balancers'].append({
                            'Region': region,
                            'Name': lb_name,
                            'Type': lb_type.upper(),
                            'DNS': lb['DNSName'],
                            'Status': 'No Healthy Targets',
                            'Est. Monthly Cost': f"${monthly_cost:.2f}"
                        })

            except Exception as e:
                print(f"  Error scanning {region}: {str(e)}")

        print(f"  Found {len(self.findings['load_balancers'])} unused load balancers")

    def _estimate_instance_cost(self, instance_type: str) -> float:
        """Rough estimate of monthly instance cost (On-Demand, us-east-1)."""
        # This is a simplified approximation
        cost_map = {
            't2': 0.0116, 't3': 0.0104, 't3a': 0.0094,
            'm5': 0.096, 'm5a': 0.086, 'm6i': 0.096,
            'c5': 0.085, 'c5a': 0.077, 'c6i': 0.085,
            'r5': 0.126, 'r5a': 0.113, 'r6i': 0.126,
        }

        # Extract family (e.g., 't3' from 't3.micro')
        family = instance_type.split('.')[0]
        hourly_cost = cost_map.get(family, 0.10)  # Default to $0.10/hour

        return hourly_cost * 730  # Hours per month

    def print_report(self):
        """Print findings report."""
        print("\n" + "="*80)
        print("AWS UNUSED RESOURCES REPORT")
        print("="*80)

        sections = [
            ('UNATTACHED EBS VOLUMES', 'ebs_volumes'),
            ('OLD SNAPSHOTS', 'snapshots'),
            ('UNUSED ELASTIC IPs', 'elastic_ips'),
            ('IDLE NAT GATEWAYS', 'nat_gateways'),
            ('IDLE EC2 INSTANCES', 'idle_instances'),
            ('UNUSED LOAD BALANCERS', 'load_balancers')
        ]

        for title, key in sections:
            findings = self.findings[key]
            if findings:
                print(f"\n{title} ({len(findings)} found)")
                print("-" * 80)
                print(tabulate(findings, headers='keys', tablefmt='grid'))

        print("\n" + "="*80)
        print(f"ESTIMATED MONTHLY SAVINGS: ${self.total_cost_estimate:.2f}")
        print("="*80)
        print("\nNOTE: Cost estimates are approximate. Actual savings may vary.")
        print("Review each resource before deletion to avoid disrupting services.")

    def run(self):
        """Run all scans."""
        print(f"Scanning AWS account across {len(self.regions)} region(s)...")
        print("This may take several minutes...\n")

        self.find_unattached_volumes()
        self.find_old_snapshots()
        self.find_unused_elastic_ips()
        self.find_idle_nat_gateways()
        self.find_idle_instances()
        self.find_unused_load_balancers()

        self.print_report()


def main():
    parser = argparse.ArgumentParser(
        description='Find unused AWS resources that are costing money',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan all regions with default profile
  python3 find_unused_resources.py

  # Scan specific region with named profile
  python3 find_unused_resources.py --region us-east-1 --profile production

  # Find snapshots older than 180 days
  python3 find_unused_resources.py --snapshot-age-days 180
        """
    )

    parser.add_argument('--region', help='AWS region (default: all regions)')
    parser.add_argument('--profile', help='AWS profile name (default: default profile)')
    parser.add_argument('--snapshot-age-days', type=int, default=90,
                        help='Snapshots older than this are flagged (default: 90)')

    args = parser.parse_args()

    try:
        finder = UnusedResourceFinder(
            profile=args.profile,
            region=args.region,
            snapshot_age_days=args.snapshot_age_days
        )
        finder.run()
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
