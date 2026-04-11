#!/usr/bin/env python3
"""
Calculate SLO compliance, error budgets, and burn rates.
Supports availability SLOs and latency SLOs.
"""

import argparse
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

try:
    from tabulate import tabulate
except ImportError:
    print("⚠️  Warning: 'tabulate' library not found. Install with: pip install tabulate")
    tabulate = None


class SLOCalculator:
    # SLO targets and allowed downtime per period
    SLO_TARGETS = {
        "90.0": {"year": 36.5, "month": 3.0, "week": 0.7, "day": 0.1},  # days
        "95.0": {"year": 18.25, "month": 1.5, "week": 0.35, "day": 0.05},
        "99.0": {"year": 3.65, "month": 0.3, "week": 0.07, "day": 0.01},
        "99.5": {"year": 1.83, "month": 0.15, "week": 0.035, "day": 0.005},
        "99.9": {"year": 0.365, "month": 0.03, "week": 0.007, "day": 0.001},
        "99.95": {"year": 0.183, "month": 0.015, "week": 0.0035, "day": 0.0005},
        "99.99": {"year": 0.0365, "month": 0.003, "week": 0.0007, "day": 0.0001},
    }

    def __init__(self, slo_target: float, period_days: int = 30):
        """
        Initialize SLO calculator.

        Args:
            slo_target: SLO target percentage (e.g., 99.9)
            period_days: Time period in days (default: 30)
        """
        self.slo_target = slo_target
        self.period_days = period_days
        self.error_budget_minutes = self.calculate_error_budget_minutes()

    def calculate_error_budget_minutes(self) -> float:
        """Calculate error budget in minutes for the period."""
        total_minutes = self.period_days * 24 * 60
        allowed_error_rate = (100 - self.slo_target) / 100
        return total_minutes * allowed_error_rate

    def calculate_availability_slo(self, total_requests: int, failed_requests: int) -> Dict[str, Any]:
        """
        Calculate availability SLO compliance.

        Args:
            total_requests: Total number of requests
            failed_requests: Number of failed requests

        Returns:
            Dict with SLO compliance metrics
        """
        if total_requests == 0:
            return {
                "error": "No requests in the period",
                "slo_met": False
            }

        success_rate = ((total_requests - failed_requests) / total_requests) * 100
        error_rate = (failed_requests / total_requests) * 100

        # Calculate error budget consumption
        allowed_failures = total_requests * ((100 - self.slo_target) / 100)
        error_budget_consumed = (failed_requests / allowed_failures) * 100 if allowed_failures > 0 else float('inf')
        error_budget_remaining = max(0, 100 - error_budget_consumed)

        # Determine if SLO is met
        slo_met = success_rate >= self.slo_target

        return {
            "slo_target": self.slo_target,
            "period_days": self.period_days,
            "total_requests": total_requests,
            "failed_requests": failed_requests,
            "success_requests": total_requests - failed_requests,
            "success_rate": success_rate,
            "error_rate": error_rate,
            "slo_met": slo_met,
            "error_budget_total": allowed_failures,
            "error_budget_consumed": error_budget_consumed,
            "error_budget_remaining": error_budget_remaining,
            "margin": success_rate - self.slo_target
        }

    def calculate_latency_slo(self, total_requests: int, requests_exceeding_threshold: int) -> Dict[str, Any]:
        """
        Calculate latency SLO compliance.

        Args:
            total_requests: Total number of requests
            requests_exceeding_threshold: Number of requests exceeding latency threshold

        Returns:
            Dict with SLO compliance metrics
        """
        if total_requests == 0:
            return {
                "error": "No requests in the period",
                "slo_met": False
            }

        within_threshold_rate = ((total_requests - requests_exceeding_threshold) / total_requests) * 100

        # Calculate error budget consumption
        allowed_slow_requests = total_requests * ((100 - self.slo_target) / 100)
        error_budget_consumed = (requests_exceeding_threshold / allowed_slow_requests) * 100 if allowed_slow_requests > 0 else float('inf')
        error_budget_remaining = max(0, 100 - error_budget_consumed)

        slo_met = within_threshold_rate >= self.slo_target

        return {
            "slo_target": self.slo_target,
            "period_days": self.period_days,
            "total_requests": total_requests,
            "requests_exceeding_threshold": requests_exceeding_threshold,
            "requests_within_threshold": total_requests - requests_exceeding_threshold,
            "within_threshold_rate": within_threshold_rate,
            "slo_met": slo_met,
            "error_budget_total": allowed_slow_requests,
            "error_budget_consumed": error_budget_consumed,
            "error_budget_remaining": error_budget_remaining,
            "margin": within_threshold_rate - self.slo_target
        }

    def calculate_burn_rate(self, errors_in_window: int, requests_in_window: int, window_hours: float) -> Dict[str, Any]:
        """
        Calculate error budget burn rate.

        Args:
            errors_in_window: Number of errors in the time window
            requests_in_window: Total requests in the time window
            window_hours: Size of the time window in hours

        Returns:
            Dict with burn rate metrics
        """
        if requests_in_window == 0:
            return {"error": "No requests in window"}

        # Calculate actual error rate in this window
        actual_error_rate = (errors_in_window / requests_in_window) * 100

        # Calculate allowed error rate for SLO
        allowed_error_rate = 100 - self.slo_target

        # Burn rate = actual error rate / allowed error rate
        burn_rate = actual_error_rate / allowed_error_rate if allowed_error_rate > 0 else float('inf')

        # Calculate time to exhaustion
        if burn_rate > 0:
            error_budget_hours = self.error_budget_minutes / 60
            hours_to_exhaustion = error_budget_hours / burn_rate
        else:
            hours_to_exhaustion = float('inf')

        # Determine severity
        if burn_rate >= 14.4:  # 1 hour window, burns budget in 2 days
            severity = "critical"
        elif burn_rate >= 6:  # 6 hour window, burns budget in 5 days
            severity = "warning"
        elif burn_rate >= 1:
            severity = "elevated"
        else:
            severity = "normal"

        return {
            "window_hours": window_hours,
            "requests_in_window": requests_in_window,
            "errors_in_window": errors_in_window,
            "actual_error_rate": actual_error_rate,
            "allowed_error_rate": allowed_error_rate,
            "burn_rate": burn_rate,
            "hours_to_exhaustion": hours_to_exhaustion,
            "severity": severity
        }

    @staticmethod
    def print_slo_table():
        """Print table of common SLO targets and allowed downtime."""
        if not tabulate:
            print("Install tabulate for formatted output: pip install tabulate")
            return

        print("\n📊 SLO TARGETS AND ALLOWED DOWNTIME")
        print("="*60)

        headers = ["SLO", "Year", "Month", "Week", "Day"]
        rows = []

        for slo, downtimes in sorted(SLOCalculator.SLO_TARGETS.items(), reverse=True):
            row = [
                f"{slo}%",
                f"{downtimes['year']:.2f} days",
                f"{downtimes['month']:.2f} days",
                f"{downtimes['week']:.2f} days",
                f"{downtimes['day']:.2f} days"
            ]
            rows.append(row)

        print(tabulate(rows, headers=headers, tablefmt="grid"))


def print_availability_results(results: Dict[str, Any]):
    """Print availability SLO results."""
    print("\n" + "="*60)
    print("📊 AVAILABILITY SLO COMPLIANCE")
    print("="*60)

    if "error" in results:
        print(f"\n❌ Error: {results['error']}")
        return

    status_emoji = "✅" if results['slo_met'] else "❌"
    print(f"\n{status_emoji} SLO Status: {'MET' if results['slo_met'] else 'VIOLATED'}")
    print(f"   Target: {results['slo_target']}%")
    print(f"   Actual: {results['success_rate']:.3f}%")
    print(f"   Margin: {results['margin']:+.3f}%")

    print(f"\n📈 Request Statistics:")
    print(f"   Total Requests: {results['total_requests']:,}")
    print(f"   Successful: {results['success_requests']:,}")
    print(f"   Failed: {results['failed_requests']:,}")
    print(f"   Error Rate: {results['error_rate']:.3f}%")

    print(f"\n💰 Error Budget:")
    budget_emoji = "✅" if results['error_budget_remaining'] > 20 else "⚠️" if results['error_budget_remaining'] > 0 else "❌"
    print(f"   {budget_emoji} Remaining: {results['error_budget_remaining']:.1f}%")
    print(f"   Consumed: {results['error_budget_consumed']:.1f}%")
    print(f"   Allowed Failures: {results['error_budget_total']:.0f}")

    print("\n" + "="*60)


def print_burn_rate_results(results: Dict[str, Any]):
    """Print burn rate results."""
    print("\n" + "="*60)
    print("🔥 ERROR BUDGET BURN RATE")
    print("="*60)

    if "error" in results:
        print(f"\n❌ Error: {results['error']}")
        return

    severity_emoji = {
        "critical": "🔴",
        "warning": "🟡",
        "elevated": "🟠",
        "normal": "🟢"
    }

    print(f"\n{severity_emoji.get(results['severity'], '❓')} Severity: {results['severity'].upper()}")
    print(f"   Burn Rate: {results['burn_rate']:.2f}x")
    print(f"   Time to Exhaustion: {results['hours_to_exhaustion']:.1f} hours ({results['hours_to_exhaustion']/24:.1f} days)")

    print(f"\n📊 Window Statistics:")
    print(f"   Window: {results['window_hours']} hours")
    print(f"   Requests: {results['requests_in_window']:,}")
    print(f"   Errors: {results['errors_in_window']:,}")
    print(f"   Actual Error Rate: {results['actual_error_rate']:.3f}%")
    print(f"   Allowed Error Rate: {results['allowed_error_rate']:.3f}%")

    print("\n" + "="*60)


def main():
    parser = argparse.ArgumentParser(
        description="Calculate SLO compliance and error budgets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show SLO reference table
  python3 slo_calculator.py --table

  # Calculate availability SLO
  python3 slo_calculator.py availability \\
    --slo 99.9 \\
    --total-requests 1000000 \\
    --failed-requests 1500 \\
    --period-days 30

  # Calculate latency SLO
  python3 slo_calculator.py latency \\
    --slo 99.5 \\
    --total-requests 500000 \\
    --slow-requests 3000 \\
    --period-days 7

  # Calculate burn rate
  python3 slo_calculator.py burn-rate \\
    --slo 99.9 \\
    --errors 50 \\
    --requests 10000 \\
    --window-hours 1
        """
    )

    parser.add_argument('mode', nargs='?', choices=['availability', 'latency', 'burn-rate'],
                       help='Calculation mode')
    parser.add_argument('--table', action='store_true', help='Show SLO reference table')
    parser.add_argument('--slo', type=float, help='SLO target percentage (e.g., 99.9)')
    parser.add_argument('--period-days', type=int, default=30, help='Period in days (default: 30)')

    # Availability SLO arguments
    parser.add_argument('--total-requests', type=int, help='Total number of requests')
    parser.add_argument('--failed-requests', type=int, help='Number of failed requests')

    # Latency SLO arguments
    parser.add_argument('--slow-requests', type=int, help='Number of requests exceeding threshold')

    # Burn rate arguments
    parser.add_argument('--errors', type=int, help='Number of errors in window')
    parser.add_argument('--requests', type=int, help='Number of requests in window')
    parser.add_argument('--window-hours', type=float, help='Window size in hours')

    args = parser.parse_args()

    # Show table if requested
    if args.table:
        SLOCalculator.print_slo_table()
        return

    if not args.mode:
        parser.print_help()
        return

    if not args.slo:
        print("❌ --slo required")
        sys.exit(1)

    calculator = SLOCalculator(args.slo, args.period_days)

    if args.mode == 'availability':
        if not args.total_requests or args.failed_requests is None:
            print("❌ --total-requests and --failed-requests required")
            sys.exit(1)

        results = calculator.calculate_availability_slo(args.total_requests, args.failed_requests)
        print_availability_results(results)

    elif args.mode == 'latency':
        if not args.total_requests or args.slow_requests is None:
            print("❌ --total-requests and --slow-requests required")
            sys.exit(1)

        results = calculator.calculate_latency_slo(args.total_requests, args.slow_requests)
        print_availability_results(results)  # Same format

    elif args.mode == 'burn-rate':
        if not all([args.errors is not None, args.requests, args.window_hours]):
            print("❌ --errors, --requests, and --window-hours required")
            sys.exit(1)

        results = calculator.calculate_burn_rate(args.errors, args.requests, args.window_hours)
        print_burn_rate_results(results)


if __name__ == "__main__":
    main()
