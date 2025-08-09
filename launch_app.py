#!/usr/bin/env python3
"""
Launch script for SubtitleToolkit Desktop Application
This script properly sets up the Python path and launches the application.
"""

import sys
import os
from pathlib import Path

# Add the app directory to Python path
app_dir = Path(__file__).parent / 'app'
sys.path.insert(0, str(app_dir))

# Set environment variable to indicate we're running from the project root
os.environ['SUBTITLE_TOOLKIT_PROJECT_ROOT'] = str(Path(__file__).parent)

# Now import and run the app
if __name__ == "__main__":
    from main import main
    main()