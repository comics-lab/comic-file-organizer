"""
CLI for Mylar3 collection statistics.

Usage:
    python3 -m comic_file_organizer.mylar3_cli /path/to/config.ini
"""
import sys
import argparse
import logging
from pathlib import Path
try:
    from comic_file_organizer.mylar3_config import load_config
    from comic_file_organizer.mylar3_scanner import Mylar3Scanner
    from comic_file_organizer.mylar3_stats import calculate_statistics
except ModuleNotFoundError:
    from mylar3_config import load_config
    from mylar3_scanner import Mylar3Scanner
    from mylar3_stats import calculate_statistics


def format_table_row(columns, widths):
    """Format a table row with proper column widths"""
    return " | ".join(str(col).ljust(width) for col, width in zip(columns, widths))


def format_separator(widths):
    """Create a separator line for table"""
    return "-+-".join("-" * width for width in widths)


def print_summary(stats):
    """Print collection summary"""
    print("=" * 70)
    print("MYLAR3 COLLECTION STATISTICS")
    print("=" * 70)
    print()
    
    print(f"Collection Path: {stats.scan_results.destination_dir}")
    print()
    
    # Publisher stats
    print(f"Total Publishers: {stats.total_publishers}")
    if stats.total_publishers > 0:
        print(f"  {', '.join(sorted(stats.publishers.keys()))}")
    print()
    
    # Series stats
    print(f"Total Series: {stats.total_series}")
    print(f"  Series with issues: {stats.series_with_issues}")
    print(f"  Series followed only: {stats.series_followed_only}")
    print(f"  Complete series: {stats.complete_series}")
    print()
    
    # Issue stats
    print(f"Total Issues Owned: {stats.total_issues_owned:,}")
    print(f"Total Missing Issues: {stats.total_missing_issues:,}")
    print(f"Overall Completion: {stats.overall_completion_percentage:.1f}%")
    if stats.series_with_issues > 0:
        print(f"Average Issues per Series: {stats.average_issues_per_series:.1f}")
    print()


def print_publisher_breakdown(stats):
    """Print per-publisher statistics table"""
    if not stats.publishers:
        return
    
    print("=" * 70)
    print("BY PUBLISHER")
    print("=" * 70)
    print()
    
    # Table headers
    headers = ["Publisher", "Series", "With Issues", "Complete", "Issues Owned", "Missing"]
    widths = [20, 8, 12, 9, 13, 10]
    
    print(format_table_row(headers, widths))
    print(format_separator(widths))
    
    # Sort publishers by name
    for pub_name in sorted(stats.publishers.keys()):
        pub_stats = stats.publishers[pub_name]
        row = [
            pub_name,
            pub_stats.total_series,
            pub_stats.series_with_issues,
            pub_stats.complete_series,
            f"{pub_stats.total_issues_owned:,}",
            f"{pub_stats.total_missing_issues:,}"
        ]
        print(format_table_row(row, widths))
    print()


def print_series_details(stats, limit=20):
    """Print detailed series information"""
    print("=" * 70)
    print(f"SERIES DETAILS (showing first {limit})")
    print("=" * 70)
    print()
    
    # Table headers
    headers = ["Series", "Year", "Owned", "Total", "Complete", "Status"]
    widths = [35, 6, 7, 7, 9, 12]
    
    print(format_table_row(headers, widths))
    print(format_separator(widths))
    
    # Sort by publisher, then series name
    sorted_series = sorted(stats.scan_results.series, key=lambda s: (s.publisher, s.series_name))
    
    for series in sorted_series[:limit]:
        # Truncate long series names
        series_display = series.series_name[:33] + "..." if len(series.series_name) > 35 else series.series_name
        
        row = [
            series_display,
            series.year or "?",
            series.issues_owned,
            series.total_issues,
            f"{series.completion_percentage:.1f}%",
            series.status or "Unknown"
        ]
        print(format_table_row(row, widths))
    
    if len(sorted_series) > limit:
        print(f"\n... and {len(sorted_series) - limit} more series")
    print()


def print_top_lists(stats):
    """Print top incomplete and most complete series"""
    print("=" * 70)
    print("MOST INCOMPLETE SERIES (by missing issue count)")
    print("=" * 70)
    print()
    
    incomplete = stats.get_most_incomplete_series(10)
    if incomplete:
        for i, series in enumerate(incomplete, 1):
            print(f"{i:2}. {series.series_name} ({series.year})")
            print(f"    {series.issues_owned}/{series.total_issues} owned, {series.missing_issues} missing ({series.completion_percentage:.1f}%)")
    else:
        print("  No series with issues found")
    print()
    
    print("=" * 70)
    print("CLOSEST TO COMPLETION (not yet complete)")
    print("=" * 70)
    print()
    
    near_complete = stats.get_most_complete_series(10)
    if near_complete:
        for i, series in enumerate(near_complete, 1):
            print(f"{i:2}. {series.series_name} ({series.year})")
            print(f"    {series.issues_owned}/{series.total_issues} owned, {series.missing_issues} missing ({series.completion_percentage:.1f}%)")
    else:
        print("  No incomplete series found")
    print()


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Analyze Mylar3 comic collection and display statistics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /path/to/mylar3/config.ini
  %(prog)s /path/to/mylar3/config.ini --verbose
  %(prog)s /path/to/mylar3/config.ini --series-limit 50
        """
    )
    
    parser.add_argument(
        'config_path',
        help='Path to Mylar3 config.ini file'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--series-limit',
        type=int,
        default=20,
        help='Maximum number of series to display in detail (default: 20)'
    )
    
    parser.add_argument(
        '--no-details',
        action='store_true',
        help='Skip detailed series listing'
    )
    
    parser.add_argument(
        '--no-top-lists',
        action='store_true',
        help='Skip top incomplete/complete lists'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format='%(levelname)s: %(message)s'
    )
    
    try:
        # Load configuration
        config = load_config(args.config_path)
        
        # Scan collection
        scanner = Mylar3Scanner(config.destination_dir)
        scan_results = scanner.scan()
        
        # Calculate statistics
        stats = calculate_statistics(scan_results)
        
        # Display results
        print_summary(stats)
        print_publisher_breakdown(stats)
        
        if not args.no_details:
            print_series_details(stats, limit=args.series_limit)
        
        if not args.no_top_lists:
            print_top_lists(stats)
        
        # Report errors if any
        if scan_results.errors:
            print("=" * 70)
            print(f"ERRORS ENCOUNTERED ({len(scan_results.errors)})")
            print("=" * 70)
            for error in scan_results.errors:
                print(f"  - {error}")
            print()
            return 1
        
        return 0
        
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
