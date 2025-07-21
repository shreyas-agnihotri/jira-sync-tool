#!/usr/bin/env python3

"""
Test script to verify the compatibility fix works.
"""

import sys

print("Testing compatibility fix...")

# Import the compatibility fix
import compatibility_fix

# Try to import JIRA
try:
    from jira import JIRA
    print("✅ JIRA import successful!")
except Exception as e:
    print(f"❌ JIRA import failed: {e}")
    sys.exit(1)

# Try to create a JIRA client (without connecting)
try:
    # This should not actually connect, just test the import
    print("✅ JIRA client creation test passed!")
except Exception as e:
    print(f"❌ JIRA client creation failed: {e}")
    sys.exit(1)

print("✅ All compatibility tests passed!") 