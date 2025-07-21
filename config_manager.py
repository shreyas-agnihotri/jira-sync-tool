#!/usr/bin/env python3

# Import compatibility fix for Python 3.13
import compatibility_fix

import json
import os
import keyring
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Dict
import threading

class ConfigManager:
    """Manages JIRA configuration and credentials"""
    
    def __init__(self):
        self.config_file = "jira_config.json"
        self.service_name = "jira_date_sync_tool"
        self.username_key = "jira_username"
        self.api_token_key = "jira_api_token"
        self.url_key = "jira_url"
        
    def get_config(self) -> Dict[str, str]:
        """Get current configuration"""
        config = {
            'url': 'https://your-jira-instance.atlassian.net',
            'email': '',
            'api_token': ''
        }
        
        # Try to load from file first
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    file_config = json.load(f)
                    config.update(file_config)
            except Exception:
                pass
        
        # Try to get credentials from keychain
        try:
            username = keyring.get_password(self.service_name, self.username_key)
            api_token = keyring.get_password(self.service_name, self.api_token_key)
            url = keyring.get_password(self.service_name, self.url_key)
            
            if username:
                config['email'] = username
            if api_token:
                config['api_token'] = api_token
            if url:
                config['url'] = url
        except Exception:
            # Keyring might not be available, continue with file config
            pass
        
        return config
    
    def save_config(self, url: str, email: str, api_token: str):
        """Save configuration to file and keychain"""
        config = {
            'url': url,
            'email': email,
            'api_token': api_token
        }
        
        # Save to file (without sensitive data)
        file_config = {'url': url}
        try:
            with open(self.config_file, 'w') as f:
                json.dump(file_config, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save config file: {e}")
        
        # Save sensitive data to keychain
        try:
            keyring.set_password(self.service_name, self.username_key, email)
            keyring.set_password(self.service_name, self.api_token_key, api_token)
            keyring.set_password(self.service_name, self.url_key, url)
        except Exception as e:
            print(f"Warning: Could not save to keychain: {e}")
    
    def clear_credentials(self):
        """Clear stored credentials"""
        try:
            keyring.delete_password(self.service_name, self.username_key)
            keyring.delete_password(self.service_name, self.api_token_key)
            keyring.delete_password(self.service_name, self.url_key)
        except Exception:
            pass
        
        # Remove config file
        if os.path.exists(self.config_file):
            try:
                os.remove(self.config_file)
            except Exception:
                pass

class CredentialsDialog:
    """Dialog for entering JIRA credentials"""
    
    def __init__(self, parent, config_manager: ConfigManager):
        self.parent = parent
        self.config_manager = config_manager
        self.result = None
        
        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("JIRA Configuration")
        self.dialog.geometry("500x600")  # Increased height even more to ensure buttons are visible
        self.dialog.resizable(False, False)
        self.dialog.minsize(500, 600)  # Set minimum size to ensure buttons are visible
        
        # Force the dialog to update its geometry
        self.dialog.update_idletasks()
        
        # Make dialog modal
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        self.create_widgets()
        self.load_existing_config()
    
    def create_widgets(self):
        """Create dialog widgets with simple pack layout"""
        # Title
        title_label = ttk.Label(self.dialog, text="JIRA Configuration", 
                               font=('SF Pro Display', 16, 'bold'))
        title_label.pack(pady=(20, 10), padx=20)
        
        # Form frame
        form_frame = ttk.Frame(self.dialog, padding="20")
        form_frame.pack(fill=tk.BOTH, expand=True, padx=20)
        
        # JIRA URL
        ttk.Label(form_frame, text="JIRA URL:", font=('SF Pro Display', 10, 'bold')).pack(anchor=tk.W, pady=(0, 5))
        self.url_entry = ttk.Entry(form_frame, width=50)
        self.url_entry.pack(fill=tk.X, pady=(0, 15))
        
        # Email
        ttk.Label(form_frame, text="Email:", font=('SF Pro Display', 10, 'bold')).pack(anchor=tk.W, pady=(0, 5))
        self.email_entry = ttk.Entry(form_frame, width=50)
        self.email_entry.pack(fill=tk.X, pady=(0, 15))
        
        # API Token
        ttk.Label(form_frame, text="API Token:", font=('SF Pro Display', 10, 'bold')).pack(anchor=tk.W, pady=(0, 5))
        self.api_token_entry = ttk.Entry(form_frame, width=50, show="*")
        self.api_token_entry.pack(fill=tk.X, pady=(0, 15))
        
        # Show/Hide password button
        self.show_password_var = tk.BooleanVar()
        show_password_btn = ttk.Checkbutton(form_frame, text="Show API Token", 
                                           variable=self.show_password_var,
                                           command=self.toggle_password_visibility)
        show_password_btn.pack(anchor=tk.W, pady=(0, 20))
        
        # Status label
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(form_frame, textvariable=self.status_var, 
                                     font=('SF Pro Display', 9))
        self.status_label.pack(anchor=tk.W, pady=(10, 0))
        
        # Buttons frame - simple pack layout
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=20)
        
        # Left side buttons
        left_frame = ttk.Frame(button_frame)
        left_frame.pack(side=tk.LEFT)
        
        test_btn = ttk.Button(left_frame, text="🔍 Test Connection", 
                              command=self.test_connection)
        test_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        clear_btn = ttk.Button(left_frame, text="🗑️ Clear Credentials", 
                               command=self.clear_credentials)
        clear_btn.pack(side=tk.LEFT)
        
        # Right side buttons
        right_frame = ttk.Frame(button_frame)
        right_frame.pack(side=tk.RIGHT)
        
        save_btn = ttk.Button(right_frame, text="💾 Save", 
                              command=self.save_config)
        save_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        cancel_btn = ttk.Button(right_frame, text="❌ Cancel", 
                                command=self.cancel)
        cancel_btn.pack(side=tk.RIGHT)
        
        # Store reference to test button for later use
        self.test_btn = test_btn
        
        # Bind Enter key to save
        self.dialog.bind('<Return>', lambda e: self.save_config())
        self.dialog.bind('<Escape>', lambda e: self.cancel())
    
    def load_existing_config(self):
        """Load existing configuration"""
        config = self.config_manager.get_config()
        self.url_entry.insert(0, config.get('url', ''))
        self.email_entry.insert(0, config.get('email', ''))
        self.api_token_entry.insert(0, config.get('api_token', ''))
    
    def toggle_password_visibility(self):
        """Toggle API token visibility"""
        if self.show_password_var.get():
            self.api_token_entry.config(show="")
        else:
            self.api_token_entry.config(show="*")
    
    def test_connection(self):
        """Test JIRA connection"""
        url = self.url_entry.get().strip()
        email = self.email_entry.get().strip()
        api_token = self.api_token_entry.get().strip()
        
        if not url or not email or not api_token:
            self.status_var.set("Please fill in all fields")
            return
        
        # Validate URL format
        if not url.startswith(('http://', 'https://')):
            self.status_var.set("✗ JIRA URL must start with http:// or https://")
            return
        
        # Validate email format
        if '@' not in email:
            self.status_var.set("✗ Please enter a valid email address")
            return
        
        self.status_var.set("Testing connection...")
        self.test_btn.config(text="Testing...", state="disabled")
        self.dialog.update()
        
        # Set a timeout to re-enable the button after 30 seconds
        self.dialog.after(30000, lambda: self.test_btn.config(text="🔍 Test Connection", state="normal") if self.test_btn.winfo_exists() else None)
        
        # Run connection test in background thread
        def run_test():
            try:
                from jira import JIRA
                import requests
                
                # Suppress SSL warnings for self-signed certificates
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                
                # Create JIRA client with timeout, API v3, and SSL verification disabled for self-signed certs
                jira = JIRA(server=url, basic_auth=(email, api_token), 
                           options={'timeout': 10, 'rest_api_version': '3', 'verify': False})  # 10 second timeout, API v3, no SSL verify
                
                # Try to get current user
                myself = jira.myself()
                
                # Test a simple search to verify permissions
                try:
                    # Try to search for issues (this tests read permissions)
                    jira.search_issues('project IS NOT EMPTY', maxResults=1)
                    # Schedule UI update in main thread
                    self.dialog.after(0, lambda: self.status_var.set(f"✓ Connected successfully as {myself['displayName']} (API v3, with read permissions)"))
                except Exception as search_error:
                    # Schedule UI update in main thread
                    self.dialog.after(0, lambda: self.status_var.set(f"⚠ Connected as {myself['displayName']} (API v3) but limited permissions: {str(search_error)}"))
                
            except Exception as e:
                error_msg = str(e)
                if "401" in error_msg or "unauthorized" in error_msg.lower():
                    # Schedule UI update in main thread
                    self.dialog.after(0, lambda: self.status_var.set("✗ Authentication failed - check email and API token"))
                elif "404" in error_msg or "not found" in error_msg.lower():
                    # Schedule UI update in main thread
                    self.dialog.after(0, lambda: self.status_var.set("✗ JIRA URL not found - check the URL"))
                elif "timeout" in error_msg.lower():
                    # Schedule UI update in main thread
                    self.dialog.after(0, lambda: self.status_var.set("✗ Connection timeout - check your internet connection"))
                else:
                    # Schedule UI update in main thread
                    self.dialog.after(0, lambda: self.status_var.set(f"✗ Connection failed: {error_msg}"))
            finally:
                # Schedule button re-enable in main thread
                self.dialog.after(0, lambda: self.test_btn.config(text="🔍 Test Connection", state="normal"))
        
        # Start the test in a background thread
        threading.Thread(target=run_test, daemon=True).start()
    
    def clear_credentials(self):
        """Clear stored credentials"""
        if messagebox.askyesno("Clear Credentials", 
                              "Are you sure you want to clear all stored credentials?"):
            self.config_manager.clear_credentials()
            self.url_entry.delete(0, tk.END)
            self.email_entry.delete(0, tk.END)
            self.api_token_entry.delete(0, tk.END)
            self.status_var.set("Credentials cleared")
    
    def save_config(self):
        """Save configuration"""
        url = self.url_entry.get().strip()
        email = self.email_entry.get().strip()
        api_token = self.api_token_entry.get().strip()
        
        if not url or not email or not api_token:
            messagebox.showerror("Error", "Please fill in all fields")
            return
        
        # Validate URL format
        if not url.startswith(('http://', 'https://')):
            messagebox.showerror("Error", "JIRA URL must start with http:// or https://")
            return
        
        # Validate email format
        if '@' not in email:
            messagebox.showerror("Error", "Please enter a valid email address")
            return
        
        try:
            self.config_manager.save_config(url, email, api_token)
            self.result = {
                'url': url,
                'email': email,
                'api_token': api_token
            }
            self.dialog.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {str(e)}")
    
    def cancel(self):
        """Cancel configuration"""
        self.dialog.destroy()
    
    def show(self):
        """Show dialog and return result"""
        self.dialog.wait_window()
        return self.result 