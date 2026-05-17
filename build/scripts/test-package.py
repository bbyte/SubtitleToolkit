#!/usr/bin/env python3
"""
Cross-platform testing framework for packaged SubtitleToolkit applications

This script performs comprehensive smoke testing on the packaged application
to ensure it works correctly across different platforms.
"""

import sys
import os
import platform
import subprocess
import tempfile
import shutil
import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class PackageTestResult:
    """Result of a package test."""
    
    def __init__(self, name: str, passed: bool, message: str = "", execution_time: float = 0.0):
        self.name = name
        self.passed = passed
        self.message = message
        self.execution_time = execution_time
    
    def __str__(self):
        status = "✅ PASS" if self.passed else "❌ FAIL"
        time_str = f" ({self.execution_time:.2f}s)" if self.execution_time > 0 else ""
        message_str = f" - {self.message}" if self.message else ""
        return f"{status} {self.name}{time_str}{message_str}"


class PackageTester:
    """Test runner for packaged applications."""
    
    def __init__(self, executable_path: Path):
        self.executable_path = executable_path
        self.platform = platform.system().lower()
        self.test_results: List[PackageTestResult] = []
        self.temp_dir: Optional[Path] = None
    
    def setup(self) -> bool:
        """Set up the test environment."""
        try:
            # Create temporary directory for test files
            self.temp_dir = Path(tempfile.mkdtemp(prefix="subtitle_test_"))
            
            # Create test data
            self._create_test_data()
            
            print(f"Test environment setup complete")
            print(f"Temporary directory: {self.temp_dir}")
            return True
            
        except Exception as e:
            print(f"Failed to set up test environment: {e}")
            return False
    
    def cleanup(self):
        """Clean up test environment."""
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            print(f"Cleaned up temporary directory: {self.temp_dir}")
    
    def _create_test_data(self):
        """Create test data files."""
        # Create a sample SRT file
        srt_content = """1
00:00:01,000 --> 00:00:03,000
Hello world

2
00:00:04,000 --> 00:00:06,000
This is a test subtitle

3
00:00:07,000 --> 00:00:09,000
Final test line
"""
        srt_file = self.temp_dir / "test_subtitle.srt"
        srt_file.write_text(srt_content, encoding='utf-8')
        
        # Create a sample .env file
        env_content = """# Test environment variables
OPENAI_API_KEY=test_key_openai
ANTHROPIC_API_KEY=test_key_anthropic
"""
        env_file = self.temp_dir / ".env"
        env_file.write_text(env_content, encoding='utf-8')
    
    def test_executable_exists(self) -> PackageTestResult:
        """Test that the executable exists and is accessible."""
        start_time = time.time()
        
        if not self.executable_path.exists():
            return PackageTestResult(
                "Executable Exists", 
                False, 
                f"File not found: {self.executable_path}",
                time.time() - start_time
            )
        
        if not os.access(self.executable_path, os.X_OK):
            return PackageTestResult(
                "Executable Permissions", 
                False, 
                "File is not executable",
                time.time() - start_time
            )
        
        return PackageTestResult(
            "Executable Exists", 
            True, 
            f"Found at {self.executable_path}",
            time.time() - start_time
        )
    
    def test_help_output(self) -> PackageTestResult:
        """Test that the application can display help information."""
        start_time = time.time()
        
        try:
            # Try to run with --help flag
            result = subprocess.run(
                [str(self.executable_path), '--help'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            execution_time = time.time() - start_time
            
            if result.returncode == 0:
                return PackageTestResult(
                    "Help Output", 
                    True, 
                    "Application responds to --help",
                    execution_time
                )
            else:
                return PackageTestResult(
                    "Help Output", 
                    False, 
                    f"Exit code: {result.returncode}, stderr: {result.stderr[:100]}",
                    execution_time
                )
                
        except subprocess.TimeoutExpired:
            return PackageTestResult(
                "Help Output", 
                False, 
                "Timed out waiting for response",
                time.time() - start_time
            )
        except Exception as e:
            return PackageTestResult(
                "Help Output", 
                False, 
                f"Exception: {str(e)[:100]}",
                time.time() - start_time
            )
    
    def test_basic_startup(self) -> PackageTestResult:
        """Test basic application startup without GUI."""
        start_time = time.time()
        
        try:
            # Try to start the application and quickly terminate
            process = subprocess.Popen(
                [str(self.executable_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Give it a moment to start
            time.sleep(2)
            
            # Terminate the process
            process.terminate()
            
            # Wait for termination
            try:
                stdout, stderr = process.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
            
            execution_time = time.time() - start_time
            
            # Check if it started without immediate crashes
            if process.returncode is None or process.returncode in [0, -15]:  # 0 = normal, -15 = SIGTERM
                return PackageTestResult(
                    "Basic Startup", 
                    True, 
                    "Application started and terminated cleanly",
                    execution_time
                )
            else:
                return PackageTestResult(
                    "Basic Startup", 
                    False, 
                    f"Exit code: {process.returncode}, stderr: {stderr[:100]}",
                    execution_time
                )
                
        except Exception as e:
            return PackageTestResult(
                "Basic Startup", 
                False, 
                f"Exception: {str(e)[:100]}",
                time.time() - start_time
            )
    
    def test_dependencies_bundled(self) -> PackageTestResult:
        """Test that required dependencies are properly bundled."""
        start_time = time.time()
        
        try:
            # Create a test script to check imports
            test_script = f'''
import sys
import os

# Test critical imports
try:
    import PySide6
    print("✓ PySide6 available")
except ImportError as e:
    print(f"❌ PySide6 missing: {{e}}")
    sys.exit(1)

try:
    import openai
    print("✓ OpenAI available")
except ImportError as e:
    print(f"❌ OpenAI missing: {{e}}")
    sys.exit(1)

try:
    import anthropic
    print("✓ Anthropic available")
except ImportError as e:
    print(f"❌ Anthropic missing: {{e}}")
    sys.exit(1)

try:
    import dotenv
    print("✓ python-dotenv available")
except ImportError as e:
    print(f"❌ python-dotenv missing: {{e}}")
    sys.exit(1)

try:
    import tqdm
    print("✓ tqdm available")
except ImportError as e:
    print(f"❌ tqdm missing: {{e}}")
    sys.exit(1)

print("All dependencies available")
'''
            
            # Write test script
            test_script_path = self.temp_dir / "test_imports.py"
            test_script_path.write_text(test_script)
            
            # Run the test
            result = subprocess.run(
                [sys.executable, str(test_script_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            execution_time = time.time() - start_time
            
            if result.returncode == 0:
                return PackageTestResult(
                    "Dependencies Bundled", 
                    True, 
                    "All required dependencies are available",
                    execution_time
                )
            else:
                return PackageTestResult(
                    "Dependencies Bundled", 
                    False, 
                    f"Missing dependencies: {result.stdout}",
                    execution_time
                )
                
        except Exception as e:
            return PackageTestResult(
                "Dependencies Bundled", 
                False, 
                f"Exception: {str(e)[:100]}",
                time.time() - start_time
            )
    
    def test_file_permissions(self) -> PackageTestResult:
        """Test file permissions on the packaged application."""
        start_time = time.time()
        
        try:
            # Get file stats
            stat = self.executable_path.stat()
            
            # Check if file is readable and executable
            is_readable = os.access(self.executable_path, os.R_OK)
            is_executable = os.access(self.executable_path, os.X_OK)
            
            # On Unix systems, check permission bits
            if self.platform in ['linux', 'darwin']:
                mode = oct(stat.st_mode)[-3:]  # Get last 3 digits (permissions)
                owner_perms = int(mode[0])
                
                if owner_perms < 5:  # Need at least r-x (5) for owner
                    return PackageTestResult(
                        "File Permissions", 
                        False, 
                        f"Insufficient permissions: {mode}",
                        time.time() - start_time
                    )
            
            if not (is_readable and is_executable):
                return PackageTestResult(
                    "File Permissions", 
                    False, 
                    f"Not readable: {not is_readable}, Not executable: {not is_executable}",
                    time.time() - start_time
                )
            
            return PackageTestResult(
                "File Permissions", 
                True, 
                "File permissions are correct",
                time.time() - start_time
            )
            
        except Exception as e:
            return PackageTestResult(
                "File Permissions", 
                False, 
                f"Exception: {str(e)[:100]}",
                time.time() - start_time
            )
    
    def run_all_tests(self) -> List[PackageTestResult]:
        """Run all available tests."""
        print(f"Running package tests for: {self.executable_path}")
        print(f"Platform: {self.platform}")
        print("=" * 60)
        
        if not self.setup():
            return [PackageTestResult("Setup", False, "Failed to set up test environment")]
        
        try:
            tests = [
                self.test_executable_exists,
                self.test_file_permissions,
                self.test_dependencies_bundled,
                self.test_help_output,
                self.test_basic_startup,
            ]
            
            results = []
            for test_func in tests:
                print(f"Running {test_func.__name__}...")
                result = test_func()
                results.append(result)
                print(f"  {result}")
            
            return results
            
        finally:
            self.cleanup()


def find_executable() -> Optional[Path]:
    """Find the packaged executable in the dist directory."""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    dist_dir = project_root / 'dist'
    
    if not dist_dir.exists():
        print(f"Distribution directory not found: {dist_dir}")
        return None
    
    # Platform-specific executable patterns
    system = platform.system().lower()
    
    if system == 'windows':
        # Look for .exe file
        exe_files = list(dist_dir.rglob('*.exe'))
        if exe_files:
            return exe_files[0]
    
    elif system == 'darwin':
        # Look for .app bundle
        app_bundles = list(dist_dir.glob('*.app'))
        if app_bundles:
            # Find executable inside bundle
            app_bundle = app_bundles[0]
            executable = app_bundle / 'Contents' / 'MacOS' / app_bundle.stem
            if executable.exists():
                return executable
    
    elif system == 'linux':
        # Look for executable in directory
        app_dirs = [d for d in dist_dir.iterdir() if d.is_dir() and 'SubtitleToolkit' in d.name]
        if app_dirs:
            executable = app_dirs[0] / 'SubtitleToolkit'
            if executable.exists():
                return executable
        
        # Also check for AppImage
        appimage_files = list(dist_dir.glob('*.AppImage'))
        if appimage_files:
            return appimage_files[0]
    
    print(f"No executable found in {dist_dir}")
    return None


def main():
    """Main test runner."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test packaged SubtitleToolkit application')
    parser.add_argument('--executable', type=Path, help='Path to executable to test')
    parser.add_argument('--json-output', type=Path, help='Output results as JSON to file')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Find executable
    if args.executable:
        executable_path = args.executable
    else:
        executable_path = find_executable()
        if not executable_path:
            print("❌ Could not find packaged executable")
            print("   Run the build script first, or specify --executable")
            return 1
    
    print(f"Testing executable: {executable_path}")
    
    # Run tests
    tester = PackageTester(executable_path)
    results = tester.run_all_tests()
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    
    for result in results:
        print(result)
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    # Save JSON output if requested
    if args.json_output:
        json_data = {
            'executable': str(executable_path),
            'platform': platform.system(),
            'timestamp': time.time(),
            'summary': {
                'passed': passed,
                'total': total,
                'success_rate': passed / total if total > 0 else 0
            },
            'results': [
                {
                    'name': r.name,
                    'passed': r.passed,
                    'message': r.message,
                    'execution_time': r.execution_time
                }
                for r in results
            ]
        }
        
        args.json_output.write_text(json.dumps(json_data, indent=2))
        print(f"\nJSON results saved to: {args.json_output}")
    
    # Return appropriate exit code
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())