#!/usr/bin/env python3

"""
Compatibility fix for Python 3.13 where imghdr module was removed.
This provides a minimal implementation to satisfy the JIRA library.
"""

import sys

# Check if imghdr module is missing (Python 3.13+)
if 'imghdr' not in sys.modules:
    # Create a minimal imghdr module
    class ImghdrModule:
        """Minimal imghdr module replacement"""
        
        def what(self, file, h=None):
            """Return the type of image contained in a file or byte stream."""
            # Return None for all cases since we don't need actual image detection
            return None
    
    # Create the module
    imghdr = ImghdrModule()
    
    # Add it to sys.modules so imports work
    sys.modules['imghdr'] = imghdr 