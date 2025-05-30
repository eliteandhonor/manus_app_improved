"""
Tests for the config manager module.
"""

import os
import pytest
import json
import tempfile

from src.utils.config_manager import ConfigManager

class TestConfigManager:
    """Test suite for the ConfigManager class."""
    
    def test_initialization(self, temp_dir):
        """Test that ConfigManager initializes correctly."""
        # Test with explicit config directory
        cm = ConfigManager(temp_dir)
        assert cm is not None
        assert cm.config_dir == temp_dir
        assert os.path.exists(os.path.join(temp_dir, 'config.json'))
        
        # Test default config values
        assert cm.get("browser") == "chromium"
        assert cm.get("headless") is False
        assert cm.get("log_level") == "INFO"
        
        # Test with environment variable override
        os.environ['AUTO_LOGIN_CONFIG_DIR'] = temp_dir
        cm2 = ConfigManager()
        assert cm2.config_dir == temp_dir
        del os.environ['AUTO_LOGIN_CONFIG_DIR']
    
    def test_get_set_config(self, config_manager):
        """Test getting and setting configuration values."""
        # Test get with default
        value = config_manager.get("nonexistent", "default_value")
        assert value == "default_value"
        
        # Test set and get
        config_manager.set("test_key", "test_value")
        value = config_manager.get("test_key")
        assert value == "test_value"
        
        # Test get_all
        all_config = config_manager.get_all()
        assert "test_key" in all_config
        assert all_config["test_key"] == "test_value"
    
    def test_reset_config(self, config_manager):
        """Test resetting configuration to defaults."""
        # Modify some values
        config_manager.set("browser", "firefox")
        config_manager.set("headless", True)
        config_manager.set("custom_key", "custom_value")
        
        # Reset
        config_manager.reset()
        
        # Verify defaults are restored
        assert config_manager.get("browser") == "chromium"
        assert config_manager.get("headless") is False
        assert config_manager.get("custom_key") is None
    
    def test_validate_config(self, config_manager):
        """Test configuration validation."""
        # Set invalid values
        config_manager.config["browser"] = "invalid_browser"
        config_manager.config["log_level"] = "INVALID_LEVEL"
        
        # Validate
        result = config_manager.validate_config()
        assert result is False
        
        # Verify corrections
        assert config_manager.get("browser") == "chromium"
        assert config_manager.get("log_level") == "INFO"
        
        # Set valid values
        config_manager.set("browser", "firefox")
        config_manager.set("log_level", "DEBUG")
        
        # Validate
        result = config_manager.validate_config()
        assert result is True
        
        # Verify no changes
        assert config_manager.get("browser") == "firefox"
        assert config_manager.get("log_level") == "DEBUG"
    
    def test_environment_overrides(self, temp_dir):
        """Test environment variable overrides."""
        # Set environment variables
        os.environ['AUTO_LOGIN_BROWSER'] = "firefox"
        os.environ['AUTO_LOGIN_HEADLESS'] = "true"
        os.environ['AUTO_LOGIN_LOG_LEVEL'] = "DEBUG"
        
        # Create config manager
        cm = ConfigManager(temp_dir)
        
        # Verify overrides
        assert cm.get("browser") == "firefox"
        assert cm.get("headless") is True
        assert cm.get("log_level") == "DEBUG"
        
        # Clean up
        del os.environ['AUTO_LOGIN_BROWSER']
        del os.environ['AUTO_LOGIN_HEADLESS']
        del os.environ['AUTO_LOGIN_LOG_LEVEL']
    
    def test_file_persistence(self, temp_dir):
        """Test that configuration persists to file."""
        # Create and modify config
        cm1 = ConfigManager(temp_dir)
        cm1.set("test_key", "test_value")
        
        # Create new instance with same directory
        cm2 = ConfigManager(temp_dir)
        
        # Verify value was loaded
        assert cm2.get("test_key") == "test_value"
        
        # Verify file content
        with open(os.path.join(temp_dir, 'config.json'), 'r') as f:
            config_data = json.load(f)
            assert "test_key" in config_data
            assert config_data["test_key"] == "test_value"
