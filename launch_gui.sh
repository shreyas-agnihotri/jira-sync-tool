#!/bin/bash

# JIRA Date Sync Tool GUI Launcher
# This script launches the GUI application with proper Python environment

echo "🚀 Launching JIRA Date Sync Tool GUI..."

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.7 or higher."
    exit 1
fi

# Check if required packages are installed
if ! python3 -c "import jira" 2>/dev/null; then
    echo "⚠️  JIRA package not found. Installing dependencies..."
    pip3 install -r requirements.txt
fi

# Launch the GUI
echo "✅ Starting GUI application..."
python3 jira_ui.py

echo "👋 GUI application closed." 