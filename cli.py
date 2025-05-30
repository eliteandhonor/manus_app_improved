"""
CLI version of the Automated Login Application.
Provides command-line interface for credential management and login automation.
"""

import os
import sys
import json
import asyncio
import getpass
import argparse
from pathlib import Path

# Add src directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.app_core import AppCore
from src.utils.config_manager import ConfigManager
from src.utils.logger import Logger
from src.core.credential_manager import CredentialManager

class CLI:
    """Command-line interface for the Automated Login Application."""
    
    def __init__(self):
        """Initialize CLI application."""
        self.logger = Logger("CLI")
        self.config_manager = ConfigManager()
        self.app_core = None  # Initialize later with password
        self.credential_manager = None  # Initialize directly when needed
        self.is_initialized = False
        
        # Parse command-line arguments
        self.parser = self._create_parser()
        self.args = self.parser.parse_args()
        
        # Process commands
        self._process_commands()
    
    def _create_parser(self):
        """Create command-line argument parser."""
        parser = argparse.ArgumentParser(
            description="Automated Login CLI - Securely manage and automate website logins"
        )
        
        # Add subparsers for different commands
        subparsers = parser.add_subparsers(dest="command", help="Command to execute")
        
        # Init command
        init_parser = subparsers.add_parser("init", help="Initialize application with master password")
        init_parser.add_argument("--password", help="Master password (not recommended, use prompt instead)")
        init_parser.add_argument("--confirm-password", help="Confirm master password (for non-interactive use)")
        init_parser.add_argument("--no-confirm", action="store_true", help="Skip password confirmation (use with caution)")
        init_parser.add_argument("--force", action="store_true", help="Force initialization even if already initialized")
        
        # Add website command
        add_parser = subparsers.add_parser("add", help="Add or update website credentials")
        add_parser.add_argument("url", help="Website URL")
        add_parser.add_argument("username", help="Login username")
        add_parser.add_argument("--password", help="Login password (not recommended, use prompt instead)")
        add_parser.add_argument("--has-bonus", action="store_true", help="Website offers free credit/trial bonus")
        add_parser.add_argument("--notes", help="Additional notes")
        add_parser.add_argument("--master-password", help="Master password (for non-interactive use)")
        
        # Remove website command
        remove_parser = subparsers.add_parser("remove", help="Remove website credentials")
        remove_parser.add_argument("url", help="Website URL")
        remove_parser.add_argument("--force", "-f", action="store_true", help="Skip confirmation")
        remove_parser.add_argument("--master-password", help="Master password (for non-interactive use)")
        
        # List websites command
        list_parser = subparsers.add_parser("list", help="List website credentials")
        list_parser.add_argument("--bonus-only", action="store_true", help="List only websites with bonus")
        list_parser.add_argument("--master-password", help="Master password (for non-interactive use)")
        
        # Login command
        login_parser = subparsers.add_parser("login", help="Login to website(s)")
        login_parser.add_argument("urls", nargs="*", help="Website URLs to login (empty for all)")
        login_parser.add_argument("--bonus-only", action="store_true", help="Login only to websites with bonus")
        login_parser.add_argument("--browser", choices=["chromium", "firefox", "webkit"], 
                                 default="chromium", help="Browser to use")
        login_parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
        login_parser.add_argument("--master-password", help="Master password (for non-interactive use)")
        
        # Change master password command
        change_parser = subparsers.add_parser("change-password", help="Change master password")
        change_parser.add_argument("--current-password", help="Current master password (not recommended, use prompt instead)")
        change_parser.add_argument("--new-password", help="New master password (not recommended, use prompt instead)")
        change_parser.add_argument("--confirm-password", help="Confirm new password (for non-interactive use)")
        change_parser.add_argument("--no-confirm", action="store_true", help="Skip password confirmation (use with caution)")
        
        return parser
    
    def _process_commands(self):
        """Process command-line arguments and execute commands."""
        if not self.args.command:
            self.parser.print_help()
            return
        
        # Initialize application if needed
        if self.args.command == "init":
            self._init_command()
        else:
            # For all other commands, ensure application is initialized
            master_password = None
            if hasattr(self.args, 'master_password') and self.args.master_password:
                master_password = self.args.master_password
                
            if not self._ensure_initialized(master_password):
                return
            
            # Execute command
            if self.args.command == "add":
                self._add_command()
            elif self.args.command == "remove":
                self._remove_command()
            elif self.args.command == "list":
                self._list_command()
            elif self.args.command == "login":
                self._login_command()
            elif self.args.command == "change-password":
                self._change_password_command()
    
    def _init_command(self):
        """Initialize application with master password."""
        # Check if already initialized
        data_dir = self.config_manager.get("data_dir")
        os.makedirs(data_dir, exist_ok=True)
        
        credentials_file = os.path.join(data_dir, "credentials.enc")
        
        if os.path.exists(credentials_file) and not self.args.force:
            print("Application already initialized. Use --force to reinitialize.")
            return
        
        # Get master password
        password = self._get_password(self.args.password, "Enter master password: ")
        
        if not password:
            print("Error: Master password is required")
            return
        
        if len(password) < 8:
            print("Error: Master password must be at least 8 characters")
            return
        
        # Handle password confirmation
        if self.args.no_confirm:
            # Skip confirmation
            confirm = password
        elif self.args.confirm_password:
            # Use provided confirmation
            confirm = self.args.confirm_password
        else:
            # Prompt for confirmation
            confirm = self._get_password(None, "Confirm master password: ")
        
        if password != confirm:
            print("Error: Passwords do not match")
            return
        
        # Initialize credential manager directly
        self.credential_manager = CredentialManager(self.config_manager, password)
        
        # Force initialization of cipher suite
        if not hasattr(self.credential_manager, 'cipher_suite') or self.credential_manager.cipher_suite is None:
            self.credential_manager._initialize_cipher_suite()
        
        # Add a dummy website to ensure the file is created
        self.credential_manager.add_website("dummy.example.com", "dummy", "dummy123")
        self.credential_manager.remove_website("dummy.example.com")
        
        # Initialize app core for other operations
        self.app_core = AppCore(self.config_manager)
        if self.app_core.initialize(password):
            print("Application initialized successfully")
            self.is_initialized = True
        else:
            print("Error: Failed to initialize application")
    
    def _add_command(self):
        """Add or update website credentials."""
        url = self.args.url
        username = self.args.username
        
        # Get password
        password = self._get_password(self.args.password, f"Enter password for {url}: ")
        
        if not password:
            print("Error: Password is required")
            return
        
        has_bonus = self.args.has_bonus
        notes = self.args.notes or ""
        
        # Add website using credential manager directly
        if self.credential_manager:
            if self.credential_manager.add_website(url, username, password, has_bonus, notes):
                print(f"Website {url} added/updated successfully")
            else:
                print(f"Error: Failed to add/update website {url}")
        else:
            # Fallback to app_core
            if self.app_core.add_website(url, username, password, has_bonus, notes):
                print(f"Website {url} added/updated successfully")
            else:
                print(f"Error: Failed to add/update website {url}")
    
    def _remove_command(self):
        """Remove website credentials."""
        url = self.args.url
        
        # Confirm removal
        if not self.args.force:
            confirm = input(f"Are you sure you want to remove {url}? (y/n): ")
            
            if confirm.lower() != "y":
                print("Removal cancelled")
                return
        
        # Remove website
        if self.credential_manager:
            if self.credential_manager.remove_website(url):
                print(f"Website {url} removed successfully")
            else:
                print(f"Error: Failed to remove website {url}")
        else:
            if self.app_core.remove_website(url):
                print(f"Website {url} removed successfully")
            else:
                print(f"Error: Failed to remove website {url}")
    
    def _list_command(self):
        """List website credentials."""
        # Get websites
        websites = {}
        if self.credential_manager:
            if self.args.bonus_only:
                websites = {url: creds for url, creds in self.credential_manager.credentials.items() 
                           if creds.get("has_bonus", False)}
                print("Listing websites with bonus:")
            else:
                websites = self.credential_manager.credentials
                print("Listing all websites:")
        else:
            if self.args.bonus_only:
                websites = self.app_core.get_bonus_websites()
                print("Listing websites with bonus:")
            else:
                websites = self.app_core.get_all_websites()
                print("Listing all websites:")
        
        if not websites:
            print("No websites found")
            return
        
        # Print websites
        print("\n{:<40} {:<20} {:<10} {:<30}".format("URL", "Username", "Has Bonus", "Last Login"))
        print("-" * 100)
        
        for url, data in websites.items():
            # Format last login info
            last_login = "Never"
            if data.get("last_login"):
                timestamp = data["last_login"]["timestamp"]
                success = "Success" if data["last_login"]["success"] else "Failed"
                last_login = f"{timestamp} ({success})"
            
            # Format has_bonus
            has_bonus = "Yes" if data.get("has_bonus", False) else "No"
            
            print("{:<40} {:<20} {:<10} {:<30}".format(
                url[:40], data["username"][:20], has_bonus, last_login[:30]
            ))
    
    def _login_command(self):
        """Login to website(s)."""
        # Set browser options
        if self.app_core.browser_automation:
            self.app_core.browser_automation.set_browser_type(self.args.browser)
            self.app_core.browser_automation.set_headless(self.args.headless)
        
        # Get websites to login
        websites = {}
        urls_to_login = []
        
        if self.credential_manager:
            websites = self.credential_manager.credentials
        else:
            websites = self.app_core.get_all_websites()
            
        if self.args.urls:
            # Login to specified websites
            urls = self.args.urls
            urls_to_login = [url for url in urls if url in websites]
            
            if not urls_to_login:
                print("Error: No valid websites specified")
                return
        elif self.args.bonus_only:
            # Login to bonus websites
            urls_to_login = [url for url, data in websites.items() if data.get("has_bonus", False)]
            
            if not urls_to_login:
                print("No bonus websites found")
                return
        else:
            # Login to all websites
            urls_to_login = list(websites.keys())
            
            if not urls_to_login:
                print("No websites found")
                return
        
        # Login to each website
        print(f"Logging in to {len(urls_to_login)} website(s)...")
        
        # Create event loop for async operations
        loop = asyncio.get_event_loop()
        
        try:
            # Login to each website
            for url in urls_to_login:
                print(f"\nLogging in to {url}...")
                
                # Get credentials
                credentials = websites[url]
                
                # Initialize browser if needed
                if not hasattr(self.app_core.browser_automation, 'browser') or not self.app_core.browser_automation.browser:
                    print("Initializing browser...")
                    loop.run_until_complete(self.app_core.browser_automation.initialize())
                
                # Login to website
                status = loop.run_until_complete(
                    self.app_core.browser_automation.login_to_website(
                        url, credentials["username"], credentials["password"],
                        lambda s: print(f"Status: {s['stage']} - {s['message']}")
                    )
                )
                
                # Check if user action is required
                if status.get("requires_user_action", False):
                    if status.get("captcha_detected", False):
                        print("\nCAPTCHA detected. Please complete the CAPTCHA in the browser window.")
                    elif status.get("two_factor_detected", False):
                        print("\nTwo-factor authentication detected. Please complete the verification in the browser window.")
                    
                    print("Waiting for user action (press Ctrl+C to skip)...")
                    
                    try:
                        # Wait for user action
                        loop.run_until_complete(self.app_core.browser_automation.wait_for_user_action())
                    except KeyboardInterrupt:
                        print("\nSkipping website...")
                        continue
                
                # Update last login timestamp
                if status["success"] is not None:
                    if self.credential_manager:
                        self.credential_manager.update_last_login(url, status["success"])
                    else:
                        self.app_core.credential_manager.update_last_login(url, status["success"])
                
                # Print result
                if status["success"]:
                    print(f"Login successful for {url}")
                elif status["success"] is False:
                    print(f"Login failed for {url}: {status['message']}")
                else:
                    print(f"Login status unknown for {url}")
        
        except KeyboardInterrupt:
            print("\nLogin process interrupted")
        finally:
            # Close browser
            if hasattr(self.app_core.browser_automation, 'browser') and self.app_core.browser_automation.browser:
                print("\nClosing browser...")
                loop.run_until_complete(self.app_core.browser_automation.close())
    
    def _change_password_command(self):
        """Change master password."""
        # Get current password
        current = self._get_password(self.args.current_password, "Enter current master password: ")
        
        if not current:
            print("Error: Current password is required")
            return
        
        # Verify current password
        if self.credential_manager:
            if current != self.credential_manager.master_password:
                print("Error: Incorrect password")
                return
        else:
            if current != self.app_core.credential_manager.master_password:
                print("Error: Incorrect password")
                return
        
        # Get new password
        new_password = self._get_password(self.args.new_password, "Enter new master password (min 8 characters): ")
        
        if not new_password:
            print("Error: New password is required")
            return
        
        if len(new_password) < 8:
            print("Error: New password must be at least 8 characters")
            return
        
        # Handle password confirmation
        if self.args.no_confirm:
            # Skip confirmation
            confirm = new_password
        elif self.args.confirm_password:
            # Use provided confirmation
            confirm = self.args.confirm_password
        else:
            # Prompt for confirmation
            confirm = self._get_password(None, "Confirm new master password: ")
        
        if new_password != confirm:
            print("Error: Passwords do not match")
            return
        
        # Change password
        if self.credential_manager:
            if self.credential_manager.set_master_password(new_password):
                print("Master password changed successfully")
            else:
                print("Error: Failed to change master password")
        else:
            if self.app_core.set_master_password(new_password):
                print("Master password changed successfully")
            else:
                print("Error: Failed to change master password")
    
    def _ensure_initialized(self, master_password=None):
        """
        Ensure application is initialized with master password.
        
        Args:
            master_password (str, optional): Master password for non-interactive use
            
        Returns:
            bool: True if initialized, False otherwise
        """
        if self.is_initialized and (self.app_core or self.credential_manager):
            return True
        
        # Check if credentials file exists
        data_dir = self.config_manager.get("data_dir")
        credentials_file = os.path.join(data_dir, "credentials.enc")
        
        if not os.path.exists(credentials_file):
            print("Error: Application not initialized. Run 'init' command first.")
            return False
        
        # Get master password
        password = self._get_password(master_password, "Enter master password: ")
        
        if not password:
            print("Error: Master password is required")
            return False
        
        # Initialize credential manager directly
        try:
            self.credential_manager = CredentialManager(self.config_manager, password)
            
            # Force initialization of cipher suite
            if not hasattr(self.credential_manager, 'cipher_suite') or self.credential_manager.cipher_suite is None:
                self.credential_manager._initialize_cipher_suite()
                
            # Load credentials
            if not self.credential_manager.load_credentials():
                print("Error: Failed to load credentials")
                return False
                
            # Initialize app core for other operations
            self.app_core = AppCore(self.config_manager)
            if not self.app_core.initialize(password):
                print("Error: Failed to initialize application core")
                return False
                
            self.is_initialized = True
            return True
        except Exception as e:
            print(f"Error: {str(e)}")
            return False
    
    def _get_password(self, arg_password, prompt):
        """
        Get password from argument or prompt.
        
        Args:
            arg_password (str): Password from command-line argument
            prompt (str): Prompt message for getpass
            
        Returns:
            str: Password
        """
        if arg_password:
            return arg_password
        
        try:
            return getpass.getpass(prompt)
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled")
            return None

def main():
    """Main entry point for CLI application."""
    CLI()

if __name__ == "__main__":
    main()
