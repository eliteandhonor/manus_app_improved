"""
Debug script for the Credential Manager.
Tests the initialization and file creation functionality.
"""

import os
import sys
import json
from pathlib import Path

# Add src directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils.config_manager import ConfigManager
from src.core.credential_manager import CredentialManager
from src.utils.logger import Logger

def main():
    """Test credential manager initialization and file creation."""
    logger = Logger("DebugScript")
    
    # Initialize configuration
    config_manager = ConfigManager()
    data_dir = config_manager.get("data_dir")
    
    print(f"Data directory: {data_dir}")
    print(f"Exists: {os.path.exists(data_dir)}")
    
    # Ensure data directory exists
    os.makedirs(data_dir, exist_ok=True)
    
    # Check for existing files
    credentials_file = os.path.join(data_dir, "credentials.enc")
    salt_file = os.path.join(data_dir, "salt.bin")
    
    print(f"Credentials file: {credentials_file}")
    print(f"Credentials file exists: {os.path.exists(credentials_file)}")
    print(f"Salt file: {salt_file}")
    print(f"Salt file exists: {os.path.exists(salt_file)}")
    
    # Initialize credential manager
    password = "TestPassword123"
    print(f"\nInitializing credential manager with password: {password}")
    
    credential_manager = CredentialManager(config_manager, password)
    
    # Force initialization of cipher suite
    print("Initializing cipher suite")
    if not hasattr(credential_manager, 'cipher_suite') or credential_manager.cipher_suite is None:
        credential_manager._initialize_cipher_suite()
    
    # Add a test website
    print("\nAdding test website")
    result = credential_manager.add_website(
        "test.example.com", 
        "testuser", 
        "testpass123", 
        has_bonus=True, 
        notes="Test website"
    )
    print(f"Add website result: {result}")
    
    # Check if credentials file exists now
    print(f"\nCredentials file exists after add: {os.path.exists(credentials_file)}")
    
    # List all files in data directory
    print("\nFiles in data directory:")
    for file in os.listdir(data_dir):
        print(f"- {file}")
    
    # Try to load credentials
    print("\nLoading credentials")
    load_result = credential_manager.load_credentials()
    print(f"Load credentials result: {load_result}")
    
    # Print credentials
    print("\nCredentials:")
    print(credential_manager.credentials)

if __name__ == "__main__":
    main()
