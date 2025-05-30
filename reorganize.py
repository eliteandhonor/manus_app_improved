"""
Utility script for moving debug and validation scripts to a dedicated tools directory.
"""

import os
import shutil
import sys
from pathlib import Path

# Create tools directory if it doesn't exist
tools_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools")
os.makedirs(tools_dir, exist_ok=True)

# Create __init__.py in tools directory
with open(os.path.join(tools_dir, "__init__.py"), "w") as f:
    f.write('"""Tools and utilities for the Automated Login Application."""\n')

# Files to move to tools directory
files_to_move = [
    "debug_credential_manager.py",
    "security_validation.py"
]

# Move files
for file in files_to_move:
    src = os.path.join(os.path.dirname(os.path.abspath(__file__)), file)
    dst = os.path.join(tools_dir, file)
    
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"Moved {file} to tools directory")
    else:
        print(f"File {file} not found")

print("Reorganization complete")
