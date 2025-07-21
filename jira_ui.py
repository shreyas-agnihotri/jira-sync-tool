#!/usr/bin/env python3

# Import compatibility fix for Python 3.13
import compatibility_fix

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import queue
import sys
import os
from datetime import datetime
import json

# Import the existing JIRA functionality
from jira_clone import (
    DateFieldCloner, JiraClient, FieldMapper, DateFieldProcessor,
    print_header, print_section, print_success, print_warning, print_error, print_info,
    set_output_queue, set_jira_config
)
from config_manager import ConfigManager, CredentialsDialog

class JiraSyncUI:
    def __init__(self, root):
        self.root = root
        self.root.title("JIRA Date Sync Tool")
        self.root.geometry("900x700")
        
        # Configure style for modern look
        self.setup_styles()
        
        # Initialize configuration manager
        self.config_manager = ConfigManager()
        
        # Initialize JIRA client
        self.jira_cloner = None
        self.output_queue = queue.Queue()
        
        # Create UI components
        self.create_widgets()
        
        # Start output monitoring
        self.monitor_output()
    
    def setup_styles(self):
        """Configure modern styling"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure colors
        style.configure('Title.TLabel', font=('SF Pro Display', 16, 'bold'))
        style.configure('Header.TLabel', font=('SF Pro Display', 12, 'bold'))
        style.configure('Success.TLabel', foreground='#28a745')
        style.configure('Warning.TLabel', foreground='#ffc107')
        style.configure('Error.TLabel', foreground='#dc3545')
        
        # Configure buttons - use default styles to avoid visibility issues
        style.configure('Primary.TButton', 
                       font=('SF Pro Display', 10),
                       padding=(10, 5))
        style.configure('Secondary.TButton', 
                       font=('SF Pro Display', 10),
                       padding=(8, 4))
    
    def create_widgets(self):
        """Create the main UI layout"""
        # Configure grid weights for root
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)  # Row 1 for main content
        
        # Main container
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights for main frame
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="JIRA Date Sync Tool", style='Title.TLabel')
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Mode selection
        self.create_mode_selector(main_frame)
        
        # Content area
        self.create_content_area(main_frame)
        
        # Output area
        self.create_output_area(main_frame)
        
        # Status bar
        self.create_status_bar(main_frame)
        
        # Add configuration button to menu bar
        self.create_menu_bar()
        
        # Check credentials after UI is fully set up
        self.check_credentials()
    
    def create_mode_selector(self, parent):
        """Create the mode selection tabs"""
        # Mode frame
        mode_frame = ttk.LabelFrame(parent, text="Operation Mode", padding="10")
        mode_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 20))
        
        # Mode variable
        self.mode_var = tk.StringVar(value="sync")
        
        # Mode buttons
        modes = [
            ("Sync Dates", "sync", "Copy dates between two issues"),
            ("Auto Sync", "auto", "Auto-discover and sync from linked ticket"),
            ("Bulk Sync", "bulk", "Sync all ideas in a project"),
            ("List Fields", "list", "Show fields in an issue"),
            ("Check Links", "links", "Check references between issues")
        ]
        
        for i, (text, value, tooltip) in enumerate(modes):
            btn = ttk.Radiobutton(mode_frame, text=text, variable=self.mode_var, 
                                 value=value, command=self.on_mode_change)
            btn.grid(row=0, column=i, padx=10)
            
            # Add tooltip-like behavior
            btn.bind('<Enter>', lambda e, t=tooltip: self.show_tooltip(e, t))
            btn.bind('<Leave>', lambda e: self.hide_tooltip())
        
        # Tooltip label
        self.tooltip_label = ttk.Label(mode_frame, text="", style='Warning.TLabel')
        self.tooltip_label.grid(row=1, column=0, columnspan=5, pady=(5, 0))
    
    def create_content_area(self, parent):
        """Create the main content area"""
        # Content frame
        self.content_frame = ttk.Frame(parent)
        self.content_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 20))
        
        # Initialize with sync mode
        self.show_sync_mode()
    
    def create_output_area(self, parent):
        """Create the output display area"""
        # Output frame
        output_frame = ttk.LabelFrame(parent, text="Output", padding="10")
        output_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Configure grid weights
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)
        
        # Output text area
        self.output_text = scrolledtext.ScrolledText(
            output_frame, 
            height=15, 
            font=('SF Mono', 10),
            bg='#f8f9fa',
            fg='#212529'
        )
        self.output_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Clear button
        clear_btn = ttk.Button(output_frame, text="Clear Output", 
                              command=self.clear_output, style='Secondary.TButton')
        clear_btn.grid(row=1, column=0, pady=(5, 0), sticky=tk.W)
    
    def create_status_bar(self, parent):
        """Create the status bar"""
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(parent, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E))
    
    def create_menu_bar(self):
        """Create menu bar with configuration options"""
        # Create a simple menu bar frame - use grid to match main window
        menu_frame = ttk.Frame(self.root)
        menu_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=10, pady=5)
        
        # Configure grid weights for menu frame
        menu_frame.columnconfigure(1, weight=1)
        
        # Status indicator (left side)
        self.connection_status = ttk.Label(menu_frame, text="🔴 Not Connected", 
                                         font=('SF Pro Display', 9))
        self.connection_status.grid(row=0, column=0, sticky=tk.W)
        
        # Configuration button (right side)
        config_btn = ttk.Button(menu_frame, text="⚙️ Configuration", 
                                command=self.show_config_dialog, style='Secondary.TButton')
        config_btn.grid(row=0, column=2, sticky=tk.E)
    
    def check_credentials(self):
        """Check if credentials are configured"""
        config = self.config_manager.get_config()
        
        if not config.get('email') or not config.get('api_token'):
            # No credentials found, show configuration dialog
            self.show_config_dialog()
        else:
            # Credentials found, set them
            set_jira_config(config)
            self.update_connection_status()
    
    def show_config_dialog(self):
        """Show configuration dialog"""
        dialog = CredentialsDialog(self.root, self.config_manager)
        result = dialog.show()
        
        if result:
            # New configuration saved
            set_jira_config(result)
            self.update_connection_status()
            messagebox.showinfo("Configuration", "JIRA configuration updated successfully!")
    
    def update_connection_status(self):
        """Update connection status indicator"""
        config = self.config_manager.get_config()
        if config.get('email') and config.get('api_token'):
            self.connection_status.config(text="🟢 Connected")
        else:
            self.connection_status.config(text="🔴 Not Connected")
    
    def check_credentials_before_execution(self):
        """Check if credentials are configured before executing operations"""
        config = self.config_manager.get_config()
        
        if not config.get('email') or not config.get('api_token'):
            messagebox.showerror("Configuration Required", 
                               "Please configure your JIRA credentials first.\n\nClick the '⚙️ Configuration' button to set up your credentials.")
            return False
        
        # Set the configuration for this execution
        set_jira_config(config)
        return True
    
    def show_tooltip(self, event, text):
        """Show tooltip text"""
        self.tooltip_label.config(text=text)
    
    def hide_tooltip(self):
        """Hide tooltip text"""
        self.tooltip_label.config(text="")
    
    def on_mode_change(self):
        """Handle mode selection change"""
        # Clear current content
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Show appropriate content
        mode = self.mode_var.get()
        if mode == "sync":
            self.show_sync_mode()
        elif mode == "auto":
            self.show_auto_mode()
        elif mode == "bulk":
            self.show_bulk_mode()
        elif mode == "list":
            self.show_list_mode()
        elif mode == "links":
            self.show_links_mode()
    
    def show_sync_mode(self):
        """Show sync mode interface"""
        # Source issue
        ttk.Label(self.content_frame, text="Source Issue Key:", style='Header.TLabel').grid(row=0, column=0, sticky=tk.W, pady=5)
        self.source_entry = ttk.Entry(self.content_frame, width=30)
        self.source_entry.grid(row=0, column=1, padx=(10, 0), pady=5, sticky=tk.W)
        
        # Target issue
        ttk.Label(self.content_frame, text="Target Issue Key:", style='Header.TLabel').grid(row=1, column=0, sticky=tk.W, pady=5)
        self.target_entry = ttk.Entry(self.content_frame, width=30)
        self.target_entry.grid(row=1, column=1, padx=(10, 0), pady=5, sticky=tk.W)
        
        # Options frame
        options_frame = ttk.LabelFrame(self.content_frame, text="Options", padding="10")
        options_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=20)
        
        self.dry_run_var = tk.BooleanVar(value=True)
        self.force_var = tk.BooleanVar(value=False)
        
        ttk.Checkbutton(options_frame, text="Dry Run (Preview Only)", 
                       variable=self.dry_run_var).grid(row=0, column=0, sticky=tk.W)
        ttk.Checkbutton(options_frame, text="Force (Skip Confirmation)", 
                       variable=self.force_var).grid(row=0, column=1, sticky=tk.W, padx=(20, 0))
        
        # Execute button
        execute_btn = ttk.Button(self.content_frame, text="Sync Dates", 
                                command=self.execute_sync, style='Primary.TButton')
        execute_btn.grid(row=3, column=0, columnspan=2, pady=20)
    
    def show_auto_mode(self):
        """Show auto sync mode interface"""
        ttk.Label(self.content_frame, text="JPD Idea Key:", style='Header.TLabel').grid(row=0, column=0, sticky=tk.W, pady=5)
        self.auto_jpd_entry = ttk.Entry(self.content_frame, width=30)
        self.auto_jpd_entry.grid(row=0, column=1, padx=(10, 0), pady=5, sticky=tk.W)
        
        # Options
        options_frame = ttk.LabelFrame(self.content_frame, text="Options", padding="10")
        options_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=20)
        
        self.auto_force_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Force (Skip Confirmation)", 
                       variable=self.auto_force_var).grid(row=0, column=0, sticky=tk.W)
        
        # Execute button
        execute_btn = ttk.Button(self.content_frame, text="Auto Sync", 
                                command=self.execute_auto_sync, style='Primary.TButton')
        execute_btn.grid(row=2, column=0, columnspan=2, pady=20)
    
    def show_bulk_mode(self):
        """Show bulk sync mode interface"""
        ttk.Label(self.content_frame, text="Project Key:", style='Header.TLabel').grid(row=0, column=0, sticky=tk.W, pady=5)
        self.bulk_project_entry = ttk.Entry(self.content_frame, width=30)
        self.bulk_project_entry.grid(row=0, column=1, padx=(10, 0), pady=5, sticky=tk.W)
        
        # Options
        options_frame = ttk.LabelFrame(self.content_frame, text="Options", padding="10")
        options_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=20)
        
        self.bulk_dry_run_var = tk.BooleanVar(value=True)
        self.bulk_force_var = tk.BooleanVar(value=False)
        
        ttk.Checkbutton(options_frame, text="Dry Run (Preview Only)", 
                       variable=self.bulk_dry_run_var).grid(row=0, column=0, sticky=tk.W)
        ttk.Checkbutton(options_frame, text="Force (Skip Confirmation)", 
                       variable=self.bulk_force_var).grid(row=0, column=1, sticky=tk.W, padx=(20, 0))
        
        # Execute button
        execute_btn = ttk.Button(self.content_frame, text="Bulk Sync", 
                                command=self.execute_bulk_sync, style='Primary.TButton')
        execute_btn.grid(row=2, column=0, columnspan=2, pady=20)
    
    def show_list_mode(self):
        """Show list fields mode interface"""
        ttk.Label(self.content_frame, text="Issue Key:", style='Header.TLabel').grid(row=0, column=0, sticky=tk.W, pady=5)
        self.list_issue_entry = ttk.Entry(self.content_frame, width=30)
        self.list_issue_entry.grid(row=0, column=1, padx=(10, 0), pady=5, sticky=tk.W)
        
        # Options
        options_frame = ttk.LabelFrame(self.content_frame, text="Options", padding="10")
        options_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=20)
        
        self.list_all_fields_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Show All Fields (Including Empty)", 
                       variable=self.list_all_fields_var).grid(row=0, column=0, sticky=tk.W)
        
        # Execute button
        execute_btn = ttk.Button(self.content_frame, text="List Fields", 
                                command=self.execute_list_fields, style='Primary.TButton')
        execute_btn.grid(row=2, column=0, columnspan=2, pady=20)
    
    def show_links_mode(self):
        """Show check links mode interface"""
        ttk.Label(self.content_frame, text="Source Issue:", style='Header.TLabel').grid(row=0, column=0, sticky=tk.W, pady=5)
        self.links_source_entry = ttk.Entry(self.content_frame, width=30)
        self.links_source_entry.grid(row=0, column=1, padx=(10, 0), pady=5, sticky=tk.W)
        
        ttk.Label(self.content_frame, text="Target Issue:", style='Header.TLabel').grid(row=1, column=0, sticky=tk.W, pady=5)
        self.links_target_entry = ttk.Entry(self.content_frame, width=30)
        self.links_target_entry.grid(row=1, column=1, padx=(10, 0), pady=5, sticky=tk.W)
        
        # Execute button
        execute_btn = ttk.Button(self.content_frame, text="Check Links", 
                                command=self.execute_check_links, style='Primary.TButton')
        execute_btn.grid(row=2, column=0, columnspan=2, pady=20)
    
    def execute_sync(self):
        """Execute sync operation"""
        # Check credentials first
        if not self.check_credentials_before_execution():
            return
        
        source = self.source_entry.get().strip()
        target = self.target_entry.get().strip()
        
        if not source or not target:
            messagebox.showerror("Error", "Please enter both source and target issue keys")
            return
        
        self.status_var.set("Executing sync...")
        self.clear_output()
        
        def run_sync():
            try:
                # Set output queue for GUI integration
                set_output_queue(self.output_queue)
                
                self.jira_cloner = DateFieldCloner(quiet=False, verbose=True)
                success = self.jira_cloner.clone_fields(
                    source, target, 
                    dry_run=self.dry_run_var.get(), 
                    force=self.force_var.get()
                )
                
                if success:
                    self.status_var.set("Sync completed successfully")
                else:
                    self.status_var.set("Sync failed")
                    
            except Exception as e:
                self.output_queue.put(f"Error: {str(e)}")
                self.status_var.set("Sync failed with error")
        
        threading.Thread(target=run_sync, daemon=True).start()
    
    def execute_auto_sync(self):
        """Execute auto sync operation"""
        # Check credentials first
        if not self.check_credentials_before_execution():
            return
        
        jpd_key = self.auto_jpd_entry.get().strip()
        
        if not jpd_key:
            messagebox.showerror("Error", "Please enter a JPD idea key")
            return
        
        self.status_var.set("Executing auto sync...")
        self.clear_output()
        
        def run_auto_sync():
            try:
                # Set output queue for GUI integration
                set_output_queue(self.output_queue)
                
                self.jira_cloner = DateFieldCloner(quiet=False, verbose=True)
                success = self.jira_cloner.auto_sync_from_jpd(
                    jpd_key, force=self.auto_force_var.get()
                )
                
                if success:
                    self.status_var.set("Auto sync completed successfully")
                else:
                    self.status_var.set("Auto sync failed")
                    
            except Exception as e:
                self.output_queue.put(f"Error: {str(e)}")
                self.status_var.set("Auto sync failed with error")
        
        threading.Thread(target=run_auto_sync, daemon=True).start()
    
    def execute_bulk_sync(self):
        """Execute bulk sync operation"""
        # Check credentials first
        if not self.check_credentials_before_execution():
            return
        
        project = self.bulk_project_entry.get().strip()
        
        if not project:
            messagebox.showerror("Error", "Please enter a project key")
            return
        
        self.status_var.set("Executing bulk sync...")
        self.clear_output()
        
        def run_bulk_sync():
            try:
                # Set output queue for GUI integration
                set_output_queue(self.output_queue)
                
                self.jira_cloner = DateFieldCloner(quiet=False, verbose=True)
                success = self.jira_cloner.bulk_sync_project(
                    project, 
                    dry_run=self.bulk_dry_run_var.get(), 
                    force=self.bulk_force_var.get()
                )
                
                if success:
                    self.status_var.set("Bulk sync completed successfully")
                else:
                    self.status_var.set("Bulk sync failed")
                    
            except Exception as e:
                self.output_queue.put(f"Error: {str(e)}")
                self.status_var.set("Bulk sync failed with error")
        
        threading.Thread(target=run_bulk_sync, daemon=True).start()
    
    def execute_list_fields(self):
        """Execute list fields operation"""
        # Check credentials first
        if not self.check_credentials_before_execution():
            return
        
        issue_key = self.list_issue_entry.get().strip()
        
        if not issue_key:
            messagebox.showerror("Error", "Please enter an issue key")
            return
        
        self.status_var.set("Listing fields...")
        self.clear_output()
        
        def run_list_fields():
            try:
                # Set output queue for GUI integration
                set_output_queue(self.output_queue)
                
                self.jira_cloner = DateFieldCloner(quiet=False, verbose=True)
                success = self.jira_cloner.field_lister.list_fields(
                    issue_key, show_empty=self.list_all_fields_var.get()
                )
                
                if success:
                    self.status_var.set("Fields listed successfully")
                else:
                    self.status_var.set("Failed to list fields")
                    
            except Exception as e:
                self.output_queue.put(f"Error: {str(e)}")
                self.status_var.set("Failed to list fields")
        
        threading.Thread(target=run_list_fields, daemon=True).start()
    
    def execute_check_links(self):
        """Execute check links operation"""
        # Check credentials first
        if not self.check_credentials_before_execution():
            return
        
        source = self.links_source_entry.get().strip()
        target = self.links_target_entry.get().strip()
        
        if not source or not target:
            messagebox.showerror("Error", "Please enter both source and target issue keys")
            return
        
        self.status_var.set("Checking links...")
        self.clear_output()
        
        def run_check_links():
            try:
                # Set output queue for GUI integration
                set_output_queue(self.output_queue)
                
                self.jira_cloner = DateFieldCloner(quiet=False, verbose=True)
                success = self.jira_cloner.check_links(source, target)
                
                if success:
                    self.status_var.set("Links found")
                else:
                    self.status_var.set("No links found")
                    
            except Exception as e:
                self.output_queue.put(f"Error: {str(e)}")
                self.status_var.set("Failed to check links")
        
        threading.Thread(target=run_check_links, daemon=True).start()
    
    def clear_output(self):
        """Clear the output text area"""
        self.output_text.delete(1.0, tk.END)
    
    def monitor_output(self):
        """Monitor output queue and update display"""
        try:
            while True:
                # Check for output from the queue
                try:
                    output = self.output_queue.get_nowait()
                    self.output_text.insert(tk.END, output + "\n")
                    self.output_text.see(tk.END)
                except queue.Empty:
                    break
        except:
            pass
        
        # Schedule next check
        self.root.after(100, self.monitor_output)

def main():
    """Main application entry point"""
    root = tk.Tk()
    app = JiraSyncUI(root)
    
    # Center the window
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
    root.geometry(f"+{x}+{y}")
    
    # Start the application
    root.mainloop()

if __name__ == "__main__":
    main() 