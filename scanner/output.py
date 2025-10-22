#!/usr/bin/env python3
"""
Output formatting module for Disk-Folder-File Analyzer (DFA)
Formats and displays tabulated results with headers.
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from stats import ScanStatistics, ExtensionStats, format_size

logger = logging.getLogger(__name__)

class TableFormatter:
    """Formats data into tabulated output with headers."""
    
    def __init__(self, human_readable_sizes: bool = True):
        """
        Initialize table formatter.
        
        Args:
            human_readable_sizes: Whether to format sizes in human-readable units
        """
        self.human_readable_sizes = human_readable_sizes
        
    def format_extension_table(self, stats: ScanStatistics, sort_by: str = 'size', max_rows: Optional[int] = None) -> str:
        """
        Format extension statistics as a table.
        
        Args:
            stats: ScanStatistics object containing the data
            sort_by: Sort criteria ('size', 'count', 'extension')
            max_rows: Maximum number of rows to display (None for all)
            
        Returns:
            Formatted table string
        """
        if not stats.extension_stats:
            return "No files found.\n"
            
        # Get sorted extensions
        sorted_extensions = stats.get_sorted_extensions(sort_by)
        if max_rows:
            sorted_extensions = sorted_extensions[:max_rows]
            
        # Prepare table data
        headers = ['Extension', 'File Count', 'Total Size', 'Largest File', 'Largest Size', 'Smallest File', 'Smallest Size']
        rows = []
        
        for ext in sorted_extensions:
            ext_stats = stats.extension_stats[ext]
            
            # Format file paths (show basename and truncate if necessary)
            largest_file = self._format_filename(ext_stats.largest_file.name) if ext_stats.largest_file else "N/A"
            smallest_file = self._format_filename(ext_stats.smallest_file.name) if ext_stats.smallest_file else "N/A"
            
            largest_size = format_size(ext_stats.largest_file.size, self.human_readable_sizes) if ext_stats.largest_file else "N/A"
            smallest_size = format_size(ext_stats.smallest_file.size, self.human_readable_sizes) if ext_stats.smallest_file else "N/A"
            
            row = [
                ext,
                str(ext_stats.file_count),
                format_size(ext_stats.total_size, self.human_readable_sizes),
                largest_file,
                largest_size,
                smallest_file,
                smallest_size
            ]
            rows.append(row)
        
        return self._create_table(headers, rows)
    
    def format_summary(self, stats: ScanStatistics) -> str:
        """
        Format summary statistics.
        
        Args:
            stats: ScanStatistics object containing the data
            
        Returns:
            Formatted summary string
        """
        lines = []
        lines.append("=" * 60)
        lines.append("DISK-FOLDER-FILE ANALYZER SUMMARY")
        lines.append("=" * 60)
        
        if stats.scan_path:
            lines.append(f"Scanned Path: {stats.scan_path}")
            lines.append("")
        
        lines.append(f"Total Files: {stats.total_files:,}")
        lines.append(f"Total Size: {format_size(stats.total_size, self.human_readable_sizes)}")
        lines.append(f"Unique Extensions: {len(stats.extension_stats)}")
        lines.append("")
        
        if stats.largest_file_overall:
            lines.append(f"Largest File Overall:")
            lines.append(f"  Name: {stats.largest_file_overall.name}")
            lines.append(f"  Size: {format_size(stats.largest_file_overall.size, self.human_readable_sizes)}")
            lines.append(f"  Path: {stats.largest_file_overall.path}")
            lines.append("")
        
        if stats.smallest_file_overall:
            lines.append(f"Smallest File Overall:")
            lines.append(f"  Name: {stats.smallest_file_overall.name}")
            lines.append(f"  Size: {format_size(stats.smallest_file_overall.size, self.human_readable_sizes)}")
            lines.append(f"  Path: {stats.smallest_file_overall.path}")
            lines.append("")
        
        return "\n".join(lines)
    
    def format_detailed_extension_info(self, ext_stats: ExtensionStats, show_all_files: bool = False) -> str:
        """
        Format detailed information for a specific extension.
        
        Args:
            ext_stats: ExtensionStats object for the extension
            show_all_files: Whether to show all files or just summary
            
        Returns:
            Formatted detailed information string
        """
        lines = []
        lines.append(f"Extension: {ext_stats.extension}")
        lines.append("-" * 40)
        lines.append(f"File Count: {ext_stats.file_count:,}")
        lines.append(f"Total Size: {format_size(ext_stats.total_size, self.human_readable_sizes)}")
        lines.append(f"Average Size: {format_size(int(ext_stats.average_size), self.human_readable_sizes)}")
        lines.append("")
        
        if ext_stats.largest_file:
            lines.append(f"Largest File:")
            lines.append(f"  Name: {ext_stats.largest_file.name}")
            lines.append(f"  Size: {format_size(ext_stats.largest_file.size, self.human_readable_sizes)}")
            lines.append(f"  Path: {ext_stats.largest_file.path}")
            lines.append("")
        
        if ext_stats.smallest_file:
            lines.append(f"Smallest File:")
            lines.append(f"  Name: {ext_stats.smallest_file.name}")
            lines.append(f"  Size: {format_size(ext_stats.smallest_file.size, self.human_readable_sizes)}")
            lines.append(f"  Path: {ext_stats.smallest_file.path}")
            lines.append("")
        
        if show_all_files and ext_stats.files:
            lines.append("All Files:")
            for file_info in sorted(ext_stats.files, key=lambda f: f.size, reverse=True):
                lines.append(f"  {file_info.name} - {format_size(file_info.size, self.human_readable_sizes)}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_filename(self, filename: str, max_length: int = 30) -> str:
        """
        Format filename for table display, truncating if necessary.
        
        Args:
            filename: Original filename
            max_length: Maximum length for display
            
        Returns:
            Formatted filename
        """
        if len(filename) <= max_length:
            return filename
        else:
            return filename[:max_length-3] + "..."
    
    def _create_table(self, headers: List[str], rows: List[List[str]]) -> str:
        """
        Create a formatted table with headers and data.
        
        Args:
            headers: List of header strings
            rows: List of row data (list of strings)
            
        Returns:
            Formatted table string
        """
        if not rows:
            return "No data to display.\n"
        
        # Calculate column widths
        col_widths = [len(header) for header in headers]
        
        for row in rows:
            for i, cell in enumerate(row):
                if i < len(col_widths):
                    col_widths[i] = max(col_widths[i], len(str(cell)))
        
        # Create format string
        format_str = " | ".join(f"{{:<{width}}}" for width in col_widths)
        
        # Build table
        lines = []
        
        # Header
        lines.append(format_str.format(*headers))
        lines.append("-" * (sum(col_widths) + 3 * (len(headers) - 1)))
        
        # Data rows
        for row in rows:
            # Pad row if needed
            padded_row = row + [""] * (len(headers) - len(row))
            lines.append(format_str.format(*padded_row))
        
        return "\n".join(lines) + "\n"
    
    def save_to_file(self, content: str, output_file: str) -> bool:
        """
        Save formatted content to a file.
        
        Args:
            content: Content to save
            output_file: Output file path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            output_path = Path(output_file)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Output saved to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving output to {output_file}: {e}")
            return False

class OutputManager:
    """Manages different types of output formatting and display."""
    
    def __init__(self, human_readable_sizes: bool = True, output_file: Optional[str] = None):
        """
        Initialize output manager.
        
        Args:
            human_readable_sizes: Whether to format sizes in human-readable units
            output_file: Optional file to save output to
        """
        self.formatter = TableFormatter(human_readable_sizes)
        self.output_file = output_file
        
    def display_results(self, stats: ScanStatistics, sort_by: str = 'size', show_summary: bool = True, max_extensions: Optional[int] = None) -> None:
        """
        Display complete analysis results.
        
        Args:
            stats: ScanStatistics object with analysis results
            sort_by: Sort criteria for extensions ('size', 'count', 'extension')
            show_summary: Whether to show summary section
            max_extensions: Maximum number of extensions to display
        """
        output_lines = []
        
        if show_summary:
            output_lines.append(self.formatter.format_summary(stats))
            output_lines.append("")
        
        output_lines.append("EXTENSION ANALYSIS")
        output_lines.append("=" * 60)
        output_lines.append("")
        
        table = self.formatter.format_extension_table(stats, sort_by, max_extensions)
        output_lines.append(table)
        
        if max_extensions and len(stats.extension_stats) > max_extensions:
            remaining = len(stats.extension_stats) - max_extensions
            output_lines.append(f"... and {remaining} more extensions")
            output_lines.append("")
        
        # Combine all output
        full_output = "\n".join(output_lines)
        
        # Display to console
        print(full_output)
        
        # Save to file if specified
        if self.output_file:
            self.formatter.save_to_file(full_output, self.output_file)
    
    def display_extension_details(self, stats: ScanStatistics, extension: str, show_all_files: bool = False) -> None:
        """
        Display detailed information for a specific extension.
        
        Args:
            stats: ScanStatistics object with analysis results
            extension: Extension to show details for
            show_all_files: Whether to show all files for the extension
        """
        if extension not in stats.extension_stats:
            print(f"Extension '{extension}' not found in analysis results.")
            return
        
        ext_stats = stats.extension_stats[extension]
        details = self.formatter.format_detailed_extension_info(ext_stats, show_all_files)
        
        print(details)
        
        if self.output_file:
            self.formatter.save_to_file(details, f"{extension}_{self.output_file}")

if __name__ == "__main__":
    # Test the output formatter
    import sys
    from scanner import DirectoryScanner
    from stats import StatisticsCalculator
    
    logging.basicConfig(level=logging.INFO)
    
    test_path = sys.argv[1] if len(sys.argv) > 1 else "."
    
    print(f"Testing output formatter with directory: {test_path}")
    
    try:
        # Scan and analyze
        scanner = DirectoryScanner(exclude_hidden=True)
        calculator = StatisticsCalculator()
        stats = calculator.process_files_streaming(scanner.scan_directory(test_path), test_path)
        
        # Display results
        output_manager = OutputManager(human_readable_sizes=True)
        output_manager.display_results(stats, sort_by='size', max_extensions=10)
        
    except Exception as e:
        print(f"Error: {e}")