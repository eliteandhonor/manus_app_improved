"""
Main Window for the Automated Login Application.
Provides the primary user interface for the application with modern styling.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import asyncio
import threading
import webbrowser
import os
from PIL import Image, ImageTk
from ..core.app_core import AppCore
from ..core.service_container import ServiceContainer
from ..utils.config_manager import ConfigManager
from ..utils.logger import Logger
from ..utils.error_handler import ErrorHandler
from .credential_ui import CredentialDialog
from .automation_ui import AutomationFrame

from .dialogs import ModernDialog, ModernPasswordDialog, PostLoginDelayDialog

class MainWindow:
    """Main application window class with modern styling."""
    
    def __init__(self, root, container: ServiceContainer):
        """
        Initialize main window.
        
        Args:
            root: Tkinter root window
            container: Service container with dependencies
        """
        self.container = container
        self.logger = container.get("logger") if container.has("logger") else Logger("MainWindow")
        self.root = root
        self.root.title("Automated Login Manager")
        self.root.geometry("1000x700")
        self.root.minsize(900, 600)
        
        # Configure styles
        self.style = ttk.Style()
        self._configure_styles()
        
        # Set icon (would be replaced with actual icon in production)
        # self.root.iconbitmap("path/to/icon.ico")
        
        # Get configuration from container
        self.config_manager = container.get("config_manager")
        
        # Use already-initialized AppCore from the service container
        if container.has("app_core"):
            self.app_core = container.get("app_core")
            self.is_initialized = True
        else:
            raise RuntimeError("AppCore must be initialized and registered in the service container before creating MainWindow.")
        
        # Create UI elements
        self._create_menu()
        self._create_main_frame()
        
        # Bind close event
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Ensure credentials are loaded on startup if already initialized
        if self.is_initialized:
            self._refresh_credentials()
    
    def _configure_styles(self):
        """Configure modern styles for the application."""
        # Configure theme
        try:
            # Try to use a modern theme if available
            self.style.theme_use("clam")
        except tk.TclError:
            # Fall back to default theme
            pass
        
        # Configure colors
        bg_color = "#f5f5f5"
        accent_color = "#3498db"
        text_color = "#333333"
        
        # Configure common styles
        self.style.configure("TFrame", background=bg_color)
        self.style.configure("TLabel", background=bg_color, foreground=text_color, font=("Segoe UI", 10))
        self.style.configure("TButton", font=("Segoe UI", 10))
        self.style.configure("TEntry", font=("Segoe UI", 10))
        self.style.configure("TCheckbutton", background=bg_color, font=("Segoe UI", 10))
        
        # Configure notebook
        self.style.configure("TNotebook", background=bg_color, tabmargins=[2, 5, 2, 0])
        self.style.configure("TNotebook.Tab", background="#e0e0e0", foreground=text_color, 
                            font=("Segoe UI", 10), padding=[10, 4], focuscolor=accent_color)
        self.style.map("TNotebook.Tab", 
                      background=[("selected", accent_color)],
                      foreground=[("selected", "white")])
        
        # Configure treeview
        self.style.configure("Treeview", 
                            background="white", 
                            foreground=text_color,
                            rowheight=25,
                            font=("Segoe UI", 10))
        self.style.configure("Treeview.Heading", 
                            font=("Segoe UI", 10, "bold"),
                            background="#e0e0e0",
                            foreground=text_color)
        self.style.map("Treeview", 
                      background=[("selected", accent_color)],
                      foreground=[("selected", "white")])
    
    def _create_menu(self):
        """Create application menu."""
        # Create menu bar
        self.menu_bar = tk.Menu(self.root)
        self.root.config(menu=self.menu_bar)
        
        # File menu
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        file_menu.add_command(label="Change Master Password", command=self._change_master_password)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_close)
        self.menu_bar.add_cascade(label="File", menu=file_menu)
        
        # Settings menu
        settings_menu = tk.Menu(self.menu_bar, tearoff=0)
        settings_menu.add_command(label="Browser Settings", command=self._browser_settings)
        settings_menu.add_command(label="Post-Login Delay", command=self._post_login_delay_settings)
        self.menu_bar.add_cascade(label="Settings", menu=settings_menu)
        
        # Help menu
        help_menu = tk.Menu(self.menu_bar, tearoff=0)
        help_menu.add_command(label="About", command=self._show_about)
        help_menu.add_command(label="Help", command=self._show_help)
        self.menu_bar.add_cascade(label="Help", menu=help_menu)
    
    def _create_main_frame(self):
        """Create main application frame with notebook tabs."""
        # Create main frame
        self.main_frame = ttk.Frame(self.root, padding=10)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create notebook
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create credential tab
        self.credential_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.credential_frame, text="Credentials")
        
        # Create automation tab
        self.automation_frame = AutomationFrame(self.notebook, self.app_core)
        self.notebook.add(self.automation_frame, text="Automation")
        
        # Create credential management UI
        self._create_credential_ui()
        
        # Create status bar
        self.status_bar = ttk.Label(self.root, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def _create_credential_ui(self):
        """Create credential management UI."""
        # Create top frame for buttons
        button_frame = ttk.Frame(self.credential_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Create buttons
        add_button = ttk.Button(button_frame, text="Add Website", command=self._add_website)
        add_button.pack(side=tk.LEFT, padx=(0, 5))
        
        edit_button = ttk.Button(button_frame, text="Edit", command=self._edit_website)
        edit_button.pack(side=tk.LEFT, padx=5)
        
        remove_button = ttk.Button(button_frame, text="Remove", command=self._remove_website)
        remove_button.pack(side=tk.LEFT, padx=5)
        
        # Create treeview for credentials
        columns = ("url", "username", "has_bonus", "google_login", "last_login")
        self.credential_tree = ttk.Treeview(self.credential_frame, columns=columns, show="headings")
        
        # Configure columns
        self.credential_tree.heading("url", text="Website URL")
        self.credential_tree.heading("username", text="Username")
        self.credential_tree.heading("has_bonus", text="Has Bonus")
        self.credential_tree.heading("google_login", text="Google Login")
        self.credential_tree.heading("last_login", text="Last Login")
        
        self.credential_tree.column("url", width=300)
        self.credential_tree.column("username", width=200)
        self.credential_tree.column("has_bonus", width=100)
        self.credential_tree.column("google_login", width=110)
        self.credential_tree.column("last_login", width=200)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.credential_frame, orient=tk.VERTICAL, command=self.credential_tree.yview)
        self.credential_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack treeview and scrollbar
        self.credential_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind double-click to edit
        self.credential_tree.bind("<Double-1>", lambda e: self._edit_website())

        # Add right-click context menu for toggling Google login flag
        self.credential_tree.bind("<Button-3>", self._show_credential_context_menu)
        self.credential_context_menu = tk.Menu(self.credential_tree, tearoff=0)
        self.credential_context_menu.add_command(label="Toggle Google Login", command=self._toggle_google_login_flag)
    
    def _refresh_credentials(self):
        """Refresh credential list."""
        # Clear treeview
        for item in self.credential_tree.get_children():
            self.credential_tree.delete(item)
        
        # Get credentials
        websites = self.app_core.get_all_websites()
# DEBUG: Print websites to console for troubleshooting
        print("DEBUG: Websites returned by get_all_websites():", websites)
        
        # Add to treeview
        for url, data in websites.items():
            has_bonus = "Yes" if data.get("has_bonus", False) else "No"
            google_login = "Yes" if data.get("google_login", False) else "No"
            last_login = data.get("last_login", "Never")
            
            self.credential_tree.insert("", tk.END, values=(url, data["username"], has_bonus, google_login, last_login))
    
    def _show_credential_context_menu(self, event):
        # Show context menu on right-click
        selected = self.credential_tree.identify_row(event.y)
        if selected:
            self.credential_tree.selection_set(selected)
            self.credential_context_menu.tk_popup(event.x_root, event.y_root)

    def _toggle_google_login_flag(self):
        # Toggle the Google login flag for the selected credential
        selected = self.credential_tree.selection()
        if not selected:
            return
        url = self.credential_tree.item(selected[0], "values")[0]
        website = self.app_core.get_website(url)
        if not website:
            return
        new_flag = not website.get("google_login", False)
        # Update credential with new flag, keep other fields the same
        self.app_core.add_website(
            url,
            website["username"],
            website["password"],
            website.get("has_bonus", False),
            website.get("notes", ""),
            google_login=new_flag
        )
        self._refresh_credentials()
        self.status_bar.config(text=f"Set Google Login to {'Yes' if new_flag else 'No'} for {url}")

    def _add_website(self):
        """Add a new website."""
        if not self.is_initialized:
            messagebox.showinfo("Info", "Please initialize the application first")
            return
        dialog = CredentialDialog(self.root, "Add Website")
        result = dialog.result

        if result:
            url, username, password, has_bonus, notes, google_login = result
            success = self.app_core.add_website(url, username, password, has_bonus, notes, google_login=google_login)

            if success:
                self._refresh_credentials()
                self.status_bar.config(text=f"Added website: {url}")
            else:
                messagebox.showerror("Error", f"Failed to add website: {url}")
    
    def _edit_website(self):
        """Edit selected website."""
        if not self.is_initialized:
            messagebox.showinfo("Info", "Please initialize the application first")
            return
        # Get selected item
        selected = self.credential_tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Please select a website to edit")
            return
        
        # Get URL from selected item
        url = self.credential_tree.item(selected[0], "values")[0]
        
        # Get website data
        website = self.app_core.get_website(url)
        if not website:
            messagebox.showerror("Error", f"Failed to get website data for: {url}")
            return
        
        # Show dialog
        dialog = CredentialDialog(self.root, "Edit Website",
                                 url=url,
                                 username=website["username"],
                                 password=website["password"],
                                 has_bonus=website.get("has_bonus", False),
                                 notes=website.get("notes", ""),
                                 google_login=website.get("google_login", False))
        result = dialog.result

        if result:
            new_url, username, password, has_bonus, notes, google_login = result

            # Remove old URL if changed
            if new_url != url:
                self.app_core.remove_website(url)

            # Add new data
            success = self.app_core.add_website(new_url, username, password, has_bonus, notes, google_login=google_login)

            if success:
                self._refresh_credentials()
                self.status_bar.config(text=f"Updated website: {new_url}")
            else:
                messagebox.showerror("Error", f"Failed to update website: {new_url}")
    
    def _remove_website(self):
        """Remove selected website."""
        if not self.is_initialized:
            messagebox.showinfo("Info", "Please initialize the application first")
            return
        # Get selected item
        selected = self.credential_tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Please select a website to remove")
            return
        
        # Get URL from selected item
        url = self.credential_tree.item(selected[0], "values")[0]
        
        # Confirm removal
        if messagebox.askyesno("Confirm", f"Are you sure you want to remove {url}?"):
            success = self.app_core.remove_website(url)
            
            if success:
                self._refresh_credentials()
                self.status_bar.config(text=f"Removed website: {url}")
            else:
                messagebox.showerror("Error", f"Failed to remove website: {url}")
    
    def _browser_settings(self):
        """Show browser settings dialog."""
        # Get current settings
        browser_type = self.config_manager.get("browser", "chromium")
        headless = self.config_manager.get("headless", False)
        
        # Create dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Browser Settings")
        dialog.geometry("400x200")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Create frame
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Create browser type selection
        ttk.Label(frame, text="Browser Type:").grid(row=0, column=0, sticky=tk.W, pady=5)
        browser_var = tk.StringVar(value=browser_type)
        browser_combo = ttk.Combobox(frame, textvariable=browser_var, state="readonly")
        browser_combo["values"] = ("chromium", "firefox", "webkit")
        browser_combo.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # Create headless mode checkbox
        headless_var = tk.BooleanVar(value=headless)
        headless_check = ttk.Checkbutton(frame, text="Headless Mode", variable=headless_var)
        headless_check.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Create buttons
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=20)
        
        def save_settings():
            self.config_manager.set("browser", browser_var.get())
            self.config_manager.set("headless", headless_var.get())
            self.config_manager.save()
            dialog.destroy()
            self.status_bar.config(text="Browser settings updated")
        
        save_button = ttk.Button(button_frame, text="Save", command=save_settings)
        save_button.pack(side=tk.LEFT, padx=5)
        
        cancel_button = ttk.Button(button_frame, text="Cancel", command=dialog.destroy)
        cancel_button.pack(side=tk.LEFT, padx=5)
    
    def _post_login_delay_settings(self):
        """Show post-login delay settings dialog."""
        # Get current setting
        current_delay = self.config_manager.get("post_login_delay", 5)
        
        # Show dialog
        dialog = PostLoginDelayDialog(self.root, current_delay)
        new_delay = dialog.result

        if new_delay is not None:
            self.config_manager.set("post_login_delay", new_delay)
            self.config_manager.save()
            self.status_bar.config(text=f"Post-login delay set to {new_delay} seconds")
    
    def _change_master_password(self):
        """Change master password."""
        if not self.is_initialized:
            messagebox.showinfo("Info", "Please initialize the application first")
            return
        
        # Show dialog
        dialog = ModernPasswordDialog(self.root, "Change Master Password", "Enter new master password:")
        new_password = dialog.show()
        
        if new_password:
            success = self.app_core.set_master_password(new_password)
            
            if success:
                messagebox.showinfo("Success", "Master password changed successfully")
                self.status_bar.config(text="Master password changed")
            else:
                messagebox.showerror("Error", "Failed to change master password")
    
    def _prompt_master_password(self):
        """Prompt for master password."""
        dialog = ModernPasswordDialog(self.root, "Master Password", "Enter master password:")
        password = dialog.show()
        
        if password:
            success = self.app_core.initialize(password)
            
            if success:
                self.is_initialized = True
                self._refresh_credentials()
                self.status_bar.config(text="Application initialized")
            else:
                messagebox.showerror("Error", "Invalid master password")
                self.root.after(500, self._prompt_master_password)
        else:
            # User cancelled, exit application
            self.root.destroy()
    
    def _show_welcome_dialog(self):
        """Show welcome dialog for first run."""
        dialog = ModernDialog(self.root, "Welcome", 
                             "Welcome to the Automated Login Manager!\n\n"
                             "This application helps you manage your website logins and automate the login process.\n\n"
                             "Please set a master password to protect your credentials.")
        dialog.show()
        
        # Prompt for master password
        self._set_initial_master_password()
    
    def _set_initial_master_password(self):
        """Set initial master password."""
        dialog = ModernPasswordDialog(self.root, "Set Master Password", "Set a master password:")
        password = dialog.show()
        
        if password:
            # Initialize application
            success = self.app_core.initialize(password)
            
            if success:
                self.is_initialized = True
                self.config_manager.set("first_run", False)
                self.config_manager.save()
                self.status_bar.config(text="Application initialized")
                
                # Show quick tutorial
                messagebox.showinfo("Tutorial", 
                                   "To get started:\n\n"
                                   "1. Add website credentials in the 'Credentials' tab\n"
                                   "2. Use the 'Automation' tab to log in to websites\n"
                                   "3. Configure browser settings in the 'Settings' menu")
            else:
                messagebox.showerror("Error", "Failed to initialize application")
                self.root.after(500, self._set_initial_master_password)
        else:
            # User cancelled, exit application
            self.root.destroy()
    
    def _show_about(self):
        """Show about dialog."""
        dialog = ModernDialog(self.root, "About", 
                             "Automated Login Manager\n\n"
                             "Version: 2.0\n\n"
                             "A secure application for managing website logins and automating the login process.")
        dialog.show()
    
    def _show_help(self):
        """Show help dialog."""
        dialog = ModernDialog(self.root, "Help", 
                             "Automated Login Manager Help\n\n"
                             "Credentials Tab:\n"
                             "- Add, edit, and remove website credentials\n\n"
                             "Automation Tab:\n"
                             "- Log in to websites automatically\n"
                             "- View login status and history\n\n"
                             "Settings Menu:\n"
                             "- Configure browser settings\n"
                             "- Set post-login delay\n\n"
                             "For more help, please refer to the documentation.")
        dialog.show()
    
    def _on_close(self):
        """Handle window close event."""
        if messagebox.askyesno("Confirm", "Are you sure you want to exit?"):
            # Close application core
            if self.is_initialized:
                self.app_core.close()
            
            # Destroy window
            self.root.destroy()
