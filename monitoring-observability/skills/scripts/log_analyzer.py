#!/usr/bin/env python3
"""
Parse and analyze logs for patterns, errors, and anomalies.
Supports: error detection, frequency analysis, pattern matching.
"""

import argparse
import sys
import re
import json
from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

try:
    from tabulate import tabulate
except ImportError:
    tabulate = None


class LogAnalyzer:
    # Common log level patterns
    LOG_LEVELS = {
        'ERROR': r'\b(ERROR|Error|error)\b',
        'WARN': r'\b(WARN|Warning|warn|warning)\b',
        'INFO': r'\b(INFO|Info|info)\b',
        'DEBUG': r'\b(DEBUG|Debug|debug)\b',
        'FATAL': r'\b(FATAL|Fatal|fatal|CRITICAL|Critical)\b'
    }

    # Common error patterns
    ERROR_PATTERNS = {
        'exception': r'Exception|exception|EXCEPTION',
        'stack_trace': r'\s+at\s+.*\(.*:\d+\)',
        'http_error': r'\b[45]\d{2}\b',  # 4xx and 5xx HTTP codes
        'timeout': r'timeout|timed out|TIMEOUT',
        'connection_refused': r'connection refused|ECONNREFUSED',
        'out_of_memory': r'OutOfMemoryError|OOM|out of memory',
        'null_pointer': r'NullPointerException|null pointer|NPE',
        'database_error': r'SQLException|database error|DB error'
    }

    def __init__(self, log_file: str):
        self.log_file = log_file
        self.lines = []
        self.log_levels = Counter()
        self.error_patterns = Counter()
        self.timestamps = []

    def parse_file(self) -> bool:
        """Parse log file."""
        try:
            with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
                self.lines = f.readlines()
            return True
        except Exception as e:
            print(f"❌ Error reading file: {e}")
            return False

    def analyze_log_levels(self):
        """Count log levels."""
        for line in self.lines:
            for level, pattern in self.LOG_LEVELS.items():
                if re.search(pattern, line):
                    self.log_levels[level] += 1
                    break  # Count each line only once

    def analyze_error_patterns(self):
        """Detect common error patterns."""
        for line in self.lines:
            for pattern_name, pattern in self.ERROR_PATTERNS.items():
                if re.search(pattern, line, re.IGNORECASE):
                    self.error_patterns[pattern_name] += 1

    def extract_timestamps(self, timestamp_pattern: Optional[str] = None):
        """Extract timestamps from logs."""
        if not timestamp_pattern:
            # Common timestamp patterns
            patterns = [
                r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}',  # ISO format
                r'\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2}',  # Apache format
                r'\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}',  # Syslog format
            ]
        else:
            patterns = [timestamp_pattern]

        for line in self.lines:
            for pattern in patterns:
                match = re.search(pattern, line)
                if match:
                    self.timestamps.append(match.group())
                    break

    def find_error_lines(self, context: int = 2) -> List[Dict[str, Any]]:
        """Find error lines with context."""
        errors = []

        for i, line in enumerate(self.lines):
            # Check if line contains error keywords
            is_error = any(re.search(pattern, line, re.IGNORECASE)
                          for pattern in [self.LOG_LEVELS['ERROR'], self.LOG_LEVELS['FATAL']])

            if is_error:
                # Get context lines
                start = max(0, i - context)
                end = min(len(self.lines), i + context + 1)
                context_lines = self.lines[start:end]

                errors.append({
                    'line_number': i + 1,
                    'line': line.strip(),
                    'context': ''.join(context_lines)
                })

        return errors

    def analyze_frequency(self, time_window_minutes: int = 5) -> Dict[str, Any]:
        """Analyze log frequency over time."""
        if not self.timestamps:
            return {"error": "No timestamps found"}

        # This is a simplified version - in production you'd parse actual timestamps
        total_lines = len(self.lines)
        if self.timestamps:
            time_span = len(self.timestamps)
            avg_per_window = total_lines / max(1, time_span / time_window_minutes)
        else:
            avg_per_window = 0

        return {
            "total_lines": total_lines,
            "timestamps_found": len(self.timestamps),
            "avg_per_window": avg_per_window
        }

    def extract_unique_messages(self, pattern: str) -> List[str]:
        """Extract unique messages matching a pattern."""
        matches = []
        seen = set()

        for line in self.lines:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                msg = match.group() if match.lastindex is None else match.group(1)
                if msg not in seen:
                    matches.append(msg)
                    seen.add(msg)

        return matches

    def find_stack_traces(self) -> List[Dict[str, Any]]:
        """Extract complete stack traces."""
        stack_traces = []
        current_trace = []
        in_trace = False

        for i, line in enumerate(self.lines):
            # Start of stack trace
            if re.search(r'Exception|Error.*:', line):
                if current_trace:
                    stack_traces.append({
                        'line_start': i - len(current_trace) + 1,
                        'trace': '\n'.join(current_trace)
                    })
                current_trace = [line.strip()]
                in_trace = True
            # Stack trace continuation
            elif in_trace and re.search(r'^\s+at\s+', line):
                current_trace.append(line.strip())
            # End of stack trace
            elif in_trace:
                if current_trace:
                    stack_traces.append({
                        'line_start': i - len(current_trace) + 1,
                        'trace': '\n'.join(current_trace)
                    })
                current_trace = []
                in_trace = False

        # Add last trace if exists
        if current_trace:
            stack_traces.append({
                'line_start': len(self.lines) - len(current_trace) + 1,
                'trace': '\n'.join(current_trace)
            })

        return stack_traces


def print_analysis_results(analyzer: LogAnalyzer, show_errors: bool = False,
                           show_traces: bool = False):
    """Print analysis results."""
    print("\n" + "="*60)
    print("📝 LOG ANALYSIS RESULTS")
    print("="*60)

    print(f"\n📁 File: {analyzer.log_file}")
    print(f"📊 Total Lines: {len(analyzer.lines):,}")

    # Log levels
    if analyzer.log_levels:
        print(f"\n{'='*60}")
        print("📊 LOG LEVEL DISTRIBUTION:")
        print(f"{'='*60}")

        level_emoji = {
            'FATAL': '🔴',
            'ERROR': '❌',
            'WARN': '⚠️',
            'INFO': 'ℹ️',
            'DEBUG': '🐛'
        }

        for level, count in analyzer.log_levels.most_common():
            emoji = level_emoji.get(level, '•')
            percentage = (count / len(analyzer.lines)) * 100
            print(f"{emoji} {level:10s}: {count:6,} ({percentage:5.1f}%)")

    # Error patterns
    if analyzer.error_patterns:
        print(f"\n{'='*60}")
        print("🔍 ERROR PATTERNS DETECTED:")
        print(f"{'='*60}")

        for pattern, count in analyzer.error_patterns.most_common(10):
            print(f"• {pattern:20s}: {count:,} occurrences")

    # Timestamps
    if analyzer.timestamps:
        print(f"\n{'='*60}")
        print(f"⏰ Timestamps Found: {len(analyzer.timestamps):,}")
        print(f"   First: {analyzer.timestamps[0]}")
        print(f"   Last:  {analyzer.timestamps[-1]}")

    # Error lines
    if show_errors:
        errors = analyzer.find_error_lines(context=1)
        if errors:
            print(f"\n{'='*60}")
            print(f"❌ ERROR LINES (showing first 10 of {len(errors)}):")
            print(f"{'='*60}")

            for error in errors[:10]:
                print(f"\nLine {error['line_number']}:")
                print(f"  {error['line']}")

    # Stack traces
    if show_traces:
        traces = analyzer.find_stack_traces()
        if traces:
            print(f"\n{'='*60}")
            print(f"📚 STACK TRACES FOUND: {len(traces)}")
            print(f"{'='*60}")

            for i, trace in enumerate(traces[:5], 1):
                print(f"\nTrace {i} (starting at line {trace['line_start']}):")
                print(trace['trace'])
                if i < len(traces):
                    print("\n" + "-"*60)

    print("\n" + "="*60)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze log files for errors, patterns, and anomalies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic analysis
  python3 log_analyzer.py application.log

  # Show error lines with context
  python3 log_analyzer.py application.log --show-errors

  # Show stack traces
  python3 log_analyzer.py application.log --show-traces

  # Full analysis
  python3 log_analyzer.py application.log --show-errors --show-traces

Features:
  • Log level distribution (ERROR, WARN, INFO, DEBUG, FATAL)
  • Common error pattern detection
  • Timestamp extraction
  • Error line identification with context
  • Stack trace extraction
  • Frequency analysis
        """
    )

    parser.add_argument('log_file', help='Path to log file')
    parser.add_argument('--show-errors', action='store_true', help='Show error lines')
    parser.add_argument('--show-traces', action='store_true', help='Show stack traces')
    parser.add_argument('--timestamp-pattern', help='Custom regex for timestamp extraction')

    args = parser.parse_args()

    if not Path(args.log_file).exists():
        print(f"❌ File not found: {args.log_file}")
        sys.exit(1)

    print(f"🔍 Analyzing log file: {args.log_file}")

    analyzer = LogAnalyzer(args.log_file)

    if not analyzer.parse_file():
        sys.exit(1)

    # Perform analysis
    analyzer.analyze_log_levels()
    analyzer.analyze_error_patterns()
    analyzer.extract_timestamps(args.timestamp_pattern)

    # Print results
    print_analysis_results(analyzer, args.show_errors, args.show_traces)


if __name__ == "__main__":
    main()
