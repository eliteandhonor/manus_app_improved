"""
Logger utility for the Automated Login Application.
Provides standardized logging functionality across the application.
"""

import logging
import os
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional, Union, Any

from ..utils.config_manager import ConfigManager

class Logger:
    """Enhanced logger class with rotation and configuration support."""
    
    def __init__(self, name: str, log_dir: Optional[str] = None, 
                config_manager: Optional[ConfigManager] = None) -> None:
        """
        Initialize logger with configuration support.
        
        Args:
            name: Logger name, typically the module name
            log_dir: Directory to store log files. Defaults to None.
            config_manager: For log level configuration
        """
        self.logger = logging.getLogger(name)
        
        # Set log level from configuration if available
        log_level = logging.INFO
        if config_manager:
            level_name = config_manager.get("log_level", "INFO").upper()
            try:
                log_level = getattr(logging, level_name)
            except AttributeError:
                # Fallback to INFO if invalid level name
                log_level = logging.INFO
        
        self.logger.setLevel(log_level)
        self.file_handler = None
        
        # Prevent duplicate handlers
        if not self.logger.handlers:
            # Create formatter
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            
            # Create console handler
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            # Ensure console handler respects logger level
            console_handler.setLevel(log_level)
            self.logger.addHandler(console_handler)
            
            # Create rotating file handler if log_dir is provided
            if log_dir:
                try:
                    os.makedirs(log_dir, exist_ok=True)
                    log_file = os.path.join(log_dir, f"app.log")
                    self.file_handler = RotatingFileHandler(
                        log_file, 
                        maxBytes=100*1024,  # 100KB (reduced for easier testing)
                        backupCount=5
                    )
                    self.file_handler.setFormatter(formatter)
                    # Ensure file handler respects logger level
                    self.file_handler.setLevel(log_level)
                    self.logger.addHandler(self.file_handler)
                except (OSError, IOError) as e:
                    # Log to console if file handler creation fails
                    console_handler.setLevel(logging.WARNING)
                    self.logger.warning(f"Failed to create log file in {log_dir}: {e}")
    
    def debug(self, message: str) -> None:
        """Log debug message."""
        self.logger.debug(message)
        self._flush_handlers()
    
    def info(self, message: str) -> None:
        """Log info message."""
        self.logger.info(message)
        self._flush_handlers()
    
    def warning(self, message: str) -> None:
        """Log warning message."""
        self.logger.warning(message)
        self._flush_handlers()
    
    def error(self, message: str) -> None:
        """Log error message."""
        self.logger.error(message)
        self._flush_handlers()
    
    def critical(self, message: str) -> None:
        """Log critical message."""
        self.logger.critical(message)
        self._flush_handlers()
    
    def exception(self, message: str) -> None:
        """Log exception with traceback."""
        self.logger.exception(message)
        self._flush_handlers()
        
    def _flush_handlers(self) -> None:
        """Flush all handlers to ensure messages are written immediately."""
        for handler in self.logger.handlers:
            handler.flush()

    def close(self) -> None:
        """Close and remove all handlers from the logger to release file locks."""
        handlers = self.logger.handlers[:]
        for handler in handlers:
            try:
                handler.flush()
                handler.close()
            except Exception:
                pass
            self.logger.removeHandler(handler)
