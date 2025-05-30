
"""
Error handler for the Automated Login Application.
Provides a centralized way to handle errors across the application.
"""

import sys
import traceback
import functools
from typing import Callable, Any, Dict, Optional, Type, TypeVar, cast, Union

from .logger import Logger
from .exceptions import AppError

F = TypeVar('F', bound=Callable[..., Any])

class ErrorHandler:
    """
    Centralized error handler for the application.
    Provides methods to handle errors consistently across the application.
    """
    
    def __init__(self, logger: Optional[Logger] = None) -> None:
        """
        Initialize error handler.
        
        Args:
            logger: Logger instance for error logging
        """
        self.logger = logger or Logger("ErrorHandler")
    
    def handle(self, func: F) -> F:
        """
        Decorator to handle exceptions in a function.
        Logs the error and re-raises it as an AppError.
        
        Args:
            func: Function to decorate
            
        Returns:
            Decorated function
        """
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except AppError as e:
                # Already an AppError, just log and re-raise
                self.logger.error(f"{e.__class__.__name__}: {e.message}")
                raise
            except Exception as e:
                # Convert to AppError, log and raise
                error_type = e.__class__.__name__
                error_message = str(e)
                self.logger.error(f"Unhandled {error_type}: {error_message}")
                self.logger.debug(f"Traceback: {traceback.format_exc()}")
                raise AppError(f"{error_type}: {error_message}") from e
        
        return cast(F, wrapper)
    
    @staticmethod
    def handle_async(func: Callable) -> Any:
        """
        Async version of handle decorator.
        
        Args:
            func: Async function to decorate
            
        Returns:
            Decorated async function
        """
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Try to get a logger from the instance (args[0]), fallback to default
            logger = None
            if args and hasattr(args[0], "logger"):
                logger = getattr(args[0], "logger")
            else:
                logger = Logger("ErrorHandler")
            try:
                return await func(*args, **kwargs)
            except AppError as e:
                # Already an AppError, just log and re-raise
                logger.error(f"{e.__class__.__name__}: {getattr(e, 'message', str(e))}")
                raise
            except Exception as e:
                # Convert to AppError, log and raise
                error_type = e.__class__.__name__
                error_message = str(e)
                logger.error(f"Unhandled {error_type}: {error_message}")
                logger.debug(f"Traceback: {traceback.format_exc()}")
                raise AppError(f"{error_type}: {error_message}") from e
        
        return wrapper
    
    def format_error(self, error: Exception) -> Dict[str, Any]:
        """
        Format an exception as a dictionary for UI display.
        
        Args:
            error: Exception to format
            
        Returns:
            Dictionary with error details
        """
        if isinstance(error, AppError):
            error_type = error.__class__.__name__
            error_message = error.message
        else:
            error_type = error.__class__.__name__
            error_message = str(error)
        
        return {
            "type": error_type,
            "message": error_message,
            "success": False
        }
    
    def log_error(self, error: Exception, context: Optional[str] = None) -> None:
        """
        Log an error with optional context.
        
        Args:
            error: Exception to log
            context: Optional context information
        """
        if context:
            self.logger.error(f"{context}: {error.__class__.__name__}: {str(error)}")
        else:
            self.logger.error(f"{error.__class__.__name__}: {str(error)}")
        
        # Log traceback at debug level
        self.logger.debug(f"Traceback: {traceback.format_exc()}")
