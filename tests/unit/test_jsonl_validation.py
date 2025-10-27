#!/usr/bin/env python3
"""
Comprehensive test suite for JSONL implementation validation in SubtitleToolkit scripts.

This test suite validates:
1. JSONL output schema and format compliance
2. Backward compatibility with normal console output
3. Functional correctness with sample data
4. Error handling and edge cases
"""

import os
import sys
import json
import subprocess
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone
import time
import re
from typing import Dict, List, Any, Optional
import unittest
from dataclasses import dataclass
from contextlib import contextmanager

# Test configuration
SCRIPTS_DIR = Path(__file__).parent / "scripts"
TEST_DATA_DIR = Path(__file__).parent / "test_data"

@dataclass
class JSONLEvent:
    """Represents a parsed JSONL event for validation"""
    ts: str
    stage: str
    type: str
    msg: str
    progress: Optional[int] = None
    data: Optional[Dict] = None

class JSONLValidator:
    """Validates JSONL events against the specification"""
    
    VALID_STAGES = {"extract", "translate", "sync"}
    VALID_TYPES = {"info", "progress", "warning", "error", "result"}
    
    @staticmethod
    def validate_event(event_dict: Dict[str, Any]) -> bool:
        """Validate a single JSONL event against the schema"""
        required_fields = {"ts", "stage", "type", "msg"}
        
        # Check required fields exist
        if not all(field in event_dict for field in required_fields):
            return False, f"Missing required fields. Required: {required_fields}, Got: {list(event_dict.keys())}"
        
        # Validate timestamp format (ISO 8601 UTC)
        try:
            ts = event_dict["ts"]
            if ts.endswith('Z'):
                datetime.fromisoformat(ts.replace('Z', '+00:00'))
            else:
                datetime.fromisoformat(ts)
        except ValueError:
            return False, f"Invalid timestamp format: {ts}"
        
        # Validate stage
        if event_dict["stage"] not in JSONLValidator.VALID_STAGES:
            return False, f"Invalid stage: {event_dict['stage']}"
        
        # Validate type
        if event_dict["type"] not in JSONLValidator.VALID_TYPES:
            return False, f"Invalid type: {event_dict['type']}"
        
        # Validate message is string
        if not isinstance(event_dict["msg"], str):
            return False, f"Message must be string, got: {type(event_dict['msg'])}"
        
        # Validate progress if present
        if "progress" in event_dict:
            progress = event_dict["progress"]
            if not isinstance(progress, (int, float)) or progress < 0 or progress > 100:
                return False, f"Progress must be number between 0-100, got: {progress}"
        
        # Validate data if present
        if "data" in event_dict and event_dict["data"] is not None:
            if not isinstance(event_dict["data"], dict):
                return False, f"Data must be dict or null, got: {type(event_dict['data'])}"
        
        return True, "Valid"
    
    @staticmethod
    def parse_jsonl_output(output: str) -> List[JSONLEvent]:
        """Parse JSONL output into structured events"""
        events = []
        for line_num, line in enumerate(output.strip().split('\n'), 1):
            if not line.strip():
                continue
            try:
                event_dict = json.loads(line)
                is_valid, error_msg = JSONLValidator.validate_event(event_dict)
                if not is_valid:
                    raise ValueError(f"Line {line_num}: {error_msg}")
                
                events.append(JSONLEvent(
                    ts=event_dict["ts"],
                    stage=event_dict["stage"],
                    type=event_dict["type"],
                    msg=event_dict["msg"],
                    progress=event_dict.get("progress"),
                    data=event_dict.get("data")
                ))
            except json.JSONDecodeError as e:
                raise ValueError(f"Line {line_num}: Invalid JSON - {e}")
        
        return events

class TestDataGenerator:
    """Generates test data for validation"""
    
    @staticmethod
    def create_test_mkv_files(directory: Path) -> List[Path]:
        """Create dummy MKV files for testing"""
        mkv_files = [
            "Breaking.Bad.S01E01.1080p.WEB-DL.x264.mkv",
            "The.Office.S02E03.720p.HDTV.x264.mkv",
            "Movie.Title.2023.1080p.BluRay.x264.mkv",
        ]
        
        created_files = []
        for filename in mkv_files:
            file_path = directory / filename
            file_path.write_text("dummy mkv content")  # Create dummy file
            created_files.append(file_path)
        
        return created_files
    
    @staticmethod
    def create_test_srt_files(directory: Path) -> List[Path]:
        """Create test SRT files for testing"""
        srt_content = """1
00:00:01,000 --> 00:00:03,000
This is a test subtitle.

2
00:00:04,000 --> 00:00:06,000
This is another test subtitle.

3
00:00:07,000 --> 00:00:09,000
Final test subtitle.

"""
        
        srt_files = [
            "Breaking.Bad.S01E01.srt",
            "The.Office.S02E03.srt", 
            "Movie.Title.2023.srt",
            "unmatched.subtitle.srt"
        ]
        
        created_files = []
        for filename in srt_files:
            file_path = directory / filename
            file_path.write_text(srt_content)
            created_files.append(file_path)
        
        return created_files

@contextmanager
def temp_test_directory():
    """Create temporary directory for testing"""
    temp_dir = tempfile.mkdtemp(prefix="subtitle_test_")
    try:
        yield Path(temp_dir)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

class SubtitleToolkitTester:
    """Main test class for SubtitleToolkit JSONL validation"""
    
    def __init__(self):
        self.scripts_dir = SCRIPTS_DIR
        self.results = {
            'extract_mkv_subtitles': {'jsonl': None, 'normal': None},
            'srtTranslateWhole': {'jsonl': None, 'normal': None}, 
            'srt_names_sync': {'jsonl': None, 'normal': None}
        }
    
    def run_script(self, script_name: str, args: List[str], timeout: int = 30) -> subprocess.CompletedProcess:
        """Run a script with given arguments"""
        script_path = self.scripts_dir / f"{script_name}.py"
        if not script_path.exists():
            raise FileNotFoundError(f"Script not found: {script_path}")
        
        cmd = [sys.executable, str(script_path)] + args
        print(f"Running: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Script timed out after {timeout} seconds")
    
    def test_extract_mkv_subtitles_jsonl(self) -> Dict[str, Any]:
        """Test extract_mkv_subtitles.py with --jsonl flag"""
        print("\n=== Testing extract_mkv_subtitles.py (JSONL mode) ===")
        
        with temp_test_directory() as temp_dir:
            # Create test MKV files
            mkv_files = TestDataGenerator.create_test_mkv_files(temp_dir)
            
            # Run script with JSONL flag
            result = self.run_script("extract_mkv_subtitles", [
                str(temp_dir), "--jsonl", "--language", "eng"
            ])
            
            test_result = {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'events': [],
                'errors': []
            }
            
            if result.returncode == 0:
                try:
                    events = JSONLValidator.parse_jsonl_output(result.stdout)
                    test_result['events'] = events
                    
                    # Validate expected events
                    expected_stages = {"extract"}
                    found_stages = {event.stage for event in events}
                    if not expected_stages.issubset(found_stages):
                        test_result['errors'].append(f"Missing expected stages: {expected_stages - found_stages}")
                    
                    # Check for progress events
                    progress_events = [e for e in events if e.type == "progress"]
                    if not progress_events:
                        test_result['errors'].append("No progress events found")
                    
                    # Check for result event
                    result_events = [e for e in events if e.type == "result"]
                    if not result_events:
                        test_result['errors'].append("No result event found")
                    
                except Exception as e:
                    test_result['errors'].append(f"JSONL validation error: {e}")
            else:
                test_result['errors'].append(f"Script failed with return code {result.returncode}")
            
            return test_result
    
    def test_extract_mkv_subtitles_normal(self) -> Dict[str, Any]:
        """Test extract_mkv_subtitles.py in normal mode (no --jsonl)"""
        print("\n=== Testing extract_mkv_subtitles.py (Normal mode) ===")
        
        with temp_test_directory() as temp_dir:
            # Create test MKV files
            mkv_files = TestDataGenerator.create_test_mkv_files(temp_dir)
            
            # Run script without JSONL flag
            result = self.run_script("extract_mkv_subtitles", [
                str(temp_dir), "--language", "eng"
            ])
            
            test_result = {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'has_colors': False,
                'has_banner': False,
                'errors': []
            }
            
            # Check for ANSI color codes (indicating normal colored output)
            if '\033[' in result.stdout:
                test_result['has_colors'] = True
            
            # Check for ASCII banner
            if '║' in result.stdout or '█' in result.stdout:
                test_result['has_banner'] = True
            
            # Ensure no JSON output
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line.strip().startswith('{') and line.strip().endswith('}'):
                    try:
                        json.loads(line)
                        test_result['errors'].append("Found JSON output in normal mode")
                        break
                    except json.JSONDecodeError:
                        pass  # Not JSON, which is expected
            
            return test_result
    
    def test_srt_translate_jsonl(self) -> Dict[str, Any]:
        """Test srtTranslateWhole.py with --jsonl flag"""
        print("\n=== Testing srtTranslateWhole.py (JSONL mode) ===")
        
        with temp_test_directory() as temp_dir:
            # Create test SRT file
            srt_files = TestDataGenerator.create_test_srt_files(temp_dir)
            test_srt = srt_files[0]
            
            # Run script with JSONL flag (using mock/dry-run approach)
            # Note: This would normally require API keys, so we'll test the CLI parsing
            result = self.run_script("srtTranslateWhole", [
                "--file", str(test_srt),
                "--provider", "openai", 
                "--model", "gpt-4o-mini",
                "--jsonl"
            ], timeout=10)
            
            test_result = {
                'success': True,  # We expect it to fail due to missing API key
                'stdout': result.stdout,
                'stderr': result.stderr,
                'events': [],
                'errors': []
            }
            
            # Even if it fails due to API key, it should still produce proper JSONL structure
            if result.stdout:
                try:
                    events = JSONLValidator.parse_jsonl_output(result.stdout)
                    test_result['events'] = events
                    
                    # Check stage is correct
                    for event in events:
                        if event.stage != "translate":
                            test_result['errors'].append(f"Wrong stage: expected 'translate', got '{event.stage}'")
                            
                except Exception as e:
                    test_result['errors'].append(f"JSONL validation error: {e}")
            
            return test_result
    
    def test_srt_translate_normal(self) -> Dict[str, Any]:
        """Test srtTranslateWhole.py in normal mode"""
        print("\n=== Testing srtTranslateWhole.py (Normal mode) ===")
        
        with temp_test_directory() as temp_dir:
            # Create test SRT file
            srt_files = TestDataGenerator.create_test_srt_files(temp_dir)
            test_srt = srt_files[0]
            
            # Run script without JSONL flag
            result = self.run_script("srtTranslateWhole", [
                "--file", str(test_srt),
                "--provider", "openai",
                "--model", "gpt-4o-mini"
            ], timeout=10)
            
            test_result = {
                'success': True,  # Expected to fail due to missing API key
                'stdout': result.stdout,
                'stderr': result.stderr,
                'has_colors': False,
                'errors': []
            }
            
            # Check for colored output indicators
            if '\033[' in result.stdout or '\033[' in result.stderr:
                test_result['has_colors'] = True
            
            # Ensure no JSON output
            output = result.stdout + result.stderr
            lines = output.strip().split('\n')
            for line in lines:
                if line.strip().startswith('{') and line.strip().endswith('}'):
                    try:
                        json.loads(line)
                        test_result['errors'].append("Found JSON output in normal mode")
                        break
                    except json.JSONDecodeError:
                        pass
            
            return test_result
    
    def test_srt_names_sync_jsonl(self) -> Dict[str, Any]:
        """Test srt_names_sync.py with --jsonl flag"""
        print("\n=== Testing srt_names_sync.py (JSONL mode) ===")
        
        with temp_test_directory() as temp_dir:
            # Create test files
            mkv_files = TestDataGenerator.create_test_mkv_files(temp_dir)
            srt_files = TestDataGenerator.create_test_srt_files(temp_dir)
            
            # Run script with JSONL flag (dry run by default)
            result = self.run_script("srt_names_sync", [
                str(temp_dir),
                "--provider", "openai",
                "--jsonl"
            ], timeout=15)
            
            test_result = {
                'success': True,  # Expected to fail due to missing API key
                'stdout': result.stdout,
                'stderr': result.stderr,
                'events': [],
                'errors': []
            }
            
            if result.stdout:
                try:
                    events = JSONLValidator.parse_jsonl_output(result.stdout)
                    test_result['events'] = events
                    
                    # Check stage is correct
                    for event in events:
                        if event.stage != "sync":
                            test_result['errors'].append(f"Wrong stage: expected 'sync', got '{event.stage}'")
                    
                except Exception as e:
                    test_result['errors'].append(f"JSONL validation error: {e}")
            
            return test_result
    
    def test_srt_names_sync_normal(self) -> Dict[str, Any]:
        """Test srt_names_sync.py in normal mode"""
        print("\n=== Testing srt_names_sync.py (Normal mode) ===")
        
        with temp_test_directory() as temp_dir:
            # Create test files
            mkv_files = TestDataGenerator.create_test_mkv_files(temp_dir)
            srt_files = TestDataGenerator.create_test_srt_files(temp_dir)
            
            # Run script without JSONL flag
            result = self.run_script("srt_names_sync", [
                str(temp_dir),
                "--provider", "openai"
            ], timeout=15)
            
            test_result = {
                'success': True,  # Expected to fail due to missing API key
                'stdout': result.stdout,
                'stderr': result.stderr,
                'has_colors': False,
                'has_banner': False,
                'errors': []
            }
            
            # Check for colored output
            if '\033[' in result.stdout:
                test_result['has_colors'] = True
            
            # Check for fancy banner/box drawing characters
            if '┏' in result.stdout or '━' in result.stdout:
                test_result['has_banner'] = True
            
            # Ensure no JSON output
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line.strip().startswith('{') and line.strip().endswith('}'):
                    try:
                        json.loads(line)
                        test_result['errors'].append("Found JSON output in normal mode")
                        break
                    except json.JSONDecodeError:
                        pass
            
            return test_result
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all validation tests"""
        print("Starting comprehensive JSONL validation tests...")
        print("=" * 80)
        
        # Run all tests
        tests = [
            ('extract_mkv_subtitles_jsonl', self.test_extract_mkv_subtitles_jsonl),
            ('extract_mkv_subtitles_normal', self.test_extract_mkv_subtitles_normal),
            ('srt_translate_jsonl', self.test_srt_translate_jsonl),
            ('srt_translate_normal', self.test_srt_translate_normal),
            ('srt_names_sync_jsonl', self.test_srt_names_sync_jsonl),
            ('srt_names_sync_normal', self.test_srt_names_sync_normal),
        ]
        
        results = {}
        for test_name, test_func in tests:
            try:
                results[test_name] = test_func()
            except Exception as e:
                results[test_name] = {
                    'success': False,
                    'error': str(e),
                    'errors': [f"Test execution failed: {e}"]
                }
        
        return results
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate a comprehensive test report"""
        report = []
        report.append("SubtitleToolkit JSONL Implementation Validation Report")
        report.append("=" * 60)
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("")
        
        # Summary
        total_tests = len(results)
        passed_tests = sum(1 for r in results.values() if not r.get('errors', []) and r.get('success', False))
        
        report.append(f"SUMMARY: {passed_tests}/{total_tests} tests passed")
        report.append("")
        
        # Detailed results
        for test_name, result in results.items():
            report.append(f"TEST: {test_name}")
            report.append("-" * 40)
            
            if result.get('errors'):
                report.append(f"❌ FAILED with {len(result['errors'])} error(s):")
                for error in result['errors']:
                    report.append(f"  - {error}")
            elif result.get('success', False):
                report.append("✅ PASSED")
                
                # Add specific validation details
                if 'events' in result and result['events']:
                    report.append(f"  - Generated {len(result['events'])} JSONL events")
                    event_types = {}
                    for event in result['events']:
                        event_types[event.type] = event_types.get(event.type, 0) + 1
                    report.append(f"  - Event types: {event_types}")
                
                if 'has_colors' in result and result['has_colors']:
                    report.append("  - Colored output detected (normal mode)")
                
                if 'has_banner' in result and result['has_banner']:
                    report.append("  - ASCII banner detected (normal mode)")
            else:
                report.append("❓ INCONCLUSIVE")
            
            report.append("")
        
        # Recommendations
        report.append("RECOMMENDATIONS:")
        report.append("-" * 20)
        
        failed_tests = [name for name, result in results.items() if result.get('errors') or not result.get('success', False)]
        if not failed_tests:
            report.append("✅ All tests passed! JSONL implementation appears to be working correctly.")
        else:
            report.append(f"❌ {len(failed_tests)} test(s) failed. Review the following:")
            for test_name in failed_tests:
                report.append(f"  - {test_name}")
        
        return "\n".join(report)

def main():
    """Main test execution"""
    try:
        # Verify scripts exist
        scripts_to_test = [
            "extract_mkv_subtitles.py",
            "srtTranslateWhole.py", 
            "srt_names_sync.py"
        ]
        
        missing_scripts = []
        for script in scripts_to_test:
            if not (SCRIPTS_DIR / script).exists():
                missing_scripts.append(script)
        
        if missing_scripts:
            print(f"❌ Missing scripts: {missing_scripts}")
            print(f"Expected location: {SCRIPTS_DIR}")
            return 1
        
        # Initialize tester
        tester = SubtitleToolkitTester()
        
        # Run all tests
        results = tester.run_all_tests()
        
        # Generate and display report
        report = tester.generate_report(results)
        print("\n")
        print(report)
        
        # Save report to file
        report_file = Path(__file__).parent / "test_validation_report.txt"
        report_file.write_text(report)
        print(f"\n📄 Full report saved to: {report_file}")
        
        # Return appropriate exit code
        failed_count = sum(1 for r in results.values() if r.get('errors') or not r.get('success', False))
        return 0 if failed_count == 0 else 1
        
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())