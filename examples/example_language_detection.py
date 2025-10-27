#!/usr/bin/env python3
"""
Example usage of MKV Language Detection in SubtitleToolkit

This script demonstrates how to use the MKVLanguageDetector utility 
to detect available subtitle languages in MKV files.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
os.environ['SUBTITLE_TOOLKIT_PROJECT_ROOT'] = str(project_root)

from app.utils.mkv_language_detector import MKVLanguageDetector


def example_usage():
    """Demonstrate basic usage of the language detector."""
    
    print("SubtitleToolkit - MKV Language Detection Example")
    print("=" * 50)
    
    # Example 1: Check available language mappings
    print("\n1. Language Code Examples:")
    example_codes = ['eng', 'es', 'fr', 'de', 'ja', 'zh', 'ar']
    for code in example_codes:
        display_name = MKVLanguageDetector.get_language_display_name(code)
        print(f"   {code} -> {display_name}")
    
    # Example 2: Detect languages in a hypothetical file
    print("\n2. File Detection Example:")
    print("   To detect languages in an MKV file:")
    print("   ```python")
    print("   result = MKVLanguageDetector.detect_languages_in_path('/path/to/movie.mkv')")
    print("   ")
    print("   if result.available_languages:")
    print("       for code, name in result.available_languages:")
    print("           print(f'Found: {code} ({name})')")
    print("   ```")
    
    # Example 3: Detect languages in a directory
    print("\n3. Directory Detection Example:")
    print("   To detect languages across all MKV files in a directory:")
    print("   ```python")
    print("   result = MKVLanguageDetector.detect_languages_in_path('/path/to/movies/')")
    print("   ")
    print("   print(f'Analyzed {result.total_files} files')")
    print("   print(f'{result.files_with_subtitles} have subtitles')")
    print("   ")
    print("   for code, name in result.available_languages:")
    print("       print(f'Available: {code} ({name})')")
    print("   ```")
    
    # Example 4: Integration with UI
    print("\n4. UI Integration Example:")
    print("   The ProjectSelector widget now automatically detects languages:")
    print("   ```python")
    print("   project_selector = ProjectSelector()")
    print("   project_selector.languages_detected.connect(on_languages_detected)")
    print("   ")
    print("   def on_languages_detected(result):")
    print("       languages = result.available_languages")
    print("       # Update UI with detected languages")
    print("   ```")
    
    print("\n" + "=" * 50)
    print("For real testing, run:")
    print("python3 test_language_detection.py /path/to/mkv/file/or/directory")


if __name__ == "__main__":
    example_usage()