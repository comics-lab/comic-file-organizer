"""
Mylar3 configuration parser for comic-file-organizer.

Reads and validates Mylar3's config.ini file to extract:
- destination_dir: Root of comic collection
- folder_format: Directory naming convention
- file_format: Comic file naming convention
"""
import configparser
import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class Mylar3Config:
    """Configuration data from Mylar3's config.ini"""
    config_path: str
    destination_dir: str
    folder_format: str
    file_format: str
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        if not os.path.exists(self.destination_dir):
            raise ValueError(f"destination_dir does not exist: {self.destination_dir}")
        if not os.path.isdir(self.destination_dir):
            raise ValueError(f"destination_dir is not a directory: {self.destination_dir}")


def load_config(config_path: str) -> Mylar3Config:
    """
    Load and parse Mylar3 config.ini file.
    
    Args:
        config_path: Path to Mylar3's config.ini file
        
    Returns:
        Mylar3Config object with parsed configuration
        
    Raises:
        FileNotFoundError: If config.ini doesn't exist
        ValueError: If required fields are missing or invalid
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    config = configparser.ConfigParser()
    config.read(config_path)
    
    # Validate [General] section exists
    if 'General' not in config:
        raise ValueError("Config file missing [General] section")
    
    general = config['General']
    
    # Extract required fields
    destination_dir = general.get('destination_dir')
    if not destination_dir:
        raise ValueError("Missing required field: destination_dir")
    
    folder_format = general.get('folder_format', '$Publisher/$Series $Type ($Year)')
    file_format = general.get('file_format', '$Series $VolumeN $Annual #$Issue ($monthname $Year)')
    
    # Expand paths (handle ~ and environment variables)
    destination_dir = os.path.expanduser(os.path.expandvars(destination_dir))
    
    return Mylar3Config(
        config_path=config_path,
        destination_dir=destination_dir,
        folder_format=folder_format,
        file_format=file_format
    )


if __name__ == "__main__":
    # Test with example config path
    import sys
    
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    else:
        # Default test path
        config_path = "/home/rmleonard/projects/Home Projects/comics-lab/mylar3-test/config.ini"
    
    try:
        config = load_config(config_path)
        print(f"Successfully loaded config from: {config.config_path}")
        print(f"  destination_dir: {config.destination_dir}")
        print(f"  folder_format: {config.folder_format}")
        print(f"  file_format: {config.file_format}")
        
        # Verify destination_dir exists and is accessible
        if os.path.exists(config.destination_dir):
            contents = os.listdir(config.destination_dir)
            print(f"\nFound {len(contents)} items in destination_dir")
            print(f"  Publishers: {[d for d in contents if os.path.isdir(os.path.join(config.destination_dir, d)) and not d.startswith('.')]}")
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)
