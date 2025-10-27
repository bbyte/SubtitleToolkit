#!/usr/bin/env python3
"""
Integration test script for the ScriptRunner system.

This script tests the complete subprocess orchestration system including:
- Configuration creation and validation
- JSONL parsing
- Event handling
- Process management

Run this script to validate the implementation.
"""

import sys
import os
from pathlib import Path

# Add app directory to path
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir))

import tempfile
import json
from datetime import datetime, timezone
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from runner import ScriptRunner, ExtractConfig, TranslateConfig, SyncConfig
from runner.jsonl_parser import JSONLParser, JSONLValidator
from runner.events import Event, EventType, Stage


def test_config_validation():
    """Test configuration validation."""
    print("Testing configuration validation...")
    
    # Test ExtractConfig
    with tempfile.TemporaryDirectory() as temp_dir:
        config = ExtractConfig(input_directory=temp_dir)
        is_valid, error = config.validate()
        assert is_valid, f"ExtractConfig validation failed: {error}"
    
    # Test invalid directory
    config = ExtractConfig(input_directory="/nonexistent/directory")
    is_valid, error = config.validate()
    assert not is_valid, "ExtractConfig should fail validation for nonexistent directory"
    
    print("✓ Configuration validation tests passed")


def test_jsonl_parser():
    """Test JSONL parser functionality."""
    print("Testing JSONL parser...")
    
    parser = JSONLParser()
    
    # Test valid JSONL event
    valid_jsonl = json.dumps({
        "ts": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "stage": "extract",
        "type": "info",
        "msg": "Test message",
        "progress": 50,
        "data": {"test": "value"}
    })
    
    events = list(parser.parse_stream_data(valid_jsonl + '\n'))
    assert len(events) == 1
    event, error = events[0]
    assert event is not None, f"Failed to parse valid JSONL: {error}"
    assert event.message == "Test message"
    assert event.progress == 50
    
    # Test invalid JSON
    invalid_json = "invalid json line\n"
    events = list(parser.parse_stream_data(invalid_json))
    assert len(events) == 1
    event, error = events[0]
    assert event is None, "Should fail to parse invalid JSON"
    assert error is not None, "Should return error for invalid JSON"
    
    # Test partial lines
    partial_data = '{"ts": "'
    events = list(parser.parse_stream_data(partial_data))
    assert len(events) == 0, "Should not parse partial lines"
    
    # Complete the line
    complete_line = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z') + '", "stage": "extract", "type": "info", "msg": "Complete"}\n'
    events = list(parser.parse_stream_data(complete_line))
    assert len(events) == 1
    event, error = events[0]
    assert event is not None, f"Failed to parse completed line: {error}"
    
    print("✓ JSONL parser tests passed")


def test_jsonl_validator():
    """Test JSONL event validation."""
    print("Testing JSONL validation...")
    
    # Valid event
    valid_event = {
        "ts": "2025-08-08T07:42:01Z",
        "stage": "extract",
        "type": "info",
        "msg": "Test message"
    }
    
    is_valid, errors = JSONLValidator.validate_event_dict(valid_event)
    assert is_valid, f"Valid event failed validation: {errors}"
    
    # Missing required field
    invalid_event = {
        "ts": "2025-08-08T07:42:01Z",
        "stage": "extract",
        "type": "info"
        # Missing 'msg' field
    }
    
    is_valid, errors = JSONLValidator.validate_event_dict(invalid_event)
    assert not is_valid, "Event missing required field should fail validation"
    assert "Missing required field: msg" in errors
    
    # Invalid stage
    invalid_event = {
        "ts": "2025-08-08T07:42:01Z",
        "stage": "invalid_stage",
        "type": "info",
        "msg": "Test"
    }
    
    is_valid, errors = JSONLValidator.validate_event_dict(invalid_event)
    assert not is_valid, "Event with invalid stage should fail validation"
    
    print("✓ JSONL validation tests passed")


def test_cli_args_generation():
    """Test CLI arguments generation."""
    print("Testing CLI arguments generation...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test ExtractConfig
        extract_config = ExtractConfig(
            input_directory=temp_dir,
            language_code="spa",
            overwrite_existing=True
        )
        
        args = extract_config.to_cli_args()
        assert temp_dir in args
        assert "-l" in args
        assert "spa" in args
        assert "--overwrite" in args
        assert "--jsonl" in args
        
        # Test TranslateConfig
        translate_config = TranslateConfig(
            input_directory=temp_dir,
            source_language="es",
            target_language="en",
            provider="openai",
            model="gpt-4o-mini"
        )
        
        args = translate_config.to_cli_args()
        assert "-d" in args
        assert temp_dir in args
        assert "-s" in args
        assert "es" in args
        assert "-t" in args
        assert "en" in args
        assert "-p" in args
        assert "openai" in args
        assert "--jsonl" in args
    
    print("✓ CLI arguments generation tests passed")


def test_event_creation():
    """Test Event object creation and serialization."""
    print("Testing Event creation...")
    
    # Create event from JSON data
    json_data = {
        "ts": "2025-08-08T07:42:01Z",
        "stage": "translate",
        "type": "progress",
        "msg": "Processing chunk 1/5",
        "progress": 20,
        "data": {"chunk": 1, "total": 5}
    }
    
    event = Event.from_jsonl(json_data)
    assert event.stage == Stage.TRANSLATE
    assert event.event_type == EventType.PROGRESS
    assert event.message == "Processing chunk 1/5"
    assert event.progress == 20
    assert event.data == {"chunk": 1, "total": 5}
    
    # Test serialization back to dict
    serialized = event.to_dict()
    assert serialized["stage"] == "translate"
    assert serialized["type"] == "progress"
    assert serialized["progress"] == 20
    
    print("✓ Event creation tests passed")


def test_script_runner_paths():
    """Test ScriptRunner path detection."""
    print("Testing ScriptRunner path detection...")
    
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    
    runner = ScriptRunner()
    
    # Check if script directory is found
    script_dir = runner._script_dir
    assert script_dir.exists(), f"Script directory not found: {script_dir}"
    
    # Check for required scripts
    required_scripts = [
        "extract_mkv_subtitles.py",
        "srtTranslateWhole.py", 
        "srt_names_sync.py"
    ]
    
    for script in required_scripts:
        script_path = script_dir / script
        assert script_path.exists(), f"Required script not found: {script_path}"
    
    print(f"✓ ScriptRunner found scripts in: {script_dir}")


def main():
    """Run all integration tests."""
    print("Running ScriptRunner integration tests...\n")
    
    try:
        test_config_validation()
        test_jsonl_parser()
        test_jsonl_validator()
        test_cli_args_generation()
        test_event_creation()
        test_script_runner_paths()
        
        print("\n🎉 All integration tests passed!")
        print("\nThe ScriptRunner system is ready for use.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()