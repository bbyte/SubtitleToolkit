"""
Integration tests for full subtitle processing pipeline.

Tests the complete end-to-end workflow: Extract → Translate → Sync
with various combinations of configurations and error scenarios.

Following TDD principles:
1. Test successful full pipeline execution
2. Test pipeline with different stage combinations  
3. Test error propagation and recovery
4. Test performance and resource usage
5. Test pipeline state management
"""

import json
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import pytest

from app.runner.script_runner import ScriptRunner
from app.runner.config_models import ExtractConfig, TranslateConfig, SyncConfig
from app.runner.events import Stage, EventType, ProcessResult


@pytest.mark.integration
class TestFullPipeline:
    """Test suite for complete subtitle processing pipeline."""
    
    def test_full_pipeline_extract_translate_sync(self, qapp, temp_dir, qt_signal_tester):
        """Test complete pipeline: Extract → Translate → Sync."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        # Create mock scripts
        for script_name in ["extract_mkv_subtitles.py", "srtTranslateWhole.py", "srt_names_sync.py"]:
            script_file = temp_dir / script_name
            script_file.write_text("#!/usr/bin/env python3")
        
        # Create test MKV file
        mkv_file = temp_dir / "Test.Movie.2023.1080p.BluRay.mkv"
        mkv_file.write_bytes(b"fake mkv content with subtitles")
        
        # Connect signals to track pipeline progress
        runner.signals.process_started.connect(qt_signal_tester.slot)
        runner.signals.process_finished.connect(qt_signal_tester.slot)
        runner.signals.progress_updated.connect(qt_signal_tester.slot)
        runner.signals.result_received.connect(qt_signal_tester.slot)
        
        # Stage 1: Extract subtitles
        extract_config = ExtractConfig(
            input_directory=str(temp_dir),
            language="en",
            output_format="srt"
        )
        
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            # Run extraction
            process = runner.run_extract(extract_config)
            assert runner._current_stage == Stage.EXTRACT
            
            # Simulate extraction completion
            extracted_srt = temp_dir / "Test.Movie.2023.1080p.BluRay.srt"
            extracted_srt.write_text("""1
00:00:01,000 --> 00:00:03,000
Hello, this is a test subtitle.

2
00:00:04,000 --> 00:00:06,000
This will be translated to Spanish.
""")
            
            # Extract result
            from app.runner.events import Event
            extract_result = Event(
                timestamp=datetime.now(),
                stage=Stage.EXTRACT,
                event_type=EventType.RESULT,
                message="Extraction complete",
                data={
                    "files_processed": 1,
                    "files_successful": 1,
                    "outputs": [str(extracted_srt)]
                }
            )
            runner._handle_event(extract_result)
            
            # Simulate process completion
            runner._on_process_finished(0, Mock())
            
            # Wait for process to complete
            assert runner._current_stage is None  # Should be reset
        
        # Stage 2: Translate subtitles
        translate_config = TranslateConfig(
            input_file=str(extracted_srt),
            output_file=str(temp_dir / "Test.Movie.2023.1080p.BluRay.es.srt"),
            provider="openai",
            model="gpt-4o-mini",
            target_language="es"
        )
        
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            # Run translation
            process = runner.run_translate(translate_config)
            assert runner._current_stage == Stage.TRANSLATE
            
            # Create translated output
            translated_srt = temp_dir / "Test.Movie.2023.1080p.BluRay.es.srt"
            translated_srt.write_text("""1
00:00:01,000 --> 00:00:03,000
Hola, este es un subtítulo de prueba.

2
00:00:04,000 --> 00:00:06,000
Esto será traducido al español.
""")
            
            # Translation result
            translate_result = Event(
                timestamp=datetime.now(),
                stage=Stage.TRANSLATE,
                event_type=EventType.RESULT,
                message="Translation complete",
                data={
                    "files_processed": 1,
                    "files_successful": 1,
                    "outputs": [str(translated_srt)]
                }
            )
            runner._handle_event(translate_result)
            
            # Complete translation
            runner._on_process_finished(0, Mock())
            assert runner._current_stage is None
        
        # Stage 3: Sync files (rename for consistency)
        sync_config = SyncConfig(
            directory=str(temp_dir),
            provider="openai",
            model="gpt-4o-mini",
            dry_run=False
        )
        
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            # Run sync
            process = runner.run_sync(sync_config)
            assert runner._current_stage == Stage.SYNC
            
            # Sync result (files already properly named in this case)
            sync_result = Event(
                timestamp=datetime.now(),
                stage=Stage.SYNC,
                event_type=EventType.RESULT,
                message="Sync complete",
                data={
                    "files_processed": 3,  # MKV + 2 SRT files
                    "files_already_synced": 2,
                    "files_renamed": 0
                }
            )
            runner._handle_event(sync_result)
            
            # Complete sync
            runner._on_process_finished(0, Mock())
            assert runner._current_stage is None
        
        # Verify pipeline completed successfully
        result_signals = [s for s in qt_signal_tester.received_signals 
                         if len(s[0]) == 2 and isinstance(s[0][1], dict)]
        
        # Should have received results from all three stages
        assert len(result_signals) >= 3
        
        # Verify final outputs exist
        assert extracted_srt.exists()
        assert translated_srt.exists()
    
    def test_pipeline_extract_and_translate_only(self, qapp, temp_dir, qt_signal_tester):
        """Test pipeline with only Extract → Translate stages."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        # Create required scripts
        for script_name in ["extract_mkv_subtitles.py", "srtTranslateWhole.py"]:
            script_file = temp_dir / script_name
            script_file.write_text("#!/usr/bin/env python3")
        
        mkv_file = temp_dir / "Series.S01E01.1080p.WEB-DL.mkv"
        mkv_file.write_bytes(b"fake series episode")
        
        runner.signals.result_received.connect(qt_signal_tester.slot)
        
        # Extract stage
        extract_config = ExtractConfig(input_directory=str(temp_dir))
        
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            process = runner.run_extract(extract_config)
            
            # Create extraction output
            extracted_srt = temp_dir / "Series.S01E01.1080p.WEB-DL.srt"
            extracted_srt.write_text("1\n00:00:01,000 --> 00:00:03,000\nSeries dialogue here\n")
            
            from app.runner.events import Event
            extract_result = Event(
                timestamp=datetime.now(),
                stage=Stage.EXTRACT,
                event_type=EventType.RESULT,
                message="Extraction complete",
                data={"outputs": [str(extracted_srt)]}
            )
            runner._handle_event(extract_result)
            runner._on_process_finished(0, Mock())
        
        # Translate stage
        translate_config = TranslateConfig(
            input_file=str(extracted_srt),
            provider="anthropic",
            model="claude-3-haiku-20240307",
            target_language="fr"
        )
        
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            process = runner.run_translate(translate_config)
            
            # Create translation output
            translated_srt = temp_dir / "Series.S01E01.1080p.WEB-DL.fr.srt"
            translated_srt.write_text("1\n00:00:01,000 --> 00:00:03,000\nDialogue de série ici\n")
            
            translate_result = Event(
                timestamp=datetime.now(),
                stage=Stage.TRANSLATE,
                event_type=EventType.RESULT,
                message="Translation complete",
                data={"outputs": [str(translated_srt)]}
            )
            runner._handle_event(translate_result)
            runner._on_process_finished(0, Mock())
        
        # Should have received results from both stages
        result_signals = [s for s in qt_signal_tester.received_signals 
                         if len(s[0]) == 2 and isinstance(s[0][1], dict)]
        assert len(result_signals) >= 2
        
        # Verify outputs
        assert extracted_srt.exists()
        assert translated_srt.exists()
    
    def test_pipeline_translate_and_sync_only(self, qapp, temp_dir, sample_srt_files, qt_signal_tester):
        """Test pipeline with existing SRT files: Translate → Sync."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        # Create required scripts
        for script_name in ["srtTranslateWhole.py", "srt_names_sync.py"]:
            script_file = temp_dir / script_name
            script_file.write_text("#!/usr/bin/env python3")
        
        # Use existing SRT file and create corresponding MKV
        existing_srt = sample_srt_files[0]
        mkv_file = temp_dir / "Existing.Content.2023.mkv"
        mkv_file.write_bytes(b"existing content")
        
        # Copy SRT to temp_dir with different name for sync testing
        misnamed_srt = temp_dir / "misnamed_subtitles.srt"
        misnamed_srt.write_text(existing_srt.read_text())
        
        runner.signals.result_received.connect(qt_signal_tester.slot)
        
        # Translate stage
        translate_config = TranslateConfig(
            input_file=str(misnamed_srt),
            output_file=str(temp_dir / "translated_subtitles.srt"),
            provider="openai",
            model="gpt-4o-mini",
            target_language="de"
        )
        
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            process = runner.run_translate(translate_config)
            
            # Create translated output
            translated_srt = temp_dir / "translated_subtitles.srt"
            translated_srt.write_text("1\n00:00:01,000 --> 00:00:03,000\nDeutscher Untertitel\n")
            
            from app.runner.events import Event
            translate_result = Event(
                timestamp=datetime.now(),
                stage=Stage.TRANSLATE,
                event_type=EventType.RESULT,
                message="Translation complete",
                data={"outputs": [str(translated_srt)]}
            )
            runner._handle_event(translate_result)
            runner._on_process_finished(0, Mock())
        
        # Sync stage
        sync_config = SyncConfig(
            directory=str(temp_dir),
            provider="openai",
            model="gpt-4o-mini"
        )
        
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            process = runner.run_sync(sync_config)
            
            sync_result = Event(
                timestamp=datetime.now(),
                stage=Stage.SYNC,
                event_type=EventType.RESULT,
                message="Sync complete",
                data={
                    "files_processed": 3,
                    "rename_suggestions": [
                        {
                            "original": "translated_subtitles.srt",
                            "suggested": "Existing.Content.2023.srt",
                            "confidence": 0.91
                        }
                    ]
                }
            )
            runner._handle_event(sync_result)
            runner._on_process_finished(0, Mock())
        
        # Should have completed both stages
        result_signals = [s for s in qt_signal_tester.received_signals 
                         if len(s[0]) == 2 and isinstance(s[0][1], dict)]
        assert len(result_signals) >= 2
    
    def test_pipeline_error_propagation(self, qapp, temp_dir, qt_signal_tester):
        """Test error handling and propagation across pipeline stages."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        # Create scripts
        extract_script = temp_dir / "extract_mkv_subtitles.py"
        extract_script.write_text("#!/usr/bin/env python3")
        
        # Create problematic MKV file
        problematic_mkv = temp_dir / "corrupted.mkv"
        problematic_mkv.write_bytes(b"corrupted content")
        
        # Connect error signal
        runner.signals.error_received.connect(qt_signal_tester.slot)
        runner.signals.process_finished.connect(qt_signal_tester.slot)
        
        extract_config = ExtractConfig(input_directory=str(temp_dir))
        
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            process = runner.run_extract(extract_config)
            
            # Simulate extraction error
            from app.runner.events import Event
            error_event = Event(
                timestamp=datetime.now(),
                stage=Stage.EXTRACT,
                event_type=EventType.ERROR,
                message="Failed to extract subtitles from corrupted.mkv: Invalid file format"
            )
            runner._handle_event(error_event)
            
            # Simulate failed process completion
            runner._on_process_finished(1, Mock())  # Exit code 1 = failure
        
        # Should have received error and failure signals
        error_signals = [s for s in qt_signal_tester.received_signals 
                        if len(s[0]) == 2 and "Failed to extract" in s[0][1]]
        process_finished_signals = [s for s in qt_signal_tester.received_signals 
                                   if len(s[0]) == 1 and isinstance(s[0][0], ProcessResult)]
        
        assert len(error_signals) >= 1
        assert len(process_finished_signals) >= 1
        
        # Process should have failed
        if process_finished_signals:
            result = process_finished_signals[0][0][0]
            assert result.success is False
    
    def test_pipeline_partial_success(self, qapp, temp_dir, qt_signal_tester):
        """Test pipeline handling partial success scenarios."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        extract_script = temp_dir / "extract_mkv_subtitles.py"
        extract_script.write_text("#!/usr/bin/env python3")
        
        # Create multiple MKV files with mixed success
        good_mkv = temp_dir / "good_video.mkv"
        bad_mkv = temp_dir / "bad_video.mkv"
        
        good_mkv.write_bytes(b"good mkv content")
        bad_mkv.write_bytes(b"corrupted mkv")
        
        runner.signals.warning_received.connect(qt_signal_tester.slot)
        runner.signals.result_received.connect(qt_signal_tester.slot)
        
        extract_config = ExtractConfig(input_directory=str(temp_dir))
        
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            process = runner.run_extract(extract_config)
            
            # Simulate partial success
            from app.runner.events import Event
            
            # Warning for one file
            warning_event = Event(
                timestamp=datetime.now(),
                stage=Stage.EXTRACT,
                event_type=EventType.WARNING,
                message="No subtitle tracks found in bad_video.mkv"
            )
            runner._handle_event(warning_event)
            
            # Success for another file
            good_srt = temp_dir / "good_video.srt"
            good_srt.write_text("1\n00:00:01,000 --> 00:00:03,000\nExtracted subtitle\n")
            
            result_event = Event(
                timestamp=datetime.now(),
                stage=Stage.EXTRACT,
                event_type=EventType.RESULT,
                message="Extraction completed with warnings",
                data={
                    "files_processed": 2,
                    "files_successful": 1,
                    "files_failed": 1,
                    "outputs": [str(good_srt)]
                }
            )
            runner._handle_event(result_event)
            
            runner._on_process_finished(0, Mock())  # Overall success despite partial failure
        
        # Should have received warning and result
        warning_signals = [s for s in qt_signal_tester.received_signals 
                          if len(s[0]) == 2 and "No subtitle tracks" in s[0][1]]
        result_signals = [s for s in qt_signal_tester.received_signals 
                         if len(s[0]) == 2 and isinstance(s[0][1], dict)]
        
        assert len(warning_signals) >= 1
        assert len(result_signals) >= 1
        
        # Should show partial success
        result_data = result_signals[-1][0][1]
        assert result_data["files_successful"] == 1
        assert result_data["files_failed"] == 1
    
    def test_pipeline_resource_cleanup(self, qapp, temp_dir, qt_signal_tester):
        """Test proper resource cleanup after pipeline stages."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        extract_script = temp_dir / "extract_mkv_subtitles.py"
        extract_script.write_text("#!/usr/bin/env python3")
        
        mkv_file = temp_dir / "cleanup_test.mkv"
        mkv_file.write_bytes(b"test content")
        
        extract_config = ExtractConfig(input_directory=str(temp_dir))
        
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            # Start process
            process = runner.run_extract(extract_config)
            
            # Verify initial state
            assert runner._current_stage == Stage.EXTRACT
            assert runner._current_process is not None
            assert runner._current_config is not None
            
            # Complete process
            from app.runner.events import Event
            result_event = Event(
                timestamp=datetime.now(),
                stage=Stage.EXTRACT,
                event_type=EventType.RESULT,
                message="Extraction complete",
                data={"files_processed": 1}
            )
            runner._handle_event(result_event)
            
            runner._on_process_finished(0, Mock())
            
            # Verify cleanup
            assert runner._current_stage is None
            assert runner._current_process is None
            assert runner._current_config is None
            assert runner._aggregator is None
            assert runner._process_start_time is None
    
    def test_pipeline_interruption_and_cancellation(self, qapp, temp_dir, qt_signal_tester):
        """Test pipeline interruption and cancellation handling."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        extract_script = temp_dir / "extract_mkv_subtitles.py"
        extract_script.write_text("#!/usr/bin/env python3")
        
        mkv_file = temp_dir / "interrupt_test.mkv"
        mkv_file.write_bytes(b"content")
        
        runner.signals.process_cancelled.connect(qt_signal_tester.slot)
        
        extract_config = ExtractConfig(input_directory=str(temp_dir))
        
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_process.state.return_value = Mock()  # Running state
            mock_start.return_value = mock_process
            
            # Start process
            process = runner.run_extract(extract_config)
            
            # Cancel process
            with patch.object(runner, 'terminate_process') as mock_terminate:
                mock_terminate.return_value = True
                
                runner.cancel_current_process()
                
                # Should have attempted termination
                mock_terminate.assert_called_once()
        
        # Should have emitted cancellation signal
        cancelled_signals = [s for s in qt_signal_tester.received_signals 
                            if len(s[0]) == 1 and s[0][0] == Stage.EXTRACT]
        assert len(cancelled_signals) >= 1
    
    @pytest.mark.performance
    def test_pipeline_performance_full_workflow(self, qapp, temp_dir, performance_tracker):
        """Test performance of complete pipeline workflow."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        # Create all required scripts
        for script_name in ["extract_mkv_subtitles.py", "srtTranslateWhole.py", "srt_names_sync.py"]:
            script_file = temp_dir / script_name
            script_file.write_text("#!/usr/bin/env python3")
        
        # Create test files
        mkv_file = temp_dir / "Performance.Test.2023.mkv"
        mkv_file.write_bytes(b"performance test content")
        
        performance_tracker.start_timer("full_pipeline_workflow")
        
        # Extract stage
        extract_config = ExtractConfig(input_directory=str(temp_dir))
        
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            # Simulate rapid pipeline execution
            process = runner.run_extract(extract_config)
            
            # Simulate quick completion
            from app.runner.events import Event
            extract_result = Event(
                timestamp=datetime.now(),
                stage=Stage.EXTRACT,
                event_type=EventType.RESULT,
                message="Quick extraction",
                data={"outputs": ["test.srt"]}
            )
            runner._handle_event(extract_result)
            runner._on_process_finished(0, Mock())
            
            # Translate stage
            translate_config = TranslateConfig(
                input_file="test.srt",
                provider="openai",
                model="gpt-4o-mini"
            )
            
            process = runner.run_translate(translate_config)
            translate_result = Event(
                timestamp=datetime.now(),
                stage=Stage.TRANSLATE,
                event_type=EventType.RESULT,
                message="Quick translation",
                data={"outputs": ["test_translated.srt"]}
            )
            runner._handle_event(translate_result)
            runner._on_process_finished(0, Mock())
            
            # Sync stage
            sync_config = SyncConfig(directory=str(temp_dir), provider="openai", model="gpt-4o-mini")
            
            process = runner.run_sync(sync_config)
            sync_result = Event(
                timestamp=datetime.now(),
                stage=Stage.SYNC,
                event_type=EventType.RESULT,
                message="Quick sync",
                data={"files_processed": 2}
            )
            runner._handle_event(sync_result)
            runner._on_process_finished(0, Mock())
        
        performance_tracker.end_timer("full_pipeline_workflow")
        
        # Pipeline setup and simulation should be fast
        performance_tracker.assert_duration_under("full_pipeline_workflow", 2.0)
    
    def test_pipeline_memory_usage_monitoring(self, qapp, temp_dir):
        """Test pipeline memory usage remains reasonable."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        extract_script = temp_dir / "extract_mkv_subtitles.py"
        extract_script.write_text("#!/usr/bin/env python3")
        
        # Create large-ish test file to simulate memory usage
        large_mkv = temp_dir / "large_test.mkv"
        large_mkv.write_bytes(b"x" * 10000)  # 10KB fake content
        
        extract_config = ExtractConfig(input_directory=str(temp_dir))
        
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            # Start and complete process
            process = runner.run_extract(extract_config)
            
            # Simulate many events to test memory usage
            from app.runner.events import Event
            for i in range(100):
                event = Event(
                    timestamp=datetime.now(),
                    stage=Stage.EXTRACT,
                    event_type=EventType.PROGRESS,
                    message=f"Processing chunk {i}",
                    progress=i
                )
                runner._handle_event(event)
            
            # Complete processing
            result_event = Event(
                timestamp=datetime.now(),
                stage=Stage.EXTRACT,
                event_type=EventType.RESULT,
                message="Processing complete",
                data={"files_processed": 1}
            )
            runner._handle_event(result_event)
            runner._on_process_finished(0, Mock())
        
        # Memory should be cleaned up
        assert runner._current_stage is None
        assert runner._aggregator is None
    
    def test_pipeline_concurrent_stage_prevention(self, qapp, temp_dir):
        """Test prevention of concurrent stage execution."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        extract_script = temp_dir / "extract_mkv_subtitles.py"
        extract_script.write_text("#!/usr/bin/env python3")
        
        mkv_file = temp_dir / "concurrent_test.mkv"
        mkv_file.write_bytes(b"test content")
        
        extract_config = ExtractConfig(input_directory=str(temp_dir))
        translate_config = TranslateConfig(input_file="test.srt", provider="openai", model="gpt-4o-mini")
        
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_process.state.return_value = Mock()  # Running state
            mock_start.return_value = mock_process
            
            # Start extraction
            process1 = runner.run_extract(extract_config)
            
            # Try to start translation while extraction is running
            with pytest.raises(RuntimeError, match="Another process is already running"):
                process2 = runner.run_translate(translate_config)
    
    def test_pipeline_state_consistency(self, qapp, temp_dir, qt_signal_tester):
        """Test pipeline maintains consistent state across stages."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        # Create scripts
        for script_name in ["extract_mkv_subtitles.py", "srtTranslateWhole.py"]:
            script_file = temp_dir / script_name
            script_file.write_text("#!/usr/bin/env python3")
        
        mkv_file = temp_dir / "state_test.mkv"
        mkv_file.write_bytes(b"test content")
        
        # Track all process lifecycle events
        runner.signals.process_started.connect(qt_signal_tester.slot)
        runner.signals.process_finished.connect(qt_signal_tester.slot)
        
        # Stage 1: Extract
        extract_config = ExtractConfig(input_directory=str(temp_dir))
        
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            process = runner.run_extract(extract_config)
            
            # Check state during extraction
            assert runner._current_stage == Stage.EXTRACT
            assert runner._current_config == extract_config
            
            # Complete extraction
            from app.runner.events import Event
            result_event = Event(
                timestamp=datetime.now(),
                stage=Stage.EXTRACT,
                event_type=EventType.RESULT,
                message="Complete",
                data={"outputs": ["test.srt"]}
            )
            runner._handle_event(result_event)
            runner._on_process_finished(0, Mock())
            
            # State should be reset
            assert runner._current_stage is None
            assert runner._current_config is None
        
        # Stage 2: Translate
        translate_config = TranslateConfig(input_file="test.srt", provider="openai", model="gpt-4o-mini")
        
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            process = runner.run_translate(translate_config)
            
            # Check state during translation
            assert runner._current_stage == Stage.TRANSLATE
            assert runner._current_config == translate_config
            
            # Complete translation
            result_event = Event(
                timestamp=datetime.now(),
                stage=Stage.TRANSLATE,
                event_type=EventType.RESULT,
                message="Complete",
                data={"outputs": ["test_translated.srt"]}
            )
            runner._handle_event(result_event)
            runner._on_process_finished(0, Mock())
            
            # State should be reset again
            assert runner._current_stage is None
            assert runner._current_config is None
        
        # Should have received start and finish signals for both stages
        start_signals = [s for s in qt_signal_tester.received_signals 
                        if len(s[0]) == 1 and isinstance(s[0][0], Stage)]
        finish_signals = [s for s in qt_signal_tester.received_signals 
                         if len(s[0]) == 1 and isinstance(s[0][0], ProcessResult)]
        
        assert len(start_signals) >= 2  # Extract + Translate starts
        assert len(finish_signals) >= 2  # Extract + Translate completions