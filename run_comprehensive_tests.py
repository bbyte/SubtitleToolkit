#!/usr/bin/env python3
"""
Comprehensive test runner for SubtitleToolkit.

This script runs the complete test suite with proper configuration,
coverage reporting, and result analysis following Phase 4 requirements.
"""

import sys
import os
import subprocess
import time
from pathlib import Path
import argparse
from typing import List, Optional


def run_test_category(category: str, markers: List[str], verbose: bool = False) -> bool:
    """Run a specific category of tests."""
    print(f"\n{'='*60}")
    print(f"Running {category} Tests")
    print(f"{'='*60}")
    
    cmd = [
        "python", "-m", "pytest",
        "--verbose" if verbose else "--tb=short",
        "--color=yes",
        "--durations=10",
    ]
    
    # Add markers
    if markers:
        for marker in markers:
            cmd.extend(["-m", marker])
    
    # Add coverage for unit and integration tests
    if any(m in ["unit", "integration"] for m in markers):
        cmd.extend([
            "--cov=app",
            "--cov-report=term-missing",
            f"--cov-report=html:htmlcov_{category.lower()}"
        ])
    
    start_time = time.time()
    
    try:
        result = subprocess.run(cmd, check=False)
        duration = time.time() - start_time
        
        if result.returncode == 0:
            print(f"\n✅ {category} tests PASSED in {duration:.1f}s")
            return True
        else:
            print(f"\n❌ {category} tests FAILED in {duration:.1f}s")
            return False
            
    except KeyboardInterrupt:
        print(f"\n⚠️  {category} tests INTERRUPTED")
        return False
    except Exception as e:
        print(f"\n💥 {category} tests ERROR: {e}")
        return False


def run_performance_tests(verbose: bool = False) -> bool:
    """Run performance tests with special configuration."""
    print(f"\n{'='*60}")
    print("Running Performance Tests")
    print(f"{'='*60}")
    
    cmd = [
        "python", "-m", "pytest",
        "--verbose" if verbose else "--tb=short",
        "--color=yes",
        "-m", "performance",
        "--durations=0",  # Show all durations
        "--benchmark-only" if "--benchmark" in sys.argv else "",
    ]
    
    # Remove empty strings
    cmd = [c for c in cmd if c]
    
    try:
        result = subprocess.run(cmd, check=False)
        
        if result.returncode == 0:
            print(f"\n✅ Performance tests PASSED")
            return True
        else:
            print(f"\n❌ Performance tests FAILED")
            return False
            
    except Exception as e:
        print(f"\n💥 Performance tests ERROR: {e}")
        return False


def generate_coverage_report():
    """Generate comprehensive coverage report."""
    print(f"\n{'='*60}")
    print("Generating Coverage Report")
    print(f"{'='*60}")
    
    try:
        # Combine coverage data if multiple runs
        subprocess.run(["python", "-m", "coverage", "combine"], check=False)
        
        # Generate HTML report
        subprocess.run([
            "python", "-m", "coverage", "html", 
            "--directory=htmlcov_combined",
            "--title=SubtitleToolkit Test Coverage"
        ], check=False)
        
        # Generate XML report for CI
        subprocess.run([
            "python", "-m", "coverage", "xml",
            "-o", "coverage.xml"
        ], check=False)
        
        # Show coverage summary
        result = subprocess.run([
            "python", "-m", "coverage", "report",
            "--show-missing"
        ], capture_output=True, text=True)
        
        print(result.stdout)
        
        print("\n📊 Coverage reports generated:")
        print(f"  - HTML: htmlcov_combined/index.html")
        print(f"  - XML:  coverage.xml")
        
        return True
        
    except Exception as e:
        print(f"💥 Coverage report generation ERROR: {e}")
        return False


def run_smoke_tests() -> bool:
    """Run quick smoke tests to verify basic functionality."""
    print(f"\n{'='*60}")
    print("Running Smoke Tests")
    print(f"{'='*60}")
    
    smoke_tests = [
        "tests/unit/test_jsonl_parser.py::TestJSONLParser::test_parser_initialization",
        "tests/unit/test_config_manager.py::TestConfigManager::test_config_manager_initialization",
        "tests/unit/test_dependency_checker.py::TestDependencyChecker::test_dependency_checker_initialization",
    ]
    
    cmd = [
        "python", "-m", "pytest",
        "--tb=short",
        "--color=yes",
        "-v"
    ] + smoke_tests
    
    try:
        result = subprocess.run(cmd, check=False, timeout=30)
        
        if result.returncode == 0:
            print("\n✅ Smoke tests PASSED")
            return True
        else:
            print("\n❌ Smoke tests FAILED")
            return False
            
    except subprocess.TimeoutExpired:
        print("\n⚠️  Smoke tests TIMED OUT")
        return False
    except Exception as e:
        print(f"\n💥 Smoke tests ERROR: {e}")
        return False


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="SubtitleToolkit Comprehensive Test Runner")
    parser.add_argument("--category", choices=["unit", "integration", "error", "platform", "performance", "smoke", "all"], 
                       default="all", help="Test category to run")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--fast", action="store_true", help="Run only fast tests")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("--benchmark", action="store_true", help="Include benchmark tests")
    
    args = parser.parse_args()
    
    print("🧪 SubtitleToolkit Comprehensive Test Suite")
    print(f"📂 Working Directory: {os.getcwd()}")
    print(f"🐍 Python: {sys.version}")
    print(f"⏰ Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Ensure we're in the right directory
    if not Path("app").exists() or not Path("tests").exists():
        print("❌ ERROR: Must be run from project root directory")
        sys.exit(1)
    
    results = {}
    
    if args.category == "smoke":
        results["smoke"] = run_smoke_tests()
    elif args.category == "unit":
        results["unit"] = run_test_category("Unit", ["unit"], args.verbose)
    elif args.category == "integration": 
        results["integration"] = run_test_category("Integration", ["integration"], args.verbose)
    elif args.category == "error":
        results["error"] = run_test_category("Error Scenarios", ["error_scenario"], args.verbose)
    elif args.category == "platform":
        results["platform"] = run_test_category("Platform", ["platform"], args.verbose)
    elif args.category == "performance":
        results["performance"] = run_performance_tests(args.verbose)
    elif args.category == "all":
        # Run all test categories
        if not args.fast:
            results["smoke"] = run_smoke_tests()
            if not results["smoke"]:
                print("💥 Smoke tests failed - stopping execution")
                sys.exit(1)
        
        # Core functionality tests
        results["unit"] = run_test_category("Unit", ["unit"], args.verbose)
        results["integration"] = run_test_category("Integration", ["integration"], args.verbose)
        
        # Specialized tests
        if not args.fast:
            results["error"] = run_test_category("Error Scenarios", ["error_scenario"], args.verbose)
            results["platform"] = run_test_category("Platform", ["platform"], args.verbose)
            
            if args.benchmark:
                results["performance"] = run_performance_tests(args.verbose)
    
    # Generate coverage report if requested
    if args.coverage and any(results.values()):
        generate_coverage_report()
    
    # Print summary
    print(f"\n{'='*60}")
    print("Test Results Summary")
    print(f"{'='*60}")
    
    total_categories = len(results)
    passed_categories = sum(1 for success in results.values() if success)
    
    for category, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {category.title()} Tests")
    
    print(f"\n📊 Overall: {passed_categories}/{total_categories} categories passed")
    
    if passed_categories == total_categories:
        print("\n🎉 ALL TESTS PASSED!")
        success_rate = 100.0
    else:
        print(f"\n⚠️  {total_categories - passed_categories} categories failed")
        success_rate = (passed_categories / total_categories) * 100
    
    print(f"📈 Success Rate: {success_rate:.1f}%")
    print(f"⏱️  Completed at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Exit with appropriate code
    if success_rate >= 90.0:  # Phase 4 requirement
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()