#!/usr/bin/env python3
"""
Compile translation files for SubtitleToolkit.

This script compiles .ts files to .qm files for use by the application.
"""

import os
import sys
import subprocess
from pathlib import Path


def find_lrelease():
    """Find the lrelease executable."""
    possible_names = ['lrelease', 'lrelease-qt6', 'pyside6-lrelease']
    
    for name in possible_names:
        try:
            result = subprocess.run([name, '-version'], 
                                  capture_output=True, text=True, check=True)
            print(f"Found lrelease: {name}")
            return name
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    
    return None


def compile_translation_file(ts_file: Path, lrelease_cmd: str) -> bool:
    """
    Compile a single .ts file to .qm format.
    
    Args:
        ts_file: Path to the .ts file
        lrelease_cmd: Command to run lrelease
        
    Returns:
        bool: True if compilation succeeded
    """
    qm_file = ts_file.with_suffix('.qm')
    
    try:
        cmd = [lrelease_cmd, str(ts_file), '-qm', str(qm_file)]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        if qm_file.exists():
            print(f"✓ Compiled: {ts_file.name} -> {qm_file.name}")
            return True
        else:
            print(f"✗ Failed to create: {qm_file.name}")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"✗ Error compiling {ts_file.name}: {e.stderr}")
        return False


def main():
    """Main function."""
    print("SubtitleToolkit Translation Compiler")
    print("=" * 40)
    
    # Find lrelease
    lrelease_cmd = find_lrelease()
    if not lrelease_cmd:
        print("Error: Could not find lrelease command.")
        print("Please install Qt6 development tools or PySide6-Essentials:")
        print("  pip install PySide6-Essentials")
        print("  # or install Qt6 development packages for your system")
        return 1
    
    # Find translation files
    translations_dir = Path(__file__).parent / "app" / "i18n" / "translations"
    ts_files = list(translations_dir.glob("*.ts"))
    
    if not ts_files:
        print(f"No .ts files found in {translations_dir}")
        return 1
    
    print(f"Found {len(ts_files)} translation files:")
    for ts_file in ts_files:
        print(f"  - {ts_file.name}")
    print()
    
    # Compile each file
    success_count = 0
    for ts_file in ts_files:
        if compile_translation_file(ts_file, lrelease_cmd):
            success_count += 1
    
    # Summary
    print()
    print(f"Compilation complete: {success_count}/{len(ts_files)} files succeeded")
    
    if success_count == len(ts_files):
        print("All translations compiled successfully!")
        return 0
    else:
        print("Some translations failed to compile.")
        return 1


if __name__ == "__main__":
    sys.exit(main())