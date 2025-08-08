#!/usr/bin/env python3
"""
Simple integration test script for the ScriptRunner system (no Qt dependencies).

Tests core functionality without requiring PySide6.
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

# Import only non-Qt components
from runner.config_models import ExtractConfig, TranslateConfig, SyncConfig
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
    """Test JSONL parser functionality (non-Qt parts)."""
    print("Testing JSONL parser...")
    
    # Test valid JSONL event
    valid_jsonl = json.dumps({
        "ts": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "stage": "extract",
        "type": "info",
        "msg": "Test message",
        "progress": 50,
        "data": {"test": "value"}
    })
    
    # We can't test the full parser without Qt, but we can test the validation
    json_data = json.loads(valid_jsonl)
    event = Event.from_jsonl(json_data)
    
    assert event.message == "Test message"
    assert event.progress == 50
    assert event.stage == Stage.EXTRACT
    assert event.event_type == EventType.INFO
    
    print("✓ Event parsing tests passed")


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
            model="gpt-4o-mini",
            api_key="test-key"
        )
        
        # Validate first
        is_valid, error = translate_config.validate()
        assert is_valid, f"TranslateConfig validation failed: {error}"
        
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
        
        # Test environment variables
        env_vars = translate_config.get_env_vars()
        assert "OPENAI_API_KEY" in env_vars
        assert env_vars["OPENAI_API_KEY"] == "test-key"
    
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


def test_config_comprehensive():
    """Test comprehensive configuration scenarios."""
    print("Testing comprehensive configuration scenarios...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create some test files
        srt_file = Path(temp_dir) / "test.srt"
        srt_file.write_text("1\n00:00:01,000 --> 00:00:03,000\nTest subtitle")
        
        # Test SyncConfig
        sync_config = SyncConfig(
            input_directory=temp_dir,
            provider="anthropic",
            model="claude-3-haiku-20240307",
            api_key="test-key",
            dry_run=True,
            confidence_threshold=0.9
        )
        
        is_valid, error = sync_config.validate()
        assert is_valid, f"SyncConfig validation failed: {error}"
        
        args = sync_config.to_cli_args()
        assert temp_dir in args
        assert "--provider" in args
        assert "anthropic" in args
        assert "--confidence" in args
        assert "0.9" in args
        assert "--jsonl" in args
        # Should NOT have --execute since dry_run=True
        assert "--execute" not in args
        
        # Test with execute mode
        sync_config.dry_run = False
        args = sync_config.to_cli_args()
        assert "--execute" in args
        
        # Test environment variables
        env_vars = sync_config.get_env_vars()
        assert "ANTHROPIC_API_KEY" in env_vars
        assert env_vars["ANTHROPIC_API_KEY"] == "test-key"
    
    print("✓ Comprehensive configuration tests passed")


def test_script_paths():
    """Test that required script files exist."""
    print("Testing script file existence...")
    
    script_dir = Path(__file__).parent / "scripts"
    
    required_scripts = [
        "extract_mkv_subtitles.py",
        "srtTranslateWhole.py", 
        "srt_names_sync.py"
    ]
    
    for script in required_scripts:
        script_path = script_dir / script
        assert script_path.exists(), f"Required script not found: {script_path}"
    
    print(f"✓ All required scripts found in: {script_dir}")


def main():
    """Run all integration tests."""
    print("Running ScriptRunner integration tests (non-Qt)...\n")
    
    try:
        test_config_validation()
        test_jsonl_parser()
        test_jsonl_validator()
        test_cli_args_generation()
        test_event_creation()
        test_config_comprehensive()
        test_script_paths()
        
        print("\n🎉 All integration tests passed!")
        print("\nThe ScriptRunner system core components are working correctly.")
        print("Note: Full Qt integration testing requires PySide6 installation.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()