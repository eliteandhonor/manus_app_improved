"""
Tests for the app core module.
"""

import os
import pytest
import asyncio
from unittest.mock import patch, MagicMock

from src.core.app_core import AppCore

class TestAppCore:
    """Test suite for the AppCore class."""
    
    def test_initialization(self, config_manager):
        """Test that AppCore initializes correctly."""
        from src.core.service_container import ServiceContainer

        # Create a service container and register config_manager
        container = ServiceContainer()
        container.register("config_manager", config_manager)

        # Create app core with patching applied before instantiation
        with patch('src.core.app_core.CredentialManager') as mock_cm, \
             patch('src.core.app_core.BrowserAutomation') as mock_ba:
            
            # Set up mocks
            mock_cm_instance = MagicMock()
            mock_ba_instance = MagicMock()
            mock_cm.return_value = mock_cm_instance
            mock_ba.return_value = mock_ba_instance
            
            # Create app core after patching
            app_core = AppCore(container)
            
            # Initialize
            result = app_core.initialize("TestPassword123!")
            
            # Verify initialization
            assert result is True
            assert app_core.is_initialized is True
            assert app_core.credential_manager == mock_cm_instance
            assert app_core.browser_automation == mock_ba_instance
            mock_cm.assert_called_once_with(config_manager, "TestPassword123!")
            mock_ba.assert_called_once_with(config_manager)
    
    @pytest.mark.asyncio
    async def test_initialize_async(self, config_manager):
        """Test asynchronous initialization."""
        # Create app core with patching applied before instantiation
        with patch('src.core.app_core.CredentialManager') as mock_cm, \
             patch('src.core.app_core.BrowserAutomation') as mock_ba:
            
            # Set up mocks
            mock_cm_instance = MagicMock()
            from unittest.mock import AsyncMock
            mock_ba_instance = MagicMock()
            mock_ba_instance.initialize = AsyncMock(return_value=True)
            mock_cm.return_value = mock_cm_instance
            mock_ba.return_value = mock_ba_instance
            
            # Create app core after patching
            app_core = AppCore(config_manager)
            
            # Initialize
            result = await app_core.initialize_async("TestPassword123!")
            
            # Verify initialization
            assert result is True
            assert app_core.is_initialized is True
            assert app_core.credential_manager == mock_cm_instance
            assert app_core.browser_automation == mock_ba_instance
            mock_cm.assert_called_once_with(config_manager, "TestPassword123!")
            mock_ba.assert_called_once_with(config_manager)
            mock_ba_instance.initialize.assert_called_once()
    
    def test_credential_methods(self, config_manager):
        """Test credential management methods."""
        # Create app core
        app_core = AppCore(config_manager)
        
        # Set up mock credential manager
        mock_cm = MagicMock()
        app_core.credential_manager = mock_cm
        app_core.is_initialized = True
        
        # Test set_master_password
        mock_cm.set_master_password.return_value = True
        result = app_core.set_master_password("NewPassword123!")
        assert result is True
        mock_cm.set_master_password.assert_called_once_with("NewPassword123!")
        
        # Test add_website
        mock_cm.add_website.return_value = True
        result = app_core.add_website("https://example.com", "testuser", "testpass", True, "Test notes")
        assert result is True
        mock_cm.add_website.assert_called_once_with("https://example.com", "testuser", "testpass", True, "Test notes")
        
        # Test remove_website
        mock_cm.remove_website.return_value = True
        result = app_core.remove_website("https://example.com")
        assert result is True
        mock_cm.remove_website.assert_called_once_with("https://example.com")
        
        # Test get_website
        mock_cm.get_website.return_value = {"username": "testuser"}
        result = app_core.get_website("https://example.com")
        assert result == {"username": "testuser"}
        mock_cm.get_website.assert_called_once_with("https://example.com")
        
        # Test get_all_websites
        mock_cm.get_all_websites.return_value = {"https://example.com": {"username": "testuser"}}
        result = app_core.get_all_websites()
        assert result == {"https://example.com": {"username": "testuser"}}
        mock_cm.get_all_websites.assert_called_once()
        
        # Test get_bonus_websites
        mock_cm.get_bonus_websites.return_value = {"https://example.com": {"username": "testuser", "has_bonus": True}}
        result = app_core.get_bonus_websites()
        assert result == {"https://example.com": {"username": "testuser", "has_bonus": True}}
        mock_cm.get_bonus_websites.assert_called_once()
    
    def test_login_to_website(self, config_manager):
        """Test login to website."""
        # Create app core
        app_core = AppCore(config_manager)
        
        # Set up mocks
        mock_cm = MagicMock()
        mock_ba = MagicMock()
        app_core.credential_manager = mock_cm
        app_core.browser_automation = mock_ba
        app_core.is_initialized = True
        
        # Mock get_website
        mock_cm.get_website.return_value = {
            "username": "testuser",
            "password": "testpass"
        }
        
        # Test login_to_website
        with patch('src.core.app_core.threading.Thread') as mock_thread:
            # Set up mock thread
            mock_thread_instance = MagicMock()
            mock_thread.return_value = mock_thread_instance
            
            # Call login_to_website
            result = app_core.login_to_website("https://example.com")
            
            # Verify result
            assert result is not None
            assert "https://example.com" in app_core.login_tasks[result]["url"]
            mock_cm.get_website.assert_called_once_with("https://example.com")
            mock_thread.assert_called_once()
            mock_thread_instance.start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_login_to_website_async(self, config_manager):
        """Test asynchronous login to website."""
        # Create app core
        app_core = AppCore(config_manager)
        
        # Set up mocks
        mock_cm = MagicMock()
        mock_ba = MagicMock()
        app_core.credential_manager = mock_cm
        app_core.browser_automation = mock_ba
        app_core.is_initialized = True
        
        # Mock get_website
        mock_cm.get_website.return_value = {
            "username": "testuser",
            "password": "testpass"
        }
        
        # Mock login_to_website
        mock_ba.login_to_website = MagicMock(return_value=asyncio.Future())
        mock_ba.login_to_website.return_value.set_result({
            "stage": "complete",
            "success": True,
            "message": "Login successful"
        })
        
        # Call login_to_website_async
        result = await app_core.login_to_website_async("https://example.com")
        
        # Verify result
        assert result["stage"] == "complete"
        assert result["success"] is True
        mock_cm.get_website.assert_called_once_with("https://example.com")
        mock_ba.login_to_website.assert_called_once_with(
            "https://example.com", "testuser", "testpass", None, 
            google_login_method=None, force_prompt=False
        )
        mock_cm.update_last_login.assert_called_once_with("https://example.com", True)
    
    def test_get_login_status(self, config_manager):
        """Test get login status."""
        # Create app core
        app_core = AppCore(config_manager)
        
        # Add a task
        task_id = "test-task-id"
        app_core.login_tasks[task_id] = {
            "url": "https://example.com",
            "status": "complete"
        }
        
        # Get status
        result = app_core.get_login_status(task_id)
        
        # Verify result
        assert result["url"] == "https://example.com"
        assert result["status"] == "complete"
        
        # Test with non-existent task
        result = app_core.get_login_status("non-existent")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_wait_for_user_action_async(self, config_manager):
        """Test asynchronous wait for user action."""
        # Create app core
        app_core = AppCore(config_manager)
        
        # Set up mock browser automation
        mock_ba = MagicMock()
        app_core.browser_automation = mock_ba
        
        # Mock wait_for_user_action
        mock_ba.wait_for_user_action = MagicMock(return_value=asyncio.Future())
        mock_ba.wait_for_user_action.return_value.set_result(True)
        
        # Call wait_for_user_action_async
        result = await app_core.wait_for_user_action_async(timeout=60)
        
        # Verify result
        assert result is True
        mock_ba.wait_for_user_action.assert_called_once_with(60)
    
    def test_wait_for_user_action(self, config_manager):
        """Test wait for user action."""
        # Create app core
        app_core = AppCore(config_manager)
        
        # Set up mock browser automation
        mock_ba = MagicMock()
        app_core.browser_automation = mock_ba
        
        # Mock asyncio
        with patch('src.core.app_core.asyncio') as mock_asyncio:
            # Set up mock event loop
            mock_loop = MagicMock()
            mock_asyncio.new_event_loop.return_value = mock_loop
            mock_loop.run_until_complete.return_value = True
            
            # Call wait_for_user_action
            result = app_core.wait_for_user_action("test-task-id", timeout=60)
            
            # Verify result
            assert result is True
            mock_asyncio.new_event_loop.assert_called_once()
            mock_asyncio.set_event_loop.assert_called_once_with(mock_loop)
            mock_loop.run_until_complete.assert_called_once()
            mock_loop.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close_async(self, config_manager):
        """Test asynchronous close."""
        # Create app core
        app_core = AppCore(config_manager)
        
        # Set up mocks
        mock_cm = MagicMock()
        mock_ba = MagicMock()
        app_core.credential_manager = mock_cm
        app_core.browser_automation = mock_ba
        
        # Mock close
        mock_ba.close = MagicMock(return_value=asyncio.Future())
        mock_ba.close.return_value.set_result(None)
        
        # Call close_async
        await app_core.close_async()
        
        # Verify result
        mock_ba.close.assert_called_once()
        mock_cm.clear_memory.assert_called_once()
    
    def test_close(self, config_manager):
        """Test close."""
        # Create app core
        app_core = AppCore(config_manager)
        
        # Set up mocks
        mock_cm = MagicMock()
        mock_ba = MagicMock()
        app_core.credential_manager = mock_cm
        app_core.browser_automation = mock_ba
        
        # Mock asyncio
        with patch('src.core.app_core.asyncio') as mock_asyncio:
            # Set up mock event loop
            mock_loop = MagicMock()
            mock_asyncio.new_event_loop.return_value = mock_loop
            
            # Call close
            app_core.close()
            
            # Verify result
            mock_asyncio.new_event_loop.assert_called_once()
            mock_asyncio.set_event_loop.assert_called_once_with(mock_loop)
            mock_loop.run_until_complete.assert_called_once()
            mock_loop.close.assert_called_once()
            mock_cm.clear_memory.assert_called_once()
    
    def test_run_async(self, config_manager):
        """Test run_async utility method."""
        # Create app core
        app_core = AppCore(config_manager)
        
        # Mock _get_event_loop
        mock_loop = MagicMock()
        mock_loop.run_until_complete.return_value = "test_result"
        app_core._get_event_loop = MagicMock(return_value=mock_loop)
        
        # Create mock coroutine
        mock_coro = MagicMock()
        
        # Call run_async
        result = app_core.run_async(mock_coro)
        
        # Verify result
        assert result == "test_result"
        app_core._get_event_loop.assert_called_once()
        mock_loop.run_until_complete.assert_called_once_with(mock_coro)
