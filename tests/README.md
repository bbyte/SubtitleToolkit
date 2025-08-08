# SubtitleToolkit Test Suite

This comprehensive test suite ensures the reliability, robustness, and cross-platform compatibility of the SubtitleToolkit desktop application. The test suite follows Test-Driven Development (TDD) principles and meets the Phase 4 quality assurance requirements.

## Overview

The test suite provides comprehensive coverage across multiple dimensions:

- **Unit Tests**: Individual component testing with 90%+ coverage
- **Integration Tests**: End-to-end workflow testing
- **Error Scenario Tests**: Edge cases and failure conditions
- **Cross-Platform Tests**: Windows, macOS, and Linux compatibility
- **Performance Tests**: Load testing and performance validation

## Test Structure

```
tests/
├── unit/                     # Unit tests for individual components
│   ├── test_jsonl_parser.py         # JSONL parser robustness testing
│   ├── test_config_manager.py       # Configuration management testing  
│   ├── test_dependency_checker.py   # Tool detection and validation
│   ├── test_script_runner.py        # Process orchestration testing
│   └── test_ui_components.py        # GUI component testing
├── integration/              # Integration tests for workflows
│   ├── test_extract_workflow.py     # MKV extraction pipeline
│   ├── test_translate_workflow.py   # Translation pipeline
│   ├── test_sync_workflow.py        # File synchronization pipeline
│   └── test_full_pipeline.py        # Complete Extract→Translate→Sync
├── error_scenarios/          # Error condition and edge case tests
│   └── test_missing_dependencies.py # Dependency failure scenarios
├── platform/                 # Cross-platform compatibility tests
│   └── test_cross_platform.py       # Windows/macOS/Linux testing
└── conftest.py               # Shared fixtures and test configuration
```

## Key Testing Areas

### 1. JSONL Parser Robustness
- Malformed JSON recovery
- Partial line buffering
- Stream interruption handling
- High-frequency data processing
- Unicode and encoding support

### 2. Configuration Management
- Settings validation and schema enforcement
- Persistence and loading mechanisms
- Default value handling
- Background tool detection
- Import/export functionality

### 3. Dependency Detection
- System tool detection (ffmpeg, ffprobe, mkvextract)
- Version parsing and comparison
- Path validation and security checks
- Cross-platform executable finding
- Installation guidance generation

### 4. Process Orchestration
- Subprocess lifecycle management
- JSONL event parsing and emission
- Qt signal/slot communication
- Process termination and cleanup
- Error propagation and handling

### 5. UI Component Testing
- Widget initialization and state management
- Signal/slot connections
- User interaction simulation
- Layout and sizing behavior
- Performance under load

### 6. Workflow Integration
- Extract workflow: MKV→SRT conversion
- Translate workflow: AI-powered translation
- Sync workflow: Intelligent file matching
- Full pipeline: End-to-end processing
- Error recovery and partial success handling

### 7. Error Scenarios
- Missing system dependencies
- Invalid configuration values
- Malformed input files
- Network failures and API errors
- Process interruption and cancellation

### 8. Cross-Platform Compatibility
- Path handling across Windows/macOS/Linux
- Executable detection mechanisms
- Configuration storage locations
- Subprocess execution behavior
- File system operations

## Running Tests

### Quick Start
```bash
# Run all tests with coverage
python run_comprehensive_tests.py --coverage

# Run specific test category
python run_comprehensive_tests.py --category unit

# Run smoke tests (fast validation)
python run_comprehensive_tests.py --category smoke
```

### Test Categories
```bash
# Unit tests (individual components)
python run_comprehensive_tests.py --category unit

# Integration tests (workflow testing)
python run_comprehensive_tests.py --category integration

# Error scenario tests
python run_comprehensive_tests.py --category error

# Cross-platform tests
python run_comprehensive_tests.py --category platform

# Performance tests
python run_comprehensive_tests.py --category performance --benchmark
```

### Advanced Usage
```bash
# Verbose output with detailed reporting
python run_comprehensive_tests.py --verbose --coverage

# Fast tests only (excludes slow integration tests)
python run_comprehensive_tests.py --fast

# Complete test suite with benchmarking
python run_comprehensive_tests.py --coverage --benchmark
```

### Using pytest directly
```bash
# Run specific test file
pytest tests/unit/test_jsonl_parser.py -v

# Run tests with specific marker
pytest -m "unit and not slow" -v

# Run with coverage
pytest --cov=app --cov-report=html --cov-report=term-missing

# Run specific test method
pytest tests/unit/test_config_manager.py::TestConfigManager::test_config_manager_initialization -v
```

## Test Markers

Tests are categorized using pytest markers:

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests  
- `@pytest.mark.error_scenario` - Error condition tests
- `@pytest.mark.platform` - Cross-platform tests
- `@pytest.mark.performance` - Performance tests
- `@pytest.mark.gui` - GUI component tests (requires QApplication)
- `@pytest.mark.slow` - Tests that take longer than 1 second
- `@pytest.mark.network` - Tests requiring network access (mocked by default)

## Test Configuration

The test suite uses `pytest.ini` for configuration:

- Minimum 90% test coverage requirement
- Comprehensive markers for test categorization
- HTML and XML coverage reporting
- Performance tracking with duration reporting
- Strict configuration validation

## Test Fixtures

Key fixtures provided in `conftest.py`:

- `qapp` - QApplication instance for GUI tests
- `temp_dir` - Temporary directory for file operations
- `sample_jsonl_events` - Valid JSONL test data
- `malformed_jsonl_data` - Invalid JSONL for robustness testing
- `sample_srt_files` - SRT files for translation testing
- `mock_api_responses` - Mocked translation service responses
- `qt_signal_tester` - Qt signal testing utilities
- `performance_tracker` - Performance measurement tools

## Coverage Requirements

The test suite maintains 90%+ code coverage as required by Phase 4:

- **Line Coverage**: 90%+ of code lines executed
- **Branch Coverage**: 85%+ of decision branches tested
- **Function Coverage**: 95%+ of functions called
- **File Coverage**: 100% of Python files included

Coverage reports are generated in multiple formats:
- HTML: `htmlcov/index.html`
- Terminal: Real-time coverage display
- XML: `coverage.xml` for CI/CD integration

## Continuous Integration

The test suite is designed for CI/CD integration:

```yaml
# Example GitHub Actions workflow
- name: Run Test Suite
  run: python run_comprehensive_tests.py --coverage
  
- name: Upload Coverage
  uses: codecov/codecov-action@v1
  with:
    file: ./coverage.xml
```

## Performance Benchmarks

Performance tests validate:

- JSONL parsing: < 2s for 1000 events
- UI updates: < 1s for 100 rapid updates  
- Workflow setup: < 2s for full pipeline
- Dependency detection: < 5s for bulk detection

## Best Practices

### Writing New Tests

1. **Follow TDD**: Write tests before implementation
2. **Use descriptive names**: Test method names should explain the scenario
3. **Single responsibility**: One test should verify one specific behavior
4. **Arrange-Act-Assert**: Structure tests clearly
5. **Mock dependencies**: Isolate units under test
6. **Test edge cases**: Include boundary conditions and error scenarios

### Test Organization

1. **Group related tests**: Use test classes for logical grouping
2. **Use appropriate markers**: Tag tests with correct categories
3. **Provide docstrings**: Explain complex test scenarios
4. **Keep tests fast**: Unit tests should complete in milliseconds
5. **Mock external dependencies**: Avoid network calls, file I/O in unit tests

### Error Testing

1. **Test failure modes**: Verify graceful error handling
2. **Test recovery**: Ensure system can recover from errors
3. **Test user guidance**: Verify helpful error messages
4. **Test edge cases**: Boundary conditions and malformed inputs
5. **Test resource cleanup**: Verify proper cleanup after failures

## Troubleshooting

### Common Issues

1. **QApplication errors**: Ensure GUI tests use `@pytest.mark.gui` and `qapp` fixture
2. **Path issues**: Use `temp_dir` fixture for file operations
3. **Signal testing**: Use `qt_signal_tester` fixture for Qt signal verification
4. **Performance timeouts**: Use `performance_tracker` to validate timing
5. **Platform differences**: Use appropriate platform markers and conditions

### Debug Mode

```bash
# Run with verbose output and no capture
pytest -v -s tests/unit/test_jsonl_parser.py

# Run single test with debugging
pytest --pdb tests/unit/test_config_manager.py::test_specific_function

# Run with coverage debugging
pytest --cov-report=term-missing --cov-fail-under=0 -v
```

## Contributing

When adding new features:

1. Write tests first (TDD approach)
2. Ensure 90%+ coverage for new code
3. Add appropriate test markers
4. Update test documentation
5. Verify cross-platform compatibility
6. Add error scenario tests
7. Include performance considerations

The comprehensive test suite ensures SubtitleToolkit maintains high quality and reliability across all supported platforms and use cases.