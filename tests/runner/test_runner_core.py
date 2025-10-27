#!/usr/bin/env python3
"""
Core integration test script for the ScriptRunner system components (no Qt).

Tests the core functionality without importing Qt-dependent modules.
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

# Import specific modules to avoid Qt dependencies
sys.path.insert(0, str(app_dir / "runner"))
from config_models import ExtractConfig, TranslateConfig, SyncConfig
from jsonl_parser import JSONLValidator
from events import Event, EventType, Stage


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
    
    # Test TranslateConfig with valid setup
    with tempfile.TemporaryDirectory() as temp_dir:
        config = TranslateConfig(
            input_directory=temp_dir,
            provider="openai",
            model="gpt-4o-mini",
            api_key="test-key"
        )
        is_valid, error = config.validate()
        assert is_valid, f"TranslateConfig validation failed: {error}"
    
    # Test TranslateConfig missing API key
    config = TranslateConfig(
        input_directory=temp_dir,
        provider="openai",
        model="gpt-4o-mini",
        api_key=""
    )
    is_valid, error = config.validate()
    assert not is_valid, "TranslateConfig should fail without API key"
    
    print("✓ Configuration validation tests passed")


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
    
    # Test progress event validation
    progress_event = {
        "ts": "2025-08-08T07:42:01Z",
        "stage": "translate",
        "type": "progress",
        "msg": "Processing...",
        "progress": 50
    }
    
    is_valid, errors = JSONLValidator.validate_progress_event(progress_event)
    assert is_valid, f"Valid progress event failed validation: {errors}"
    
    # Progress event without progress field
    invalid_progress = {
        "ts": "2025-08-08T07:42:01Z",
        "stage": "translate",
        "type": "progress",
        "msg": "Processing..."
        # Missing progress field
    }
    
    is_valid, errors = JSONLValidator.validate_progress_event(invalid_progress)
    assert not is_valid, "Progress event without progress field should fail"
    
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
        
        # Test environment variables
        env_vars = extract_config.get_env_vars()
        assert isinstance(env_vars, dict)  # Should return empty dict
        
        # Test TranslateConfig
        translate_config = TranslateConfig(
            input_directory=temp_dir,
            source_language="es",
            target_language="en",
            provider="openai",
            model="gpt-4o-mini",
            api_key="test-key"
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
        
        # Test environment variables
        env_vars = translate_config.get_env_vars()
        assert "OPENAI_API_KEY" in env_vars
        assert env_vars["OPENAI_API_KEY"] == "test-key"
        
        # Test SyncConfig
        sync_config = SyncConfig(
            input_directory=temp_dir,
            provider="anthropic",
            model="claude-3-haiku-20240307",
            api_key="test-key",
            dry_run=False  # Test with execute mode
        )
        
        args = sync_config.to_cli_args()
        assert temp_dir in args
        assert "--provider" in args
        assert "anthropic" in args
        assert "--execute" in args  # Should have execute since dry_run=False
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
    
    # Test event without optional fields
    minimal_json = {
        "ts": "2025-08-08T07:42:01Z",
        "stage": "extract",
        "type": "info",
        "msg": "Simple message"
    }
    
    minimal_event = Event.from_jsonl(minimal_json)
    assert minimal_event.progress is None
    assert minimal_event.data is None
    
    print("✓ Event creation tests passed")


def test_comprehensive_scenarios():
    """Test comprehensive configuration scenarios."""
    print("Testing comprehensive scenarios...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create some test files
        srt_file = Path(temp_dir) / "test.srt"
        srt_file.write_text("1\n00:00:01,000 --> 00:00:03,000\nTest subtitle")
        
        # Test individual file translation
        translate_config = TranslateConfig(
            input_files=[str(srt_file)],
            provider="anthropic",
            model="claude-3-haiku-20240307",
            api_key="test-key",
            source_language="es",
            target_language="en"
        )
        
        is_valid, error = translate_config.validate()
        assert is_valid, f"Single file TranslateConfig validation failed: {error}"
        
        args = translate_config.to_cli_args()
        assert "-f" in args
        assert str(srt_file) in args
        
        # Test advanced configuration parameters
        advanced_config = TranslateConfig(
            input_directory=temp_dir,
            provider="lm_studio",
            model="local-model",
            base_url="http://localhost:1234/v1",
            api_key="lm-studio",
            temperature=0.7,
            max_tokens=2048,
            timeout=60,
            max_workers=2,
            chunk_size=10
        )
        
        is_valid, error = advanced_config.validate()
        assert is_valid, f"Advanced TranslateConfig validation failed: {error}"
        
        args = advanced_config.to_cli_args()
        assert "--temperature" in args
        assert "0.7" in args
        assert "--max-tokens" in args
        assert "2048" in args
        assert "--timeout" in args
        assert "60" in args
        
        # Test sync with custom template
        sync_config = SyncConfig(
            input_directory=temp_dir,
            provider="openai",
            model="gpt-4o",
            api_key="test-key",
            confidence_threshold=0.95,
            naming_template="{show_title} S{season:02d}E{episode:02d}"
        )
        
        is_valid, error = sync_config.validate()
        assert is_valid, f"Custom template SyncConfig validation failed: {error}"
        
        args = sync_config.to_cli_args()
        assert "--template" in args
        template_found = False
        for i, arg in enumerate(args):
            if arg == "--template" and i + 1 < len(args):
                template_found = "{show_title}" in args[i + 1]
                break
        assert template_found, "Custom template not found in arguments"
    
    print("✓ Comprehensive scenarios tests passed")


def test_error_conditions():
    """Test various error conditions and edge cases."""
    print("Testing error conditions...")
    
    # Test invalid JSON event creation
    try:
        invalid_json = {
            "ts": "invalid-timestamp",
            "stage": "extract",
            "type": "info",
            "msg": "Test"
        }
        Event.from_jsonl(invalid_json)
        assert False, "Should have raised ValueError for invalid timestamp"
    except ValueError:
        pass  # Expected
    
    # Test configuration with invalid parameters
    config = TranslateConfig(
        input_directory="/nonexistent",
        provider="invalid_provider",
        model="test-model",
        api_key="test"
    )
    is_valid, error = config.validate()
    assert not is_valid, "Should fail validation for invalid provider"
    assert "Invalid provider" in error
    
    # Test temperature out of range
    config = TranslateConfig(
        input_directory="/tmp",
        provider="openai",
        model="gpt-4",
        api_key="test",
        temperature=3.0  # Invalid, should be 0-2
    )
    is_valid, error = config.validate()
    assert not is_valid, "Should fail validation for temperature out of range"
    
    print("✓ Error conditions tests passed")


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
    print("Running ScriptRunner core component tests...\n")
    
    try:
        test_config_validation()
        test_jsonl_validator()
        test_cli_args_generation()
        test_event_creation()
        test_comprehensive_scenarios()
        test_error_conditions()
        test_script_paths()
        
        print("\n🎉 All core component tests passed!")
        print("\nThe ScriptRunner system components are working correctly:")
        print("  ✓ Configuration validation and CLI argument generation")
        print("  ✓ JSONL event validation and parsing")
        print("  ✓ Event creation and serialization")
        print("  ✓ Error handling and edge cases")
        print("  ✓ Required script files exist")
        print("\nNext steps:")
        print("  • Install PySide6 to test full Qt integration")
        print("  • Test with actual script execution")
        print("  • Integrate with desktop application UI")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()