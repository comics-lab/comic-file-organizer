#!/usr/bin/env python3
"""
Statistics calculation module for Disk-Folder-File Analyzer (DFA)
Processes file data and calculates totals, largest/smallest files by extension.
"""

from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import logging
from dataclasses import dataclass, field
from pathlib import Path

from scanner import FileInfo

logger = logging.getLogger(__name__)

@dataclass
class ExtensionStats:
    """Statistics for a specific file extension."""
    extension: str
    file_count: int = 0
    total_size: int = 0
    largest_file: Optional[FileInfo] = None
    smallest_file: Optional[FileInfo] = None
    files: List[FileInfo] = field(default_factory=list, repr=False)
    
    def add_file(self, file_info: FileInfo) -> None:
        """Add a file to the statistics."""
        self.files.append(file_info)
        self.file_count += 1
        self.total_size += file_info.size
        
        # Update largest file
        if self.largest_file is None or file_info.size > self.largest_file.size:
            self.largest_file = file_info
            
        # Update smallest file
        if self.smallest_file is None or file_info.size < self.smallest_file.size:
            self.smallest_file = file_info
    
    @property
    def average_size(self) -> float:
        """Calculate average file size."""
        return self.total_size / self.file_count if self.file_count > 0 else 0

@dataclass
class ScanStatistics:
    """Complete statistics for a directory scan."""
    extension_stats: Dict[str, ExtensionStats] = field(default_factory=dict)
    total_files: int = 0
    total_size: int = 0
    largest_file_overall: Optional[FileInfo] = None
    smallest_file_overall: Optional[FileInfo] = None
    scan_path: str = ""
    
    def get_sorted_extensions(self, sort_by: str = 'size') -> List[str]:
        """
        Get extensions sorted by specified criteria.
        
        Args:
            sort_by: Sort criteria ('size', 'count', 'extension')
            
        Returns:
            List of extension names sorted by criteria
        """
        if sort_by == 'size':
            return sorted(self.extension_stats.keys(), 
                         key=lambda x: self.extension_stats[x].total_size, 
                         reverse=True)
        elif sort_by == 'count':
            return sorted(self.extension_stats.keys(), 
                         key=lambda x: self.extension_stats[x].file_count, 
                         reverse=True)
        elif sort_by == 'extension':
            return sorted(self.extension_stats.keys())
        else:
            return list(self.extension_stats.keys())

class StatisticsCalculator:
    """Calculates file statistics from scanner data."""
    
    def __init__(self):
        """Initialize statistics calculator."""
        self.stats = ScanStatistics()
        
    def process_files(self, files: List[FileInfo], scan_path: str = "") -> ScanStatistics:
        """
        Process a list of files and calculate statistics.
        
        Args:
            files: List of FileInfo objects
            scan_path: Path that was scanned
            
        Returns:
            ScanStatistics object with calculated statistics
        """
        logger.info(f"Processing {len(files)} files for statistics")
        
        self.stats = ScanStatistics(scan_path=scan_path)
        
        for file_info in files:
            self._process_single_file(file_info)
            
        logger.info(f"Statistics calculated for {self.stats.total_files} files with {len(self.stats.extension_stats)} different extensions")
        
        return self.stats
    
    def process_files_streaming(self, file_generator, scan_path: str = "") -> ScanStatistics:
        """
        Process files from a generator/iterator for memory efficiency.
        
        Args:
            file_generator: Generator yielding FileInfo objects
            scan_path: Path that was scanned
            
        Returns:
            ScanStatistics object with calculated statistics
        """
        logger.info("Processing files for statistics (streaming mode)")
        
        self.stats = ScanStatistics(scan_path=scan_path)
        
        try:
            for file_info in file_generator:
                self._process_single_file(file_info)
                
                # Log progress every 1000 files
                if self.stats.total_files % 1000 == 0:
                    logger.debug(f"Processed {self.stats.total_files} files...")
                    
        except Exception as e:
            logger.error(f"Error processing files: {e}")
            raise
            
        logger.info(f"Statistics calculated for {self.stats.total_files} files with {len(self.stats.extension_stats)} different extensions")
        
        return self.stats
    
    def _process_single_file(self, file_info: FileInfo) -> None:
        """
        Process a single file and update statistics.
        
        Args:
            file_info: FileInfo object to process
        """
        # Update overall statistics
        self.stats.total_files += 1
        self.stats.total_size += file_info.size
        
        # Update overall largest/smallest files
        if (self.stats.largest_file_overall is None or 
            file_info.size > self.stats.largest_file_overall.size):
            self.stats.largest_file_overall = file_info
            
        if (self.stats.smallest_file_overall is None or 
            file_info.size < self.stats.smallest_file_overall.size):
            self.stats.smallest_file_overall = file_info
        
        # Update extension-specific statistics
        extension = file_info.extension
        if extension not in self.stats.extension_stats:
            self.stats.extension_stats[extension] = ExtensionStats(extension=extension)
            
        self.stats.extension_stats[extension].add_file(file_info)
    
    def get_summary(self) -> Dict:
        """
        Get a summary of the statistics.
        
        Returns:
            Dictionary with summary information
        """
        return {
            'total_files': self.stats.total_files,
            'total_size': self.stats.total_size,
            'unique_extensions': len(self.stats.extension_stats),
            'largest_file': {
                'name': self.stats.largest_file_overall.name if self.stats.largest_file_overall else None,
                'size': self.stats.largest_file_overall.size if self.stats.largest_file_overall else 0,
                'path': str(self.stats.largest_file_overall.path) if self.stats.largest_file_overall else None
            },
            'smallest_file': {
                'name': self.stats.smallest_file_overall.name if self.stats.smallest_file_overall else None,
                'size': self.stats.smallest_file_overall.size if self.stats.smallest_file_overall else 0,
                'path': str(self.stats.smallest_file_overall.path) if self.stats.smallest_file_overall else None
            }
        }
    
    def get_top_extensions(self, count: int = 10, sort_by: str = 'size') -> List[ExtensionStats]:
        """
        Get top extensions by specified criteria.
        
        Args:
            count: Number of top extensions to return
            sort_by: Sort criteria ('size', 'count')
            
        Returns:
            List of ExtensionStats objects
        """
        sorted_extensions = self.stats.get_sorted_extensions(sort_by)
        top_extensions = sorted_extensions[:count]
        
        return [self.stats.extension_stats[ext] for ext in top_extensions]

def format_size(size_bytes: int, human_readable: bool = True) -> str:
    """
    Format file size for display.
    
    Args:
        size_bytes: Size in bytes
        human_readable: Whether to format in human-readable units
        
    Returns:
        Formatted size string
    """
    if not human_readable:
        return str(size_bytes)
        
    if size_bytes == 0:
        return "0 B"
        
    # Define size units
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    size = float(size_bytes)
    unit_index = 0
    
    while size >= 1024.0 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1
    
    # Format with appropriate precision
    if unit_index == 0:  # Bytes
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.1f} {units[unit_index]}"

if __name__ == "__main__":
    # Test the statistics calculator
    import sys
    from scanner import DirectoryScanner
    
    logging.basicConfig(level=logging.INFO)
    
    test_path = sys.argv[1] if len(sys.argv) > 1 else "."
    
    print(f"Analyzing directory: {test_path}")
    
    # Scan directory
    scanner = DirectoryScanner(exclude_hidden=True)
    calculator = StatisticsCalculator()
    
    try:
        # Process files and calculate statistics
        stats = calculator.process_files_streaming(
            scanner.scan_directory(test_path), 
            test_path
        )
        
        # Display summary
        summary = calculator.get_summary()
        print(f"\nSummary:")
        print(f"  Total files: {summary['total_files']}")
        print(f"  Total size: {format_size(summary['total_size'])}")
        print(f"  Unique extensions: {summary['unique_extensions']}")
        
        if summary['largest_file']['name']:
            print(f"  Largest file: {summary['largest_file']['name']} ({format_size(summary['largest_file']['size'])})")
        
        if summary['smallest_file']['name']:
            print(f"  Smallest file: {summary['smallest_file']['name']} ({format_size(summary['smallest_file']['size'])})")
        
        # Show top 5 extensions by size
        print(f"\nTop 5 extensions by size:")
        top_extensions = calculator.get_top_extensions(5, 'size')
        for ext_stats in top_extensions:
            print(f"  {ext_stats.extension}: {ext_stats.file_count} files, {format_size(ext_stats.total_size)}")
            
    except KeyboardInterrupt:
        print("\nAnalysis interrupted by user")
    except Exception as e:
        print(f"Error: {e}")