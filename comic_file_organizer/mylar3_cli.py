"""
CLI for Mylar3 collection statistics.

Usage:
    python3 -m comic_file_organizer.mylar3_cli /path/to/config.ini
"""
import sys
import argparse
import logging
from pathlib import Path
from typing import Dict
from collections import defaultdict
try:
    from comic_file_organizer.mylar3_config import load_config
    from comic_file_organizer.mylar3_scanner import Mylar3Scanner, SeriesInfo
    from comic_file_organizer.mylar3_stats import calculate_statistics
except ModuleNotFoundError:
    from mylar3_config import load_config
    from mylar3_scanner import Mylar3Scanner, SeriesInfo
    from mylar3_stats import calculate_statistics


def format_table_row(columns, widths):
    """Format a table row with proper column widths"""
    return " | ".join(str(col).ljust(width) for col, width in zip(columns, widths))


def format_separator(widths):
    """Create a separator line for table"""
    return "-+-".join("-" * width for width in widths)


def format_size(size_bytes: int) -> str:
    """
    Format file size in bytes to human-readable format (B, KB, MB, GB).
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted string like "250MB" or "2.8GB"
    """
    if size_bytes == 0:
        return "0B"
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            if unit == 'B':
                return f"{int(size_bytes)}{unit}"
            else:
                return f"{size_bytes:.1f}{unit}".rstrip('0').rstrip('.')
        size_bytes /= 1024.0
    
    return f"{size_bytes:.1f}PB"


def print_publisher_detail_report(scan_results, publisher_name: str):
    """
    Print detailed report for a specific publisher showing file types and sizes per series.
    
    Format matches the example:
    Publisher    | Series | types | Sizes
    --------------------------------------------------
    Marvel        | 4          
      Spider-man  | CBR |   14 | 250MB |  TTL
                          | CBZ |  122| 2.8GB    | 3.1GB
    """
    # Find publisher (case-insensitive)
    publisher_lower = publisher_name.lower()
    matching_publisher = None
    for pub in scan_results.publishers:
        if pub.lower() == publisher_lower:
            matching_publisher = pub
            break
    
    if not matching_publisher:
        print(f"Error: Publisher '{publisher_name}' not found in collection.")
        print(f"Available publishers: {', '.join(sorted(scan_results.publishers))}")
        return
    
    # Get all series for this publisher
    publisher_series = [s for s in scan_results.series if s.publisher.lower() == publisher_lower]
    publisher_series.sort(key=lambda s: s.series_name.lower())
    
    if not publisher_series:
        print(f"No series found for publisher '{matching_publisher}'")
        return
    
    # Calculate totals
    total_series = len(publisher_series)
    total_by_type: Dict[str, int] = defaultdict(int)  # Count by type
    total_size_by_type: Dict[str, int] = defaultdict(int)  # Size by type
    
    for series in publisher_series:
        for file_type, count in series.file_type_counts.items():
            total_by_type[file_type] += count
        for file_type, size in series.file_type_sizes.items():
            total_size_by_type[file_type] += size
    
    # Print header
    print("=" * 70)
    print(f"PUBLISHER DETAIL REPORT: {matching_publisher}")
    print("=" * 70)
    print()
    
    # Print publisher summary line (matches example style)
    print(f"{'Publisher':<20} | {'Series':>5}")
    print("-" * 70)
    print(f"{matching_publisher:<20} | {total_series:>5}")
    print()
    
    # Print each series with file type breakdown
    for series in publisher_series:
        # Series name line
        series_display = series.series_name
        if series.year:
            series_display += f" ({series.year})"
        
        # Get all file types for this series, sorted
        file_types = sorted(set(series.file_type_counts.keys()) | set(series.file_type_sizes.keys()))
        
        if not file_types:
            print(f"  {series_display}")
            print("    (no comic files)")
            print()
            continue
        
        # Print series name
        print(f"  {series_display}")
        
        # Print file type rows (indented, matching example style)
        for file_type in file_types:
            count = series.file_type_counts.get(file_type, 0)
            size_bytes = series.file_type_sizes.get(file_type, 0)
            size_str = format_size(size_bytes)
            print(f"    {'':>20} | {file_type:>3} | {count:>5} | {size_str:>10}")
        
        # Print series total (TTL)
        series_total = series.total_size_bytes
        series_total_str = format_size(series_total)
        print(f"    {'':>20} {'TTL':>3} {'':>5} {series_total_str:>10}")
        print()
    
    # Print publisher totals
    print("-" * 70)
    all_types = sorted(set(total_by_type.keys()) | set(total_size_by_type.keys()))
    
    if all_types:
        # Print header for totals
        print(f"{'Publisher Totals':>20} |", end="")
        for file_type in all_types:
            print(f" {file_type:>3} |", end="")
        print(f" {'Total':>10}")
        
        # Print counts
        print(f"{'':>20} |", end="")
        for file_type in all_types:
            count = total_by_type.get(file_type, 0)
            print(f" {count:>5} |", end="")
        print()
        
        # Print sizes
        print(f"{'':>20} |", end="")
        for file_type in all_types:
            size_bytes = total_size_by_type.get(file_type, 0)
            size_str = format_size(size_bytes)
            print(f" {size_str:>10} |", end="")
        
        # Grand total
        grand_total = sum(total_size_by_type.values())
        grand_total_str = format_size(grand_total)
        print(f" {grand_total_str:>10}")
    
    print("=" * 70)
    print()


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
  %(prog)s /path/to/mylar3/config.ini --publisher Marvel
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
    
    parser.add_argument(
        '--publisher',
        type=str,
        help='Generate detailed report for a specific publisher (case-insensitive)'
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
        
        # Check if detailed publisher report requested
        if args.publisher:
            print_publisher_detail_report(scan_results, args.publisher)
        else:
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
