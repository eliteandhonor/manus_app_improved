"""
Application Core for the Automated Login Application.
Connects GUI with backend functionality and manages application state.
"""

import asyncio
import threading
import uuid
from typing import Dict, Optional, Any, Callable, List, Tuple, Union, Awaitable

from ..core.credential_manager import CredentialManager
from ..core.browser_automation import BrowserAutomation, precheck_google_oauth
from ..core.service_container import ServiceContainer
from ..utils.logger import Logger
from ..utils.config_manager import ConfigManager
from ..utils.error_handler import ErrorHandler
from ..utils.exceptions import AppError, BrowserError, CredentialError

error_handler = ErrorHandler(Logger("AppCore"))

class AppCore:
    """
    Core application logic that connects GUI with backend functionality.
    Manages application state and coordinates between modules.
    """
    
    def __init__(self, container_or_config) -> None:
        """
        Initialize application core with dependencies from service container or directly from ConfigManager.
        
        Args:
            container_or_config: ServiceContainer or ConfigManager instance
        """
        # Support both ServiceContainer and ConfigManager for test and app flexibility
        from ..utils.config_manager import ConfigManager
        from ..core.service_container import ServiceContainer

        self.container = None
        self.logger = None
        self.config_manager = None
        self.error_handler = None

        if isinstance(container_or_config, ServiceContainer):
            self.container = container_or_config
            self.logger = self.container.get("logger") if self.container.has("logger") else Logger("AppCore")
            self.config_manager = self.container.get("config_manager")
            self.error_handler = self.container.get("error_handler") if self.container.has("error_handler") else ErrorHandler(self.logger)
        elif isinstance(container_or_config, ConfigManager):
            self.config_manager = container_or_config
            self.logger = Logger("AppCore")
            self.error_handler = ErrorHandler(self.logger)
        else:
            raise TypeError("AppCore requires a ServiceContainer or ConfigManager as its argument.")

        # These will be initialized lazily when needed
        self.credential_manager: Optional[CredentialManager] = None
        self._browser_automation: Optional[BrowserAutomation] = None

        self.login_tasks: Dict[str, Dict[str, Any]] = {}
        self.is_initialized: bool = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
    
    @property
    def get_credential_manager(self) -> CredentialManager:
        """
        Get or initialize credential manager.
        
        Returns:
            Credential manager instance
        
        Raises:
            CredentialError: If credential manager is not initialized
        """
        if not self.credential_manager:
            raise CredentialError("Credential manager not initialized")
        return self.credential_manager
    
    @property
    def browser_automation(self) -> BrowserAutomation:
        """
        Lazily instantiate and return the browser automation instance.

        Returns:
            Browser automation instance

        Raises:
            BrowserError: If config_manager is not initialized
        """
        if self._browser_automation is None:
            # Prefer container if it has a browser_automation, else create new
            if getattr(self, "container", None) is not None and self.container.has("browser_automation"):
                self._browser_automation = self.container.get("browser_automation")
            else:
                if self.config_manager is None:
                    raise BrowserError("Config manager not initialized for browser automation")
                self._browser_automation = BrowserAutomation(self.config_manager)
        return self._browser_automation

    @browser_automation.setter
    def browser_automation(self, value: BrowserAutomation) -> None:
        self._browser_automation = value
    
    async def initialize_async(self, master_password: Optional[str] = None) -> bool:
        """
        Initialize application core components asynchronously.
        
        Args:
            master_password: Master password for credential encryption
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure config_manager is set
            if self.config_manager is None:
                self.config_manager = ConfigManager()
            # Initialize credential manager
            self.credential_manager = CredentialManager(self.config_manager, master_password)
            
            # Instantiate and initialize browser automation
            self._browser_automation = BrowserAutomation(self.config_manager)
            await self._browser_automation.initialize()
            
            self.is_initialized = True
            self.logger.info("Application core initialized asynchronously")
            return True
        except Exception as e:
            self.logger.error(f"Error initializing application core asynchronously: {e}")
            return False
    
    @error_handler.handle
    def initialize(self, master_password: Optional[str] = None) -> bool:
        """
        Initialize application core components (synchronous wrapper).
        
        Args:
            master_password: Master password for credential encryption
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure config_manager is set
            if self.config_manager is None:
                self.config_manager = ConfigManager()
            # Initialize credential manager
            self.credential_manager = CredentialManager(self.config_manager, master_password)
            
            # Do not instantiate browser automation here (lazy loading)
            self.is_initialized = True
            self.logger.info("Application core initialized")
            return True
        except Exception as e:
            self.logger.error(f"Error initializing application core: {e}")
            return False
    
    @error_handler.handle
    def set_master_password(self, password: str) -> bool:
        """
        Set or change master password.
        
        Args:
            password: New master password
            
        Returns:
            True if successful, False otherwise
        """
        credential_manager = self.get_credential_manager
        return credential_manager.set_master_password(password)
    
    @error_handler.handle
    def add_website(self, url: str, username: str, password: str,
                   has_bonus: bool = False, notes: str = "", google_login: bool = False) -> bool:
        """
        Add or update website credentials.
        
        Args:
            url: Website URL
            username: Login username
            password: Login password
            has_bonus: Whether site offers free credit/trial bonus
            notes: Additional notes
            google_login: Whether this site uses Google login (manual system browser required)
            
        Returns:
            True if successful, False otherwise
        """
        self.logger.debug(f"add_website ENTRY: url={url}, username={username}, has_bonus={has_bonus}, google_login={google_login}")
        credential_manager = self.get_credential_manager
        
        self.logger.debug("add_website: calling credential_manager.add_website")
        result = credential_manager.add_website(url, username, password, has_bonus, notes, google_login=google_login)
        self.logger.debug(f"add_website EXIT: result={result}")
        return result
    
    @error_handler.handle
    def remove_website(self, url: str) -> bool:
        """
        Remove website credentials.
        
        Args:
            url: Website URL
            
        Returns:
            True if successful, False otherwise
        """
        credential_manager = self.get_credential_manager
        return credential_manager.remove_website(url)
    
    @error_handler.handle
    def get_website(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get website credentials.
        
        Args:
            url: Website URL
            
        Returns:
            Website credentials or None if not found
        """
        credential_manager = self.get_credential_manager
        return credential_manager.get_website(url)
    
    @error_handler.handle
    def get_all_websites(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all website credentials.
        
        Returns:
            All website credentials
        """
        credential_manager = self.get_credential_manager
        return credential_manager.get_all_websites()
    
    @error_handler.handle
    def get_bonus_websites(self) -> Dict[str, Dict[str, Any]]:
        """
        Get websites with bonus flag.
        
        Returns:
            Website credentials with has_bonus=True
        """
        credential_manager = self.get_credential_manager
        return credential_manager.get_bonus_websites()
    
    def _get_event_loop(self) -> asyncio.AbstractEventLoop:
        """
        Get or create an event loop for async operations.
        
        Returns:
            Event loop
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            return loop
        except RuntimeError:
            # No event loop in current thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop
    
    async def login_to_website_async(self, url: str,
                                   status_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
                                   google_login_method: Optional[str] = None,
                                   force_prompt: bool = False,
                                   prompt_google_login_method: Optional[Callable[[str], str]] = None,
                                   wait_for_manual_login_confirmation: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """
        Login to a website asynchronously.

        Args:
            url: Website URL
            status_callback: Callback function for status updates
            google_login_method: "playwright" or "system_browser" for Google login, or None
            force_prompt: Force prompt for login method selection
            prompt_google_login_method: Optional callback to prompt user for Google login method

        Returns:
            Status dictionary with login result
        """
        try:
            # Always perform Google login detection scan before any browser automation
            self.logger.info(f"Performing Google login detection scan for {url} before browser automation.")
            if status_callback:
                status_callback({
                    "url": url,
                    "stage": "precheck_google_oauth",
                    "success": None,
                    "message": "Performing Google login detection scan before browser automation."
                })
            has_google_oauth = precheck_google_oauth(url, logger=self.logger)

            browser_automation = self.browser_automation
            credential_manager = self.get_credential_manager

            # Get website credentials
            credentials = credential_manager.get_website(url)
            if not credentials:
                self.logger.error(f"No credentials found for {url}")
                return {"success": False, "message": f"No credentials found for {url}"}

            # If Google login is detected and no method is set, prompt the user for their choice
            if has_google_oauth and not google_login_method:
                self.logger.info(f"Google login detected for {url}. Prompting user for login method.")
                if prompt_google_login_method is not None:
                    user_choice = prompt_google_login_method(url)
                    if user_choice == "manual_browser":
                        google_login_method = "system_browser"
                    elif user_choice == "continue_automation":
                        google_login_method = "playwright"
                    else:
                        self.logger.error("User cancelled Google login method selection or invalid choice.")
                        error_status = {
                            "url": url,
                            "stage": "user_cancelled",
                            "success": False,
                            "message": "User cancelled Google login method selection."
                        }
                        if status_callback:
                            status_callback(error_status)
                        return error_status
                else:
                    # No prompt available, abort automation to avoid defaulting to automation
                    self.logger.error("Google login detected but no prompt function provided. Aborting automation to avoid defaulting to automation.")
                    error_status = {
                        "url": url,
                        "stage": "prompt_missing",
                        "success": False,
                        "message": "Google login detected but no prompt function provided. Aborting automation."
                    }
                    if status_callback:
                        status_callback(error_status)
                    return error_status

            # If Google login is not detected, proceed with default (form) automation
            if not has_google_oauth and not google_login_method:
                google_login_method = None  # Will default to form login in browser_automation

            # If manual browser is chosen, open system browser and wait for user confirmation
            if google_login_method == "system_browser" and wait_for_manual_login_confirmation is not None:
                # Open the system browser for manual login
                import webbrowser
                webbrowser.open(url)
                if status_callback:
                    status_callback({
                        "url": url,
                        "stage": "manual_browser_opened",
                        "success": None,
                        "message": "System browser opened for manual login. Please complete login and click Continue."
                    })
                # Wait for user confirmation before proceeding
                wait_for_manual_login_confirmation(url)

            # Run login coroutine (for automation or after manual confirmation)
            status = await browser_automation.login_to_website(
                url, credentials["username"], credentials["password"], status_callback,
                google_login_method=google_login_method,
                force_prompt=force_prompt
            )

            # Update last login timestamp
            if status["success"] is not None:
                credential_manager.update_last_login(url, status["success"])

            return status
        except Exception as e:
            self.logger.error(f"Error in login task: {e}")
            error_status = {
                "url": url,
                "stage": "error",
                "success": False,
                "message": f"Error: {str(e)}"
            }
            if status_callback:
                status_callback(error_status)
            return error_status
    
    @error_handler.handle
    def login_to_website(self, url: str, 
                        status_callback: Optional[Callable[[Dict[str, Any]], None]] = None, 
                        google_login_method: Optional[str] = None, 
                        force_prompt: bool = False) -> Optional[str]:
        """
        Login to a website in a separate thread.

        Args:
            url: Website URL
            status_callback: Callback function for status updates
            google_login_method: "playwright" or "system_browser" for Google login, or None
            force_prompt: Force prompt for login method selection

        Returns:
            Task ID for tracking login progress
        """
        try:
            credential_manager = self.get_credential_manager

            # Get website credentials
            credentials = credential_manager.get_website(url)
            if not credentials:
                self.logger.error(f"No credentials found for {url}")
                return None

            # Generate task ID
            task_id = str(uuid.uuid4())

            # Create login task
            self.login_tasks[task_id] = {
                "url": url,
                "status": "starting",
                "thread": None
            }

            # Start login thread
            thread = threading.Thread(
                target=self._run_login_task,
                args=(task_id, url, credentials["username"], credentials["password"], 
                     status_callback, google_login_method, force_prompt)
            )
            thread.daemon = True
            thread.start()

            self.login_tasks[task_id]["thread"] = thread

            return task_id
        except Exception as e:
            self.logger.error(f"Error starting login task: {e}")
            return None
    
    def _run_login_task(self, task_id: str, url: str, username: str, password: str, 
                       status_callback: Optional[Callable[[Dict[str, Any]], None]], 
                       google_login_method: Optional[str] = None, 
                       force_prompt: bool = False) -> None:
        """
        Run login task in a separate thread.

        Args:
            task_id: Task ID
            url: Website URL
            username: Login username
            password: Login password
            status_callback: Callback function for status updates
            google_login_method: "playwright" or "system_browser" for Google login, or None
            force_prompt: Force prompt for login method selection
        """
        # Create event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Use property to ensure lazy instantiation
            browser_automation = self.browser_automation

            # Run login coroutine
            status = loop.run_until_complete(
                browser_automation.login_to_website(
                    url, username, password, status_callback,
                    google_login_method=google_login_method,
                    force_prompt=force_prompt
                )
            )

            # Update task status
            self.login_tasks[task_id]["status"] = status["stage"]

            # Update last login timestamp
            if status["success"] is not None and self.credential_manager:
                self.credential_manager.update_last_login(url, status["success"])

        except Exception as e:
            self.logger.error(f"Error in login task: {e}")
            if status_callback:
                status_callback({
                    "url": url,
                    "stage": "error",
                    "success": False,
                    "message": f"Error: {str(e)}"
                })
        finally:
            # Close event loop
            loop.close()
    
    @error_handler.handle
    def get_login_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of login task.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task status or None if not found
        """
        return self.login_tasks.get(task_id)
    
    async def wait_for_user_action_async(self, timeout: int = 300) -> bool:
        """
        Wait for user to complete manual steps asynchronously (like CAPTCHA or 2FA).
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            True if user completed action, False if timed out
        """
        try:
            browser_automation = self.browser_automation
            
            # Run wait coroutine
            return await browser_automation.wait_for_user_action(timeout)
        except Exception as e:
            self.logger.error(f"Error waiting for user action: {e}")
            return False
    
    @error_handler.handle
    def wait_for_user_action(self, task_id: str, timeout: int = 300) -> bool:
        """
        Wait for user to complete manual steps (like CAPTCHA or 2FA).
        
        Args:
            task_id: Task ID
            timeout: Timeout in seconds
            
        Returns:
            True if user completed action, False if timed out
        """
        try:
            browser_automation = self.browser_automation
            
            # Create event loop for async operations
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Run wait coroutine
                result = loop.run_until_complete(
                    browser_automation.wait_for_user_action(timeout)
                )
                return result
            finally:
                # Close event loop
                loop.close()
        except Exception as e:
            self.logger.error(f"Error waiting for user action: {e}")
            return False
    
    async def close_async(self) -> None:
        """Close application core and release resources asynchronously."""
        if self.browser_automation:
            try:
                # Close browser
                await self.browser_automation.close()
            except Exception as e:
                self.logger.error(f"Error closing browser: {e}")
        
        # Clear sensitive data
        if self.credential_manager:
            self.credential_manager.clear_memory()
        
        self.logger.info("Application core closed asynchronously")
    
    @error_handler.handle
    def close(self) -> None:
        """Close application core and release resources."""
        if self.browser_automation:
            # Create event loop for async operations
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Close browser
                loop.run_until_complete(self.browser_automation.close())
            except Exception as e:
                self.logger.error(f"Error closing browser: {e}")
            finally:
                # Close event loop
                loop.close()
        
        # Clear sensitive data
        if self.credential_manager:
            self.credential_manager.clear_memory()
        
        self.logger.info("Application core closed")
    
    def run_async(self, coroutine: Awaitable[Any]) -> Any:
        """
        Run an async coroutine from synchronous code.
        
        Args:
            coroutine: Async coroutine to run
            
        Returns:
            Result of the coroutine
        """
        loop = self._get_event_loop()
        return loop.run_until_complete(coroutine)
