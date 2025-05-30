"""
Credential Manager for the Automated Login Application.
Handles secure storage and retrieval of website credentials.
"""

import os
import json
import base64
import datetime
import secrets
import hashlib
from typing import Dict, Optional, Any, Union, List, Tuple, Dict, Set
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import InvalidToken
from cryptography.hazmat.backends import default_backend
from ..utils.logger import Logger
from ..utils.config_manager import ConfigManager

class CredentialManager:
    """
    Manages secure storage and retrieval of website credentials.
    Uses Fernet symmetric encryption for local credential storage.
    """
    
    def __init__(self, config_manager: ConfigManager, master_password: Optional[str] = None) -> None:
        """
        Initialize credential manager with configuration.
        
        Args:
            config_manager: Application configuration manager
            master_password: Master password for encryption.
                           If None, will prompt user during first use.
        """
        self.logger = Logger("CredentialManager")
        self.logger.debug(f"CredentialManager __init__ called with master_password={'***' if master_password else None}")
        self.config_manager = config_manager
        self.data_dir = self.config_manager.get("data_dir")
        
        # Ensure data directory exists
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            # Set secure permissions on data directory (0700 - only owner can access)
            os.chmod(self.data_dir, 0o700)
        except OSError as e:
            self.logger.error(f"Failed to create data directory {self.data_dir}: {e}")
            raise RuntimeError(f"Failed to create data directory: {e}") from e
        
        self.credentials_file = os.path.join(self.data_dir, "credentials.enc")
        self.salt_file = os.path.join(self.data_dir, "salt.bin")
        
        # Initialize credentials dictionary first to avoid AttributeError
        self.credentials: Dict[str, Dict[str, Any]] = {}
        
        # Initialize or load salt
        self.salt = self._initialize_or_load_salt()
        
        # Set master password if provided, otherwise it will be set during first use
        self._master_password = None
        self.cipher_suite = None
        
        if master_password:
            self.logger.debug("Master password provided at initialization; initializing cipher suite.")
            self.set_master_password(master_password)
            
            # Load credentials if file exists and cipher suite is initialized
            if os.path.exists(self.credentials_file) and self.cipher_suite:
                self.logger.debug("Credentials file exists and cipher suite initialized; loading credentials.")
                self.load_credentials()
        else:
            self.logger.debug("No master password provided at initialization; cipher suite will not be initialized yet.")
    
    def _initialize_or_load_salt(self) -> bytes:
        """
        Initialize new salt or load existing one.
        
        Returns:
            Salt for key derivation
            
        Raises:
            IOError: If salt file cannot be read or written
        """
        try:
            if os.path.exists(self.salt_file):
                with open(self.salt_file, "rb") as f:
                    salt = f.read()
                # Set secure permissions on salt file (0600 - only owner can read/write)
                os.chmod(self.salt_file, 0o600)
                return salt
            else:
                # Generate new salt with cryptographically secure random number generator
                salt = secrets.token_bytes(32)  # Increased from 16 to 32 bytes for better security
                with open(self.salt_file, "wb") as f:
                    f.write(salt)
                # Set secure permissions on salt file (0600 - only owner can read/write)
                os.chmod(self.salt_file, 0o600)
                return salt
        except IOError as e:
            self.logger.error(f"Failed to access salt file {self.salt_file}: {e}")
            raise IOError(f"Failed to access salt file: {e}") from e
    
    def _initialize_cipher_suite(self) -> None:
        """
        Initialize cipher suite with derived key from master password.
        
        Raises:
            ValueError: If master password is not set
            RuntimeError: If key derivation fails
        """
        self.logger.debug(f"_initialize_cipher_suite called. master_password is {'set' if self._master_password else 'not set'}")
        if not self._master_password:
            self.logger.error("Attempted to initialize cipher suite without master password.")
            raise ValueError("Master password not set")
        
        try:
            # Derive key from password with stronger parameters
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=self.salt,
                iterations=600000,  # Increased from 100000 to 600000 for better security
                backend=default_backend()
            )
            key = base64.urlsafe_b64encode(kdf.derive(self._master_password.encode()))
            self.cipher_suite = Fernet(key)
            self.logger.debug("Cipher suite successfully initialized.")
        except Exception as e:
            self.logger.error(f"Failed to initialize cipher suite: {e}")
            raise RuntimeError(f"Failed to initialize encryption: {e}") from e
    
    def set_master_password(self, password: str) -> bool:
        """
        Set or change master password.
        
        Args:
            password: New master password
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            ValueError: If password is empty or None
        """
        if not password:
            self.logger.error("Attempted to set empty master password")
            raise ValueError("Master password cannot be empty")
            
        try:
            # Validate password strength
            if len(password) < 8:
                self.logger.warning("Master password is less than 8 characters")
                return False
                
            old_cipher_suite = self.cipher_suite
            old_credentials = self.credentials.copy() if hasattr(self, 'credentials') and self.credentials else {}
            
            # Set new password and initialize cipher suite
            self._master_password = password
            self._initialize_cipher_suite()
            
            # If we had existing credentials, re-encrypt them with new key
            if old_cipher_suite and old_credentials:
                self.credentials = old_credentials
                self.save_credentials()
            
            return True
        except ValueError as e:
            self.logger.error(f"Invalid password format: {e}")
            return False
        except RuntimeError as e:
            self.logger.error(f"Encryption error while setting master password: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error setting master password: {e}")
            return False
        finally:
            # Clear password from memory
            password = None
    
    def load_credentials(self) -> bool:
        """
        Load encrypted credentials from file.

        Returns:
            True if successful, False otherwise

        Raises:
            RuntimeError: If cipher suite is not initialized
        """
        if not self.cipher_suite:
            self.logger.error("Cipher suite not initialized")
            raise RuntimeError("Cipher suite not initialized. Please set the master password before loading credentials.")

        if not os.path.exists(self.credentials_file):
            self.logger.info("No credentials file found, starting with empty credentials")
            self.credentials = {}
            return True

        try:
            with open(self.credentials_file, "rb") as f:
                encrypted_data = f.read()

            decrypted_data = self.cipher_suite.decrypt(encrypted_data)
            self.credentials = json.loads(decrypted_data.decode())

            # Migrate credentials to ensure 'login_strategy' field exists for all
            for cred in self.credentials.values():
                if "login_strategy" not in cred:
                    cred["login_strategy"] = None

            self.logger.info(f"Loaded {len(self.credentials)} credential entries")
            return True
        except FileNotFoundError as e:
            self.logger.error(f"Credentials file not found: {e}")
            self.credentials = {}
            return False
        except InvalidToken as e:
            self.logger.error(f"Invalid master password or corrupted credentials file: {e}")
            return False
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON format in credentials file: {e}")
            return False
        except IOError as e:
            self.logger.error(f"I/O error reading credentials file: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error loading credentials: {e}")
            return False
    
    def save_credentials(self) -> bool:
        """
        Save encrypted credentials to file.
        
        Returns:
            True if successful, False otherwise
            
        Raises:
            RuntimeError: If cipher suite is not initialized
        """
        self.logger.debug("save_credentials ENTRY")
        if not self.cipher_suite:
            self.logger.error("Cipher suite not initialized")
            raise RuntimeError("Cipher suite not initialized. Please set the master password before saving credentials.")
        
        try:
            # Convert credentials to JSON string
            credentials_json = json.dumps(self.credentials)
            
            # Encrypt the JSON string
            encrypted_data = self.cipher_suite.encrypt(credentials_json.encode())
            
            # Write encrypted data to file with secure permissions
            # First write to a temporary file, then rename for atomicity
            temp_file = f"{self.credentials_file}.tmp"
            with open(temp_file, "wb") as f:
                f.write(encrypted_data)
            
            # Set secure permissions (0600 - only owner can read/write)
            os.chmod(temp_file, 0o600)
            
            # Rename for atomic update
            os.replace(temp_file, self.credentials_file)
            
            self.logger.info(f"Saved {len(self.credentials)} credential entries")
            self.logger.debug("save_credentials EXIT: result=True")
            return True
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to serialize credentials to JSON: {e}")
            self.logger.debug("save_credentials EXIT: result=False (JSONDecodeError)")
            return False
        except IOError as e:
            self.logger.error(f"I/O error writing credentials file: {e}")
            self.logger.debug("save_credentials EXIT: result=False (IOError)")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error saving credentials: {e}")
            self.logger.debug("save_credentials EXIT: result=False (Exception)")
            return False
    
    def add_website(self, url: str, username: str, password: str,
                   has_bonus: bool = False, notes: str = "", login_strategy: Optional[str] = None, google_login: bool = False) -> bool:
        """
        Add or update website credentials.

        Args:
            url: Website URL
            username: Login username
            password: Login password
            has_bonus: Whether site offers free credit/trial bonus
            notes: Additional notes
            login_strategy: Login strategy for this website/account

        Returns:
            True if successful, False otherwise

        Raises:
            RuntimeError: If cipher suite is not initialized
            ValueError: If required parameters are missing
        """
        self.logger.debug(f"add_website ENTRY: url={url}, username={username}, has_bonus={has_bonus}, login_strategy={login_strategy}")
        if not self.cipher_suite:
            self.logger.error("Cipher suite not initialized")
            raise RuntimeError("Cipher suite not initialized. Please set the master password before adding credentials.")

        if not url:
            self.logger.error("Attempted to add website with empty URL")
            raise ValueError("Website URL cannot be empty")

        if not username:
            self.logger.error(f"Attempted to add website {url} with empty username")
            raise ValueError("Username cannot be empty")

        try:
            # Normalize URL (remove trailing slash)
            url = url.rstrip('/')

            # Add or update credentials
            self.credentials[url] = {
                "username": username,
                "password": password,
                "has_bonus": has_bonus,
                "notes": notes,
                "last_login": None,  # Will be updated after successful login
                "created_at": datetime.datetime.now().isoformat(),
                "updated_at": datetime.datetime.now().isoformat(),
                "login_strategy": login_strategy,
                "google_login": google_login
            }

            # Log the current state (without sensitive data)
            self.logger.debug(f"add_website: Added/updated URL '{url}'. Credentials now: {list(self.credentials.keys())}")

            # Save updated credentials
            result = self.save_credentials()
            self.logger.debug(f"add_website EXIT: url={url}, result={result}")
            return result
        except ValueError as e:
            self.logger.error(f"Invalid parameter for website {url}: {e}")
            self.logger.debug(f"add_website EXIT: url={url}, result=False (ValueError)")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error adding website {url}: {e}")
            self.logger.debug(f"add_website EXIT: url={url}, result=False (Exception)")
            return False
    
    def remove_website(self, url: str) -> bool:
        """
        Remove website credentials.
        
        Args:
            url: Website URL
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            RuntimeError: If cipher suite is not initialized
            ValueError: If URL is empty
        """
        if not self.cipher_suite:
            self.logger.error("Cipher suite not initialized")
            raise RuntimeError("Cipher suite not initialized. Please set the master password before removing credentials.")

        if not url:
            self.logger.error("Attempted to remove website with empty URL")
            raise ValueError("Website URL cannot be empty")
            
        # Normalize URL (remove trailing slash)
        url = url.rstrip('/')
            
        if url not in self.credentials:
            self.logger.warning(f"Website not found: {url}")
            return False
        
        try:
            # Remove credentials
            del self.credentials[url]
            
            # Save updated credentials
            return self.save_credentials()
        except KeyError:
            self.logger.error(f"Website {url} not found in credentials")
            return False
        except Exception as e:
            self.logger.error(f"Error removing website {url}: {e}")
            return False
    
    def get_website(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get website credentials.

        Args:
            url: Website URL

        Returns:
            Website credentials or None if not found

        Raises:
            RuntimeError: If cipher suite is not initialized
            ValueError: If URL is empty
        """
        if not self.cipher_suite:
            self.logger.error("Cipher suite not initialized")
            raise RuntimeError("Cipher suite not initialized. Please set the master password before retrieving credentials.")

        if not url:
            self.logger.error("Attempted to get website with empty URL")
            raise ValueError("Website URL cannot be empty")

        # Normalize URL (remove trailing slash)
        url = url.rstrip('/')

        cred = self.credentials.get(url)
        if cred is None:
            return None
        # Always return a copy with 'login_strategy' present
        cred_copy = dict(cred)
        if "login_strategy" not in cred_copy:
            cred_copy["login_strategy"] = None
        if "google_login" not in cred_copy:
            cred_copy["google_login"] = False
        return cred_copy
    
    def get_all_websites(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all website credentials.

        Returns:
            Dictionary of all website credentials

        Raises:
            RuntimeError: If cipher suite is not initialized
        """
        if not self.cipher_suite:
            self.logger.error("Cipher suite not initialized")
            raise RuntimeError("Cipher suite not initialized. Please set the master password before retrieving credentials.")

        # Return a dict of credentials, each with 'login_strategy' present
        return {
            url: {
                **cred,
                "login_strategy": cred.get("login_strategy", None),
                "google_login": cred.get("google_login", False)
            }
            for url, cred in self.credentials.items()
        }
    
    def get_bonus_websites(self) -> Dict[str, Dict[str, Any]]:
        """
        Get websites with bonus flag.
        
        Returns:
            Dictionary of website credentials with bonus flag
            
        Raises:
            RuntimeError: If cipher suite is not initialized
        """
        if not self.cipher_suite:
            self.logger.error("Cipher suite not initialized")
            raise RuntimeError("Cipher suite not initialized. Please set the master password before retrieving credentials.")
            
        return {url: data for url, data in self.credentials.items() if data.get("has_bonus", False)}
    
    def update_last_login(self, url: str, success: bool) -> bool:
        """
        Update last login timestamp for a website.
        
        Args:
            url: Website URL
            success: Whether login was successful
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            RuntimeError: If cipher suite is not initialized
            ValueError: If URL is empty
        """
        if not self.cipher_suite:
            self.logger.error("Cipher suite not initialized")
            raise RuntimeError("Cipher suite not initialized. Please set the master password before updating credentials.")

        if not url:
            self.logger.error("Attempted to update website with empty URL")
            raise ValueError("Website URL cannot be empty")
            
        # Normalize URL (remove trailing slash)
        url = url.rstrip('/')
            
        if url not in self.credentials:
            self.logger.warning(f"Website not found: {url}")
            return False
        
        try:
            # Update last login
            self.credentials[url]["last_login"] = {
                "timestamp": datetime.datetime.now().isoformat(),
                "success": success
            }
            
            # Save updated credentials
            return self.save_credentials()
        except KeyError:
            self.logger.error(f"Website {url} not found in credentials")
            return False
        except Exception as e:
            self.logger.error(f"Error updating last login for {url}: {e}")
            return False
    
    def change_website_password(self, url: str, new_password: str, login_strategy: Optional[str] = None) -> bool:
        """
        Change password and/or login strategy for a website.

        Args:
            url: Website URL
            new_password: New password
            login_strategy: New login strategy (optional)

        Returns:
            True if successful, False otherwise

        Raises:
            RuntimeError: If cipher suite is not initialized
            ValueError: If URL or password is empty
        """
        if not self.cipher_suite:
            self.logger.error("Cipher suite not initialized")
            raise RuntimeError("Cipher suite not initialized. Please set the master password before changing credentials.")

        if not url:
            self.logger.error("Attempted to change password for website with empty URL")
            raise ValueError("Website URL cannot be empty")

        if not new_password:
            self.logger.error(f"Attempted to set empty password for website {url}")
            raise ValueError("Password cannot be empty")

        # Normalize URL (remove trailing slash)
        url = url.rstrip('/')

        if url not in self.credentials:
            self.logger.warning(f"Website not found: {url}")
            return False

        try:
            # Update password
            self.credentials[url]["password"] = new_password
            self.credentials[url]["updated_at"] = datetime.datetime.now().isoformat()
            if login_strategy is not None:
                self.credentials[url]["login_strategy"] = login_strategy

            # Save updated credentials
            return self.save_credentials()
        except KeyError:
            self.logger.error(f"Website {url} not found in credentials")
            return False
        except Exception as e:
            self.logger.error(f"Error changing password for {url}: {e}")
            return False
    
    def clear_memory(self) -> None:
        """
        Clear sensitive data from memory.
        """
        self._master_password = None
        self.cipher_suite = None
        self.credentials = {}
        
    @property
    def master_password(self) -> Optional[str]:
        """
        Get master password.
        
        Returns:
            Master password or None if not set
        """
        return self._master_password
