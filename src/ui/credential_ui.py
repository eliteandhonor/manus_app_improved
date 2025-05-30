"""
Credential Dialog for the Automated Login Application.
Provides UI for adding and editing website credentials.
"""

import tkinter as tk
from tkinter import ttk

from .dialogs import ModernDialog
import tkinter as tk
from tkinter import ttk, messagebox

class CredentialDialog(ModernDialog):
    """Modern styled dialog for adding or editing website credentials with accessibility and tooltips."""

    def __init__(self, parent, title, url="", username="", password="", has_bonus=False, notes="", google_login=False):
        self._init_args = (url, username, password, has_bonus, notes, google_login)
        super().__init__(parent, title)

    def body(self, master):
        url, username, password, has_bonus, notes, google_login = self._init_args
        super().body(master)
        # URL field
        ttk.Label(master, text="Website URL:", style="Modern.TLabel").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.url_var = tk.StringVar(value=url)
        url_entry = ttk.Entry(master, textvariable=self.url_var, width=40)
        url_entry.grid(row=0, column=1, sticky=tk.W+tk.E, pady=5)
        url_entry.focus_set()
        # Tooltip/help
        url_help = ttk.Label(master, text="Enter the full website address (e.g., https://example.com)", style="Modern.TLabel", foreground="#666666")
        url_help.grid(row=1, column=1, sticky=tk.W, pady=(0, 5))

        # Username field
        ttk.Label(master, text="Username:", style="Modern.TLabel").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.username_var = tk.StringVar(value=username)
        username_entry = ttk.Entry(master, textvariable=self.username_var, width=40)
        username_entry.grid(row=2, column=1, sticky=tk.W+tk.E, pady=5)
        username_help = ttk.Label(master, text="Your login username or email for this site.", style="Modern.TLabel", foreground="#666666")
        username_help.grid(row=3, column=1, sticky=tk.W, pady=(0, 5))

        # Password field
        ttk.Label(master, text="Password:", style="Modern.TLabel").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.password_var = tk.StringVar(value=password)
        password_frame = ttk.Frame(master)
        password_frame.grid(row=4, column=1, sticky=tk.W+tk.E, pady=5)
        self.password_entry = ttk.Entry(password_frame, textvariable=self.password_var, width=38, show="*")
        self.password_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.show_password = tk.BooleanVar(value=False)
        self.show_button = ttk.Button(password_frame, text="👁", width=2, command=self._toggle_password_visibility)
        self.show_button.pack(side=tk.RIGHT)
        password_help = ttk.Label(master, text="Your login password. Click 👁 to show/hide.", style="Modern.TLabel", foreground="#666666")
        password_help.grid(row=5, column=1, sticky=tk.W, pady=(0, 5))

        # Has bonus checkbox
        self.has_bonus_var = tk.BooleanVar(value=has_bonus)
        ttk.Checkbutton(
            master,
            text="This site offers free credit or trial bonus",
            variable=self.has_bonus_var,
            style="Modern.TCheckbutton"
        ).grid(row=6, column=0, columnspan=2, sticky=tk.W, pady=10)

        # Google login checkbox
        self.google_login_var = tk.BooleanVar(value=google_login)
        ttk.Checkbutton(
            master,
            text="This site uses Google login (manual system browser required)",
            variable=self.google_login_var,
            style="Modern.TCheckbutton"
        ).grid(row=7, column=0, columnspan=2, sticky=tk.W, pady=2)

        # Notes field
        ttk.Label(master, text="Notes:", style="Modern.TLabel").grid(row=8, column=0, sticky=tk.W+tk.N, pady=5)
        notes_frame = ttk.Frame(master)
        notes_frame.grid(row=8, column=1, sticky=tk.W+tk.E, pady=5)
        self.notes_text = tk.Text(notes_frame, width=38, height=5)
        self.notes_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.notes_text.insert(tk.END, notes)
        notes_help = ttk.Label(master, text="Optional: Add notes or hints for this login.", style="Modern.TLabel", foreground="#666666")
        notes_help.grid(row=9, column=1, sticky=tk.W, pady=(0, 5))
        notes_scrollbar = ttk.Scrollbar(notes_frame, orient=tk.VERTICAL, command=self.notes_text.yview)
        notes_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.notes_text.configure(yscrollcommand=notes_scrollbar.set)

        # Keyboard accessibility: Enter=Save, Esc=Cancel
        self.bind("<Return>", lambda e: self.ok())
        self.bind("<Escape>", lambda e: self.cancel())

        return url_entry  # Initial focus

    def _toggle_password_visibility(self):
        """Toggle password visibility."""
        if self.password_entry["show"] == "*":
            self.password_entry["show"] = ""
        else:
            self.password_entry["show"] = "*"

    def validate(self):
        """Validate required fields before accepting dialog."""
        url = self.url_var.get().strip()
        username = self.username_var.get().strip()
        password = self.password_var.get()
        if not url:
            messagebox.showerror("Error", "Website URL is required", parent=self)
            return False
        if not username:
            messagebox.showerror("Error", "Username is required", parent=self)
            return False
        if not password:
            messagebox.showerror("Error", "Password is required", parent=self)
            return False
        return True

    def apply(self):
        """Set result tuple when dialog is accepted."""
        url = self.url_var.get().strip()
        username = self.username_var.get().strip()
        password = self.password_var.get()
        has_bonus = self.has_bonus_var.get()
        google_login = self.google_login_var.get()
        notes = self.notes_text.get("1.0", tk.END).strip()
        self.result = (url, username, password, has_bonus, notes, google_login)
