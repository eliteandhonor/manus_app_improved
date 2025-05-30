"""
Automation UI for the Automated Login Application.
Provides UI for controlling browser automation.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time

from ..utils.logger import Logger
from ..utils.error_handler import ErrorHandler
error_handler = ErrorHandler(Logger("AutomationUI"))

class AutomationFrame(ttk.Frame):
    """Frame for controlling browser automation."""

    def __init__(self, parent, app_core):
        """
        Initialize automation frame.
    
        Args:
            parent: Parent widget
            app_core: Application core
        """
        from ..utils.logger import Logger
        from ..utils.config_manager import ConfigManager
        from ..utils.error_handler import ErrorHandler
        
        # Use the app's config_manager for log level control
        config_manager = getattr(app_core, "config_manager", None)
        self.logger = Logger("AutomationUI", config_manager=config_manager)
        self.error_handler = ErrorHandler(self.logger)
        
        super().__init__(parent, padding=10)
        self.app_core = app_core
        self.active_tasks = {}
        
        # Create UI elements
        self._create_ui()
    
    def _create_ui(self):
        """Create UI elements."""
        # Create top frame for controls
        control_frame = ttk.Frame(self)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Create website selection
        ttk.Label(control_frame, text="Website:").pack(side=tk.LEFT, padx=(0, 5))
        self.website_var = tk.StringVar()
        self.website_combo = ttk.Combobox(control_frame, textvariable=self.website_var, width=40)
        self.website_combo.pack(side=tk.LEFT, padx=5)
        self.website_combo.bind("<<ComboboxSelected>>", self._on_website_selected)

        # Google Login checkbox
        self.google_login_var = tk.BooleanVar(value=False)
        self.google_login_checkbox = ttk.Checkbutton(
            control_frame,
            text="Google Login",
            variable=self.google_login_var,
            command=self._on_google_login_toggle
        )
        self.google_login_checkbox.pack(side=tk.LEFT, padx=5)

        # Create login button
        self.login_button = ttk.Button(control_frame, text="Login", command=self._login)
        self.login_button.pack(side=tk.LEFT, padx=5)

        # Run All Logins button
        self.run_all_button = ttk.Button(control_frame, text="Run All Logins", command=self._run_all_logins)
        self.run_all_button.pack(side=tk.LEFT, padx=5)

        # Clear Logins button
        self.clear_logins_button = ttk.Button(control_frame, text="Clear Logins", command=self._clear_logins)
        self.clear_logins_button.pack(side=tk.LEFT, padx=5)
        
        # Create refresh button
        refresh_button = ttk.Button(control_frame, text="Refresh", command=self._refresh_websites)
        refresh_button.pack(side=tk.LEFT, padx=5)

        # Credential display frame (for extracted credentials or errors)
        self.credential_display_frame = ttk.LabelFrame(self, text="Credential Extraction Result", padding=10)
        self.credential_display_frame.pack(fill=tk.X, pady=(0, 10))
        self.credential_display_label = ttk.Label(self.credential_display_frame, text="", style="TLabel", anchor="w", justify="left")
        self.credential_display_label.pack(fill=tk.X)

        # Create status frame
        status_frame = ttk.LabelFrame(self, text="Login Status", padding=10)
        status_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create status treeview
        columns = ("url", "status", "message", "time")
        self.status_tree = ttk.Treeview(status_frame, columns=columns, show="headings")
        
        # Configure columns
        self.status_tree.heading("url", text="Website URL")
        self.status_tree.heading("status", text="Status")
        self.status_tree.heading("message", text="Message")
        self.status_tree.heading("time", text="Time")
        
        self.status_tree.column("url", width=300)
        self.status_tree.column("status", width=100)
        self.status_tree.column("message", width=300)
        self.status_tree.column("time", width=100)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(status_frame, orient=tk.VERTICAL, command=self.status_tree.yview)
        self.status_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack treeview and scrollbar
        self.status_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Refresh websites
        self._refresh_websites()
        self._sync_google_login_checkbox()
    
    @error_handler.handle
    def _refresh_websites(self):
        """Refresh website list."""
        # Clear combobox
        self.website_combo["values"] = ()
        
        # Get websites
        websites = self.app_core.get_all_websites()
        
        # Add to combobox
        self.website_combo["values"] = list(websites.keys())
        
        # Select first website if available
        if websites:
            self.website_combo.current(0)
        self._sync_google_login_checkbox()
    
    def _on_website_selected(self, event=None):
        self._sync_google_login_checkbox()

    def _sync_google_login_checkbox(self):
        url = self.website_var.get()
        if not url:
            self.google_login_var.set(False)
            self.google_login_checkbox.state(["disabled"])
            return
        website = self.app_core.get_website(url)
        if not website:
            self.google_login_var.set(False)
            self.google_login_checkbox.state(["disabled"])
            return
        self.google_login_var.set(bool(website.get("google_login", False)))
        self.google_login_checkbox.state(["!disabled"])

    def _on_google_login_toggle(self):
        url = self.website_var.get()
        if not url:
            return
        website = self.app_core.get_website(url)
        if not website:
            return
        new_flag = self.google_login_var.get()
        # Update credential with new flag, keep other fields the same
        self.app_core.add_website(
            url,
            website["username"],
            website["password"],
            website.get("has_bonus", False),
            website.get("notes", ""),
            google_login=new_flag
        )
        # No need to refresh combobox, just update status
        self.logger.info(f"Set Google Login to {'Yes' if new_flag else 'No'} for {url}")

    @error_handler.handle
    def _login(self):
        """Login to selected website using Google login flag for workflow branching."""
        import asyncio

        # Get selected website
        url = self.website_var.get()
        if not url:
            messagebox.showinfo("Info", "Please select a website")
            return

        # Check if already logging in
        if url in self.active_tasks:
            messagebox.showinfo("Info", f"Already logging in to {url}")
            return

        # Retrieve credentials
        credentials = self.app_core.get_website(url)
        if not credentials:
            messagebox.showerror("Error", f"No credentials found for {url}")
            return

        # Disable login button
        self.login_button.config(state=tk.DISABLED)

        # Add to status tree
        task_id = f"task_{int(time.time())}"
        self.active_tasks[url] = task_id

        self.status_tree.insert("", 0, iid=task_id, values=(
            url,
            "Starting",
            "Initializing login process...",
            time.strftime("%H:%M:%S")
        ))

        def wait_for_manual_login_confirmation(url):
            # Show a modal dialog with a "Continue" button
            dialog = tk.Toplevel(self)
            dialog.title("Manual Login Confirmation")
            dialog.geometry("420x180")
            dialog.transient(self)
            dialog.grab_set()
            ttk.Label(dialog, text="Manual Login Required", style="TLabel", font=("Segoe UI", 12, "bold")).pack(pady=(15, 5))
            ttk.Label(dialog, text="Please complete the login in the system browser that was just opened.\n\nOnce you have finished logging in, click Continue to proceed.", style="TLabel", wraplength=380, justify="left").pack(pady=(0, 10), padx=10)
            button_frame = ttk.Frame(dialog)
            button_frame.pack(pady=10)
            confirmed = tk.BooleanVar(value=False)
            def on_continue():
                confirmed.set(True)
                dialog.destroy()
            ttk.Button(button_frame, text="Continue", command=on_continue).pack(side=tk.LEFT, padx=5)
            dialog.wait_variable(confirmed)

        def run_login_google_manual():
            # Open system browser for manual login
            import webbrowser
            webbrowser.open(url)
            self._update_status({
                "url": url,
                "stage": "manual_browser_opened",
                "success": None,
                "message": "System browser opened for manual login. Please complete login and click Continue."
            })
            wait_for_manual_login_confirmation(url)
            self._update_status({
                "url": url,
                "stage": "manual_login_complete",
                "success": True,
                "message": "Manual login complete. Proceeding to next step."
            })
            # Monetization: open link in new tab after every login (manual)
            import webbrowser
            webbrowser.open_new_tab("https://otieu.com/4/8811956")
            self.after(1000, lambda: self.login_button.config(state=tk.NORMAL))

        def run_async_login():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # Use the async login_to_website_async, which guarantees pre-browser scan and prompt
                result = loop.run_until_complete(
                    self.app_core.login_to_website_async(
                        url,
                        status_callback=self._update_status,
                        wait_for_manual_login_confirmation=wait_for_manual_login_confirmation
                    )
                )
                # Final status update
                self._update_status(result)
                # Monetization: open link in new tab after every login
                import webbrowser
                webbrowser.open_new_tab("https://otieu.com/4/8811956")
            except Exception as e:
                self.logger.error(f"Error starting async login: {e}")
                self._update_status({
                    "url": url,
                    "stage": "error",
                    "success": False,
                    "message": f"Error: {str(e)}"
                })
            finally:
                loop.close()
                # Re-enable login button after a short delay
                self.after(1000, lambda: self.login_button.config(state=tk.NORMAL))

        # Branch: Google login flag
        if credentials.get("google_login", False):
            threading.Thread(target=run_login_google_manual, daemon=True).start()
        else:
            threading.Thread(target=run_async_login, daemon=True).start()
    
    def _run_all_logins(self):
        """Run login for all sites in order, always attempt all, handle manual/auto as needed."""
        import threading

        def batch_login():
            websites = self.app_core.get_all_websites()
            urls = list(websites.keys())
            for url in urls:
                credentials = self.app_core.get_website(url)
                if not credentials:
                    continue
                # UI update: select site in combobox
                self.website_var.set(url)
                self._sync_google_login_checkbox()
                # Run login for this site, wait for completion
                done = threading.Event()
                def on_done(*args, **kwargs):
                    done.set()
                def wait_for_manual_login_confirmation(url):
                    # Show a modal dialog with a "Continue" button
                    dialog = tk.Toplevel(self)
                    dialog.title("Manual Login Confirmation")
                    dialog.geometry("420x180")
                    dialog.transient(self)
                    dialog.grab_set()
                    ttk.Label(dialog, text="Manual Login Required", style="TLabel", font=("Segoe UI", 12, "bold")).pack(pady=(15, 5))
                    ttk.Label(dialog, text="Please complete the login in the system browser that was just opened.\n\nOnce you have finished logging in, click Continue to proceed.", style="TLabel", wraplength=380, justify="left").pack(pady=(0, 10), padx=10)
                    button_frame = ttk.Frame(dialog)
                    button_frame.pack(pady=10)
                    confirmed = tk.BooleanVar(value=False)
                    def on_continue():
                        confirmed.set(True)
                        dialog.destroy()
                    ttk.Button(button_frame, text="Continue", command=on_continue).pack(side=tk.LEFT, padx=5)
                    dialog.wait_variable(confirmed)
                def run_login():
                    if credentials.get("google_login", False):
                        import webbrowser
                        webbrowser.open(url)
                        self._update_status({
                            "url": url,
                            "stage": "manual_browser_opened",
                            "success": None,
                            "message": "System browser opened for manual login. Please complete login and click Continue."
                        })
                        wait_for_manual_login_confirmation(url)
                        self._update_status({
                            "url": url,
                            "stage": "manual_login_complete",
                            "success": True,
                            "message": "Manual login complete. Proceeding to next step."
                        })
                        self.after(100, on_done)
                        # Monetization: open link in new tab after every manual login in batch
                        import webbrowser
                        webbrowser.open_new_tab("https://otieu.com/4/8811956")
                    else:
                        import asyncio
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            result = loop.run_until_complete(
                                self.app_core.login_to_website_async(
                                    url,
                                    status_callback=self._update_status,
                                    wait_for_manual_login_confirmation=wait_for_manual_login_confirmation
                                )
                            )
                            self._update_status(result)
                            # Monetization: open link in new tab after every automated login in batch
                            import webbrowser
                            webbrowser.open_new_tab("https://otieu.com/4/8811956")
                        except Exception as e:
                            self.logger.error(f"Error in batch login for {url}: {e}")
                            self._update_status({
                                "url": url,
                                "stage": "error",
                                "success": False,
                                "message": f"Error: {str(e)}"
                            })
                        finally:
                            loop.close()
                            self.after(100, on_done)
                # Run login for this site and wait for it to finish
                self.after(0, run_login)
                done.wait()
            self.credential_display_label.config(text="Batch login complete.", style="TLabel")

        threading.Thread(target=batch_login, daemon=True).start()

    def _clear_logins(self):
        """Clear the status display and reset last login timestamps for all sites."""
        # Clear status tree
        for item in self.status_tree.get_children():
            self.status_tree.delete(item)
        # Reset last login timestamps
        websites = self.app_core.get_all_websites()
        for url in websites:
            self.app_core.get_credential_manager.update_last_login(url, None)
        self.credential_display_label.config(text="Login status and last login timestamps cleared.", style="TLabel")

    def _update_status(self, status):
        """
        Update login status in UI and credential display.
        
        Args:
            status: Status dictionary
        """
        # Get URL
        url = status.get("url", "Unknown")
        
        # Get task ID
        task_id = self.active_tasks.get(url)
        if not task_id:
            # Create new task ID if not found
            task_id = f"task_{int(time.time())}"
            self.active_tasks[url] = task_id
            
            # Add to status tree
            self.status_tree.insert("", 0, iid=task_id, values=(
                url,
                "Starting",
                "Initializing login process...",
                time.strftime("%H:%M:%S")
            ))
        
        # Update status
        stage = status.get("stage", "unknown")
        message = status.get("message", "No message")
        
        # Format stage for display
        stage_display = stage.replace("_", " ").title()
        
        # Update treeview
        self.status_tree.item(task_id, values=(
            url,
            stage_display,
            message,
            time.strftime("%H:%M:%S")
        ))
        
        # Scroll to show the item
        self.status_tree.see(task_id)

        # Update credential display frame based on status
        def set_credential_display(text, style="TLabel"):
            self.credential_display_label.config(text=text, style=style)

        # Actionable error dialog for automation failures
        def show_actionable_error_dialog(error_message):
            dialog = tk.Toplevel(self)
            dialog.title("Automation Error")
            dialog.geometry("420x220")
            dialog.transient(self)
            dialog.grab_set()
            ttk.Label(dialog, text="Automation Error", style="TLabel", font=("Segoe UI", 12, "bold")).pack(pady=(15, 5))
            ttk.Label(dialog, text=error_message, style="TLabel", wraplength=380, justify="left").pack(pady=(0, 10), padx=10)

            button_frame = ttk.Frame(dialog)
            button_frame.pack(pady=10)

            def retry():
                dialog.destroy()
                self._login()

            def manual_override():
                dialog.destroy()
                set_credential_display("Manual override selected. Please log in manually in your browser and update credentials if needed.", "TLabel")

            def try_non_headless():
                dialog.destroy()
                set_credential_display("Suggestion: Try running the browser in non-headless mode via Settings > Browser Settings.", "TLabel")

            ttk.Button(button_frame, text="Retry", command=retry).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="Manual Override", command=manual_override).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="Try Non-Headless Mode", command=try_non_headless).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="Close", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

        # Check if login is complete
        if stage in ["success", "error"]:
            # Remove from active tasks
            if url in self.active_tasks:
                del self.active_tasks[url]

            if stage == "success":
                set_credential_display("Credential extraction and login successful.\nCredentials were used for login.", "TLabel")
            elif stage == "error":
                # Detect common automation errors for actionable dialog
                lower_msg = message.lower()
                if (
                    "not found" in lower_msg
                    or "not clickable" in lower_msg
                    or "automation" in lower_msg
                    or "google sign-in button" in lower_msg
                    or "dynamic rendering" in lower_msg
                    or "overlay" in lower_msg
                    or "anti-bot" in lower_msg
                ):
                    self.after(100, lambda: show_actionable_error_dialog(message))
                else:
                    self.after(100, lambda: messagebox.showerror("Login Error", message))
                set_credential_display(f"Error: {message}\n\nActionable options: Retry, Manual Override, or Try Non-Headless Mode.", "TLabel")
        else:
            # For intermediate stages, clear or update credential display
            if stage == "precheck_google_oauth":
                set_credential_display("Scanning for Google login before browser opens...", "TLabel")
            elif stage in ["starting", "navigating", "detecting_form", "filling_form", "submitting", "waiting_for_navigation", "detecting_google_oauth", "clicking_google_oauth", "filling_google_form", "waiting_for_google_auth"]:
                set_credential_display("Automation in progress...", "TLabel")
            elif stage == "ambiguous_form":
                set_credential_display("Ambiguous login form detected. Please select the correct fields manually or use manual override.", "TLabel")
            elif stage == "captcha_detected":
                set_credential_display("CAPTCHA detected. Manual intervention required.", "TLabel")
            elif stage == "two_factor_detected":
                set_credential_display("Two-factor authentication detected. Manual intervention required.", "TLabel")
            elif stage == "manual_login":
                set_credential_display("Manual login required. Please complete the login in your browser.", "TLabel")
            else:
                set_credential_display("", "TLabel")
