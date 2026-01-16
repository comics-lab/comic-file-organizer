"""
Mylar3 collection scanner for comic-file-organizer.

Scans the destination_dir hierarchy:
- Level 1: Publishers (directories)
- Level 2: Series/Volumes (directories with series.json)
- Level 3: Issues (CBR/CBZ files)

Collects data for statistical analysis.
"""
import os
import json
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple


logger = logging.getLogger(__name__)


@dataclass
class SeriesInfo:
    """Information about a comic series"""
    publisher: str
    series_name: str
    series_path: str
    year: Optional[int]
    total_issues: int
    issues_owned: int
    comicid: Optional[int] = None
    status: Optional[str] = None  # "Continuing" or "Ended"
    publication_run: Optional[str] = None
    file_type_counts: Dict[str, int] = field(default_factory=dict)  # e.g., {'CBR': 14, 'CBZ': 122}
    file_type_sizes: Dict[str, int] = field(default_factory=dict)  # e.g., {'CBR': 262144000, 'CBZ': 3006477107}
    
    @property
    def missing_issues(self) -> int:
        """Calculate number of missing issues"""
        return max(0, self.total_issues - self.issues_owned)
    
    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage"""
        if self.total_issues == 0:
            return 0.0
        return (self.issues_owned / self.total_issues) * 100.0
    
    @property
    def is_complete(self) -> bool:
        """Check if series is complete"""
        return self.issues_owned >= self.total_issues
    
    @property
    def is_followed_only(self) -> bool:
        """Check if series is followed but has no issues"""
        return self.issues_owned == 0
    
    @property
    def total_size_bytes(self) -> int:
        """Total size of all comic files in bytes"""
        return sum(self.file_type_sizes.values())


@dataclass
class ScanResults:
    """Results from scanning Mylar3 collection"""
    destination_dir: str
    publishers: List[str] = field(default_factory=list)
    series: List[SeriesInfo] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    @property
    def total_publishers(self) -> int:
        return len(self.publishers)
    
    @property
    def total_series(self) -> int:
        return len(self.series)
    
    @property
    def series_with_issues(self) -> int:
        return sum(1 for s in self.series if s.issues_owned > 0)
    
    @property
    def series_followed_only(self) -> int:
        return sum(1 for s in self.series if s.is_followed_only)
    
    @property
    def complete_series_count(self) -> int:
        return sum(1 for s in self.series if s.is_complete)
    
    @property
    def total_issues_owned(self) -> int:
        return sum(s.issues_owned for s in self.series)
    
    @property
    def total_missing_issues(self) -> int:
        return sum(s.missing_issues for s in self.series)


class Mylar3Scanner:
    """Scanner for Mylar3 comic collection"""
    
    COMIC_EXTENSIONS = {'.cbz', '.cbr'}
    METADATA_FILES = {'series.json', 'cvinfo'}
    
    def __init__(self, destination_dir: str):
        self.destination_dir = destination_dir
        
    def scan(self) -> ScanResults:
        """
        Scan the Mylar3 collection and return results.
        
        Returns:
            ScanResults object with all collected data
        """
        results = ScanResults(destination_dir=self.destination_dir)
        
        if not os.path.exists(self.destination_dir):
            results.errors.append(f"destination_dir does not exist: {self.destination_dir}")
            return results
        
        # Scan publisher directories
        try:
            for entry in os.listdir(self.destination_dir):
                # Skip .zzz_check and other files
                if entry.startswith('.'):
                    continue
                
                publisher_path = os.path.join(self.destination_dir, entry)
                
                # Only process directories
                if not os.path.isdir(publisher_path):
                    logger.warning(f"Unexpected file at publisher level: {entry}")
                    continue
                
                # Check if publisher has any series subdirectories
                has_series = False
                for series_entry in os.listdir(publisher_path):
                    series_path = os.path.join(publisher_path, series_entry)
                    if os.path.isdir(series_path):
                        has_series = True
                        break
                
                # Skip publishers with no series
                if not has_series:
                    logger.debug(f"Skipping publisher with no series: {entry}")
                    continue
                
                # Add publisher
                results.publishers.append(entry)
                
                # Scan series in this publisher
                self._scan_publisher(entry, publisher_path, results)
                
        except Exception as e:
            results.errors.append(f"Error scanning destination_dir: {e}")
            logger.error(f"Error scanning {self.destination_dir}: {e}")
        
        return results
    
    def _scan_publisher(self, publisher_name: str, publisher_path: str, results: ScanResults):
        """Scan all series under a publisher directory"""
        try:
            for series_entry in os.listdir(publisher_path):
                series_path = os.path.join(publisher_path, series_entry)
                
                # Only process directories
                if not os.path.isdir(series_path):
                    logger.warning(f"Unexpected file in publisher directory: {series_entry}")
                    continue
                
                # Process the series
                series_info = self._scan_series(publisher_name, series_entry, series_path)
                if series_info:
                    results.series.append(series_info)
                    
        except Exception as e:
            results.errors.append(f"Error scanning publisher {publisher_name}: {e}")
            logger.error(f"Error scanning publisher {publisher_name}: {e}")
    
    def _scan_series(self, publisher_name: str, series_dirname: str, series_path: str) -> Optional[SeriesInfo]:
        """
        Scan a series directory and extract metadata.
        
        Returns:
            SeriesInfo object or None if series.json is missing
        """
        # Check for series.json
        series_json_path = os.path.join(series_path, 'series.json')
        if not os.path.exists(series_json_path):
            logger.warning(f"No series.json found in: {series_path}")
            return None
        
        # Parse series.json
        try:
            with open(series_json_path, 'r', encoding='utf-8') as f:
                series_data = json.load(f)
            
            metadata = series_data.get('metadata', {})
            series_name = metadata.get('name', series_dirname)
            year = metadata.get('year')
            total_issues = metadata.get('total_issues', 0)
            comicid = metadata.get('comicid')
            status = metadata.get('status')
            publication_run = metadata.get('publication_run')
            
        except Exception as e:
            logger.error(f"Error parsing series.json in {series_path}: {e}")
            return None
        
        # Count comic files and collect file type information
        file_counts, file_sizes = self._analyze_comic_files(series_path)
        issues_owned = sum(file_counts.values())
        
        return SeriesInfo(
            publisher=publisher_name,
            series_name=series_name,
            series_path=series_path,
            year=year,
            total_issues=total_issues,
            issues_owned=issues_owned,
            comicid=comicid,
            status=status,
            publication_run=publication_run,
            file_type_counts=file_counts,
            file_type_sizes=file_sizes
        )
    
    def _analyze_comic_files(self, series_path: str) -> Tuple[Dict[str, int], Dict[str, int]]:
        """
        Analyze comic files in series directory, returning counts and sizes by file type.
        
        Returns:
            Tuple of (file_type_counts, file_type_sizes) dictionaries
            e.g., ({'CBR': 14, 'CBZ': 122}, {'CBR': 262144000, 'CBZ': 3006477107})
        """
        file_counts: Dict[str, int] = {}
        file_sizes: Dict[str, int] = {}
        
        try:
            for entry in os.listdir(series_path):
                # Skip metadata files
                if entry in self.METADATA_FILES:
                    continue
                
                # Check if it's a comic file
                file_path = os.path.join(series_path, entry)
                if os.path.isfile(file_path):
                    _, ext = os.path.splitext(entry)
                    ext_upper = ext.upper()
                    if ext.lower() in self.COMIC_EXTENSIONS:
                        # Get file size
                        try:
                            size = os.path.getsize(file_path)
                            # Track by uppercase extension (CBR, CBZ, etc.)
                            file_counts[ext_upper] = file_counts.get(ext_upper, 0) + 1
                            file_sizes[ext_upper] = file_sizes.get(ext_upper, 0) + size
                        except OSError as e:
                            logger.warning(f"Could not get size for {file_path}: {e}")
                            # Still count the file even if we can't get size
                            file_counts[ext_upper] = file_counts.get(ext_upper, 0) + 1
                            
        except Exception as e:
            logger.error(f"Error analyzing files in {series_path}: {e}")
        
        return file_counts, file_sizes


if __name__ == "__main__":
    # Test scanner
    import sys
    from mylar3_config import load_config
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    else:
        config_path = "/home/rmleonard/projects/Home Projects/comics-lab/mylar3-test/config.ini"
    
    try:
        # Load config
        config = load_config(config_path)
        print(f"Scanning: {config.destination_dir}\n")
        
        # Run scanner
        scanner = Mylar3Scanner(config.destination_dir)
        results = scanner.scan()
        
        # Display results
        print(f"Publishers: {results.total_publishers}")
        print(f"  {', '.join(results.publishers)}\n")
        
        print(f"Total Series: {results.total_series}")
        print(f"  Series with issues: {results.series_with_issues}")
        print(f"  Series followed only: {results.series_followed_only}")
        print(f"  Complete series: {results.complete_series_count}\n")
        
        print(f"Total Issues Owned: {results.total_issues_owned}")
        print(f"Total Missing Issues: {results.total_missing_issues}\n")
        
        # Show first few series
        if results.series:
            print("Sample series:")
            for series in results.series[:5]:
                print(f"  {series.series_name} ({series.year}): {series.issues_owned}/{series.total_issues} issues ({series.completion_percentage:.1f}%)")
        
        # Show errors
        if results.errors:
            print(f"\nErrors encountered: {len(results.errors)}")
            for error in results.errors:
                print(f"  - {error}")
                
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
