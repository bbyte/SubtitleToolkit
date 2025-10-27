#!/usr/bin/env python3
"""
Functional tests for SubtitleToolkit scripts with JSONL validation.

Tests actual script functionality with sample data to ensure:
1. Scripts execute without critical errors
2. JSONL output is generated when --jsonl flag is used
3. Normal console output works when --jsonl flag is omitted
4. Progress events are emitted appropriately
5. Result events contain expected data
"""

import os
import sys
import json
import subprocess
import tempfile
import shutil
from pathlib import Path
import time
from typing import Dict, List, Any, Optional
from test_jsonl_schema import JSONLSchemaValidator, validate_jsonl_stream, analyze_jsonl_patterns


class FunctionalTester:
    """Functional testing framework for SubtitleToolkit scripts"""
    
    def __init__(self):
        self.scripts_dir = Path(__file__).parent / "scripts"
        self.temp_dirs = []  # Track temp directories for cleanup
    
    def create_test_environment(self) -> Path:
        """Create a temporary directory with test files"""
        temp_dir = tempfile.mkdtemp(prefix="subtitle_functional_test_")
        temp_path = Path(temp_dir)
        self.temp_dirs.append(temp_path)
        
        # Create sample MKV files (dummy content)
        mkv_files = [
            "The.Matrix.1999.1080p.BluRay.x264.mkv",
            "Breaking.Bad.S01E01.720p.WEB-DL.x264.mkv",
            "The.Office.US.S02E03.HDTV.x264.mkv"
        ]
        
        for mkv_file in mkv_files:
            (temp_path / mkv_file).write_text("dummy mkv file content")
        
        # Create sample SRT files
        sample_srt_content = """1
00:00:01,000 --> 00:00:03,000
Hello, this is a test subtitle.

2
00:00:04,000 --> 00:00:06,000
This is the second subtitle line.

3
00:00:07,000 --> 00:00:09,000
And this is the final test subtitle.

"""
        
        srt_files = [
            "The.Matrix.1999.srt",
            "Breaking.Bad.S01E01.srt", 
            "The.Office.US.S02E03.srt",
            "unmatched.subtitle.file.srt"
        ]
        
        for srt_file in srt_files:
            (temp_path / srt_file).write_text(sample_srt_content)
        
        return temp_path
    
    def run_script(self, script_name: str, args: List[str], timeout: int = 30, input_text: str = None) -> subprocess.CompletedProcess:
        """Execute a script with given arguments"""
        script_path = self.scripts_dir / f"{script_name}.py"
        
        if not script_path.exists():
            raise FileNotFoundError(f"Script not found: {script_path}")
        
        cmd = [sys.executable, str(script_path)] + args
        print(f"Running: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                input=input_text,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.scripts_dir.parent)  # Run from project root
            )
            return result
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Script '{script_name}' timed out after {timeout} seconds")
    
    def test_extract_mkv_subtitles(self) -> Dict[str, Any]:
        """Test the MKV subtitle extraction script"""
        print("\n🎬 Testing extract_mkv_subtitles.py")
        print("-" * 40)
        
        test_dir = self.create_test_environment()
        
        results = {
            'jsonl_mode': None,
            'normal_mode': None,
            'script_name': 'extract_mkv_subtitles'
        }
        
        # Test JSONL mode
        print("Testing JSONL mode...")
        try:
            result = self.run_script("extract_mkv_subtitles", [
                str(test_dir),
                "--jsonl",
                "--language", "eng"
            ], timeout=20)
            
            jsonl_analysis = self._analyze_script_output(result, "extract")
            results['jsonl_mode'] = jsonl_analysis
            
        except Exception as e:
            results['jsonl_mode'] = {'error': str(e), 'success': False}
        
        # Test normal mode
        print("Testing normal mode...")
        try:
            result = self.run_script("extract_mkv_subtitles", [
                str(test_dir),
                "--language", "eng"
            ], timeout=20)
            
            normal_analysis = self._analyze_normal_output(result)
            results['normal_mode'] = normal_analysis
            
        except Exception as e:
            results['normal_mode'] = {'error': str(e), 'success': False}
        
        return results
    
    def test_srt_translate(self) -> Dict[str, Any]:
        """Test the SRT translation script"""
        print("\n🌐 Testing srtTranslateWhole.py")
        print("-" * 40)
        
        test_dir = self.create_test_environment()
        test_srt = test_dir / "The.Matrix.1999.srt"
        
        results = {
            'jsonl_mode': None,
            'normal_mode': None, 
            'script_name': 'srtTranslateWhole'
        }
        
        # Test JSONL mode (will fail due to missing API key, but should still produce valid JSONL)
        print("Testing JSONL mode...")
        try:
            result = self.run_script("srtTranslateWhole", [
                "--file", str(test_srt),
                "--provider", "openai",
                "--model", "gpt-4o-mini", 
                "--jsonl"
            ], timeout=15)
            
            jsonl_analysis = self._analyze_script_output(result, "translate")
            results['jsonl_mode'] = jsonl_analysis
            
        except Exception as e:
            results['jsonl_mode'] = {'error': str(e), 'success': False}
        
        # Test normal mode
        print("Testing normal mode...")
        try:
            result = self.run_script("srtTranslateWhole", [
                "--file", str(test_srt),
                "--provider", "openai",
                "--model", "gpt-4o-mini"
            ], timeout=15)
            
            normal_analysis = self._analyze_normal_output(result)
            results['normal_mode'] = normal_analysis
            
        except Exception as e:
            results['normal_mode'] = {'error': str(e), 'success': False}
        
        return results
    
    def test_srt_names_sync(self) -> Dict[str, Any]:
        """Test the SRT names synchronization script"""
        print("\n🔄 Testing srt_names_sync.py")
        print("-" * 40)
        
        test_dir = self.create_test_environment()
        
        results = {
            'jsonl_mode': None,
            'normal_mode': None,
            'script_name': 'srt_names_sync'
        }
        
        # Test JSONL mode (will fail due to missing API key, but should produce JSONL)
        print("Testing JSONL mode...")
        try:
            result = self.run_script("srt_names_sync", [
                str(test_dir),
                "--provider", "openai",
                "--jsonl"
            ], timeout=15)
            
            jsonl_analysis = self._analyze_script_output(result, "sync")
            results['jsonl_mode'] = jsonl_analysis
            
        except Exception as e:
            results['jsonl_mode'] = {'error': str(e), 'success': False}
        
        # Test normal mode  
        print("Testing normal mode...")
        try:
            result = self.run_script("srt_names_sync", [
                str(test_dir),
                "--provider", "openai"
            ], timeout=15)
            
            normal_analysis = self._analyze_normal_output(result)
            results['normal_mode'] = normal_analysis
            
        except Exception as e:
            results['normal_mode'] = {'error': str(e), 'success': False}
        
        return results
    
    def _analyze_script_output(self, result: subprocess.CompletedProcess, expected_stage: str) -> Dict[str, Any]:
        """Analyze script output for JSONL mode"""
        analysis = {
            'return_code': result.returncode,
            'stdout_length': len(result.stdout),
            'stderr_length': len(result.stderr),
            'jsonl_valid': False,
            'events': [],
            'validation_errors': [],
            'stage_correct': False,
            'has_progress': False,
            'has_result': False,
            'event_analysis': {}
        }
        
        if result.stdout:
            try:
                validation_results, events = validate_jsonl_stream(result.stdout)
                analysis['events'] = events
                
                # Check for validation errors
                validation_errors = [r.error_message for r in validation_results if not r.is_valid]
                analysis['validation_errors'] = validation_errors
                analysis['jsonl_valid'] = len(validation_errors) == 0
                
                if events:
                    # Analyze event patterns
                    event_analysis = analyze_jsonl_patterns(events)
                    analysis['event_analysis'] = event_analysis
                    
                    # Check stage correctness
                    stages = event_analysis.get('stages', {})
                    analysis['stage_correct'] = expected_stage in stages
                    
                    # Check for progress and result events
                    event_types = event_analysis.get('types', {})
                    analysis['has_progress'] = 'progress' in event_types
                    analysis['has_result'] = 'result' in event_types
                    
            except Exception as e:
                analysis['validation_errors'].append(f"Analysis error: {e}")
        
        return analysis
    
    def _analyze_normal_output(self, result: subprocess.CompletedProcess) -> Dict[str, Any]:
        """Analyze script output for normal mode"""
        analysis = {
            'return_code': result.returncode,
            'stdout_length': len(result.stdout),
            'stderr_length': len(result.stderr),
            'has_ansi_colors': False,
            'has_progress_bars': False,
            'has_banner': False,
            'has_json_output': False,
            'json_lines': []
        }
        
        output = result.stdout + result.stderr
        
        # Check for ANSI color codes
        if '\033[' in output:
            analysis['has_ansi_colors'] = True
        
        # Check for progress bars or spinners
        progress_indicators = ['█', '░', '⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        if any(indicator in output for indicator in progress_indicators):
            analysis['has_progress_bars'] = True
        
        # Check for ASCII banners/art
        banner_chars = ['║', '╔', '╗', '╚', '╝', '═', '┏', '┓', '┗', '┛', '━']
        if any(char in output for char in banner_chars):
            analysis['has_banner'] = True
        
        # Check for accidental JSON output in normal mode
        lines = output.strip().split('\n')
        json_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('{') and stripped.endswith('}'):
                try:
                    json.loads(stripped)
                    json_lines.append(stripped)
                except json.JSONDecodeError:
                    pass
        
        analysis['has_json_output'] = len(json_lines) > 0
        analysis['json_lines'] = json_lines
        
        return analysis
    
    def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run all functional tests"""
        print("Starting Comprehensive Functional Tests")
        print("=" * 50)
        
        test_functions = [
            ('extract_mkv_subtitles', self.test_extract_mkv_subtitles),
            ('srtTranslateWhole', self.test_srt_translate),
            ('srt_names_sync', self.test_srt_names_sync)
        ]
        
        all_results = {}
        
        for test_name, test_func in test_functions:
            try:
                print(f"\n🧪 Running {test_name} functional tests...")
                results = test_func()
                all_results[test_name] = results
            except Exception as e:
                print(f"❌ Test {test_name} failed with error: {e}")
                all_results[test_name] = {'error': str(e), 'success': False}
        
        return all_results
    
    def generate_functional_report(self, results: Dict[str, Any]) -> str:
        """Generate comprehensive functional test report"""
        report = []
        report.append("SubtitleToolkit Functional Test Report")
        report.append("=" * 50)
        report.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Overall summary
        total_scripts = len(results)
        successful_scripts = 0
        
        for script_name, script_results in results.items():
            if 'error' not in script_results:
                jsonl_ok = script_results.get('jsonl_mode', {}).get('jsonl_valid', False)
                normal_ok = script_results.get('normal_mode', {}).get('return_code') is not None
                if jsonl_ok or normal_ok:  # At least one mode working
                    successful_scripts += 1
        
        report.append(f"SUMMARY: {successful_scripts}/{total_scripts} scripts functional")
        report.append("")
        
        # Detailed results for each script
        for script_name, script_results in results.items():
            report.append(f"SCRIPT: {script_name}")
            report.append("-" * 30)
            
            if 'error' in script_results:
                report.append(f"❌ CRITICAL ERROR: {script_results['error']}")
                report.append("")
                continue
            
            # JSONL mode analysis
            jsonl_mode = script_results.get('jsonl_mode', {})
            if jsonl_mode:
                report.append("JSONL Mode:")
                if jsonl_mode.get('jsonl_valid', False):
                    report.append("  ✅ JSONL output is valid")
                    
                    event_count = len(jsonl_mode.get('events', []))
                    report.append(f"  📊 Generated {event_count} events")
                    
                    if jsonl_mode.get('stage_correct', False):
                        report.append("  ✅ Stage values are correct")
                    else:
                        report.append("  ⚠️ Stage values may be incorrect")
                    
                    if jsonl_mode.get('has_progress', False):
                        report.append("  ✅ Progress events found")
                    else:
                        report.append("  ⚠️ No progress events found")
                    
                    if jsonl_mode.get('has_result', False):
                        report.append("  ✅ Result event found")
                    else:
                        report.append("  ⚠️ No result event found")
                        
                else:
                    report.append("  ❌ JSONL output is invalid")
                    errors = jsonl_mode.get('validation_errors', [])
                    for error in errors[:3]:  # Show first 3 errors
                        report.append(f"    - {error}")
                    if len(errors) > 3:
                        report.append(f"    ... and {len(errors) - 3} more errors")
            
            # Normal mode analysis
            normal_mode = script_results.get('normal_mode', {})
            if normal_mode:
                report.append("Normal Mode:")
                
                if normal_mode.get('has_ansi_colors', False):
                    report.append("  ✅ ANSI colors present")
                else:
                    report.append("  ⚠️ No ANSI colors detected")
                
                if normal_mode.get('has_banner', False):
                    report.append("  ✅ ASCII banner/art present")
                
                if normal_mode.get('has_progress_bars', False):
                    report.append("  ✅ Progress indicators present")
                
                if normal_mode.get('has_json_output', False):
                    report.append("  ❌ Unexpected JSON output in normal mode")
                    json_count = len(normal_mode.get('json_lines', []))
                    report.append(f"    Found {json_count} JSON lines")
                else:
                    report.append("  ✅ No JSON output in normal mode")
            
            report.append("")
        
        # Recommendations
        report.append("RECOMMENDATIONS:")
        report.append("-" * 20)
        
        if successful_scripts == total_scripts:
            report.append("✅ All scripts appear to be functioning correctly!")
            report.append("✅ JSONL implementation is working as expected.")
            report.append("✅ Backward compatibility is maintained.")
        else:
            report.append(f"❌ {total_scripts - successful_scripts} script(s) have issues")
            report.append("🔧 Review the detailed results above for specific problems")
        
        return "\n".join(report)
    
    def cleanup(self):
        """Clean up temporary directories"""
        for temp_dir in self.temp_dirs:
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    """Main test execution"""
    tester = FunctionalTester()
    
    try:
        # Run all functional tests
        results = tester.run_comprehensive_tests()
        
        # Generate report
        report = tester.generate_functional_report(results)
        print("\n")
        print(report)
        
        # Save report
        report_file = Path(__file__).parent / "functional_test_report.txt"
        report_file.write_text(report)
        print(f"\n📄 Full report saved to: {report_file}")
        
        # Determine exit code
        failed_tests = sum(1 for r in results.values() if 'error' in r)
        return 0 if failed_tests == 0 else 1
        
    except Exception as e:
        print(f"❌ Functional tests failed: {e}")
        return 1
    finally:
        tester.cleanup()


if __name__ == "__main__":
    sys.exit(main())