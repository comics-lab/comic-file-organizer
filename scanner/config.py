#!/usr/bin/env python3
"""
Configuration management module for Disk-Folder-File Analyzer (DFA)
Handles loading, validation, and management of application configuration.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    """Manages application configuration from JSON file."""
    
    DEFAULT_CONFIG = {
        "starting_directory": os.path.expanduser("~"),
        "extension_list": [".txt", ".pdf", ".doc", ".docx", ".jpg", ".png", ".mp4", ".mp3"],
        "use_extension_list": False,
        "exclude_hidden_files": True,
        "human_readable_sizes": True,
        "log_level": "INFO",
        "log_file": "dfa.log"
    }
    
    def __init__(self, config_file: str = "config.json"):
        """Initialize configuration manager with config file path."""
        self.config_file = Path(config_file)
        self.config = self.DEFAULT_CONFIG.copy()
        
    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file.
        Creates default config file if it doesn't exist.
        """
        try:
            if not self.config_file.exists():
                logger.warning(f"Config file {self.config_file} not found. Creating default config.")
                self.save_default_config()
                
            with open(self.config_file, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                
            # Validate and merge with defaults
            self.config.update(loaded_config)
            self._validate_config()
            
            logger.info(f"Configuration loaded from {self.config_file}")
            return self.config
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}")
            logger.info("Using default configuration")
            return self.config
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            logger.info("Using default configuration")
            return self.config
            
    def save_default_config(self) -> None:
        """Save default configuration to file."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.DEFAULT_CONFIG, f, indent=2)
            logger.info(f"Default configuration saved to {self.config_file}")
        except Exception as e:
            logger.error(f"Error saving default config: {e}")
            
    def _validate_config(self) -> None:
        """Validate configuration values."""
        # Validate starting_directory
        if not isinstance(self.config.get("starting_directory"), str):
            logger.warning("Invalid starting_directory in config. Using default.")
            self.config["starting_directory"] = self.DEFAULT_CONFIG["starting_directory"]
            
        # Expand user path
        self.config["starting_directory"] = os.path.expanduser(self.config["starting_directory"])
        
        # Validate extension_list
        if not isinstance(self.config.get("extension_list"), list):
            logger.warning("Invalid extension_list in config. Using default.")
            self.config["extension_list"] = self.DEFAULT_CONFIG["extension_list"]
            
        # Validate boolean values
        for key in ["use_extension_list", "exclude_hidden_files", "human_readable_sizes"]:
            if not isinstance(self.config.get(key), bool):
                logger.warning(f"Invalid {key} in config. Using default.")
                self.config[key] = self.DEFAULT_CONFIG[key]
                
        # Validate log_level
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.config.get("log_level") not in valid_levels:
            logger.warning("Invalid log_level in config. Using INFO.")
            self.config["log_level"] = "INFO"
            
        # Validate log_file
        if not isinstance(self.config.get("log_file"), str):
            logger.warning("Invalid log_file in config. Using default.")
            self.config["log_file"] = self.DEFAULT_CONFIG["log_file"]
            
    def get(self, key: str, default=None):
        """Get configuration value by key."""
        return self.config.get(key, default)
        
    def update_config(self, updates: Dict[str, Any]) -> None:
        """Update configuration with new values."""
        self.config.update(updates)
        self._validate_config()
        
    def save_config(self) -> None:
        """Save current configuration to file."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Configuration saved to {self.config_file}")
        except Exception as e:
            logger.error(f"Error saving config: {e}")

if __name__ == "__main__":
    # Test the configuration manager
    config_mgr = ConfigManager()
    config = config_mgr.load_config()
    print("Configuration loaded:")
    for key, value in config.items():
        print(f"  {key}: {value}")