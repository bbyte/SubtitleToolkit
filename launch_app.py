#!/usr/bin/env python3
"""
Launch script for SubtitleToolkit Desktop Application
This script properly sets up the Python path and launches the application.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path so we can import app modules
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set environment variable to indicate we're running from the project root
os.environ['SUBTITLE_TOOLKIT_PROJECT_ROOT'] = str(project_root)

# Now import and run the app
if __name__ == "__main__":
    from app.main import main
    main()