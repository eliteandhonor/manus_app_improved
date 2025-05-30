"""
Security validation script for the Automated Login Application.
Tests encryption, password handling, and data security.
"""

import os
import sys
import json
import base64
import secrets
import unittest
from pathlib import Path

# Add src directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils.config_manager import ConfigManager
from src.core.credential_manager import CredentialManager
from src.utils.logger import Logger

class SecurityValidationTest(unittest.TestCase):
    """Test case for security validation."""
    
    def setUp(self):
        """Set up test environment."""
        self.logger = Logger("SecurityTest")
        self.config_manager = ConfigManager()
        self.data_dir = self.config_manager.get("data_dir")
        self.test_password = "TestPassword" + secrets.token_hex(4)
        self.test_website = "security-test-" + secrets.token_hex(4) + ".com"
        
        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Initialize credential manager
        self.credential_manager = CredentialManager(self.config_manager, self.test_password)
    
    def test_encryption_key_derivation(self):
        """Test that encryption keys are properly derived from password."""
        # Initialize cipher suite
        self.credential_manager._initialize_cipher_suite()
        
        # Check that salt exists
        salt_file = os.path.join(self.data_dir, "salt.bin")
        self.assertTrue(os.path.exists(salt_file), "Salt file should be created")
        
        # Check that cipher suite is initialized
        self.assertIsNotNone(self.credential_manager.cipher_suite, "Cipher suite should be initialized")
        
        # Create a second credential manager with same password
        cm2 = CredentialManager(self.config_manager, self.test_password)
        cm2._initialize_cipher_suite()
        
        # They should encrypt the same data to the same ciphertext
        test_data = b"test data for encryption"
        encrypted1 = self.credential_manager.cipher_suite.encrypt(test_data)
        encrypted2 = cm2.cipher_suite.encrypt(test_data)
        
        # The encrypted data should be decryptable by both instances
        self.assertEqual(
            self.credential_manager.cipher_suite.decrypt(encrypted2),
            test_data,
            "Same password should allow cross-decryption"
        )
        
        self.assertEqual(
            cm2.cipher_suite.decrypt(encrypted1),
            test_data,
            "Same password should allow cross-decryption"
        )
        
        # Create a third credential manager with different password
        cm3 = CredentialManager(self.config_manager, self.test_password + "different")
        cm3._initialize_cipher_suite()
        
        # They should not be able to decrypt each other's data
        encrypted3 = cm3.cipher_suite.encrypt(test_data)
        
        with self.assertRaises(Exception):
            self.credential_manager.cipher_suite.decrypt(encrypted3)
    
    def test_credential_encryption(self):
        """Test that credentials are properly encrypted."""
        # Add a test website
        self.credential_manager.add_website(
            self.test_website,
            "testuser",
            "testpass123",
            has_bonus=True,
            notes="Security test"
        )
        
        # Check that credentials file exists
        credentials_file = os.path.join(self.data_dir, "credentials.enc")
        self.assertTrue(os.path.exists(credentials_file), "Credentials file should be created")
        
        # Read the raw encrypted file
        with open(credentials_file, "rb") as f:
            encrypted_data = f.read()
        
        # Check that it's not plaintext JSON (this might fail if the file is empty)
        try:
            decoded = json.loads(encrypted_data)
            # If we can decode it as JSON, make sure it doesn't contain our plaintext credentials
            self.assertNotIn(self.test_website, str(decoded), "Credentials should not be stored in plaintext")
            self.assertNotIn("testuser", str(decoded), "Username should not be stored in plaintext")
            self.assertNotIn("testpass123", str(decoded), "Password should not be stored in plaintext")
        except json.JSONDecodeError:
            # This is expected if the file is properly encrypted
            pass
        
        # Create a new credential manager with same password
        cm2 = CredentialManager(self.config_manager, self.test_password)
        cm2.load_credentials()
        
        # Check that it can decrypt and read the credentials
        self.assertIn(self.test_website, cm2.credentials, "Should be able to decrypt credentials")
        self.assertEqual(
            cm2.credentials[self.test_website]["username"],
            "testuser",
            "Username should be correctly decrypted"
        )
        
        # Create a credential manager with wrong password
        cm3 = CredentialManager(self.config_manager, self.test_password + "wrong")
        
        # It should fail to load credentials or return empty credentials
        result = cm3.load_credentials()
        if result:
            # If load_credentials returns True but credentials are empty, that's acceptable
            self.assertNotIn(self.test_website, cm3.credentials, 
                            "Wrong password should not be able to decrypt credentials")
        # Otherwise, the test passes if load_credentials returned False
    
    def test_password_handling(self):
        """Test that passwords are handled securely."""
        # Check that master password is stored in memory
        self.assertEqual(
            self.credential_manager.master_password,
            self.test_password,
            "Master password should be available in memory"
        )
        
        # But it should not be stored in any files
        for root, dirs, files in os.walk(self.data_dir):
            for file in files:
                with open(os.path.join(root, file), "rb") as f:
                    content = f.read()
                    self.assertNotIn(
                        self.test_password.encode(),
                        content,
                        f"Master password should not be stored in {file}"
                    )
    
    def test_password_change(self):
        """Test that changing password re-encrypts credentials."""
        # Add a test website
        self.credential_manager.add_website(
            self.test_website,
            "testuser",
            "testpass123",
            has_bonus=True,
            notes="Security test"
        )
        
        # Change password
        new_password = "NewPassword" + secrets.token_hex(4)
        self.credential_manager.set_master_password(new_password)
        
        # Create a new credential manager with new password
        cm2 = CredentialManager(self.config_manager, new_password)
        cm2.load_credentials()
        
        # Check that it can decrypt and read the credentials
        self.assertIn(self.test_website, cm2.credentials, "Should be able to decrypt credentials with new password")
        
        # Create a credential manager with old password
        cm3 = CredentialManager(self.config_manager, self.test_password)
        
        # It should fail to load credentials or return empty credentials
        result = cm3.load_credentials()
        if result:
            # If load_credentials returns True but credentials are empty, that's acceptable
            self.assertNotIn(self.test_website, cm3.credentials, 
                            "Old password should not be able to decrypt credentials after password change")
        # Otherwise, the test passes if load_credentials returned False
    
    def tearDown(self):
        """Clean up test environment."""
        # Remove test website from credentials
        if hasattr(self.credential_manager, 'credentials') and self.test_website in self.credential_manager.credentials:
            self.credential_manager.remove_website(self.test_website)

if __name__ == "__main__":
    unittest.main()
