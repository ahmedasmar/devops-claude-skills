#!/usr/bin/env python3
"""
Detect old generation EC2 and RDS instances that should be migrated to newer generations.

This script identifies:
- Old generation EC2 instances (t2 → t3, m4 → m5, etc.)
- ARM/Graviton migration opportunities
- Old generation RDS instances
- Calculates cost savings from migration

Usage:
    python3 detect_old_generations.py [--region REGION] [--profile PROFILE]

Requirements:
    pip install boto3 tabulate
"""

import argparse
import boto3
from typing import List, Dict, Any
from tabulate import tabulate
import sys


class OldGenerationDetector:
    def __init__(self, profile: str = None, region: str = None):
        self.session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        self.regions = [region] if region else self._get_all_regions()
        self.findings = {
            'ec2_migrations': [],
            'graviton_opportunities': [],
            'rds_migrations': []
        }
        self.total_savings = 0.0

        # Migration mapping: old → new generation
        self.ec2_migrations = {
            # General Purpose
            't2.micro': ('t3.micro', 0.10),        # ~10% savings
            't2.small': ('t3.small', 0.10),
            't2.medium': ('t3.medium', 0.10),
            't2.large': ('t3.large', 0.10),
            't2.xlarge': ('t3.xlarge', 0.10),
            't2.2xlarge': ('t3.2xlarge', 0.10),
            'm4.large': ('m5.large', 0.04),        # ~4% savings
            'm4.xlarge': ('m5.xlarge', 0.04),
            'm4.2xlarge': ('m5.2xlarge', 0.04),
            'm4.4xlarge': ('m5.4xlarge', 0.04),
            'm4.10xlarge': ('m5.12xlarge', 0.10),
            'm4.16xlarge': ('m5.24xlarge', 0.10),
            'm5.large': ('m6i.large', 0.04),       # M5 → M6i
            'm5.xlarge': ('m6i.xlarge', 0.04),
            # Compute Optimized
            'c4.large': ('c5.large', 0.10),        # ~10% savings
            'c4.xlarge': ('c5.xlarge', 0.10),
            'c4.2xlarge': ('c5.2xlarge', 0.10),
            'c4.4xlarge': ('c5.4xlarge', 0.10),
            'c4.8xlarge': ('c5.9xlarge', 0.10),
            'c5.large': ('c6i.large', 0.05),       # C5 → C6i
            'c5.xlarge': ('c6i.xlarge', 0.05),
            # Memory Optimized
            'r4.large': ('r5.large', 0.08),        # ~8% savings
            'r4.xlarge': ('r5.xlarge', 0.08),
            'r4.2xlarge': ('r5.2xlarge', 0.08),
            'r4.4xlarge': ('r5.4xlarge', 0.08),
            'r4.8xlarge': ('r5.8xlarge', 0.08),
            'r5.large': ('r6i.large', 0.03),       # R5 → R6i
            'r5.xlarge': ('r6i.xlarge', 0.03),
        }

        # Graviton migration opportunities (even better savings)
        self.graviton_migrations = {
            't3.micro': ('t4g.micro', 0.20),       # ~20% savings
            't3.small': ('t4g.small', 0.20),
            't3.medium': ('t4g.medium', 0.20),
            't3.large': ('t4g.large', 0.20),
            't3.xlarge': ('t4g.xlarge', 0.20),
            't3.2xlarge': ('t4g.2xlarge', 0.20),
            'm5.large': ('m6g.large', 0.20),
            'm5.xlarge': ('m6g.xlarge', 0.20),
            'm5.2xlarge': ('m6g.2xlarge', 0.20),
            'm5.4xlarge': ('m6g.4xlarge', 0.20),
            'm6i.large': ('m6g.large', 0.20),
            'm6i.xlarge': ('m6g.xlarge', 0.20),
            'c5.large': ('c6g.large', 0.20),
            'c5.xlarge': ('c6g.xlarge', 0.20),
            'c5.2xlarge': ('c6g.2xlarge', 0.20),
            'r5.large': ('r6g.large', 0.20),
            'r5.xlarge': ('r6g.xlarge', 0.20),
            'r5.2xlarge': ('r6g.2xlarge', 0.20),
        }

        # RDS instance migrations
        self.rds_migrations = {
            'db.t2.micro': ('db.t3.micro', 0.10),
            'db.t2.small': ('db.t3.small', 0.10),
            'db.t2.medium': ('db.t3.medium', 0.10),
            'db.m4.large': ('db.m5.large', 0.05),
            'db.m4.xlarge': ('db.m5.xlarge', 0.05),
            'db.m4.2xlarge': ('db.m5.2xlarge', 0.05),
            'db.r4.large': ('db.r5.large', 0.08),
            'db.r4.xlarge': ('db.r5.xlarge', 0.08),
            'db.r4.2xlarge': ('db.r5.2xlarge', 0.08),
        }

    def _get_all_regions(self) -> List[str]:
        """Get all enabled AWS regions."""
        ec2 = self.session.client('ec2', region_name='us-east-1')
        regions = ec2.describe_regions(AllRegions=False)
        return [region['RegionName'] for region in regions['Regions']]

    def _estimate_hourly_cost(self, instance_type: str) -> float:
        """Rough estimate of hourly cost."""
        cost_map = {
            't2.micro': 0.0116, 't2.small': 0.023, 't2.medium': 0.0464,
            't3.micro': 0.0104, 't3.small': 0.0208, 't3.medium': 0.0416,
            't3.large': 0.0832, 't3.xlarge': 0.1664, 't3.2xlarge': 0.3328,
            't4g.micro': 0.0084, 't4g.small': 0.0168, 't4g.medium': 0.0336,
            'm4.large': 0.10, 'm4.xlarge': 0.20, 'm4.2xlarge': 0.40,
            'm5.large': 0.096, 'm5.xlarge': 0.192, 'm5.2xlarge': 0.384,
            'm6i.large': 0.096, 'm6i.xlarge': 0.192,
            'm6g.large': 0.077, 'm6g.xlarge': 0.154, 'm6g.2xlarge': 0.308,
            'c4.large': 0.10, 'c4.xlarge': 0.199, 'c4.2xlarge': 0.398,
            'c5.large': 0.085, 'c5.xlarge': 0.17, 'c5.2xlarge': 0.34,
            'c6i.large': 0.085, 'c6i.xlarge': 0.17,
            'c6g.large': 0.068, 'c6g.xlarge': 0.136, 'c6g.2xlarge': 0.272,
            'r4.large': 0.133, 'r4.xlarge': 0.266, 'r4.2xlarge': 0.532,
            'r5.large': 0.126, 'r5.xlarge': 0.252, 'r5.2xlarge': 0.504,
            'r6i.large': 0.126, 'r6i.xlarge': 0.252,
            'r6g.large': 0.101, 'r6g.xlarge': 0.202, 'r6g.2xlarge': 0.403,
        }
        return cost_map.get(instance_type, 0.10)

    def detect_ec2_migrations(self):
        """Detect old generation EC2 instances."""
        print("\n[1/3] Scanning for old generation EC2 instances...")

        for region in self.regions:
            try:
                ec2 = self.session.client('ec2', region_name=region)
                instances = ec2.describe_instances(
                    Filters=[{'Name': 'instance-state-name', 'Values': ['running', 'stopped']}]
                )

                for reservation in instances['Reservations']:
                    for instance in reservation['Instances']:
                        instance_id = instance['InstanceId']
                        instance_type = instance['InstanceType']
                        state = instance['State']['Name']

                        name_tag = next((tag['Value'] for tag in instance.get('Tags', [])
                                       if tag['Key'] == 'Name'), 'N/A')

                        # Check for standard migration
                        if instance_type in self.ec2_migrations:
                            new_type, savings_pct = self.ec2_migrations[instance_type]
                            current_cost = self._estimate_hourly_cost(instance_type)
                            new_cost = self._estimate_hourly_cost(new_type)
                            monthly_savings = (current_cost - new_cost) * 730

                            if state == 'running':
                                self.total_savings += monthly_savings * 12

                            self.findings['ec2_migrations'].append({
                                'Region': region,
                                'Instance ID': instance_id,
                                'Name': name_tag,
                                'Current Type': instance_type,
                                'Recommended Type': new_type,
                                'State': state,
                                'Savings %': f"{savings_pct*100:.0f}%",
                                'Monthly Savings': f"${monthly_savings:.2f}",
                                'Migration Type': 'Standard Upgrade'
                            })

                        # Check for Graviton migration
                        elif instance_type in self.graviton_migrations:
                            new_type, savings_pct = self.graviton_migrations[instance_type]
                            current_cost = self._estimate_hourly_cost(instance_type)
                            new_cost = self._estimate_hourly_cost(new_type)
                            monthly_savings = (current_cost - new_cost) * 730

                            if state == 'running':
                                self.total_savings += monthly_savings * 12

                            self.findings['graviton_opportunities'].append({
                                'Region': region,
                                'Instance ID': instance_id,
                                'Name': name_tag,
                                'Current Type': instance_type,
                                'Graviton Type': new_type,
                                'State': state,
                                'Savings %': f"{savings_pct*100:.0f}%",
                                'Monthly Savings': f"${monthly_savings:.2f}",
                                'Note': 'Requires ARM64 compatibility'
                            })

            except Exception as e:
                print(f"  Error scanning {region}: {str(e)}")

        print(f"  Found {len(self.findings['ec2_migrations'])} standard migrations")
        print(f"  Found {len(self.findings['graviton_opportunities'])} Graviton opportunities")

    def detect_rds_migrations(self):
        """Detect old generation RDS instances."""
        print("\n[2/3] Scanning for old generation RDS instances...")

        for region in self.regions:
            try:
                rds = self.session.client('rds', region_name=region)
                instances = rds.describe_db_instances()

                for instance in instances['DBInstances']:
                    instance_id = instance['DBInstanceIdentifier']
                    instance_class = instance['DBInstanceClass']
                    engine = instance['Engine']
                    status = instance['DBInstanceStatus']

                    if instance_class in self.rds_migrations:
                        new_class, savings_pct = self.rds_migrations[instance_class]

                        # RDS pricing is roughly 2x EC2
                        base_type = instance_class.replace('db.', '')
                        current_cost = self._estimate_hourly_cost(base_type) * 2
                        new_cost = current_cost * (1 - savings_pct)
                        monthly_savings = (current_cost - new_cost) * 730

                        if status == 'available':
                            self.total_savings += monthly_savings * 12

                        self.findings['rds_migrations'].append({
                            'Region': region,
                            'Instance ID': instance_id,
                            'Engine': engine,
                            'Current Class': instance_class,
                            'Recommended Class': new_class,
                            'Status': status,
                            'Savings %': f"{savings_pct*100:.0f}%",
                            'Monthly Savings': f"${monthly_savings:.2f}"
                        })

            except Exception as e:
                print(f"  Error scanning {region}: {str(e)}")

        print(f"  Found {len(self.findings['rds_migrations'])} RDS migrations")

    def print_report(self):
        """Print migration recommendations report."""
        print("\n" + "="*100)
        print("OLD GENERATION INSTANCE MIGRATION REPORT")
        print("="*100)

        if self.findings['ec2_migrations']:
            print("\nEC2 STANDARD MIGRATION OPPORTUNITIES")
            print("-" * 100)
            print(tabulate(self.findings['ec2_migrations'], headers='keys', tablefmt='grid'))

        if self.findings['graviton_opportunities']:
            print("\nEC2 GRAVITON (ARM64) MIGRATION OPPORTUNITIES")
            print("-" * 100)
            print(tabulate(self.findings['graviton_opportunities'], headers='keys', tablefmt='grid'))
            print("\nNOTE: Graviton instances offer significant savings but require ARM64-compatible workloads")
            print("Test thoroughly before migrating production workloads")

        if self.findings['rds_migrations']:
            print("\nRDS MIGRATION OPPORTUNITIES")
            print("-" * 100)
            print(tabulate(self.findings['rds_migrations'], headers='keys', tablefmt='grid'))

        print("\n" + "="*100)
        print(f"ESTIMATED ANNUAL SAVINGS: ${self.total_savings:.2f}")
        print("="*100)

        print("\n\nMIGRATION RECOMMENDATIONS:")
        print("\nEC2 Standard Migrations (x86):")
        print("- Generally drop-in replacements with better performance")
        print("- Can be done with instance type change (stop/start required)")
        print("- Minimal to no application changes needed")
        print("\nGraviton Migrations (ARM64):")
        print("- Requires ARM64-compatible applications and dependencies")
        print("- Test in non-production first")
        print("- Most modern languages/frameworks support ARM64")
        print("- Offers best price/performance ratio")
        print("\nRDS Migrations:")
        print("- Requires database instance modification")
        print("- Triggers brief downtime during modification")
        print("- Schedule during maintenance window")
        print("- Test with Multi-AZ for minimal downtime")

    def run(self):
        """Run old generation detection."""
        print(f"Scanning for old generation instances across {len(self.regions)} region(s)...")

        self.detect_ec2_migrations()
        self.detect_rds_migrations()

        self.print_report()


def main():
    parser = argparse.ArgumentParser(
        description='Detect old generation AWS instances and recommend migrations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan all regions with default profile
  python3 detect_old_generations.py

  # Scan specific region
  python3 detect_old_generations.py --region us-east-1

  # Use named profile
  python3 detect_old_generations.py --profile production
        """
    )

    parser.add_argument('--region', help='AWS region (default: all regions)')
    parser.add_argument('--profile', help='AWS profile name (default: default profile)')

    args = parser.parse_args()

    try:
        detector = OldGenerationDetector(
            profile=args.profile,
            region=args.region
        )
        detector.run()
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
