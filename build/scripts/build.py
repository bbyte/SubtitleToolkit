#!/usr/bin/env python3
"""
Universal build script for SubtitleToolkit
Automatically detects platform and runs appropriate build process
"""

import sys
import os
import platform
import subprocess
import argparse
from pathlib import Path


def get_platform():
    """Detect the current platform."""
    system = platform.system().lower()
    if system == 'windows':
        return 'windows'
    elif system == 'darwin':
        return 'macos'
    elif system == 'linux':
        return 'linux'
    else:
        raise ValueError(f"Unsupported platform: {system}")


def run_build(platform_name, clean=False, test=True):
    """Run the build for the specified platform."""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    
    # Change to project root
    os.chdir(project_root)
    
    print(f"Building SubtitleToolkit for {platform_name}...")
    print(f"Project root: {project_root}")
    
    if clean:
        print("Cleaning previous builds...")
        dist_dir = project_root / 'dist'
        build_temp_dir = project_root / 'build' / 'SubtitleToolkit'
        
        if dist_dir.exists():
            import shutil
            shutil.rmtree(dist_dir)
            print(f"Removed {dist_dir}")
        
        if build_temp_dir.exists():
            import shutil
            shutil.rmtree(build_temp_dir)
            print(f"Removed {build_temp_dir}")
    
    # Run platform-specific build script
    if platform_name == 'windows':
        build_script = script_dir / 'build-windows.bat'
        if not build_script.exists():
            raise FileNotFoundError(f"Windows build script not found: {build_script}")
        
        # Run batch file
        result = subprocess.run([str(build_script)], shell=True)
        
    elif platform_name == 'macos':
        build_script = script_dir / 'build-macos.sh'
        if not build_script.exists():
            raise FileNotFoundError(f"macOS build script not found: {build_script}")
        
        # Make script executable and run
        os.chmod(build_script, 0o755)
        result = subprocess.run(['bash', str(build_script)])
        
    elif platform_name == 'linux':
        build_script = script_dir / 'build-linux.sh'
        if not build_script.exists():
            raise FileNotFoundError(f"Linux build script not found: {build_script}")
        
        # Make script executable and run
        os.chmod(build_script, 0o755)
        result = subprocess.run(['bash', str(build_script)])
    
    else:
        raise ValueError(f"Unsupported platform: {platform_name}")
    
    if result.returncode != 0:
        print(f"ERROR: Build failed with exit code {result.returncode}")
        return False
    
    print(f"✓ Build completed successfully for {platform_name}")
    return True


def validate_environment():
    """Validate that the build environment is properly set up."""
    errors = []
    warnings = []
    
    # Check Python version
    python_version = sys.version_info
    if python_version < (3, 8):
        errors.append(f"Python 3.8+ required, found {python_version.major}.{python_version.minor}")
    
    # Check if we're in the right directory
    project_root = Path(__file__).parent.parent.parent
    if not (project_root / 'app' / 'main.py').exists():
        errors.append("Could not find app/main.py - please run from project root")
    
    # Check for requirements.txt
    if not (project_root / 'requirements.txt').exists():
        warnings.append("requirements.txt not found - dependencies may not be installed")
    
    # Check for PyInstaller
    try:
        import PyInstaller
    except ImportError:
        warnings.append("PyInstaller not found - will attempt to install during build")
    
    # Platform-specific checks
    platform_name = get_platform()
    
    if platform_name == 'windows':
        # Check for Windows build tools
        if not subprocess.run(['where', 'python'], capture_output=True, shell=True).returncode == 0:
            errors.append("Python not found in PATH")
    
    elif platform_name == 'macos':
        # Check for Xcode command line tools
        if not subprocess.run(['which', 'gcc'], capture_output=True).returncode == 0:
            warnings.append("Xcode command line tools not found - some features may not work")
    
    elif platform_name == 'linux':
        # Check for build essentials
        if not subprocess.run(['which', 'gcc'], capture_output=True).returncode == 0:
            warnings.append("build-essential not found - may cause issues with native extensions")
    
    # Report results
    if errors:
        print("❌ Environment validation failed:")
        for error in errors:
            print(f"   ERROR: {error}")
        return False
    
    if warnings:
        print("⚠️  Environment validation warnings:")
        for warning in warnings:
            print(f"   WARNING: {warning}")
    
    print("✅ Environment validation passed")
    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Universal build script for SubtitleToolkit',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Build for current platform
  %(prog)s --platform linux   # Build for Linux
  %(prog)s --clean            # Clean build
  %(prog)s --validate-only    # Only validate environment
        """
    )
    
    parser.add_argument(
        '--platform',
        choices=['windows', 'macos', 'linux', 'auto'],
        default='auto',
        help='Target platform (default: auto-detect)'
    )
    
    parser.add_argument(
        '--clean',
        action='store_true',
        help='Clean previous builds before building'
    )
    
    parser.add_argument(
        '--no-test',
        action='store_true',
        help='Skip post-build testing'
    )
    
    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Only validate environment, do not build'
    )
    
    args = parser.parse_args()
    
    try:
        # Validate environment
        if not validate_environment():
            print("\nEnvironment validation failed. Please fix the errors above.")
            return 1
        
        if args.validate_only:
            print("\nEnvironment validation complete.")
            return 0
        
        # Determine platform
        if args.platform == 'auto':
            platform_name = get_platform()
            print(f"Auto-detected platform: {platform_name}")
        else:
            platform_name = args.platform
            print(f"Building for specified platform: {platform_name}")
        
        # Run build
        success = run_build(
            platform_name, 
            clean=args.clean, 
            test=not args.no_test
        )
        
        if success:
            print(f"\n🎉 Build completed successfully!")
            
            # Show output locations
            project_root = Path(__file__).parent.parent.parent
            dist_dir = project_root / 'dist'
            
            if dist_dir.exists():
                print(f"\nBuild artifacts:")
                for item in dist_dir.iterdir():
                    if item.is_file():
                        size = item.stat().st_size
                        print(f"  📦 {item.name} ({size:,} bytes)")
                    elif item.is_dir():
                        print(f"  📁 {item.name}/")
        else:
            print(f"\n❌ Build failed!")
            return 1
            
    except KeyboardInterrupt:
        print("\n\nBuild interrupted by user.")
        return 130
    except Exception as e:
        print(f"\n❌ Build failed with error: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())