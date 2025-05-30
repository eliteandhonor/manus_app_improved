"""
Tests for the credential manager module.
"""

import os
import pytest
import json
import tempfile
from cryptography.fernet import InvalidToken

from src.core.credential_manager import CredentialManager

class TestCredentialManager:
    """Test suite for the CredentialManager class."""
    
    def test_initialization(self, config_manager):
        """Test that CredentialManager initializes correctly."""
        cm = CredentialManager(config_manager, "TestPassword123!")
        assert cm is not None
        assert cm.cipher_suite is not None
        
    def test_set_master_password(self, credential_manager):
        """Test setting and changing the master password."""
        # Password should already be set from fixture
        assert credential_manager.cipher_suite is not None
        
        # Change password
        result = credential_manager.set_master_password("NewPassword456!")
        assert result is True
        
        # Test with weak password
        result = credential_manager.set_master_password("weak")
        assert result is False
        
        # Test with empty password
        with pytest.raises(ValueError):
            credential_manager.set_master_password("")
    
    def test_add_website(self, credential_manager):
        """Test adding website credentials."""
        # Add a website
        result = credential_manager.add_website(
            "https://example.com", 
            "testuser", 
            "testpass", 
            has_bonus=True, 
            notes="Test notes"
        )
        assert result is True
        
        # Verify it was added
        creds = credential_manager.get_website("https://example.com")
        assert creds is not None
        assert creds["username"] == "testuser"
        assert creds["password"] == "testpass"
        assert creds["has_bonus"] is True
        assert creds["notes"] == "Test notes"
        
        # Test with empty URL
        with pytest.raises(ValueError):
            credential_manager.add_website("", "user", "pass")
            
        # Test with empty username
        with pytest.raises(ValueError):
            credential_manager.add_website("https://example.com", "", "pass")
    
    def test_remove_website(self, credential_manager):
        """Test removing website credentials."""
        # Add a website
        credential_manager.add_website("https://example.com", "testuser", "testpass")
        
        # Remove it
        result = credential_manager.remove_website("https://example.com")
        assert result is True
        
        # Verify it was removed
        creds = credential_manager.get_website("https://example.com")
        assert creds is None
        
        # Test removing non-existent website
        result = credential_manager.remove_website("https://nonexistent.com")
        assert result is False
        
        # Test with empty URL
        with pytest.raises(ValueError):
            credential_manager.remove_website("")
    
    def test_get_website(self, credential_manager):
        """Test retrieving website credentials."""
        # Add a website
        credential_manager.add_website("https://example.com", "testuser", "testpass")
        
        # Get it
        creds = credential_manager.get_website("https://example.com")
        assert creds is not None
        assert creds["username"] == "testuser"
        assert creds["password"] == "testpass"
        
        # Test with non-existent website
        creds = credential_manager.get_website("https://nonexistent.com")
        assert creds is None
        
        # Test with empty URL
        with pytest.raises(ValueError):
            credential_manager.get_website("")
    
    def test_get_all_websites(self, credential_manager):
        """Test retrieving all website credentials."""
        # Add some websites
        credential_manager.add_website("https://example1.com", "user1", "pass1")
        credential_manager.add_website("https://example2.com", "user2", "pass2")
        
        # Get all
        all_creds = credential_manager.get_all_websites()
        assert len(all_creds) == 2
        assert "https://example1.com" in all_creds
        assert "https://example2.com" in all_creds
    
    def test_get_bonus_websites(self, credential_manager):
        """Test retrieving websites with bonus flag."""
        # Add some websites with and without bonus
        credential_manager.add_website("https://example1.com", "user1", "pass1", has_bonus=True)
        credential_manager.add_website("https://example2.com", "user2", "pass2", has_bonus=False)
        
        # Get bonus websites
        bonus_creds = credential_manager.get_bonus_websites()
        assert len(bonus_creds) == 1
        assert "https://example1.com" in bonus_creds
        assert "https://example2.com" not in bonus_creds
    
    def test_update_last_login(self, credential_manager):
        """Test updating last login timestamp."""
        # Add a website
        credential_manager.add_website("https://example.com", "testuser", "testpass")
        
        # Update last login
        result = credential_manager.update_last_login("https://example.com", True)
        assert result is True
        
        # Verify it was updated
        creds = credential_manager.get_website("https://example.com")
        assert creds["last_login"] is not None
        assert creds["last_login"]["success"] is True
        
        # Test with non-existent website
        result = credential_manager.update_last_login("https://nonexistent.com", True)
        assert result is False
        
        # Test with empty URL
        with pytest.raises(ValueError):
            credential_manager.update_last_login("", True)
    
    def test_change_website_password(self, credential_manager):
        """Test changing a website password."""
        # Add a website
        credential_manager.add_website("https://example.com", "testuser", "testpass")
        
        # Change password
        result = credential_manager.change_website_password("https://example.com", "newpass")
        assert result is True
        
        # Verify it was changed
        creds = credential_manager.get_website("https://example.com")
        assert creds["password"] == "newpass"
        
        # Test with non-existent website
        result = credential_manager.change_website_password("https://nonexistent.com", "newpass")
        assert result is False
        
        # Test with empty URL
        with pytest.raises(ValueError):
            credential_manager.change_website_password("", "newpass")
            
        # Test with empty password
        with pytest.raises(ValueError):
            credential_manager.change_website_password("https://example.com", "")
    
    def test_save_load_credentials(self, credential_manager):
        """Test saving and loading credentials."""
        # Add some websites
        credential_manager.add_website("https://example1.com", "user1", "pass1")
        credential_manager.add_website("https://example2.com", "user2", "pass2")
        
        # Save credentials
        result = credential_manager.save_credentials()
        assert result is True
        
        # Create a new credential manager with the same config
        new_cm = CredentialManager(credential_manager.config_manager, "TestPassword123!")
        
        # Load credentials
        result = new_cm.load_credentials()
        assert result is True
        
        # Verify credentials were loaded
        all_creds = new_cm.get_all_websites()
        assert len(all_creds) == 2
        assert "https://example1.com" in all_creds
        assert "https://example2.com" in all_creds
    
    def test_wrong_password(self, config_manager):
        """Test loading credentials with wrong password."""
        # Create a credential manager and add a website
        cm1 = CredentialManager(config_manager, "CorrectPassword123!")
        cm1.add_website("https://example.com", "testuser", "testpass")
        cm1.save_credentials()
        
        # Create a new credential manager with wrong password
        cm2 = CredentialManager(config_manager, "WrongPassword456!")
        
        # Try to load credentials
        result = cm2.load_credentials()
        assert result is False
    
    def test_clear_memory(self, credential_manager):
        """Test clearing sensitive data from memory."""
        # Add a website
        credential_manager.add_website("https://example.com", "testuser", "testpass")
        
        # Clear memory
        credential_manager.clear_memory()
        
        # Verify cipher suite is cleared
        assert credential_manager.cipher_suite is None
        
        # Verify credentials are cleared
        assert len(credential_manager.credentials) == 0
