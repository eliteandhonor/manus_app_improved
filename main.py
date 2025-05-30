"""
Main entry point for the Automated Login Application.
"""

import tkinter as tk
import sys
import os

# Add src directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ui.main_window import MainWindow
from src.core.service_container import ServiceContainer
from src.utils.config_manager import ConfigManager
from src.utils.logger import Logger
from src.utils.error_handler import ErrorHandler
from src.core.browser_automation import BrowserAutomation

def main():
    """Main application entry point."""
    # Create service container
    container = ServiceContainer()
    
    # Register services
    config_manager = ConfigManager()
    container.register("config_manager", config_manager)
    
    logger = Logger("Application")
    container.register("logger", logger)
    
    error_handler = ErrorHandler(logger)
    container.register("error_handler", error_handler)
    
    # Register browser automation as a factory for lazy loading
    container.register_factory("browser_automation", lambda: BrowserAutomation(config_manager))
    
    # Create root window (needed for dialogs)
    root = tk.Tk()
    root.withdraw()  # Hide main window during credential prompt

    from src.core.app_core import AppCore
    from src.ui.dialogs import ModernPasswordDialog, ModernDialog

    # Determine if first run
    first_run = config_manager.get("first_run", True)
    app_core = None
    is_initialized = False

    if first_run:
        # Show welcome dialog
        dlg = ModernDialog(
            root, "Welcome",
            "Welcome to the Automated Login Manager!\n\n"
            "This application helps you manage your website logins and automate the login process.\n\n"
            "Please set a master password to protect your credentials."
        )
        # No need to use dlg.result for welcome dialog, just instantiate
        # Prompt for initial master password
        while not is_initialized:
            dlg = ModernPasswordDialog(root, "Set Master Password", "Set a master password:")
            password = dlg.result
            if not password:
                root.destroy()
                return
            app_core = AppCore(container)
            is_initialized = app_core.initialize(password)
            if not is_initialized:
                tk.messagebox.showerror("Error", "Failed to initialize application. Please try again.")
        config_manager.set("first_run", False)
        config_manager.save()
    else:
        # Prompt for master password
        while not is_initialized:
            dlg = ModernPasswordDialog(root, "Master Password", "Enter master password:")
            password = dlg.result
            if not password:
                root.destroy()
                return
            app_core = AppCore(container)
            is_initialized = app_core.initialize(password)
            if not is_initialized:
                tk.messagebox.showerror("Error", "Invalid master password. Please try again.")

    # Register initialized AppCore in the service container
    container.register("app_core", app_core)

    root.deiconify()  # Show main window after initialization

    # Set application style
    style = tk.ttk.Style()
    style.theme_use('clam')  # Use a modern-looking theme

    # Create main window with service container
    app = MainWindow(root, container)

    # Start main loop
    root.mainloop()

if __name__ == "__main__":
    main()
