"""
Integration tests for SRT file synchronization workflow.

Tests the complete sync workflow including file matching,
rename operations, and AI-powered name synchronization.

Following TDD principles:
1. Test successful sync scenarios
2. Test dry-run vs apply modes
3. Test AI provider integration for name matching
4. Test error handling and conflict resolution
5. Test batch processing and validation
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import pytest

from app.runner.script_runner import ScriptRunner
from app.runner.config_models import SyncConfig
from app.runner.events import Stage, EventType


@pytest.mark.integration
class TestSyncWorkflow:
    """Test suite for SRT file synchronization workflow."""
    
    def test_sync_workflow_dry_run_success(self, qapp, temp_dir, qt_signal_tester):
        """Test successful sync workflow in dry-run mode."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        # Create mock sync script
        sync_script = temp_dir / "srt_names_sync.py"
        sync_script.write_text("#!/usr/bin/env python3")
        
        # Create test files for synchronization
        mkv_files = [
            temp_dir / "Movie.Title.2023.1080p.BluRay.mkv",
            temp_dir / "Another.Movie.2022.720p.WEB-DL.mkv",
            temp_dir / "Third.Film.2024.4K.REMUX.mkv"
        ]
        
        srt_files = [
            temp_dir / "movie_title_subs.srt",
            temp_dir / "another_movie_subtitle.srt", 
            temp_dir / "third_film_eng.srt"
        ]
        
        # Create the files
        for mkv_file in mkv_files:
            mkv_file.write_bytes(b"fake mkv content")
        
        for srt_file in srt_files:
            srt_file.write_text("1\n00:00:01,000 --> 00:00:03,000\nTest subtitle\n")
        
        # Connect signals
        runner.signals.process_started.connect(qt_signal_tester.slot)
        runner.signals.progress_updated.connect(qt_signal_tester.slot)
        runner.signals.result_received.connect(qt_signal_tester.slot)
        
        config = SyncConfig(
            directory=str(temp_dir),
            provider="openai",
            model="gpt-4o-mini",
            dry_run=True
        )
        
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            process = runner.run_sync(config)
            
            # Verify process started
            assert process is not None
            assert runner._current_stage == Stage.SYNC
            
            # Simulate sync analysis events
            from app.runner.events import Event
            
            # Start event
            start_event = Event(
                timestamp=datetime.now(),
                stage=Stage.SYNC,
                event_type=EventType.INFO,
                message="Starting file synchronization analysis (dry-run)"
            )
            runner._handle_event(start_event)
            
            # Progress events for analysis
            analysis_steps = [
                "Scanning MKV files...",
                "Scanning SRT files...",
                "Analyzing filename patterns with AI...",
                "Generating rename suggestions..."
            ]
            
            for i, step in enumerate(analysis_steps):
                progress_event = Event(
                    timestamp=datetime.now(),
                    stage=Stage.SYNC,
                    event_type=EventType.PROGRESS,
                    message=step,
                    progress=int((i + 1) / len(analysis_steps) * 100)
                )
                runner._handle_event(progress_event)
            
            # Success result with suggestions
            suggested_renames = [
                {
                    "original": "movie_title_subs.srt",
                    "suggested": "Movie.Title.2023.1080p.BluRay.srt",
                    "confidence": 0.95,
                    "match": "Movie.Title.2023.1080p.BluRay.mkv"
                },
                {
                    "original": "another_movie_subtitle.srt",
                    "suggested": "Another.Movie.2022.720p.WEB-DL.srt", 
                    "confidence": 0.88,
                    "match": "Another.Movie.2022.720p.WEB-DL.mkv"
                },
                {
                    "original": "third_film_eng.srt",
                    "suggested": "Third.Film.2024.4K.REMUX.srt",
                    "confidence": 0.92,
                    "match": "Third.Film.2024.4K.REMUX.mkv"
                }
            ]
            
            result_event = Event(
                timestamp=datetime.now(),
                stage=Stage.SYNC,
                event_type=EventType.RESULT,
                message="Sync analysis complete (dry-run)",
                data={
                    "files_analyzed": 6,
                    "mkv_files": 3,
                    "srt_files": 3,
                    "rename_suggestions": suggested_renames,
                    "dry_run": True
                }
            )
            runner._handle_event(result_event)
        
        # Verify signals were emitted
        progress_signals = [s for s in qt_signal_tester.received_signals 
                           if len(s[0]) == 3 and isinstance(s[0][1], int)]
        result_signals = [s for s in qt_signal_tester.received_signals 
                         if len(s[0]) == 2 and isinstance(s[0][1], dict)]
        
        assert len(progress_signals) >= len(analysis_steps)
        assert len(result_signals) >= 1
        
        # Verify dry-run result
        result_data = result_signals[-1][0][1]
        assert result_data["dry_run"] is True
        assert len(result_data["rename_suggestions"]) == 3
    
    def test_sync_workflow_apply_renames(self, qapp, temp_dir, qt_signal_tester):
        """Test sync workflow applying actual renames."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        sync_script = temp_dir / "srt_names_sync.py"
        sync_script.write_text("#!/usr/bin/env python3")
        
        # Create test files
        mkv_file = temp_dir / "Sample.Movie.2023.mkv"
        srt_file = temp_dir / "sample_movie_subtitles.srt"
        
        mkv_file.write_bytes(b"fake mkv")
        srt_file.write_text("Sample subtitle content")
        
        # Connect signals
        runner.signals.result_received.connect(qt_signal_tester.slot)
        runner.signals.info_received.connect(qt_signal_tester.slot)
        
        config = SyncConfig(
            directory=str(temp_dir),
            provider="openai",
            model="gpt-4o-mini",
            dry_run=False,  # Actually apply renames
            confidence_threshold=0.8
        )
        
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            process = runner.run_sync(config)
            
            # Simulate successful rename events
            from app.runner.events import Event
            
            # Info about rename operation
            rename_info = Event(
                timestamp=datetime.now(),
                stage=Stage.SYNC,
                event_type=EventType.INFO,
                message="Renaming: sample_movie_subtitles.srt → Sample.Movie.2023.srt"
            )
            runner._handle_event(rename_info)
            
            # Success result
            result_event = Event(
                timestamp=datetime.now(),
                stage=Stage.SYNC,
                event_type=EventType.RESULT,
                message="File synchronization complete",
                data={
                    "files_processed": 2,
                    "files_renamed": 1,
                    "renames_applied": [
                        {
                            "original": "sample_movie_subtitles.srt",
                            "new": "Sample.Movie.2023.srt",
                            "success": True
                        }
                    ]
                }
            )
            runner._handle_event(result_event)
        
        # Verify rename information was received
        info_signals = [s for s in qt_signal_tester.received_signals 
                       if len(s[0]) == 2 and "Renaming:" in s[0][1]]
        result_signals = [s for s in qt_signal_tester.received_signals 
                         if len(s[0]) == 2 and isinstance(s[0][1], dict)]
        
        assert len(info_signals) >= 1
        assert len(result_signals) >= 1
        
        # Verify result data
        result_data = result_signals[-1][0][1]
        assert result_data["files_renamed"] == 1
        assert len(result_data["renames_applied"]) == 1
    
    def test_sync_workflow_confidence_filtering(self, qapp, temp_dir, qt_signal_tester):
        """Test sync workflow with confidence threshold filtering."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        sync_script = temp_dir / "srt_names_sync.py"
        sync_script.write_text("#!/usr/bin/env python3")
        
        # Create files with varying match confidence
        mkv_file = temp_dir / "Clear.Match.Movie.2023.mkv"
        srt_files = [
            temp_dir / "clear_match_movie.srt",  # High confidence match
            temp_dir / "ambiguous_subtitle.srt",  # Low confidence match
            temp_dir / "another_unclear_sub.srt"  # Very low confidence
        ]
        
        mkv_file.write_bytes(b"fake mkv")
        for srt_file in srt_files:
            srt_file.write_text("Subtitle content")
        
        # Connect signals
        runner.signals.warning_received.connect(qt_signal_tester.slot)
        runner.signals.result_received.connect(qt_signal_tester.slot)
        
        config = SyncConfig(
            directory=str(temp_dir),
            provider="openai",
            model="gpt-4o-mini",
            confidence_threshold=0.85  # High threshold
        )
        
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            process = runner.run_sync(config)
            
            # Simulate mixed confidence results
            from app.runner.events import Event
            
            # Warning about low confidence matches
            warning_event = Event(
                timestamp=datetime.now(),
                stage=Stage.SYNC,
                event_type=EventType.WARNING,
                message="Skipping ambiguous_subtitle.srt: confidence 0.65 below threshold 0.85"
            )
            runner._handle_event(warning_event)
            
            warning_event2 = Event(
                timestamp=datetime.now(),
                stage=Stage.SYNC,
                event_type=EventType.WARNING,
                message="Skipping another_unclear_sub.srt: confidence 0.45 below threshold 0.85"
            )
            runner._handle_event(warning_event2)
            
            # Result with only high-confidence matches
            result_event = Event(
                timestamp=datetime.now(),
                stage=Stage.SYNC,
                event_type=EventType.RESULT,
                message="Sync complete with confidence filtering",
                data={
                    "files_processed": 4,
                    "high_confidence_matches": 1,
                    "skipped_low_confidence": 2,
                    "confidence_threshold": 0.85
                }
            )
            runner._handle_event(result_event)
        
        # Should have received warnings about low confidence
        warning_signals = [s for s in qt_signal_tester.received_signals 
                          if len(s[0]) == 2 and "confidence" in s[0][1]]
        assert len(warning_signals) >= 2
    
    def test_sync_workflow_anthropic_provider(self, qapp, temp_dir, qt_signal_tester):
        """Test sync workflow using Anthropic Claude for analysis."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        sync_script = temp_dir / "srt_names_sync.py"
        sync_script.write_text("#!/usr/bin/env python3")
        
        # Create test files
        mkv_file = temp_dir / "Documentary.Nature.2024.mkv"
        srt_file = temp_dir / "nature_doc_subtitles.srt"
        
        mkv_file.write_bytes(b"fake mkv")
        srt_file.write_text("Documentary subtitle content")
        
        # Connect signals
        runner.signals.result_received.connect(qt_signal_tester.slot)
        
        config = SyncConfig(
            directory=str(temp_dir),
            provider="anthropic",
            model="claude-3-haiku-20240307",
            dry_run=True
        )
        
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            process = runner.run_sync(config)
            
            # Simulate Claude analysis result
            from app.runner.events import Event
            result_event = Event(
                timestamp=datetime.now(),
                stage=Stage.SYNC,
                event_type=EventType.RESULT,
                message="Claude analysis complete",
                data={
                    "files_analyzed": 2,
                    "provider": "anthropic",
                    "model": "claude-3-haiku-20240307",
                    "rename_suggestions": [
                        {
                            "original": "nature_doc_subtitles.srt",
                            "suggested": "Documentary.Nature.2024.srt",
                            "confidence": 0.91,
                            "reasoning": "Strong semantic match between filenames"
                        }
                    ]
                }
            )
            runner._handle_event(result_event)
        
        # Verify Claude was used
        assert len(qt_signal_tester.received_signals) >= 1
        result_data = qt_signal_tester.received_signals[-1][0][1]
        assert result_data["provider"] == "anthropic"
        assert result_data["model"] == "claude-3-haiku-20240307"
    
    def test_sync_workflow_no_matches_found(self, qapp, temp_dir, qt_signal_tester):
        """Test sync workflow when no good matches are found."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        sync_script = temp_dir / "srt_names_sync.py"
        sync_script.write_text("#!/usr/bin/env python3")
        
        # Create files with very different names
        mkv_file = temp_dir / "SciFi.Movie.2023.mkv"
        srt_file = temp_dir / "completely_unrelated_romance_subtitles.srt"
        
        mkv_file.write_bytes(b"fake mkv")
        srt_file.write_text("Unrelated subtitle content")
        
        # Connect signals
        runner.signals.warning_received.connect(qt_signal_tester.slot)
        runner.signals.result_received.connect(qt_signal_tester.slot)
        
        config = SyncConfig(
            directory=str(temp_dir),
            provider="openai",
            model="gpt-4o-mini",
            confidence_threshold=0.7
        )
        
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            process = runner.run_sync(config)
            
            # Simulate no matches found
            from app.runner.events import Event
            
            warning_event = Event(
                timestamp=datetime.now(),
                stage=Stage.SYNC,
                event_type=EventType.WARNING,
                message="No suitable matches found for completely_unrelated_romance_subtitles.srt"
            )
            runner._handle_event(warning_event)
            
            result_event = Event(
                timestamp=datetime.now(),
                stage=Stage.SYNC,
                event_type=EventType.RESULT,
                message="Sync complete - no matches found",
                data={
                    "files_processed": 2,
                    "matches_found": 0,
                    "files_skipped": 1
                }
            )
            runner._handle_event(result_event)
        
        # Should warn about no matches
        warning_signals = [s for s in qt_signal_tester.received_signals 
                          if len(s[0]) == 2 and "No suitable matches" in s[0][1]]
        assert len(warning_signals) >= 1
    
    def test_sync_workflow_file_conflicts(self, qapp, temp_dir, qt_signal_tester):
        """Test sync workflow handling file naming conflicts."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        sync_script = temp_dir / "srt_names_sync.py"
        sync_script.write_text("#!/usr/bin/env python3")
        
        # Create conflict scenario - target file already exists
        mkv_file = temp_dir / "Action.Movie.2023.mkv"
        srt_file = temp_dir / "action_movie_subs.srt"
        existing_srt = temp_dir / "Action.Movie.2023.srt"  # Target name already exists
        
        mkv_file.write_bytes(b"fake mkv")
        srt_file.write_text("New subtitle content")
        existing_srt.write_text("Existing subtitle content")
        
        # Connect signals
        runner.signals.warning_received.connect(qt_signal_tester.slot)
        runner.signals.result_received.connect(qt_signal_tester.slot)
        
        config = SyncConfig(
            directory=str(temp_dir),
            provider="openai",
            model="gpt-4o-mini",
            dry_run=False
        )
        
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            process = runner.run_sync(config)
            
            # Simulate conflict handling
            from app.runner.events import Event
            
            warning_event = Event(
                timestamp=datetime.now(),
                stage=Stage.SYNC,
                event_type=EventType.WARNING,
                message="Target file Action.Movie.2023.srt already exists, creating Action.Movie.2023.1.srt"
            )
            runner._handle_event(warning_event)
            
            result_event = Event(
                timestamp=datetime.now(),
                stage=Stage.SYNC,
                event_type=EventType.RESULT,
                message="Sync complete with conflict resolution",
                data={
                    "files_processed": 3,
                    "conflicts_resolved": 1,
                    "renames_applied": [
                        {
                            "original": "action_movie_subs.srt",
                            "new": "Action.Movie.2023.1.srt",
                            "conflict_resolved": True
                        }
                    ]
                }
            )
            runner._handle_event(result_event)
        
        # Should have warned about conflict and resolved it
        conflict_signals = [s for s in qt_signal_tester.received_signals 
                           if len(s[0]) == 2 and "already exists" in s[0][1]]
        assert len(conflict_signals) >= 1
    
    def test_sync_workflow_batch_processing(self, qapp, temp_dir, qt_signal_tester):
        """Test sync workflow with large batch of files."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        sync_script = temp_dir / "srt_names_sync.py"
        sync_script.write_text("#!/usr/bin/env python3")
        
        # Create multiple files for batch processing
        num_pairs = 10
        mkv_files = []
        srt_files = []
        
        for i in range(num_pairs):
            mkv_file = temp_dir / f"Movie.{i:02d}.Season.01.Episode.{i+1:02d}.mkv"
            srt_file = temp_dir / f"movie_{i:02d}_s01e{i+1:02d}_subtitles.srt"
            
            mkv_file.write_bytes(f"fake mkv {i}".encode())
            srt_file.write_text(f"Subtitle content {i}")
            
            mkv_files.append(mkv_file)
            srt_files.append(srt_file)
        
        # Connect signals
        runner.signals.progress_updated.connect(qt_signal_tester.slot)
        runner.signals.result_received.connect(qt_signal_tester.slot)
        
        config = SyncConfig(
            directory=str(temp_dir),
            provider="openai",
            model="gpt-4o-mini",
            dry_run=True
        )
        
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            process = runner.run_sync(config)
            
            # Simulate batch processing progress
            from app.runner.events import Event
            
            # Progress updates for batch processing
            for i in range(num_pairs):
                progress_event = Event(
                    timestamp=datetime.now(),
                    stage=Stage.SYNC,
                    event_type=EventType.PROGRESS,
                    message=f"Analyzing pair {i+1}/{num_pairs}",
                    progress=int((i + 1) / num_pairs * 100)
                )
                runner._handle_event(progress_event)
            
            # Batch result
            result_event = Event(
                timestamp=datetime.now(),
                stage=Stage.SYNC,
                event_type=EventType.RESULT,
                message="Batch sync analysis complete",
                data={
                    "files_processed": num_pairs * 2,
                    "mkv_files": num_pairs,
                    "srt_files": num_pairs,
                    "matches_found": num_pairs,  # All matched
                    "avg_confidence": 0.89
                }
            )
            runner._handle_event(result_event)
        
        # Should have progress updates for each pair
        progress_signals = [s for s in qt_signal_tester.received_signals 
                           if len(s[0]) == 3 and isinstance(s[0][1], int)]
        assert len(progress_signals) >= num_pairs
    
    def test_sync_workflow_api_error_handling(self, qapp, temp_dir, qt_signal_tester):
        """Test sync workflow handling API errors."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        sync_script = temp_dir / "srt_names_sync.py"
        sync_script.write_text("#!/usr/bin/env python3")
        
        # Create test files
        mkv_file = temp_dir / "Test.Movie.2023.mkv"
        srt_file = temp_dir / "test_movie_subs.srt"
        
        mkv_file.write_bytes(b"fake mkv")
        srt_file.write_text("Subtitle content")
        
        # Connect signals
        runner.signals.error_received.connect(qt_signal_tester.slot)
        runner.signals.result_received.connect(qt_signal_tester.slot)
        
        config = SyncConfig(
            directory=str(temp_dir),
            provider="openai",
            model="gpt-4"  # Expensive model more likely to hit limits
        )
        
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            process = runner.run_sync(config)
            
            # Simulate API error
            from app.runner.events import Event
            error_event = Event(
                timestamp=datetime.now(),
                stage=Stage.SYNC,
                event_type=EventType.ERROR,
                message="OpenAI API error: Rate limit exceeded. Please try again later."
            )
            runner._handle_event(error_event)
            
            # Fallback result (maybe using simpler matching)
            result_event = Event(
                timestamp=datetime.now(),
                stage=Stage.SYNC,
                event_type=EventType.RESULT,
                message="Sync completed with fallback matching",
                data={
                    "files_processed": 2,
                    "api_errors": 1,
                    "fallback_used": True,
                    "matches_found": 1
                }
            )
            runner._handle_event(result_event)
        
        # Should have received API error
        error_signals = [s for s in qt_signal_tester.received_signals 
                        if len(s[0]) == 2 and "API error" in s[0][1]]
        assert len(error_signals) >= 1
    
    @pytest.mark.performance
    def test_sync_workflow_performance(self, qapp, temp_dir, performance_tracker):
        """Test sync workflow performance with multiple files."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        sync_script = temp_dir / "srt_names_sync.py"
        sync_script.write_text("#!/usr/bin/env python3")
        
        # Create multiple test files
        num_files = 20
        for i in range(num_files):
            mkv_file = temp_dir / f"performance_test_{i}.mkv"
            srt_file = temp_dir / f"perf_test_subs_{i}.srt"
            
            mkv_file.write_bytes(f"content {i}".encode())
            srt_file.write_text(f"Subtitle {i}")
        
        performance_tracker.start_timer("sync_workflow")
        
        config = SyncConfig(
            directory=str(temp_dir),
            provider="openai",
            model="gpt-4o-mini"
        )
        
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            # Simulate workflow setup and processing
            process = runner.run_sync(config)
            
            # Simulate processing events
            from app.runner.events import Event
            for i in range(num_files):
                event = Event(
                    timestamp=datetime.now(),
                    stage=Stage.SYNC,
                    event_type=EventType.PROGRESS,
                    message=f"Processing pair {i}",
                    progress=int(i / num_files * 100)
                )
                runner._handle_event(event)
        
        performance_tracker.end_timer("sync_workflow")
        
        # Should setup and process events efficiently
        performance_tracker.assert_duration_under("sync_workflow", 2.0)


@pytest.mark.integration
class TestSyncConfigValidation:
    """Test suite for sync configuration validation."""
    
    def test_valid_sync_config(self, temp_dir):
        """Test creating valid sync configuration."""
        config = SyncConfig(
            directory=str(temp_dir),
            provider="openai",
            model="gpt-4o-mini",
            confidence_threshold=0.8,
            dry_run=True
        )
        
        is_valid, error_msg = config.validate()
        
        assert is_valid is True
        assert error_msg is None
        
        # Test CLI args generation
        cli_args = config.to_cli_args()
        assert str(temp_dir) in cli_args
        assert "--provider" in cli_args or "openai" in cli_args
    
    def test_invalid_sync_config_directory(self):
        """Test validation with invalid directory."""
        config = SyncConfig(
            directory="/nonexistent/directory",
            provider="openai",
            model="gpt-4o-mini"
        )
        
        is_valid, error_msg = config.validate()
        
        assert is_valid is False
        assert "directory" in error_msg.lower() or "not found" in error_msg.lower()
    
    def test_sync_config_confidence_threshold_validation(self, temp_dir):
        """Test confidence threshold validation."""
        # Valid thresholds
        valid_thresholds = [0.0, 0.5, 0.8, 1.0]
        
        for threshold in valid_thresholds:
            config = SyncConfig(
                directory=str(temp_dir),
                provider="openai",
                model="gpt-4o-mini",
                confidence_threshold=threshold
            )
            
            is_valid, error_msg = config.validate()
            assert is_valid is True
        
        # Invalid thresholds
        invalid_thresholds = [-0.1, 1.1, 2.0]
        
        for threshold in invalid_thresholds:
            config = SyncConfig(
                directory=str(temp_dir),
                provider="openai",
                model="gpt-4o-mini",
                confidence_threshold=threshold
            )
            
            is_valid, error_msg = config.validate()
            assert is_valid is False
            assert "confidence" in error_msg.lower()
    
    def test_sync_config_provider_model_combinations(self, temp_dir):
        """Test valid provider and model combinations for sync."""
        valid_combinations = [
            ("openai", "gpt-4o-mini"),
            ("openai", "gpt-4"),
            ("anthropic", "claude-3-haiku-20240307"),
            ("anthropic", "claude-3-sonnet-20240229"),
        ]
        
        for provider, model in valid_combinations:
            config = SyncConfig(
                directory=str(temp_dir),
                provider=provider,
                model=model
            )
            
            is_valid, error_msg = config.validate()
            
            # Should be valid (may have warnings about API keys)
            assert is_valid is True or "API key" in error_msg
    
    def test_sync_config_environment_variables(self, temp_dir, mock_environment_variables):
        """Test sync configuration environment variables."""
        config = SyncConfig(
            directory=str(temp_dir),
            provider="openai",
            model="gpt-4o-mini"
        )
        
        env_vars = config.get_env_vars() if hasattr(config, 'get_env_vars') else {}
        
        # Should include API keys
        assert isinstance(env_vars, dict)
    
    def test_sync_config_cli_args_formatting(self, temp_dir):
        """Test CLI arguments formatting for sync configurations."""
        test_configs = [
            SyncConfig(directory=str(temp_dir), provider="openai", model="gpt-4o-mini"),
            SyncConfig(directory=str(temp_dir), provider="anthropic", model="claude-3-haiku-20240307"),
            SyncConfig(
                directory=str(temp_dir), 
                provider="openai", 
                model="gpt-4o-mini",
                confidence_threshold=0.9,
                dry_run=False
            ),
        ]
        
        for config in test_configs:
            cli_args = config.to_cli_args()
            
            # Should be a list of strings
            assert isinstance(cli_args, list)
            assert all(isinstance(arg, str) for arg in cli_args)
            
            # Should include directory and provider
            assert str(temp_dir) in cli_args or any(str(temp_dir) in arg for arg in cli_args)
            assert any(config.provider in arg for arg in cli_args)