"""
Test script for the improved Manus auto login application.
Tests the top 3 improvements:
1. Dependency Injection
2. Lazy Loading for Browser Automation
3. Standardized Error Handling
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio

# Add src directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.service_container import ServiceContainer
from src.core.app_core import AppCore
from src.core.browser_automation import BrowserAutomation
from src.utils.config_manager import ConfigManager
from src.utils.logger import Logger
from src.utils.error_handler import ErrorHandler
from src.utils.exceptions import AppError, BrowserError, CredentialError

class TestServiceContainer(unittest.TestCase):
    """Test the ServiceContainer class."""
    
    def test_register_and_get(self):
        """Test registering and getting services."""
        container = ServiceContainer()
        
        # Register a service
        service = MagicMock()
        container.register("test_service", service)
        
        # Get the service
        retrieved_service = container.get("test_service")
        
        # Check that the retrieved service is the same as the registered one
        self.assertIs(retrieved_service, service)
    
    def test_register_factory(self):
        """Test registering and using a factory function."""
        container = ServiceContainer()
        
        # Register a factory
        factory = MagicMock(return_value="test_value")
        container.register_factory("test_factory", factory)
        
        # Get the service
        retrieved_value = container.get("test_factory")
        
        # Check that the factory was called and the value was returned
        factory.assert_called_once()
        self.assertEqual(retrieved_value, "test_value")
        
        # Get the service again
        retrieved_value_2 = container.get("test_factory")
        
        # Check that the factory was not called again
        self.assertEqual(factory.call_count, 1)
        self.assertEqual(retrieved_value_2, "test_value")
    
    def test_has(self):
        """Test checking if a service is registered."""
        container = ServiceContainer()
        
        # Register a service
        container.register("test_service", "test_value")
        
        # Check that the service is registered
        self.assertTrue(container.has("test_service"))
        self.assertFalse(container.has("nonexistent_service"))

class TestLazyLoading(unittest.TestCase):
    """Test lazy loading of browser automation."""
    
    def setUp(self):
        """Set up test environment."""
        self.config_manager = ConfigManager()
        self.logger = Logger("TestLazyLoading")
        self.error_handler = ErrorHandler(self.logger)
        
        # Create service container
        self.container = ServiceContainer()
        self.container.register("config_manager", self.config_manager)
        self.container.register("logger", self.logger)
        self.container.register("error_handler", self.error_handler)
    
    def test_browser_lazy_loading(self):
        """Test that browser is only initialized when needed."""
        # Patch the *wrapped* async method, not the decorated one
        with patch('src.core.browser_automation.BrowserAutomation.initialize', new_callable=AsyncMock) as mock_initialize:
            mock_initialize.return_value = True

            browser_automation = BrowserAutomation(self.config_manager)

            # Check that initialize was not called yet
            mock_initialize.assert_not_called()

            # Use asyncio.run for robust event loop handling
            asyncio.run(browser_automation.get_browser())

            # Check that initialize was called
            mock_initialize.assert_called_once()
    
    def test_app_core_lazy_loading(self):
        """Test that AppCore only initializes browser when needed and uses a mock CredentialManager."""
        with patch('src.core.app_core.BrowserAutomation') as mock_browser_automation:
            # Setup BrowserAutomation mock
            mock_browser = MagicMock()
            mock_browser_automation.return_value = mock_browser

            # Register browser automation factory
            self.container.register_factory("browser_automation", lambda: mock_browser_automation(self.config_manager))

            # Create app core
            app_core = AppCore(self.container)

            # Check that browser automation was not created yet
            mock_browser_automation.assert_not_called()

            # Initialize app core
            app_core.initialize("test_password")

            # Inject a mock CredentialManager that returns valid credentials for the test URL
            mock_cred_mgr = MagicMock()
            mock_cred_mgr.get_website.return_value = {
                "username": "tomsmith",
                "password": "SuperSecretPassword!"
            }
            app_core.credential_manager = mock_cred_mgr

            # Check that browser automation was still not created (lazy loading)
            mock_browser_automation.assert_not_called()

            # Call a method that uses browser automation with the new test URL
            task_id = app_core.login_to_website("https://the-internet.herokuapp.com/login")
            # Wait for the login thread to finish to ensure lazy instantiation occurs
            if task_id is not None:
                app_core.login_tasks[task_id]["thread"].join()

            # Check that browser automation was created
            mock_browser_automation.assert_called_once()

class TestErrorHandling(unittest.TestCase):
    """Test standardized error handling."""
    
    def setUp(self):
        """Set up test environment."""
        self.logger = Logger("TestErrorHandling")
        self.error_handler = ErrorHandler(self.logger)
    
    def test_error_handler_decorator(self):
        """Test that error handler decorator catches exceptions."""
        # Create a function that raises an exception
        @self.error_handler.handle
        def test_function():
            raise ValueError("Test error")
        
        # Call the function and check that it raises an AppError
        with self.assertRaises(AppError):
            test_function()
    
    def test_custom_exceptions(self):
        """Test custom exception hierarchy."""
        # Create exceptions
        app_error = AppError("App error")
        browser_error = BrowserError("Browser error")
        credential_error = CredentialError("Credential error")
        
        # Check that exceptions are instances of their parent classes
        self.assertIsInstance(app_error, AppError)
        self.assertIsInstance(browser_error, AppError)
        self.assertIsInstance(credential_error, AppError)
        
        # Check that exceptions have the correct messages
        self.assertEqual(str(app_error), "App error")
        self.assertEqual(str(browser_error), "Browser error")
        self.assertEqual(str(credential_error), "Credential error")

if __name__ == "__main__":
    unittest.main()
