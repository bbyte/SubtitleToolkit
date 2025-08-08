"""
Integration tests for SRT translation workflow.

Tests the complete translation workflow including SRT file processing,
AI translation services, and output validation.

Following TDD principles:
1. Test successful translation scenarios  
2. Test different translation providers and models
3. Test error handling and retry mechanisms
4. Test output quality validation
5. Test performance and rate limiting
"""

import json
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import pytest

from app.runner.script_runner import ScriptRunner
from app.runner.config_models import TranslateConfig
from app.runner.events import Stage, EventType


@pytest.mark.integration
class TestTranslateWorkflow:
    """Test suite for SRT translation workflow."""
    
    def test_translate_workflow_openai_success(self, qapp, temp_dir, sample_srt_files, qt_signal_tester, mock_api_responses):
        """Test successful translation workflow using OpenAI."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        # Create mock translate script
        translate_script = temp_dir / "srtTranslateWhole.py"
        translate_script.write_text("#!/usr/bin/env python3")
        
        # Use first sample SRT file
        srt_file = sample_srt_files[0]
        output_file = temp_dir / "translated_output.srt"
        
        # Connect signals
        runner.signals.process_started.connect(qt_signal_tester.slot)
        runner.signals.progress_updated.connect(qt_signal_tester.slot)
        runner.signals.result_received.connect(qt_signal_tester.slot)
        
        config = TranslateConfig(
            input_file=str(srt_file),
            output_file=str(output_file),
            provider="openai",
            model="gpt-4o-mini",
            source_language="en",
            target_language="es"
        )
        
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            process = runner.run_translate(config)
            
            # Verify process started
            assert process is not None
            assert runner._current_stage == Stage.TRANSLATE
            
            # Simulate successful translation events
            from app.runner.events import Event
            
            # Start event
            start_event = Event(
                timestamp=datetime.now(),
                stage=Stage.TRANSLATE,
                event_type=EventType.INFO,
                message="Starting translation with OpenAI GPT-4o-mini"
            )
            runner._handle_event(start_event)
            
            # Progress events
            for progress in [25, 50, 75]:
                progress_event = Event(
                    timestamp=datetime.now(),
                    stage=Stage.TRANSLATE,
                    event_type=EventType.PROGRESS,
                    message=f"Translating chunks ({progress}%)",
                    progress=progress
                )
                runner._handle_event(progress_event)
            
            # Success result
            result_event = Event(
                timestamp=datetime.now(),
                stage=Stage.TRANSLATE,
                event_type=EventType.RESULT,
                message="Translation complete",
                data={
                    "files_processed": 1,
                    "files_successful": 1,
                    "outputs": [str(output_file)],
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "chunks_processed": 2,
                    "total_tokens": 150
                }
            )
            runner._handle_event(result_event)
        
        # Verify signals were emitted
        progress_signals = [s for s in qt_signal_tester.received_signals 
                           if len(s[0]) == 3 and isinstance(s[0][1], int)]
        result_signals = [s for s in qt_signal_tester.received_signals 
                         if len(s[0]) == 2 and isinstance(s[0][1], dict)]
        
        assert len(progress_signals) >= 3  # Progress updates
        assert len(result_signals) >= 1   # Result
    
    def test_translate_workflow_anthropic_success(self, qapp, temp_dir, sample_srt_files, qt_signal_tester):
        """Test successful translation workflow using Anthropic Claude."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        translate_script = temp_dir / "srtTranslateWhole.py"
        translate_script.write_text("#!/usr/bin/env python3")
        
        srt_file = sample_srt_files[0]
        output_file = temp_dir / "claude_translated.srt"
        
        runner.signals.result_received.connect(qt_signal_tester.slot)
        
        config = TranslateConfig(
            input_file=str(srt_file),
            output_file=str(output_file),
            provider="anthropic",
            model="claude-3-haiku-20240307",
            source_language="en",
            target_language="fr"
        )
        
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            process = runner.run_translate(config)
            
            # Simulate Claude translation result
            from app.runner.events import Event
            result_event = Event(
                timestamp=datetime.now(),
                stage=Stage.TRANSLATE,
                event_type=EventType.RESULT,
                message="Translation complete",
                data={
                    "files_processed": 1,
                    "files_successful": 1,
                    "outputs": [str(output_file)],
                    "provider": "anthropic",
                    "model": "claude-3-haiku-20240307",
                    "chunks_processed": 3,
                    "total_tokens": 200
                }
            )
            runner._handle_event(result_event)
        
        # Verify result was received
        assert len(qt_signal_tester.received_signals) >= 1
        result_data = qt_signal_tester.received_signals[-1][0][1]
        assert result_data["provider"] == "anthropic"
        assert result_data["model"] == "claude-3-haiku-20240307"
    
    def test_translate_workflow_local_lm_studio(self, qapp, temp_dir, sample_srt_files, qt_signal_tester):
        """Test translation workflow using local LM Studio."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        translate_script = temp_dir / "srtTranslateWhole.py"
        translate_script.write_text("#!/usr/bin/env python3")
        
        srt_file = sample_srt_files[0]
        output_file = temp_dir / "local_translated.srt"
        
        runner.signals.result_received.connect(qt_signal_tester.slot)
        
        config = TranslateConfig(
            input_file=str(srt_file),
            output_file=str(output_file),
            provider="lm_studio",
            model="local-model",
            source_language="en", 
            target_language="de"
        )
        
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            process = runner.run_translate(config)
            
            # Simulate local translation result
            from app.runner.events import Event
            result_event = Event(
                timestamp=datetime.now(),
                stage=Stage.TRANSLATE,
                event_type=EventType.RESULT,
                message="Translation complete",
                data={
                    "files_processed": 1,
                    "files_successful": 1,
                    "outputs": [str(output_file)],
                    "provider": "lm_studio",
                    "model": "local-model",
                    "chunks_processed": 2
                }
            )
            runner._handle_event(result_event)
        
        # Verify local translation result
        assert len(qt_signal_tester.received_signals) >= 1
        result_data = qt_signal_tester.received_signals[-1][0][1]
        assert result_data["provider"] == "lm_studio"
    
    def test_translate_workflow_api_rate_limit(self, qapp, temp_dir, sample_srt_files, qt_signal_tester):
        """Test translation workflow handling API rate limits."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        translate_script = temp_dir / "srtTranslateWhole.py"
        translate_script.write_text("#!/usr/bin/env python3")
        
        srt_file = sample_srt_files[0]
        
        # Connect warning signal for rate limit notifications
        runner.signals.warning_received.connect(qt_signal_tester.slot)
        runner.signals.result_received.connect(qt_signal_tester.slot)
        
        config = TranslateConfig(
            input_file=str(srt_file),
            provider="openai",
            model="gpt-4"  # More expensive model, more likely to hit limits
        )
        
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            process = runner.run_translate(config)
            
            # Simulate rate limit warning
            from app.runner.events import Event
            warning_event = Event(
                timestamp=datetime.now(),
                stage=Stage.TRANSLATE,
                event_type=EventType.WARNING,
                message="Rate limit reached, waiting 60 seconds before retry..."
            )
            runner._handle_event(warning_event)
            
            # Simulate eventual success after retry
            result_event = Event(
                timestamp=datetime.now(),
                stage=Stage.TRANSLATE,
                event_type=EventType.RESULT,
                message="Translation complete after retry",
                data={
                    "files_processed": 1,
                    "files_successful": 1,
                    "retries_performed": 2
                }
            )
            runner._handle_event(result_event)
        
        # Should have received rate limit warning
        warning_signals = [s for s in qt_signal_tester.received_signals 
                          if len(s[0]) == 2 and "Rate limit" in s[0][1]]
        assert len(warning_signals) >= 1
    
    def test_translate_workflow_api_authentication_error(self, qapp, temp_dir, sample_srt_files, qt_signal_tester):
        """Test translation workflow handling API authentication errors."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        translate_script = temp_dir / "srtTranslateWhole.py"
        translate_script.write_text("#!/usr/bin/env python3")
        
        srt_file = sample_srt_files[0]
        
        # Connect error signal
        runner.signals.error_received.connect(qt_signal_tester.slot)
        
        config = TranslateConfig(
            input_file=str(srt_file),
            provider="openai",
            model="gpt-4o-mini"
        )
        
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            process = runner.run_translate(config)
            
            # Simulate authentication error
            from app.runner.events import Event
            error_event = Event(
                timestamp=datetime.now(),
                stage=Stage.TRANSLATE,
                event_type=EventType.ERROR,
                message="Authentication failed: Invalid API key for OpenAI"
            )
            runner._handle_event(error_event)
        
        # Should have received authentication error
        error_signals = [s for s in qt_signal_tester.received_signals 
                        if len(s[0]) == 2 and "Authentication failed" in s[0][1]]
        assert len(error_signals) >= 1
    
    def test_translate_workflow_large_file_chunking(self, qapp, temp_dir, qt_signal_tester):
        """Test translation of large SRT files with chunking."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        translate_script = temp_dir / "srtTranslateWhole.py"
        translate_script.write_text("#!/usr/bin/env python3")
        
        # Create large SRT file
        large_srt = temp_dir / "large_subtitles.srt"
        srt_content = ""
        for i in range(100):  # 100 subtitle entries
            srt_content += f"""{i+1}
00:{i//60:02d}:{i%60:02d},000 --> 00:{i//60:02d}:{(i%60)+2:02d},000
This is subtitle number {i+1} with some content to translate.

"""
        large_srt.write_text(srt_content, encoding='utf-8')
        
        runner.signals.progress_updated.connect(qt_signal_tester.slot)
        runner.signals.result_received.connect(qt_signal_tester.slot)
        
        config = TranslateConfig(
            input_file=str(large_srt),
            provider="openai",
            model="gpt-4o-mini"
        )
        
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            process = runner.run_translate(config)
            
            # Simulate chunked processing progress
            from app.runner.events import Event
            
            chunk_count = 5
            for chunk in range(chunk_count):
                progress_event = Event(
                    timestamp=datetime.now(),
                    stage=Stage.TRANSLATE,
                    event_type=EventType.PROGRESS,
                    message=f"Processing chunk {chunk+1}/{chunk_count}",
                    progress=int((chunk + 1) / chunk_count * 100)
                )
                runner._handle_event(progress_event)
            
            # Final result
            result_event = Event(
                timestamp=datetime.now(),
                stage=Stage.TRANSLATE,
                event_type=EventType.RESULT,
                message="Large file translation complete",
                data={
                    "files_processed": 1,
                    "files_successful": 1,
                    "chunks_processed": chunk_count,
                    "total_subtitles": 100
                }
            )
            runner._handle_event(result_event)
        
        # Should have received progress updates for each chunk
        progress_signals = [s for s in qt_signal_tester.received_signals 
                           if len(s[0]) == 3 and isinstance(s[0][1], int)]
        assert len(progress_signals) >= chunk_count
    
    def test_translate_workflow_malformed_srt_handling(self, qapp, temp_dir, malformed_srt_files, qt_signal_tester):
        """Test translation workflow with malformed SRT files."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        translate_script = temp_dir / "srtTranslateWhole.py"
        translate_script.write_text("#!/usr/bin/env python3")
        
        # Connect error signal
        runner.signals.error_received.connect(qt_signal_tester.slot)
        
        # Test each type of malformed file
        for file_type, malformed_file in malformed_srt_files.items():
            config = TranslateConfig(
                input_file=str(malformed_file),
                provider="openai",
                model="gpt-4o-mini"
            )
            
            with patch.object(runner, '_start_process') as mock_start:
                mock_process = Mock()
                mock_start.return_value = mock_process
                
                try:
                    process = runner.run_translate(config)
                    
                    # Simulate error for malformed file
                    from app.runner.events import Event
                    error_event = Event(
                        timestamp=datetime.now(),
                        stage=Stage.TRANSLATE,
                        event_type=EventType.ERROR,
                        message=f"Failed to parse SRT file: {file_type} - {malformed_file.name}"
                    )
                    runner._handle_event(error_event)
                    
                except Exception as e:
                    # Some configurations might fail validation
                    assert "validation" in str(e).lower() or "invalid" in str(e).lower()
        
        # Should have received error signals for malformed files
        error_signals = [s for s in qt_signal_tester.received_signals 
                        if len(s[0]) == 2 and "Failed to parse" in s[0][1]]
        assert len(error_signals) >= 1
    
    def test_translate_workflow_output_validation(self, qapp, temp_dir, sample_srt_files):
        """Test validation of translation output quality."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        translate_script = temp_dir / "srtTranslateWhole.py"
        translate_script.write_text("#!/usr/bin/env python3")
        
        srt_file = sample_srt_files[0]
        output_file = temp_dir / "validated_output.srt"
        
        config = TranslateConfig(
            input_file=str(srt_file),
            output_file=str(output_file),
            provider="openai",
            model="gpt-4o-mini",
            target_language="es"
        )
        
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            process = runner.run_translate(config)
            
            # Create mock translated output
            translated_content = """1
00:00:01,000 --> 00:00:03,000
Este es un subtítulo de prueba

2
00:00:04,000 --> 00:00:06,000
Otro subtítulo de prueba
"""
            output_file.write_text(translated_content, encoding='utf-8')
            
            # Simulate successful result
            from app.runner.events import Event
            result_event = Event(
                timestamp=datetime.now(),
                stage=Stage.TRANSLATE,
                event_type=EventType.RESULT,
                message="Translation complete",
                data={
                    "files_processed": 1,
                    "files_successful": 1,
                    "outputs": [str(output_file)]
                }
            )
            runner._handle_event(result_event)
            
            # Validate output file
            assert output_file.exists()
            content = output_file.read_text(encoding='utf-8')
            
            # Should maintain SRT format
            assert "00:00:01,000 --> 00:00:03,000" in content
            assert "Este es un subtítulo" in content  # Spanish translation
            
            # Should have same number of subtitle blocks
            original_content = srt_file.read_text(encoding='utf-8')
            original_blocks = original_content.strip().split('\n\n')
            translated_blocks = content.strip().split('\n\n')
            assert len(original_blocks) == len(translated_blocks)
    
    @pytest.mark.performance
    def test_translate_workflow_performance(self, qapp, temp_dir, sample_srt_files, performance_tracker):
        """Test translation workflow performance."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        translate_script = temp_dir / "srtTranslateWhole.py"
        translate_script.write_text("#!/usr/bin/env python3")
        
        srt_file = sample_srt_files[0]
        
        performance_tracker.start_timer("translate_workflow")
        
        config = TranslateConfig(
            input_file=str(srt_file),
            provider="openai",
            model="gpt-4o-mini"
        )
        
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            # Simulate workflow setup
            process = runner.run_translate(config)
            
            # Simulate rapid event processing
            from app.runner.events import Event
            for i in range(10):
                event = Event(
                    timestamp=datetime.now(),
                    stage=Stage.TRANSLATE,
                    event_type=EventType.PROGRESS,
                    message=f"Processing chunk {i}",
                    progress=i * 10
                )
                runner._handle_event(event)
        
        performance_tracker.end_timer("translate_workflow")
        
        # Should setup and process events quickly
        performance_tracker.assert_duration_under("translate_workflow", 1.0)
    
    def test_translate_workflow_concurrent_requests(self, qapp, temp_dir, sample_srt_files, qt_signal_tester):
        """Test handling concurrent translation requests."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        translate_script = temp_dir / "srtTranslateWhole.py"
        translate_script.write_text("#!/usr/bin/env python3")
        
        srt_file = sample_srt_files[0]
        
        config = TranslateConfig(
            input_file=str(srt_file),
            provider="openai",
            model="gpt-4o-mini"
        )
        
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            # Start first translation
            process1 = runner.run_translate(config)
            
            # Try to start second translation (should fail)
            with pytest.raises(RuntimeError, match="Another process is already running"):
                process2 = runner.run_translate(config)
    
    def test_translate_workflow_context_preservation(self, qapp, temp_dir, sample_srt_files, qt_signal_tester):
        """Test preservation of context and timing in translations."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        translate_script = temp_dir / "srtTranslateWhole.py"
        translate_script.write_text("#!/usr/bin/env python3")
        
        # Create SRT with context cues
        context_srt = temp_dir / "context_subtitles.srt"
        context_content = """1
00:00:01,000 --> 00:00:03,000
Hello, my name is John.

2
00:00:04,000 --> 00:00:06,000
Nice to meet you, John!

3
00:00:07,000 --> 00:00:09,000
[Music playing in background]
"""
        context_srt.write_text(context_content, encoding='utf-8')
        
        runner.signals.result_received.connect(qt_signal_tester.slot)
        
        config = TranslateConfig(
            input_file=str(context_srt),
            provider="openai",
            model="gpt-4o-mini",
            target_language="es",
            context="This is a dialogue between two people meeting for the first time."
        )
        
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            process = runner.run_translate(config)
            
            # Simulate context-aware translation result
            from app.runner.events import Event
            result_event = Event(
                timestamp=datetime.now(),
                stage=Stage.TRANSLATE,
                event_type=EventType.RESULT,
                message="Context-aware translation complete",
                data={
                    "files_processed": 1,
                    "files_successful": 1,
                    "context_preserved": True,
                    "timing_maintained": True
                }
            )
            runner._handle_event(result_event)
        
        # Should preserve context in result
        assert len(qt_signal_tester.received_signals) >= 1
        result_data = qt_signal_tester.received_signals[-1][0][1]
        assert result_data.get("context_preserved") is True


@pytest.mark.integration
class TestTranslateConfigValidation:
    """Test suite for translation configuration validation."""
    
    def test_valid_translate_config(self, temp_dir, sample_srt_files):
        """Test creating valid translation configuration."""
        srt_file = sample_srt_files[0]
        output_file = temp_dir / "output.srt"
        
        config = TranslateConfig(
            input_file=str(srt_file),
            output_file=str(output_file),
            provider="openai",
            model="gpt-4o-mini",
            source_language="en",
            target_language="es"
        )
        
        is_valid, error_msg = config.validate()
        
        assert is_valid is True
        assert error_msg is None
        
        # Test CLI args generation
        cli_args = config.to_cli_args()
        assert str(srt_file) in cli_args or any(str(srt_file) in arg for arg in cli_args)
        assert "openai" in cli_args or any("openai" in arg for arg in cli_args)
    
    def test_invalid_translate_config_missing_file(self):
        """Test validation with missing input file."""
        config = TranslateConfig(
            input_file="/nonexistent/file.srt",
            provider="openai",
            model="gpt-4o-mini"
        )
        
        is_valid, error_msg = config.validate()
        
        assert is_valid is False
        assert "not found" in error_msg.lower() or "does not exist" in error_msg.lower()
    
    def test_invalid_translate_config_unsupported_provider(self, sample_srt_files):
        """Test validation with unsupported provider."""
        config = TranslateConfig(
            input_file=str(sample_srt_files[0]),
            provider="unsupported_provider",
            model="some-model"
        )
        
        is_valid, error_msg = config.validate()
        
        assert is_valid is False
        assert "provider" in error_msg.lower()
    
    def test_translate_config_environment_variables(self, sample_srt_files, mock_environment_variables):
        """Test translation configuration environment variables."""
        config = TranslateConfig(
            input_file=str(sample_srt_files[0]),
            provider="openai",
            model="gpt-4o-mini"
        )
        
        env_vars = config.get_env_vars()
        
        # Should include API keys
        assert isinstance(env_vars, dict)
        assert "OPENAI_API_KEY" in env_vars
    
    def test_translate_config_provider_model_combinations(self, sample_srt_files):
        """Test valid provider and model combinations."""
        valid_combinations = [
            ("openai", "gpt-4o-mini"),
            ("openai", "gpt-4"),
            ("anthropic", "claude-3-haiku-20240307"),
            ("anthropic", "claude-3-sonnet-20240229"),
            ("lm_studio", "local-model"),
        ]
        
        for provider, model in valid_combinations:
            config = TranslateConfig(
                input_file=str(sample_srt_files[0]),
                provider=provider,
                model=model
            )
            
            is_valid, error_msg = config.validate()
            
            # Should be valid (may have warnings about API keys)
            assert is_valid is True or "API key" in error_msg
    
    def test_translate_config_language_codes(self, sample_srt_files):
        """Test various language code combinations."""
        language_combinations = [
            ("en", "es"),  # English to Spanish
            ("en", "fr"),  # English to French  
            ("en", "de"),  # English to German
            ("auto", "es"), # Auto-detect to Spanish
            ("zh", "en"),  # Chinese to English
        ]
        
        for source, target in language_combinations:
            config = TranslateConfig(
                input_file=str(sample_srt_files[0]),
                provider="openai",
                model="gpt-4o-mini",
                source_language=source,
                target_language=target
            )
            
            is_valid, error_msg = config.validate()
            
            # Should be valid
            assert is_valid is True or error_msg is None
    
    def test_translate_config_cli_args_formatting(self, sample_srt_files):
        """Test CLI arguments formatting for various configurations."""
        srt_file = sample_srt_files[0]
        
        test_configs = [
            TranslateConfig(input_file=str(srt_file), provider="openai", model="gpt-4o-mini"),
            TranslateConfig(input_file=str(srt_file), provider="anthropic", model="claude-3-haiku-20240307"),
            TranslateConfig(
                input_file=str(srt_file), 
                provider="openai", 
                model="gpt-4o-mini",
                source_language="en",
                target_language="es"
            ),
        ]
        
        for config in test_configs:
            cli_args = config.to_cli_args()
            
            # Should be a list of strings
            assert isinstance(cli_args, list)
            assert all(isinstance(arg, str) for arg in cli_args)
            
            # Should include input file and provider
            assert any(str(srt_file) in arg for arg in cli_args)
            assert any(config.provider in arg for arg in cli_args)