#!/usr/bin/env python3
"""
Analyze EC2 workloads and recommend Spot instance opportunities.

This script identifies:
- Fault-tolerant workloads suitable for Spot instances
- Potential savings from Spot vs On-Demand
- Instances in Auto Scaling Groups (good Spot candidates)
- Non-critical workloads based on tags

Usage:
    python3 spot_recommendations.py [--region REGION] [--profile PROFILE]

Requirements:
    pip install boto3 tabulate
"""

import argparse
import boto3
from datetime import datetime, timedelta
from typing import List, Dict, Any
from tabulate import tabulate
import sys


class SpotRecommendationAnalyzer:
    def __init__(self, profile: str = None, region: str = None):
        self.session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        self.regions = [region] if region else self._get_all_regions()
        self.recommendations = []
        self.total_savings = 0.0

        # Average Spot savings (typically 60-90% discount)
        self.spot_discount = 0.70  # Conservative 70% discount

        # Tags that indicate Spot suitability
        self.spot_friendly_tags = {
            'Environment': ['dev', 'development', 'test', 'testing', 'staging', 'qa'],
            'Workload': ['batch', 'processing', 'worker', 'ci', 'build'],
            'CriticalLevel': ['low', 'non-critical', 'noncritical']
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
            'm5.4xlarge': 0.768, 'm5.8xlarge': 1.536,
            'c5.large': 0.085, 'c5.xlarge': 0.17, 'c5.2xlarge': 0.34,
            'c5.4xlarge': 0.68, 'c5.9xlarge': 1.53,
            'r5.large': 0.126, 'r5.xlarge': 0.252, 'r5.2xlarge': 0.504,
            'r5.4xlarge': 1.008, 'r5.8xlarge': 2.016,
        }

        # Default fallback
        if instance_type not in cost_map:
            family = instance_type.split('.')[0]
            family_defaults = {'t3': 0.04, 'm5': 0.10, 'c5': 0.09, 'r5': 0.13}
            return family_defaults.get(family, 0.10)

        return cost_map[instance_type]

    def _calculate_suitability_score(self, instance: Dict, asg_member: bool) -> tuple:
        """Calculate Spot suitability score (0-100) and reasons."""
        score = 0
        reasons = []

        # Check if in Auto Scaling Group (high suitability)
        if asg_member:
            score += 40
            reasons.append("Part of Auto Scaling Group")

        # Check tags for environment/workload type
        tags = {tag['Key']: tag['Value'].lower() for tag in instance.get('Tags', [])}

        for key, spot_values in self.spot_friendly_tags.items():
            if key in tags and tags[key] in spot_values:
                score += 20
                reasons.append(f"{key}={tags[key]}")

        # Check instance age (older instances might be more stable)
        launch_time = instance['LaunchTime']
        days_running = (datetime.now(launch_time.tzinfo) - launch_time).days
        if days_running > 30:
            score += 10
            reasons.append(f"Running {days_running} days (stable)")

        # Check instance size (smaller instances have better Spot availability)
        instance_type = instance['InstanceType']
        if any(size in instance_type for size in ['micro', 'small', 'medium', 'large']):
            score += 15
            reasons.append("Standard size (good Spot availability)")

        # Default baseline
        if not reasons:
            score = 30
            reasons.append("General compute workload")

        return min(score, 100), reasons

    def analyze_instances(self):
        """Analyze EC2 instances for Spot opportunities."""
        print(f"\nAnalyzing EC2 instances across {len(self.regions)} region(s)...")

        for region in self.regions:
            try:
                ec2 = self.session.client('ec2', region_name=region)
                autoscaling = self.session.client('autoscaling', region_name=region)

                # Get all Auto Scaling Groups
                asg_instances = set()
                try:
                    asgs = autoscaling.describe_auto_scaling_groups()
                    for asg in asgs['AutoScalingGroups']:
                        for instance in asg['Instances']:
                            asg_instances.add(instance['InstanceId'])
                except Exception:
                    pass

                # Get all running On-Demand instances
                instances = ec2.describe_instances(
                    Filters=[
                        {'Name': 'instance-state-name', 'Values': ['running']},
                        {'Name': 'instance-lifecycle', 'Values': ['on-demand', 'scheduled']}
                    ]
                )

                for reservation in instances['Reservations']:
                    for instance in reservation['Instances']:
                        instance_id = instance['InstanceId']
                        instance_type = instance['InstanceType']
                        asg_member = instance_id in asg_instances

                        # Calculate suitability
                        score, reasons = self._calculate_suitability_score(instance, asg_member)

                        # Calculate savings
                        hourly_cost = self._estimate_hourly_cost(instance_type)
                        monthly_savings = hourly_cost * 730 * self.spot_discount
                        annual_savings = monthly_savings * 12

                        self.total_savings += annual_savings

                        # Get instance name
                        name_tag = next((tag['Value'] for tag in instance.get('Tags', [])
                                       if tag['Key'] == 'Name'), 'N/A')

                        # Determine recommendation
                        if score >= 70:
                            recommendation = "Highly Recommended"
                        elif score >= 50:
                            recommendation = "Recommended"
                        elif score >= 30:
                            recommendation = "Consider (with caution)"
                        else:
                            recommendation = "Not Recommended"

                        self.recommendations.append({
                            'Region': region,
                            'Instance ID': instance_id,
                            'Name': name_tag,
                            'Type': instance_type,
                            'In ASG': 'Yes' if asg_member else 'No',
                            'Suitability Score': f"{score}/100",
                            'Monthly Savings': f"${monthly_savings:.2f}",
                            'Recommendation': recommendation,
                            'Reasons': ', '.join(reasons[:2])  # Show top 2 reasons
                        })

            except Exception as e:
                print(f"  Error scanning {region}: {str(e)}")

        print(f"  Analyzed {len(self.recommendations)} instances")

    def print_report(self):
        """Print Spot recommendations report."""
        print("\n" + "="*120)
        print("SPOT INSTANCE RECOMMENDATIONS")
        print("="*120)

        # Sort by suitability score (descending)
        sorted_recs = sorted(self.recommendations,
                           key=lambda x: int(x['Suitability Score'].split('/')[0]),
                           reverse=True)

        if sorted_recs:
            print(tabulate(sorted_recs, headers='keys', tablefmt='grid'))

        print("\n" + "="*120)
        print(f"TOTAL ANNUAL SAVINGS POTENTIAL: ${self.total_savings:.2f}")
        print(f"(Assumes {int(self.spot_discount*100)}% average Spot discount)")
        print("="*120)

        print("\n\nSPOT INSTANCE BEST PRACTICES:")
        print("\n1. Use Spot Instances for:")
        print("   - Stateless applications")
        print("   - Batch processing jobs")
        print("   - CI/CD and build servers")
        print("   - Data analysis and processing")
        print("   - Dev/test/staging environments")
        print("   - Auto Scaling Groups with mixed instance types")

        print("\n2. Do NOT use Spot Instances for:")
        print("   - Databases without replicas")
        print("   - Stateful applications without checkpointing")
        print("   - Real-time, latency-sensitive services")
        print("   - Applications that can't handle interruptions")

        print("\n3. Spot Best Practices:")
        print("   - Use Spot Fleet or Auto Scaling Groups with Spot")
        print("   - Diversify across multiple instance types")
        print("   - Implement graceful shutdown handlers (2-minute warning)")
        print("   - Use Spot Instance interruption notices")
        print("   - Consider Spot + On-Demand mix (e.g., 70/30)")
        print("   - Set appropriate max price (typically On-Demand price)")

        print("\n4. Implementation Steps:")
        print("   - Test Spot behavior in non-production first")
        print("   - Implement interruption handling in your application")
        print("   - Use EC2 Fleet or Auto Scaling with mixed instances policy")
        print("   - Monitor Spot interruption rates")
        print("   - Set up CloudWatch alarms for Spot terminations")

        print("\n5. Tools to Use:")
        print("   - EC2 Spot Instance Advisor (check interruption rates)")
        print("   - Auto Scaling Groups with mixed instances policy")
        print("   - Spot Fleet for diverse instance type selection")
        print("   - AWS Spot Instances best practices guide")

    def run(self):
        """Run Spot analysis."""
        print("="*80)
        print("AWS SPOT INSTANCE OPPORTUNITY ANALYZER")
        print("="*80)

        self.analyze_instances()
        self.print_report()


def main():
    parser = argparse.ArgumentParser(
        description='Analyze EC2 workloads for Spot instance opportunities',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze all regions with default profile
  python3 spot_recommendations.py

  # Analyze specific region
  python3 spot_recommendations.py --region us-east-1

  # Use named profile
  python3 spot_recommendations.py --profile production
        """
    )

    parser.add_argument('--region', help='AWS region (default: all regions)')
    parser.add_argument('--profile', help='AWS profile name (default: default profile)')

    args = parser.parse_args()

    try:
        analyzer = SpotRecommendationAnalyzer(
            profile=args.profile,
            region=args.region
        )
        analyzer.run()
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
