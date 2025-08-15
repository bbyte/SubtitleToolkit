#!/usr/bin/env python3
"""
Test script for MKV Language Detection functionality.

This script tests the MKVLanguageDetector utility to ensure it works correctly
with the existing project structure and ffprobe dependency.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path so we can import app modules
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set environment variable to indicate we're running from the project root
os.environ['SUBTITLE_TOOLKIT_PROJECT_ROOT'] = str(project_root)

from app.utils.mkv_language_detector import MKVLanguageDetector, LanguageDetectionResult


def test_language_mapping():
    """Test the language code to display name mapping."""
    print("=== Testing Language Code Mapping ===")
    
    test_codes = ['eng', 'en', 'spa', 'es', 'fra', 'fr', 'deu', 'de', 'ger', 'unknown']
    
    for code in test_codes:
        display_name = MKVLanguageDetector.get_language_display_name(code)
        print(f"  {code:8} -> {display_name}")
    
    print()


def test_directory_detection(test_dir: str):
    """Test language detection on a directory."""
    print(f"=== Testing Directory: {test_dir} ===")
    
    if not Path(test_dir).exists():
        print(f"Directory does not exist: {test_dir}")
        print("Please provide a valid directory containing MKV files for testing.\n")
        return
    
    try:
        result = MKVLanguageDetector.detect_languages_in_path(test_dir)
        
        print(f"Total files analyzed: {result.total_files}")
        print(f"Files with subtitles: {result.files_with_subtitles}")
        
        if result.errors:
            print("Errors encountered:")
            for error in result.errors:
                print(f"  - {error}")
        
        if result.available_languages:
            print("Available languages:")
            for code, name in result.available_languages:
                print(f"  {code:8} -> {name}")
        else:
            print("No subtitle languages found.")
        
        print("\nFile-by-file analysis:")
        for file_result in result.file_results:
            print(f"  {file_result.file_path.name}:")
            if file_result.error:
                print(f"    ERROR: {file_result.error}")
            elif file_result.has_subtitles:
                print(f"    Found {len(file_result.subtitle_tracks)} subtitle track(s):")
                for track in file_result.subtitle_tracks:
                    flags = []
                    if track.forced:
                        flags.append("forced")
                    if track.default:
                        flags.append("default")
                    flag_str = f" ({', '.join(flags)})" if flags else ""
                    
                    title_str = f" - {track.title}" if track.title else ""
                    print(f"      Track {track.index}: {track.language_code} ({track.language_name}){title_str}{flag_str}")
            else:
                print(f"    No subtitle tracks found")
        
    except Exception as e:
        print(f"Error during directory detection: {e}")
    
    print()


def test_file_detection(test_file: str):
    """Test language detection on a single file."""
    print(f"=== Testing File: {test_file} ===")
    
    if not Path(test_file).exists():
        print(f"File does not exist: {test_file}")
        print("Please provide a valid MKV file for testing.\n")
        return
    
    try:
        result = MKVLanguageDetector.detect_languages_in_path(test_file)
        
        print(f"Total files analyzed: {result.total_files}")
        print(f"Files with subtitles: {result.files_with_subtitles}")
        
        if result.errors:
            print("Errors encountered:")
            for error in result.errors:
                print(f"  - {error}")
        
        if result.available_languages:
            print("Available languages:")
            for code, name in result.available_languages:
                print(f"  {code:8} -> {name}")
        else:
            print("No subtitle languages found.")
        
        if result.file_results:
            file_result = result.file_results[0]
            if file_result.has_subtitles:
                print(f"\nSubtitle tracks in {file_result.file_path.name}:")
                for track in file_result.subtitle_tracks:
                    flags = []
                    if track.forced:
                        flags.append("forced")
                    if track.default:
                        flags.append("default")
                    flag_str = f" ({', '.join(flags)})" if flags else ""
                    
                    title_str = f" - {track.title}" if track.title else ""
                    codec_str = f" [{track.codec}]" if track.codec else ""
                    print(f"  Track {track.index}: {track.language_code} ({track.language_name}){title_str}{codec_str}{flag_str}")
    
    except Exception as e:
        print(f"Error during file detection: {e}")
    
    print()


def main():
    """Main test function."""
    print("SubtitleToolkit - MKV Language Detection Test")
    print("=" * 50)
    print()
    
    # Test language mapping
    test_language_mapping()
    
    # Test with command line arguments if provided
    if len(sys.argv) > 1:
        test_path = sys.argv[1]
        path_obj = Path(test_path)
        
        if path_obj.is_file() and path_obj.suffix.lower() == '.mkv':
            test_file_detection(test_path)
        elif path_obj.is_dir():
            test_directory_detection(test_path)
        else:
            print(f"Invalid path or not an MKV file/directory: {test_path}")
    else:
        print("Usage: python3 test_language_detection.py <path_to_mkv_file_or_directory>")
        print()
        print("Example:")
        print("  python3 test_language_detection.py /path/to/movie.mkv")
        print("  python3 test_language_detection.py /path/to/movies/")
    
    print("Test completed.")


if __name__ == "__main__":
    main()