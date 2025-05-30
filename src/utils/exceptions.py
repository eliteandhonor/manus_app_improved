
"""
Custom exceptions for the Automated Login Application.
Provides a standardized way to handle errors across the application.
"""

class AppError(Exception):
    """Base exception for all application errors."""
    
    def __init__(self, message: str, *args, **kwargs) -> None:
        """
        Initialize application error.
        
        Args:
            message: Error message
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
        """
        self.message = message
        super().__init__(message, *args, **kwargs)


class ConfigError(AppError):
    """Error related to configuration."""
    pass


class CredentialError(AppError):
    """Error related to credentials."""
    pass


class EncryptionError(CredentialError):
    """Error related to encryption/decryption."""
    pass


class BrowserError(AppError):
    """Error related to browser automation."""
    pass


class LoginError(BrowserError):
    """Error related to login process."""
    pass


class NetworkError(AppError):
    """Error related to network operations."""
    pass


class UIError(AppError):
    """Error related to user interface."""
    pass


class ValidationError(AppError):
    """Error related to data validation."""
    pass
