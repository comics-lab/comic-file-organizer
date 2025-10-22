#!/usr/bin/env python3
"""
Main CLI interface for Disk-Folder-File Analyzer (DFA)
Provides command-line interface with argument parsing, input sanitization, and orchestration.
"""

import argparse
import logging
import sys
import os
from pathlib import Path
from typing import Optional
from typing import Union
import signal

from config import ConfigManager
from scanner import DirectoryScanner
from stats import StatisticsCalculator
from output import OutputManager

# Global variables for graceful shutdown
interrupted: bool = False
# scanner will be an instance of DirectoryScanner or None
scanner: Optional["DirectoryScanner"] = None

def setup_logging(log_level: str, log_file: str) -> None:
    """
    Set up logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Log file path
    """
    # Convert string level to logging level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create formatters
    console_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )
    
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(max(numeric_level, logging.WARNING))  # Only show warnings+ on console
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler
    try:
        file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        
        logging.info(f"Logging initialized. Log file: {log_file}")
        
    except Exception as e:
        logging.warning(f"Could not set up file logging: {e}")

def signal_handler(signum: int, frame) -> None:
    """Handle interrupt signals for graceful shutdown."""
    global interrupted
    interrupted = True
    logging.info("Interrupt signal received. Shutting down gracefully...")
    print("\nInterrupt received. Cleaning up...")

def sanitize_directory_input(directory: str) -> Optional[str]:
    """
    Sanitize and validate directory input.
    
    Args:
        directory: Input directory path
        
    Returns:
        Sanitized directory path or None if invalid
    """
    try:
        # Strip whitespace and resolve path
        sanitized = os.path.normpath(os.path.expanduser(directory.strip()))
        
        # Check if it's an absolute path or relative path
        if not os.path.isabs(sanitized):
            # Make it relative to current working directory
            sanitized = os.path.abspath(sanitized)
        
        # Basic validation
        if not os.path.exists(sanitized):
            logging.error(f"Directory does not exist: {sanitized}")
            return None
            
        if not os.path.isdir(sanitized):
            logging.error(f"Path is not a directory: {sanitized}")
            return None
            
        if not os.access(sanitized, os.R_OK):
            logging.error(f"No read permission for directory: {sanitized}")
            return None
        
        return sanitized
        
    except Exception as e:
        logging.error(f"Error validating directory '{directory}': {e}")
        return None

def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description="Disk-Folder-File Analyzer (DFA) - Analyze file types and sizes in directories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Analyze current directory using config
  %(prog)s /path/to/directory       # Analyze specific directory
  %(prog)s -s size -m 20            # Show top 20 extensions sorted by size
  %(prog)s -o analysis.txt          # Save output to file
  %(prog)s --no-summary             # Skip summary section
  %(prog)s --extension-filter       # Use extension filter from config
  %(prog)s -v                       # Verbose output
        """)
    
    # Positional arguments
    parser.add_argument(
        'directory',
        nargs='?',
        help='Directory to analyze (uses config default if not specified)'
    )
    
    # Optional arguments
    parser.add_argument(
        '-c', '--config',
        default='config.json',
        help='Configuration file path (default: config.json)'
    )
    
    parser.add_argument(
        '-s', '--sort',
        choices=['size', 'count', 'extension'],
        default='size',
        help='Sort extensions by: size, count, or extension name (default: size)'
    )
    
    parser.add_argument(
        '-m', '--max-extensions',
        type=int,
        help='Maximum number of extensions to display (default: show all)'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Output file to save results'
    )
    
    parser.add_argument(
        '--no-summary',
        action='store_true',
        help='Skip summary section in output'
    )
    
    parser.add_argument(
        '--extension-filter',
        action='store_true',
        help='Use extension filter from configuration (overrides config setting)'
    )
    
    parser.add_argument(
        '--show-hidden',
        action='store_true',
        help='Include hidden files and directories (overrides config setting)'
    )
    
    parser.add_argument(
        '--raw-sizes',
        action='store_true',
        help='Display file sizes in raw bytes instead of human-readable format'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output (INFO level logging to console)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug output (DEBUG level logging)'
    )
    
    parser.add_argument(
        '--log-file',
        help='Custom log file path (overrides config setting)'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='DFA (Disk-Folder-File Analyzer) 1.0.0'
    )
    
    return parser

def main() -> int:
    """Main application entry point."""
    global scanner, interrupted
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Parse command line arguments
    parser = create_argument_parser()
    args = parser.parse_args()
    
    try:
        # Load configuration
        config_manager = ConfigManager(args.config)
        config = config_manager.load_config()
        
        # Set up logging
        log_level = "DEBUG" if args.debug else ("INFO" if args.verbose else config.get("log_level", "INFO"))
        log_file = args.log_file or config.get("log_file", "dfa.log")
        setup_logging(log_level, log_file)
        
        logging.info("DFA (Disk-Folder-File Analyzer) starting up")
        logging.info(f"Configuration loaded from: {args.config}")
        logging.info(f"Command line arguments: {vars(args)}")
        
        # Determine directory to analyze
        target_directory = args.directory or config.get("starting_directory", ".")
        sanitized_directory = sanitize_directory_input(target_directory)
        
        if not sanitized_directory:
            print(f"Error: Invalid directory '{target_directory}'")
            return 1
        
        logging.info(f"Target directory: {sanitized_directory}")
        
        # Configure scanner options
        exclude_hidden = not args.show_hidden and config.get("exclude_hidden_files", True)
        use_extension_filter = args.extension_filter or config.get("use_extension_list", False)
        extension_list = config.get("extension_list", [])
        
        # Create scanner
        scanner = DirectoryScanner(
            exclude_hidden=exclude_hidden,
            extension_filter=extension_list,
            use_filter=use_extension_filter
        )
        
        # Create statistics calculator
        calculator = StatisticsCalculator()
        
        # Configure output manager
        human_readable_sizes = not args.raw_sizes and config.get("human_readable_sizes", True)
        output_manager = OutputManager(
            human_readable_sizes=human_readable_sizes,
            output_file=args.output
        )
        
        # Log configuration
        logging.info(f"Exclude hidden files: {exclude_hidden}")
        logging.info(f"Use extension filter: {use_extension_filter}")
        if use_extension_filter:
            logging.info(f"Extension filter: {extension_list}")
        logging.info(f"Human readable sizes: {human_readable_sizes}")
        
        print(f"Analyzing directory: {sanitized_directory}")
        if use_extension_filter:
            print(f"Using extension filter: {', '.join(extension_list)}")
        
        # Perform analysis
        print("Scanning files...")
        
        try:
            stats = calculator.process_files_streaming(
                scanner.scan_directory(sanitized_directory),
                sanitized_directory
            )
            
            if interrupted:
                print("\nAnalysis interrupted.")
                return 130  # Standard exit code for SIGINT
            
            # Display results
            print("\nAnalysis complete!\n")
            
            output_manager.display_results(
                stats,
                sort_by=args.sort,
                show_summary=not args.no_summary,
                max_extensions=args.max_extensions
            )
            
            # Log scan statistics
            scan_stats = scanner.get_scan_stats()
            logging.info(f"Scan completed successfully: {scan_stats}")
            
            if args.output:
                print(f"\nResults saved to: {args.output}")
            
            return 0
            
        except KeyboardInterrupt:
            print("\nAnalysis interrupted by user.")
            return 130
        except Exception as e:
            logging.error(f"Error during analysis: {e}", exc_info=True)
            print(f"Error during analysis: {e}")
            return 1
    
    except Exception as e:
        # Set up basic logging if setup failed
        logging.basicConfig(level=logging.ERROR)
        logging.error(f"Fatal error: {e}", exc_info=True)
        print(f"Fatal error: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)