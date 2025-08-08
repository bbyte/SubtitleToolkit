# SubtitleToolkit JSONL Implementation Testing Guide

This guide explains how to validate the JSONL implementation in the SubtitleToolkit scripts.

## Overview

The testing suite validates three critical aspects:

1. **JSONL Output Validation** - Ensures JSONL events conform to the specification
2. **Backward Compatibility** - Verifies normal console output still works
3. **Functionality Testing** - Tests actual script behavior with sample data

## Test Files

### Core Test Files

- `run_tests.py` - Main test runner (orchestrates all tests)
- `test_jsonl_validation.py` - Comprehensive JSONL validation tests
- `test_jsonl_schema.py` - Focused JSONL schema validation
- `test_functional.py` - Functional tests with sample data

## Quick Start

### Run All Tests
```bash
# Run comprehensive test suite
python run_tests.py

# Verbose output
python run_tests.py --verbose

# Quick validation (skip edge cases)
python run_tests.py --quick

# Schema validation only (fastest)
python run_tests.py --skip-functional --quick
```

### Run Individual Test Modules
```bash
# Schema validation only
python test_jsonl_schema.py

# Functional tests only
python test_functional.py

# Comprehensive validation
python test_jsonl_validation.py
```

## JSONL Schema Specification

The tests validate against this JSONL event schema:

```json
{
  "ts": "2024-01-01T12:00:00Z",     // ISO 8601 UTC timestamp (required)
  "stage": "extract|translate|sync", // Script stage (required)
  "type": "info|progress|warning|error|result", // Event type (required)
  "msg": "Human readable message",   // Message string (required)
  "progress": 50,                    // 0-100 percentage (optional)
  "data": {                         // Additional structured data (optional)
    "key": "value"
  }
}
```

## What the Tests Validate

### Schema Validation Tests
- ✅ Required fields are present (`ts`, `stage`, `type`, `msg`)
- ✅ Timestamp format is ISO 8601 UTC
- ✅ Stage values are valid (`extract`, `translate`, `sync`)
- ✅ Event types are valid (`info`, `progress`, `warning`, `error`, `result`)
- ✅ Progress values are 0-100
- ✅ Data field is dict or null
- ✅ Each line is valid JSON

### Functional Tests
- ✅ Scripts execute without critical errors
- ✅ JSONL mode generates valid events with `--jsonl` flag
- ✅ Normal mode preserves colored output without `--jsonl`
- ✅ Progress events show meaningful percentages
- ✅ Result events contain summary data
- ✅ No JSON output in normal mode
- ✅ ANSI colors and banners work in normal mode

### Backward Compatibility Tests
- ✅ All existing CLI arguments still work
- ✅ Scripts produce same output format in normal mode
- ✅ No breaking changes to script interfaces
- ✅ Error handling remains consistent

## Expected Test Results

### All Tests Passing
```
SubtitleToolkit JSONL Implementation - Test Report
============================================================

EXECUTIVE SUMMARY
✅ schema_tests: PASSED (0.5s)
✅ functional_tests: PASSED (15.2s)
✅ validation_tests: PASSED (12.8s)
✅ edge_case_tests: PASSED (3.1s)

🎉 OVERALL RESULT: ALL TESTS PASSED
✅ JSONL implementation is working correctly
✅ Backward compatibility is maintained
✅ All scripts are functioning as expected
```

### Interpreting Results

**Schema Tests**: Validate JSONL format compliance
- Should show multiple passes for valid events
- Should show expected failures for invalid events

**Functional Tests**: Test actual script execution
- May show warnings about missing API keys (expected)
- Should generate valid JSONL events even when scripts can't complete
- Should maintain colored output in normal mode

**Validation Tests**: Comprehensive integration testing
- Tests all three scripts in both modes
- Validates complete workflow scenarios

**Edge Case Tests**: Handle unusual scenarios
- Empty directories
- Invalid arguments
- Missing files

## Troubleshooting

### Common Issues

**Missing Dependencies**
```bash
pip install openai anthropic python-dotenv tqdm
```

**API Key Warnings**
API key warnings in functional tests are expected and don't indicate test failure.

**Permission Errors**
Ensure scripts are executable:
```bash
chmod +x scripts/*.py
```

**Import Errors**
Run tests from the project root directory:
```bash
cd /path/to/SubtitleToolkit
python run_tests.py
```

## Test Data

Tests automatically generate:
- Sample MKV files (dummy content)
- Sample SRT files with proper subtitle format
- Temporary directories for testing

No manual test data setup is required.

## Continuous Integration

For CI/CD pipelines:
```bash
# Quick validation suitable for CI
python run_tests.py --quick

# Exit code 0 = all tests passed
# Exit code 1 = one or more tests failed
```

## Next Steps

After all tests pass:
1. ✅ JSONL implementation is validated
2. ✅ Backward compatibility is confirmed
3. ✅ Ready for GUI development phase
4. ✅ Scripts can be used in production

## Manual Testing

You can also manually test the JSONL implementation:

```bash
# Test extract_mkv_subtitles.py with JSONL
python scripts/extract_mkv_subtitles.py /path/to/mkv/files --jsonl

# Test srtTranslateWhole.py with JSONL
python scripts/srtTranslateWhole.py -f sample.srt -p openai --jsonl

# Test srt_names_sync.py with JSONL
python scripts/srt_names_sync.py /path/to/files --provider openai --jsonl
```

Each should output one JSON object per line following the schema specification.