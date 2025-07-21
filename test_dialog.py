#!/usr/bin/env python3

"""
Test script to verify the JIRA Configuration dialog layout.
"""

import tkinter as tk
from tkinter import ttk
from config_manager import CredentialsDialog, ConfigManager

def test_dialog():
    """Test the configuration dialog"""
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    
    # Create config manager
    config_manager = ConfigManager()
    
    # Create and show dialog
    dialog = CredentialsDialog(root, config_manager)
    result = dialog.show()
    
    if result:
        print("Configuration saved successfully!")
        print(f"URL: {result['url']}")
        print(f"Email: {result['email']}")
        print(f"API Token: {'*' * len(result['api_token'])}")
    else:
        print("Configuration cancelled")
    
    root.destroy()

if __name__ == "__main__":
    test_dialog() 