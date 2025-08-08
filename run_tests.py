#!/usr/bin/env python3
"""
Comprehensive test runner for SubtitleToolkit JSONL implementation validation.

This script orchestrates all test suites:
1. Schema validation tests
2. Functional tests with sample data  
3. Backward compatibility verification
4. Edge case testing

Usage:
    python run_tests.py [--verbose] [--skip-functional] [--quick]
"""

import sys
import argparse
import time
from pathlib import Path
from typing import Dict, Any, List
import traceback

# Import our test modules
try:
    from test_jsonl_schema import run_schema_tests, JSONLSchemaValidator
    from test_functional import FunctionalTester
    from test_jsonl_validation import SubtitleToolkitTester
except ImportError as e:
    print(f"❌ Failed to import test modules: {e}")
    print("Make sure all test files are in the same directory")
    sys.exit(1)


class TestSuite:
    """Comprehensive test suite runner"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results = {}
        self.start_time = time.time()
    
    def log(self, message: str, level: str = "INFO"):
        """Log message if verbose mode is enabled"""
        if self.verbose or level in ["ERROR", "CRITICAL"]:
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}] {level}: {message}")
    
    def run_schema_tests(self) -> Dict[str, Any]:
        """Run JSONL schema validation tests"""
        print("\n🔍 Running Schema Validation Tests")
        print("=" * 40)
        
        start_time = time.time()
        
        try:
            # Capture output from schema tests
            import io
            from contextlib import redirect_stdout
            
            output_buffer = io.StringIO()
            with redirect_stdout(output_buffer):
                run_schema_tests()
            
            output = output_buffer.getvalue()
            duration = time.time() - start_time
            
            # Count passes and fails from output
            lines = output.split('\n')
            pass_count = sum(1 for line in lines if '✅ PASS' in line)
            fail_count = sum(1 for line in lines if '❌ FAIL' in line)
            
            result = {
                'success': fail_count == 0,
                'duration': duration,
                'pass_count': pass_count,
                'fail_count': fail_count,
                'output': output
            }
            
            print(f"Schema tests: {pass_count} passed, {fail_count} failed ({duration:.2f}s)")
            return result
            
        except Exception as e:
            error_msg = f"Schema tests failed with error: {e}"
            self.log(error_msg, "ERROR")
            if self.verbose:
                traceback.print_exc()
            
            return {
                'success': False,
                'duration': time.time() - start_time,
                'error': str(e),
                'output': ''
            }
    
    def run_functional_tests(self) -> Dict[str, Any]:
        """Run functional tests"""
        print("\n⚙️ Running Functional Tests")
        print("=" * 40)
        
        start_time = time.time()
        
        try:
            tester = FunctionalTester()
            results = tester.run_comprehensive_tests()
            tester.cleanup()
            
            duration = time.time() - start_time
            
            # Analyze results
            total_scripts = len(results)
            successful_scripts = 0
            
            for script_name, script_results in results.items():
                if 'error' not in script_results:
                    jsonl_mode = script_results.get('jsonl_mode', {})
                    normal_mode = script_results.get('normal_mode', {})
                    
                    jsonl_valid = jsonl_mode.get('jsonl_valid', False)
                    normal_working = 'return_code' in normal_mode
                    
                    if jsonl_valid and normal_working:
                        successful_scripts += 1
                        self.log(f"✅ {script_name}: Both modes working")
                    elif jsonl_valid:
                        self.log(f"⚠️ {script_name}: JSONL working, normal mode issues")
                    elif normal_working:
                        self.log(f"⚠️ {script_name}: Normal mode working, JSONL issues")
                    else:
                        self.log(f"❌ {script_name}: Both modes have issues")
                else:
                    self.log(f"❌ {script_name}: Critical error - {script_results.get('error', 'Unknown')}")
            
            result = {
                'success': successful_scripts == total_scripts,
                'duration': duration,
                'total_scripts': total_scripts,
                'successful_scripts': successful_scripts,
                'detailed_results': results
            }
            
            print(f"Functional tests: {successful_scripts}/{total_scripts} scripts working ({duration:.2f}s)")
            return result
            
        except Exception as e:
            error_msg = f"Functional tests failed with error: {e}"
            self.log(error_msg, "ERROR")
            if self.verbose:
                traceback.print_exc()
            
            return {
                'success': False,
                'duration': time.time() - start_time,
                'error': str(e)
            }
    
    def run_validation_tests(self) -> Dict[str, Any]:
        """Run comprehensive validation tests"""
        print("\n🧪 Running Comprehensive Validation Tests")
        print("=" * 40)
        
        start_time = time.time()
        
        try:
            tester = SubtitleToolkitTester()
            results = tester.run_all_tests()
            
            duration = time.time() - start_time
            
            # Count successful tests
            total_tests = len(results)
            passed_tests = 0
            
            for test_name, result in results.items():
                success = result.get('success', False) and not result.get('errors', [])
                if success:
                    passed_tests += 1
                    self.log(f"✅ {test_name}: Passed")
                else:
                    error_count = len(result.get('errors', []))
                    self.log(f"❌ {test_name}: Failed ({error_count} errors)")
            
            validation_result = {
                'success': passed_tests == total_tests,
                'duration': duration,
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'detailed_results': results
            }
            
            print(f"Validation tests: {passed_tests}/{total_tests} passed ({duration:.2f}s)")
            return validation_result
            
        except Exception as e:
            error_msg = f"Validation tests failed with error: {e}"
            self.log(error_msg, "ERROR")
            if self.verbose:
                traceback.print_exc()
            
            return {
                'success': False,
                'duration': time.time() - start_time,
                'error': str(e)
            }
    
    def run_edge_case_tests(self) -> Dict[str, Any]:
        """Run edge case tests"""
        print("\n🔬 Running Edge Case Tests")
        print("=" * 40)
        
        start_time = time.time()
        edge_cases_passed = 0
        total_edge_cases = 0
        
        # Edge case: Empty directory
        try:
            from test_functional import FunctionalTester
            import tempfile
            
            tester = FunctionalTester()
            empty_dir = Path(tempfile.mkdtemp(prefix="empty_test_"))
            
            # Test extract script with empty directory
            result = tester.run_script("extract_mkv_subtitles", [
                str(empty_dir), "--jsonl"
            ], timeout=10)
            
            total_edge_cases += 1
            if result.returncode == 0:  # Should handle empty directory gracefully
                edge_cases_passed += 1
                self.log("✅ Empty directory handled gracefully")
            else:
                self.log("⚠️ Empty directory not handled gracefully")
            
            empty_dir.rmdir()
            tester.cleanup()
            
        except Exception as e:
            self.log(f"Edge case test failed: {e}", "ERROR")
        
        # Edge case: Invalid arguments
        try:
            tester = FunctionalTester()
            
            # Test with invalid provider
            result = tester.run_script("srt_names_sync", [
                ".", "--provider", "invalid", "--jsonl"
            ], timeout=10)
            
            total_edge_cases += 1
            if result.returncode != 0:  # Should fail with invalid provider
                edge_cases_passed += 1
                self.log("✅ Invalid provider handled correctly")
            else:
                self.log("⚠️ Invalid provider not caught")
                
            tester.cleanup()
            
        except Exception as e:
            self.log(f"Edge case test failed: {e}", "ERROR")
        
        duration = time.time() - start_time
        
        result = {
            'success': edge_cases_passed == total_edge_cases and total_edge_cases > 0,
            'duration': duration,
            'passed': edge_cases_passed,
            'total': total_edge_cases
        }
        
        print(f"Edge case tests: {edge_cases_passed}/{total_edge_cases} passed ({duration:.2f}s)")
        return result
    
    def generate_overall_report(self) -> str:
        """Generate comprehensive test report"""
        total_duration = time.time() - self.start_time
        
        report = []
        report.append("SubtitleToolkit JSONL Implementation - Test Report")
        report.append("=" * 60)
        report.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Total Duration: {total_duration:.2f} seconds")
        report.append("")
        
        # Executive Summary
        report.append("EXECUTIVE SUMMARY")
        report.append("-" * 20)
        
        all_passed = True
        test_summaries = []
        
        for test_type, result in self.results.items():
            success = result.get('success', False)
            duration = result.get('duration', 0)
            
            if success:
                test_summaries.append(f"✅ {test_type}: PASSED ({duration:.1f}s)")
            else:
                test_summaries.append(f"❌ {test_type}: FAILED ({duration:.1f}s)")
                all_passed = False
        
        for summary in test_summaries:
            report.append(summary)
        
        report.append("")
        
        if all_passed:
            report.append("🎉 OVERALL RESULT: ALL TESTS PASSED")
            report.append("✅ JSONL implementation is working correctly")
            report.append("✅ Backward compatibility is maintained")
            report.append("✅ All scripts are functioning as expected")
        else:
            failed_tests = [name for name, result in self.results.items() if not result.get('success', False)]
            report.append(f"❌ OVERALL RESULT: {len(failed_tests)} TEST SUITE(S) FAILED")
            report.append(f"Failed suites: {', '.join(failed_tests)}")
        
        report.append("")
        
        # Detailed Results
        report.append("DETAILED RESULTS")
        report.append("-" * 20)
        
        for test_type, result in self.results.items():
            report.append(f"\n{test_type.upper()}:")
            
            if 'error' in result:
                report.append(f"  ❌ Critical Error: {result['error']}")
            else:
                # Schema tests
                if test_type == "schema_tests":
                    pass_count = result.get('pass_count', 0)
                    fail_count = result.get('fail_count', 0)
                    report.append(f"  Tests: {pass_count} passed, {fail_count} failed")
                
                # Functional tests
                elif test_type == "functional_tests":
                    total = result.get('total_scripts', 0)
                    successful = result.get('successful_scripts', 0)
                    report.append(f"  Scripts: {successful}/{total} working correctly")
                
                # Validation tests  
                elif test_type == "validation_tests":
                    total = result.get('total_tests', 0)
                    passed = result.get('passed_tests', 0)
                    report.append(f"  Tests: {passed}/{total} passed")
                
                # Edge case tests
                elif test_type == "edge_case_tests":
                    total = result.get('total', 0)
                    passed = result.get('passed', 0)
                    report.append(f"  Edge cases: {passed}/{total} handled correctly")
        
        # Recommendations
        report.append("\nRECOMMENDATIONS")
        report.append("-" * 20)
        
        if all_passed:
            report.append("✅ The JSONL implementation is ready for use!")
            report.append("✅ All scripts maintain backward compatibility")
            report.append("✅ Consider proceeding with GUI development")
        else:
            report.append("🔧 Address the failed tests before proceeding:")
            for test_type, result in self.results.items():
                if not result.get('success', False):
                    report.append(f"  - Review {test_type} results and fix identified issues")
            report.append("🔧 Re-run tests after making fixes")
        
        return "\n".join(report)
    
    def run_all_tests(self, skip_functional: bool = False, quick: bool = False) -> Dict[str, Any]:
        """Run all test suites"""
        print("Starting Comprehensive Test Suite for SubtitleToolkit JSONL Implementation")
        print("=" * 80)
        
        # Always run schema tests
        self.results['schema_tests'] = self.run_schema_tests()
        
        # Run functional tests unless skipped
        if not skip_functional:
            self.results['functional_tests'] = self.run_functional_tests()
        else:
            print("\n⏭️ Skipping functional tests (--skip-functional)")
        
        # Run validation tests
        self.results['validation_tests'] = self.run_validation_tests()
        
        # Run edge case tests unless quick mode
        if not quick:
            self.results['edge_case_tests'] = self.run_edge_case_tests()
        else:
            print("\n⏭️ Skipping edge case tests (--quick)")
        
        return self.results


def main():
    """Main test execution"""
    parser = argparse.ArgumentParser(
        description="Comprehensive test runner for SubtitleToolkit JSONL implementation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                     # Run all tests
  python run_tests.py --verbose           # Verbose output
  python run_tests.py --skip-functional   # Skip functional tests (faster)
  python run_tests.py --quick            # Skip edge cases (fastest)
        """
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--skip-functional",
        action="store_true", 
        help="Skip functional tests (useful for quick schema validation)"
    )
    
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick mode - skip edge case tests"
    )
    
    args = parser.parse_args()
    
    try:
        # Verify we're in the right directory
        scripts_dir = Path(__file__).parent / "scripts"
        if not scripts_dir.exists():
            print(f"❌ Scripts directory not found: {scripts_dir}")
            print(f"Please run this script from the SubtitleToolkit project root")
            return 1
        
        # Initialize test suite
        suite = TestSuite(verbose=args.verbose)
        
        # Run all tests
        results = suite.run_all_tests(
            skip_functional=args.skip_functional,
            quick=args.quick
        )
        
        # Generate and display report
        report = suite.generate_overall_report()
        print("\n" + "=" * 80)
        print(report)
        
        # Save report to file
        report_file = Path(__file__).parent / "comprehensive_test_report.txt"
        report_file.write_text(report)
        print(f"\n📄 Full report saved to: {report_file}")
        
        # Return appropriate exit code
        overall_success = all(result.get('success', False) for result in results.values())
        return 0 if overall_success else 1
        
    except KeyboardInterrupt:
        print("\n❌ Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Test runner failed: {e}")
        if args.verbose:
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())