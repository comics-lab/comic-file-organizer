"""
Statistical analysis for Mylar3 comic collections.

Provides detailed breakdowns and insights from scan results.
"""
from typing import List, Dict, Tuple
from dataclasses import dataclass
from collections import defaultdict
try:
    from comic_file_organizer.mylar3_scanner import ScanResults, SeriesInfo
except ModuleNotFoundError:
    from mylar3_scanner import ScanResults, SeriesInfo


@dataclass
class PublisherStats:
    """Statistics for a single publisher"""
    name: str
    total_series: int
    series_with_issues: int
    series_followed_only: int
    complete_series: int
    total_issues_owned: int
    total_missing_issues: int
    
    @property
    def average_completion(self) -> float:
        """Average completion percentage across all series"""
        if self.total_series == 0:
            return 0.0
        # This is calculated when the object is created
        return getattr(self, '_avg_completion', 0.0)


@dataclass
class CollectionStatistics:
    """Comprehensive statistics for entire collection"""
    scan_results: ScanResults
    publishers: Dict[str, PublisherStats]
    
    @property
    def total_publishers(self) -> int:
        return len(self.publishers)
    
    @property
    def publishers_with_series(self) -> int:
        return sum(1 for p in self.publishers.values() if p.total_series > 0)
    
    @property
    def total_series(self) -> int:
        return self.scan_results.total_series
    
    @property
    def series_with_issues(self) -> int:
        return self.scan_results.series_with_issues
    
    @property
    def series_followed_only(self) -> int:
        return self.scan_results.series_followed_only
    
    @property
    def complete_series(self) -> int:
        return self.scan_results.complete_series_count
    
    @property
    def total_issues_owned(self) -> int:
        return self.scan_results.total_issues_owned
    
    @property
    def total_missing_issues(self) -> int:
        return self.scan_results.total_missing_issues
    
    @property
    def average_issues_per_series(self) -> float:
        """Average number of issues owned per series (excluding followed-only)"""
        series_with_issues = [s for s in self.scan_results.series if s.issues_owned > 0]
        if not series_with_issues:
            return 0.0
        return sum(s.issues_owned for s in series_with_issues) / len(series_with_issues)
    
    @property
    def overall_completion_percentage(self) -> float:
        """Overall completion percentage across all series"""
        total_expected = sum(s.total_issues for s in self.scan_results.series)
        if total_expected == 0:
            return 0.0
        return (self.total_issues_owned / total_expected) * 100.0
    
    def get_largest_publishers(self, limit: int = 5) -> List[Tuple[str, int]]:
        """Get publishers with most series"""
        sorted_publishers = sorted(
            self.publishers.items(),
            key=lambda x: x[1].total_series,
            reverse=True
        )
        return [(name, stats.total_series) for name, stats in sorted_publishers[:limit]]
    
    def get_most_complete_series(self, limit: int = 10) -> List[SeriesInfo]:
        """Get series closest to completion (but not 100%)"""
        incomplete = [s for s in self.scan_results.series if not s.is_complete and s.issues_owned > 0]
        sorted_series = sorted(incomplete, key=lambda s: s.completion_percentage, reverse=True)
        return sorted_series[:limit]
    
    def get_most_incomplete_series(self, limit: int = 10) -> List[SeriesInfo]:
        """Get series with most missing issues"""
        with_issues = [s for s in self.scan_results.series if s.issues_owned > 0]
        sorted_series = sorted(with_issues, key=lambda s: s.missing_issues, reverse=True)
        return sorted_series[:limit]
    
    def get_recently_started_series(self, limit: int = 10) -> List[SeriesInfo]:
        """Get series with fewest issues owned (but at least one)"""
        with_issues = [s for s in self.scan_results.series if s.issues_owned > 0]
        sorted_series = sorted(with_issues, key=lambda s: s.issues_owned)
        return sorted_series[:limit]


def calculate_statistics(scan_results: ScanResults) -> CollectionStatistics:
    """
    Calculate comprehensive statistics from scan results.
    
    Args:
        scan_results: Results from Mylar3Scanner.scan()
        
    Returns:
        CollectionStatistics object with all calculated stats
    """
    # Group series by publisher
    publisher_series: Dict[str, List[SeriesInfo]] = defaultdict(list)
    for series in scan_results.series:
        publisher_series[series.publisher].append(series)
    
    # Calculate per-publisher statistics
    publisher_stats: Dict[str, PublisherStats] = {}
    for publisher_name, series_list in publisher_series.items():
        total_series = len(series_list)
        series_with_issues = sum(1 for s in series_list if s.issues_owned > 0)
        series_followed = sum(1 for s in series_list if s.is_followed_only)
        complete = sum(1 for s in series_list if s.is_complete)
        issues_owned = sum(s.issues_owned for s in series_list)
        missing = sum(s.missing_issues for s in series_list)
        
        # Calculate average completion
        if series_with_issues > 0:
            avg_completion = sum(s.completion_percentage for s in series_list if s.issues_owned > 0) / series_with_issues
        else:
            avg_completion = 0.0
        
        stats = PublisherStats(
            name=publisher_name,
            total_series=total_series,
            series_with_issues=series_with_issues,
            series_followed_only=series_followed,
            complete_series=complete,
            total_issues_owned=issues_owned,
            total_missing_issues=missing
        )
        # Store average as private attribute
        stats._avg_completion = avg_completion
        publisher_stats[publisher_name] = stats
    
    return CollectionStatistics(
        scan_results=scan_results,
        publishers=publisher_stats
    )


if __name__ == "__main__":
    # Test statistics calculation
    import sys
    from mylar3_config import load_config
    from mylar3_scanner import Mylar3Scanner
    
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    else:
        config_path = "/home/rmleonard/projects/Home Projects/comics-lab/mylar3-test/config.ini"
    
    try:
        # Load and scan
        config = load_config(config_path)
        scanner = Mylar3Scanner(config.destination_dir)
        scan_results = scanner.scan()
        
        # Calculate statistics
        stats = calculate_statistics(scan_results)
        
        print("=== COLLECTION STATISTICS ===\n")
        print(f"Total Publishers: {stats.total_publishers}")
        print(f"Publishers with Series: {stats.publishers_with_series}\n")
        
        print(f"Total Series: {stats.total_series}")
        print(f"  Series with issues: {stats.series_with_issues}")
        print(f"  Series followed only: {stats.series_followed_only}")
        print(f"  Complete series: {stats.complete_series}\n")
        
        print(f"Total Issues Owned: {stats.total_issues_owned}")
        print(f"Total Missing Issues: {stats.total_missing_issues}")
        print(f"Overall Completion: {stats.overall_completion_percentage:.1f}%")
        print(f"Average Issues per Series: {stats.average_issues_per_series:.1f}\n")
        
        # Publisher breakdown
        print("=== BY PUBLISHER ===")
        for pub_name, pub_stats in sorted(stats.publishers.items()):
            print(f"\n{pub_name}:")
            print(f"  Total series: {pub_stats.total_series}")
            print(f"  Series with issues: {pub_stats.series_with_issues}")
            print(f"  Complete series: {pub_stats.complete_series}")
            print(f"  Issues owned: {pub_stats.total_issues_owned}")
            print(f"  Missing issues: {pub_stats.total_missing_issues}")
            if hasattr(pub_stats, '_avg_completion'):
                print(f"  Average completion: {pub_stats._avg_completion:.1f}%")
        
        # Most complete series
        print("\n=== MOST COMPLETE SERIES (NOT 100%) ===")
        for series in stats.get_most_complete_series(5):
            print(f"  {series.series_name} ({series.year}): {series.issues_owned}/{series.total_issues} ({series.completion_percentage:.1f}%)")
        
        # Most incomplete series
        print("\n=== MOST INCOMPLETE SERIES ===")
        for series in stats.get_most_incomplete_series(5):
            print(f"  {series.series_name} ({series.year}): {series.issues_owned}/{series.total_issues} (missing {series.missing_issues})")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
