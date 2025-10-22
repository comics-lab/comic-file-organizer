#!/usr/bin/env python3
"""
File scanner module for Disk-Folder-File Analyzer (DFA)
Recursively scans directories and collects file information.
"""

import os
import stat
from pathlib import Path
from typing import List, Dict, Optional, Generator
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class FileInfo:
    """Data class to store file information."""
    path: Path
    name: str
    extension: str
    size: int
    is_hidden: bool
    inode: Optional[int] = None
    device: Optional[int] = None
    
    def __post_init__(self):
        """Post-init processing to normalize extension."""
        if self.extension and not self.extension.startswith('.'):
            self.extension = '.' + self.extension
        if not self.extension:
            self.extension = '<no_extension>'

class DirectoryScanner:
    """Scans directories recursively and collects file information."""
    
    def __init__(self, exclude_hidden: bool = True, extension_filter: Optional[List[str]] = None, use_filter: bool = False):
        """
        Initialize directory scanner.
        
        Args:
            exclude_hidden: Whether to exclude hidden files/directories
            extension_filter: List of extensions to filter by
            use_filter: Whether to use the extension filter
        """
        self.exclude_hidden = exclude_hidden
        self.extension_filter = set(extension_filter) if extension_filter else set()
        self.use_filter = use_filter
        self.stats = {
            'total_files': 0,
            'total_size': 0,
            'directories_scanned': 0,
            'errors': 0,
            'skipped_files': 0
        }
        # Track seen inodes to avoid double-counting hardlinks (device, inode)
        self._seen_inodes = set()
        # Track seen directories by (device, inode) to avoid following symlink loops
        self._seen_dirs = set()
        
    def sanitize_path(self, path: str) -> Optional[Path]:
        """
        Sanitize and validate input path.
        
        Args:
            path: Input path string
            
        Returns:
            Path object if valid, None otherwise
        """
        try:
            # Remove any dangerous characters and resolve path
            sanitized = os.path.normpath(os.path.expanduser(path.strip()))
            path_obj = Path(sanitized).resolve()
            
            # Check if path exists and is accessible
            if not path_obj.exists():
                logger.error(f"Path does not exist: {path_obj}")
                return None
                
            if not path_obj.is_dir():
                logger.error(f"Path is not a directory: {path_obj}")
                return None
                
            # Check read permissions
            if not os.access(path_obj, os.R_OK):
                logger.error(f"No read permission for directory: {path_obj}")
                return None
                
            return path_obj
            
        except Exception as e:
            logger.error(f"Error sanitizing path '{path}': {e}")
            return None
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """
        Determine if a file should be skipped based on filters.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file should be skipped, False otherwise
        """
        # Check if hidden and should be excluded
        if self.exclude_hidden and file_path.name.startswith('.'):
            return True
            
        # Check extension filter if enabled
        if self.use_filter and self.extension_filter:
            file_extension = file_path.suffix.lower()
            if file_extension not in self.extension_filter:
                return True
                
        return False
    
    def _get_file_info(self, file_path: Path) -> Optional[FileInfo]:
        """
        Extract file information.
        
        Args:
            file_path: Path to the file
            
        Returns:
            FileInfo object or None if error
        """
        try:
            # Use stat following symlinks so we get target file size
            stat_result = file_path.stat()

            inode = getattr(stat_result, 'st_ino', None)
            device = getattr(stat_result, 'st_dev', None)

            return FileInfo(
                path=file_path,
                name=file_path.name,
                extension=file_path.suffix.lower(),
                size=stat_result.st_size,
                is_hidden=file_path.name.startswith('.'),
                inode=inode,
                device=device
            )
            
        except (OSError, IOError) as e:
            logger.warning(f"Cannot access file {file_path}: {e}")
            self.stats['errors'] += 1
            return None
        except Exception as e:
            logger.error(f"Unexpected error processing file {file_path}: {e}")
            self.stats['errors'] += 1
            return None
    
    def scan_directory(self, start_path: str) -> Generator[FileInfo, None, None]:
        """
        Scan directory recursively and yield file information.
        
        Args:
            start_path: Starting directory path
            
        Yields:
            FileInfo objects for each valid file
        """
        sanitized_path = self.sanitize_path(start_path)
        if not sanitized_path:
            logger.error(f"Cannot scan invalid path: {start_path}")
            return
            
        logger.info(f"Starting directory scan: {sanitized_path}")
        
        try:
            # followlinks=True allows os.walk to traverse symlinked directories
            for root, dirs, files in os.walk(sanitized_path, followlinks=True):
                root_path = Path(root)

                # Build new dirs list while avoiding symlink loops by checking directory inodes
                new_dirs = []
                for d in list(dirs):
                    try:
                        candidate = root_path / d
                        # stat follows symlinks and gives target's inode
                        st = candidate.stat()
                        dir_id = (getattr(st, 'st_dev', None), getattr(st, 'st_ino', None))
                        if dir_id in self._seen_dirs:
                            logger.debug(f"Skipping directory already seen (possible symlink loop): {candidate} -> {dir_id}")
                            continue
                        # Optionally skip hidden directories
                        if self.exclude_hidden and d.startswith('.'):
                            continue
                        new_dirs.append(d)
                        self._seen_dirs.add(dir_id)
                    except (OSError, IOError) as e:
                        logger.warning(f"Cannot access directory {root_path / d}: {e}")
                        self.stats['errors'] += 1
                        # don't descend into this directory
                        continue
                    except Exception as e:
                        logger.error(f"Unexpected error accessing directory {root_path / d}: {e}")
                        self.stats['errors'] += 1
                        continue

                # Modify dirs in-place so os.walk uses our pruned list
                dirs[:] = new_dirs
                
                self.stats['directories_scanned'] += 1
                
                if self.stats['directories_scanned'] % 100 == 0:
                    logger.debug(f"Scanned {self.stats['directories_scanned']} directories, found {self.stats['total_files']} files")
                
                # Process files in current directory
                for filename in files:
                    file_path = root_path / filename
                    
                    # Check if file should be skipped
                    if self._should_skip_file(file_path):
                        self.stats['skipped_files'] += 1
                        continue
                    
                    # Get file information
                    file_info = self._get_file_info(file_path)
                    if file_info:
                        # Deduplicate hardlinks by tracking (device, inode)
                        inode_id = (file_info.device, file_info.inode)
                        if file_info.inode is not None and inode_id in self._seen_inodes:
                            logger.debug(f"Skipping already seen inode: {inode_id} for file {file_path}")
                            self.stats['skipped_files'] += 1
                            continue

                        if file_info.inode is not None:
                            self._seen_inodes.add(inode_id)

                        self.stats['total_files'] += 1
                        self.stats['total_size'] += file_info.size
                        yield file_info
                        
        except KeyboardInterrupt:
            logger.info("Scan interrupted by user")
            raise
        except Exception as e:
            logger.error(f"Error during directory scan: {e}")
            raise
        
        logger.info(f"Scan completed. Processed {self.stats['total_files']} files in {self.stats['directories_scanned']} directories")
        if self.stats['skipped_files'] > 0:
            logger.info(f"Skipped {self.stats['skipped_files']} files based on filters")
        if self.stats['errors'] > 0:
            logger.warning(f"Encountered {self.stats['errors']} errors during scan")
    
    def get_scan_stats(self) -> Dict[str, int]:
        """Get scanning statistics."""
        return self.stats.copy()

if __name__ == "__main__":
    # Test the scanner
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    test_path = sys.argv[1] if len(sys.argv) > 1 else "."
    scanner = DirectoryScanner(exclude_hidden=True)
    
    print(f"Scanning: {test_path}")
    file_count = 0
    
    try:
        for file_info in scanner.scan_directory(test_path):
            file_count += 1
            if file_count <= 10:  # Show first 10 files
                print(f"  {file_info.name} ({file_info.extension}) - {file_info.size} bytes")
        
        print(f"\nScan Statistics:")
        for key, value in scanner.get_scan_stats().items():
            print(f"  {key}: {value}")
            
    except KeyboardInterrupt:
        print("\nScan interrupted by user")
    except Exception as e:
        print(f"Error: {e}")