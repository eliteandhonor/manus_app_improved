"""
Configuration manager for the Automated Login Application.
Handles application settings and user preferences with environment variable support.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, Union, List, Set

class ConfigManager:
    """Configuration manager for application settings with environment variable support."""
    
    def __init__(self, config_dir: Optional[str] = None) -> None:
        """
        Initialize configuration manager with environment variable support.
        
        Args:
            config_dir: Directory to store configuration. 
                       Defaults to user's home directory.
        """
        # Allow environment variable to override config directory
        if config_dir is None:
            self.config_dir = os.environ.get(
                'AUTO_LOGIN_CONFIG_DIR', 
                os.path.join(str(Path.home()), '.auto_login_app')
            )
        else:
            self.config_dir = config_dir
            
        os.makedirs(self.config_dir, exist_ok=True)
        self.config_file = os.path.join(self.config_dir, 'config.json')
        self.config: Dict[str, Any] = self._load_config()
        
        # Apply environment variable overrides
        self._apply_env_overrides()
    
    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides to configuration."""
        env_mapping: Dict[str, str] = {
            'AUTO_LOGIN_BROWSER': 'browser',
            'AUTO_LOGIN_HEADLESS': 'headless',
            'AUTO_LOGIN_LOG_LEVEL': 'log_level',
            'AUTO_LOGIN_DATA_DIR': 'data_dir',
            'AUTO_LOGIN_POST_LOGIN_DELAY': 'post_login_delay'
        }
        
        for env_var, config_key in env_mapping.items():
            if env_var in os.environ:
                # Convert string to boolean for boolean settings
                if config_key == 'headless':
                    self.config[config_key] = os.environ[env_var].lower() in ('true', 'yes', '1')
                elif config_key == 'post_login_delay':
                    try:
                        self.config[config_key] = float(os.environ[env_var])
                    except ValueError:
                        self.config[config_key] = 5
                else:
                    self.config[config_key] = os.environ[env_var]
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file or create default if not exists.
        
        Returns:
            Configuration dictionary
        """
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: Config file {self.config_file} is corrupted. Using defaults.")
                return self._get_default_config()
            except IOError as e:
                print(f"Warning: Could not read config file: {e}. Using defaults.")
                return self._get_default_config()
        else:
            # Create default config
            default_config = self._get_default_config()
            self._save_config(default_config)
            return default_config
    
    def _save_config(self, config: Dict[str, Any]) -> None:
        """
        Save configuration to file.
        
        Args:
            config: Configuration dictionary to save
        """
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=4)
        except IOError as e:
            print(f"Error saving configuration: {e}")
    def save(self) -> None:
        """
        Persist the current configuration to disk.
        """
        self._save_config(self.config)
    
    def _get_default_config(self) -> Dict[str, Any]:
        """
        Get default configuration.
        
        Returns:
            Default configuration dictionary
        """
        return {
            "browser": "chromium",  # Default browser
            "headless": False,      # Show browser by default
            "data_dir": os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data'),
            "first_run": True,
            "check_updates": True,
            "log_level": "INFO",
            "post_login_delay": 5  # Default post-login delay in seconds
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value.
        
        Args:
            key: Configuration key
            value: Value to set
        """
        self.config[key] = value
        self._save_config(self.config)
    
    def has(self, key: str) -> bool:
        """
        Check if a configuration key exists.

        Args:
            key: Configuration key to check

        Returns:
            True if the key exists in the configuration, False otherwise
        """
        return key in self.config

    def get_all(self) -> Dict[str, Any]:
        """
        Get all configuration values.
        
        Returns:
            All configuration values
        """
        return self.config.copy()
    
    def reset(self) -> None:
        """Reset configuration to defaults."""
        self.config = self._get_default_config()
        self._save_config(self.config)
        
    def validate_config(self) -> bool:
        """
        Validate configuration values and correct any issues.
        
        Returns:
            True if valid, False if corrections were made
        """
        valid = True
        
        # Validate browser type
        valid_browsers = ["chromium", "firefox", "webkit"]
        if self.config.get("browser") not in valid_browsers:
            self.config["browser"] = "chromium"
            valid = False
            
        # Validate log level
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.config.get("log_level") not in valid_log_levels:
            self.config["log_level"] = "INFO"
            valid = False

        # Validate post_login_delay
        try:
            delay = float(self.config.get("post_login_delay", 5))
            if delay < 0:
                raise ValueError
            self.config["post_login_delay"] = delay
        except (ValueError, TypeError):
            self.config["post_login_delay"] = 5
            valid = False
            
        # Ensure data directory exists
        if not os.path.exists(self.config.get("data_dir")):
            try:
                os.makedirs(self.config.get("data_dir"), exist_ok=True)
            except OSError:
                # If we can't create the directory, use a default
                self.config["data_dir"] = os.path.join(self.config_dir, 'data')
                os.makedirs(self.config["data_dir"], exist_ok=True)
                valid = False
                
        # Save if corrections were made
        if not valid:
            self._save_config(self.config)
            
        return valid
