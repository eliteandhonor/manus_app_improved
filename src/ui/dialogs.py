import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

class ModernDialog(simpledialog.Dialog):
    """Modern styled dialog base class."""

    def __init__(self, parent, title, **kwargs):
        """
        Initialize modern dialog.

        Args:
            parent: Parent window
            title: Dialog title
            **kwargs: Additional arguments
        """
        self.result = None
        self.style = ttk.Style()
        self._configure_styles()
        super().__init__(parent, title, **kwargs)

    def _configure_styles(self):
        """Configure modern styles for the dialog."""
        self.style.configure("Modern.TFrame", background="#f5f5f5")
        self.style.configure("Modern.TLabel", background="#f5f5f5", font=("Segoe UI", 10))
        self.style.configure("Modern.TButton", font=("Segoe UI", 10))
        self.style.configure("Title.TLabel", background="#f5f5f5", font=("Segoe UI", 12, "bold"))

    def body(self, master):
        """Create dialog body. Override in subclasses."""
        if isinstance(master, ttk.Frame):
            master.configure(style="Modern.TFrame", padding=(20, 10))
        else:
            try:
                master.configure(background="#f5f5f5")
            except Exception:
                pass
        return None

    def buttonbox(self):
        """Create custom styled button box."""
        box = ttk.Frame(self, style="Modern.TFrame", padding=(10, 10))
        box.pack(fill=tk.X)

        ok_button = ttk.Button(box, text="OK", width=10, command=self.ok)
        ok_button.pack(side=tk.RIGHT, padx=5, pady=5)

        cancel_button = ttk.Button(box, text="Cancel", width=10, command=self.cancel)
        cancel_button.pack(side=tk.RIGHT, padx=5, pady=5)

        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)

class ModernPasswordDialog(ModernDialog):
    """Modern styled password dialog."""

    def __init__(self, parent, title, prompt, show="*", confirm=False, min_length=0):
        """
        Initialize password dialog.

        Args:
            parent: Parent window
            title: Dialog title
            prompt: Password prompt
            show: Character to show instead of actual input
            confirm: Whether to ask for confirmation
            min_length: Minimum password length
        """
        self.prompt = prompt
        self.show = show
        self.confirm = confirm
        self.min_length = min_length
        self.password_var = tk.StringVar()
        self.confirm_var = tk.StringVar()
        super().__init__(parent, title)

    def body(self, master):
        """Create dialog body with password entry."""
        super().body(master)

        ttk.Label(master, text=self.prompt, style="Title.TLabel").grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))

        ttk.Label(master, text="Password:", style="Modern.TLabel").grid(row=1, column=0, sticky=tk.W, pady=5)
        password_entry = ttk.Entry(master, textvariable=self.password_var, show=self.show, width=30)
        password_entry.grid(row=1, column=1, sticky=tk.W, pady=5)

        if self.confirm:
            ttk.Label(master, text="Confirm:", style="Modern.TLabel").grid(row=2, column=0, sticky=tk.W, pady=5)
            confirm_entry = ttk.Entry(master, textvariable=self.confirm_var, show=self.show, width=30)
            confirm_entry.grid(row=2, column=1, sticky=tk.W, pady=5)

        if self.min_length > 0:
            hint = f"Minimum {self.min_length} characters"
            ttk.Label(master, text=hint, foreground="#666666", style="Modern.TLabel").grid(
                row=3, column=1, sticky=tk.W, pady=(0, 10))

        return password_entry  # Initial focus

    def validate(self):
        """Validate password input."""
        password = self.password_var.get()

        if not password:
            messagebox.showerror("Error", "Password cannot be empty", parent=self)
            return False

        if self.min_length > 0 and len(password) < self.min_length:
            messagebox.showerror("Error", f"Password must be at least {self.min_length} characters", parent=self)
            return False

        if self.confirm and password != self.confirm_var.get():
            messagebox.showerror("Error", "Passwords do not match", parent=self)
            return False

        return True

    def apply(self):
        """Apply dialog result."""
        self.result = self.password_var.get()

class PostLoginDelayDialog(ModernDialog):
    """Dialog for setting post-login delay."""

    def __init__(self, parent, current_value):
        self.delay_var = tk.StringVar(value=str(current_value))
        super().__init__(parent, "Set Post-Login Delay (seconds)")

    def body(self, master):
        super().body(master)
        ttk.Label(master, text="Post-Login Delay (seconds):", style="Modern.TLabel").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        entry = ttk.Entry(master, textvariable=self.delay_var, width=10)
        entry.grid(row=0, column=1, sticky=tk.W, pady=(0, 5))
        help_label = ttk.Label(
            master,
            text="How long to keep the browser open after a successful login.\n"
                 "Set to 0 to close immediately. Default is 5 seconds.",
            style="Modern.TLabel",
            foreground="#666666"
        )
        help_label.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        entry.focus_set()
        return entry

    def validate(self):
        val = self.delay_var.get()
        try:
            fval = float(val)
            if fval < 0:
                raise ValueError
        except Exception:
            messagebox.showerror("Invalid Value", "Please enter a non-negative number of seconds.", parent=self)
            return False
        return True

    def apply(self):
        self.result = float(self.delay_var.get())
class LoginStrategyDialog(ModernDialog):
    """
    Dialog to select login strategy: Autopilot (automated login) or Manual Browser (Google login).
    Sets self.result to "autopilot" or "manual_browser" based on user selection.
    """

    def __init__(self, parent, title="Select Login Strategy"):
        self.strategy_var = tk.StringVar(value="autopilot")
        super().__init__(parent, title)

    def body(self, master):
        super().body(master)
        ttk.Label(
            master,
            text="Choose how you want to log in to your account:",
            style="Title.TLabel"
        ).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))

        # Autopilot option
        autopilot_rb = ttk.Radiobutton(
            master,
            text="Autopilot (automated login)",
            variable=self.strategy_var,
            value="autopilot",
            style="Modern.TRadiobutton"
        )
        autopilot_rb.grid(row=1, column=0, sticky=tk.W, pady=2, padx=(0, 10))
        ttk.Label(
            master,
            text="Let the app log in for you automatically (recommended for most sites).",
            style="Modern.TLabel"
        ).grid(row=2, column=0, columnspan=2, sticky=tk.W, padx=(30, 0))

        # Manual Browser option
        manual_rb = ttk.Radiobutton(
            master,
            text="Manual Browser (Google login)",
            variable=self.strategy_var,
            value="manual_browser",
            style="Modern.TRadiobutton"
        )
        manual_rb.grid(row=3, column=0, sticky=tk.W, pady=(10, 2), padx=(0, 10))
        ttk.Label(
            master,
            text="Open a browser for you to log in manually (required for Google and some protected accounts).",
            style="Modern.TLabel"
        ).grid(row=4, column=0, columnspan=2, sticky=tk.W, padx=(30, 0))

        return autopilot_rb  # Initial focus

    def apply(self):
        self.result = self.strategy_var.get()