"""
Unit tests for script runner functionality.

Tests the ScriptRunner class for subprocess orchestration, JSONL parsing,
Qt signal emission, and process lifecycle management.

Following TDD principles:
1. Test process lifecycle management
2. Test JSONL stream parsing and event handling
3. Test Qt signal emission
4. Test error handling and recovery
5. Test process termination and cleanup
"""

import sys
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import pytest
from PySide6.QtCore import QProcess, QObject, QTimer

from app.runner.script_runner import ScriptRunner
from app.runner.config_models import ExtractConfig, TranslateConfig, SyncConfig
from app.runner.events import Event, EventType, Stage, ProcessResult


@pytest.mark.unit
@pytest.mark.gui
class TestScriptRunner:
    """Test suite for ScriptRunner core functionality."""
    
    def test_script_runner_initialization(self, qapp):
        """Test ScriptRunner initializes correctly."""
        runner = ScriptRunner()
        
        assert runner.signals is not None
        assert runner._current_process is None
        assert runner._current_stage is None
        assert runner._current_config is None
        assert runner._parser is not None
        assert runner._aggregator is None
        assert runner._process_start_time is None
        assert runner._termination_timer is not None
        assert runner._logger is not None
        assert runner._script_dir is not None
    
    def test_is_running_property(self, qapp, mock_process):
        """Test is_running property correctly identifies running state."""
        runner = ScriptRunner()
        
        # Initially not running
        assert runner.is_running is False
        
        # Mock running process
        mock_process.state.return_value = QProcess.Running
        runner._current_process = mock_process
        
        assert runner.is_running is True
        
        # Mock stopped process
        mock_process.state.return_value = QProcess.NotRunning
        
        assert runner.is_running is False
    
    def test_current_stage_property(self, qapp):
        """Test current_stage property."""
        runner = ScriptRunner()
        
        # Initially no current stage
        assert runner.current_stage is None
        
        # Set current stage
        runner._current_stage = Stage.EXTRACT
        
        assert runner.current_stage == Stage.EXTRACT
    
    def test_script_directory_detection(self, qapp, temp_dir):
        """Test script directory detection logic."""
        runner = ScriptRunner()
        
        # Should find a script directory
        script_dir = runner._script_dir
        assert isinstance(script_dir, Path)
        
        # Test with mocked paths
        with patch('pathlib.Path.exists') as mock_exists:
            with patch('pathlib.Path.is_dir') as mock_is_dir:
                mock_exists.return_value = True
                mock_is_dir.return_value = True
                
                # Mock script files existence
                with patch('pathlib.Path.__truediv__') as mock_div:
                    mock_script = Mock()
                    mock_script.exists.return_value = True
                    mock_div.return_value = mock_script
                    
                    runner = ScriptRunner()
                    assert runner._script_dir is not None
    
    @patch('app.runner.script_runner.sys.executable', '/usr/bin/python3')
    def test_run_extract_success(self, qapp, temp_dir, qt_signal_tester):
        """Test successful extract process execution."""
        runner = ScriptRunner()
        
        # Mock script directory
        runner._script_dir = temp_dir
        
        # Create mock extract script
        extract_script = temp_dir / "extract_mkv_subtitles.py"
        extract_script.write_text("# Mock script")
        
        # Create valid extract config
        config = ExtractConfig(
            input_directory=str(temp_dir),
            language="en"
        )
        
        # Connect signals
        runner.signals.process_started.connect(qt_signal_tester.slot)
        
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            result_process = runner.run_extract(config)
            
            assert result_process == mock_process
            mock_start.assert_called_once()
            
            # Verify stage was set
            assert runner._current_stage == Stage.EXTRACT
            assert runner._current_config == config
    
    def test_run_extract_invalid_config(self, qapp, temp_dir):
        """Test extract execution with invalid configuration."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        # Create invalid config (missing required fields)
        config = ExtractConfig()  # No input directory
        
        with pytest.raises(RuntimeError, match="Configuration validation failed"):
            runner.run_extract(config)
    
    def test_run_extract_already_running(self, qapp, temp_dir, mock_process):
        """Test extract execution when another process is running."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        # Set up running process
        mock_process.state.return_value = QProcess.Running
        runner._current_process = mock_process
        
        config = ExtractConfig(input_directory=str(temp_dir))
        
        with pytest.raises(RuntimeError, match="Another process is already running"):
            runner.run_extract(config)
    
    def test_run_translate_success(self, qapp, temp_dir, qt_signal_tester):
        """Test successful translate process execution."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        # Create mock translate script
        translate_script = temp_dir / "srtTranslateWhole.py"
        translate_script.write_text("# Mock script")
        
        # Create valid translate config
        srt_file = temp_dir / "test.srt"
        srt_file.write_text("Sample SRT content")
        
        config = TranslateConfig(
            input_file=str(srt_file),
            provider="openai",
            model="gpt-4o-mini"
        )
        
        # Connect signals
        runner.signals.process_started.connect(qt_signal_tester.slot)
        
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            result_process = runner.run_translate(config)
            
            assert result_process == mock_process
            assert runner._current_stage == Stage.TRANSLATE
    
    def test_run_sync_success(self, qapp, temp_dir, qt_signal_tester):
        """Test successful sync process execution."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        # Create mock sync script
        sync_script = temp_dir / "srt_names_sync.py"
        sync_script.write_text("# Mock script")
        
        # Create valid sync config
        config = SyncConfig(
            directory=str(temp_dir),
            provider="openai"
        )
        
        # Connect signals
        runner.signals.process_started.connect(qt_signal_tester.slot)
        
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            result_process = runner.run_sync(config)
            
            assert result_process == mock_process
            assert runner._current_stage == Stage.SYNC
    
    def test_start_process_success(self, qapp, temp_dir, mock_process):
        """Test successful process start."""
        runner = ScriptRunner()
        
        command = [sys.executable, "-c", "print('hello')"]
        env_vars = {"TEST_VAR": "test_value"}
        
        # Mock QProcess creation and setup
        with patch('PySide6.QtCore.QProcess') as MockQProcess:
            MockQProcess.return_value = mock_process
            
            process = runner._start_process(command, env_vars)
            
            assert process == mock_process
            assert runner._current_process == mock_process
            
            # Verify process setup
            mock_process.setEnvironment.assert_called_once()
            mock_process.setWorkingDirectory.assert_called_once()
            mock_process.start.assert_called_once()
    
    def test_start_process_failed_to_start(self, qapp, temp_dir, mock_process):
        """Test process start failure."""
        runner = ScriptRunner()
        
        command = [sys.executable, "-c", "print('hello')"]
        env_vars = {}
        
        # Mock process that fails to start
        mock_process.waitForStarted.return_value = False
        mock_process.errorString.return_value = "Failed to start"
        
        with patch('PySide6.QtCore.QProcess') as MockQProcess:
            MockQProcess.return_value = mock_process
            
            with pytest.raises(RuntimeError, match="Failed to start process"):
                runner._start_process(command, env_vars)
    
    def test_process_stdout_handling(self, qapp, temp_dir, mock_process, qt_signal_tester):
        """Test processing of stdout data from subprocess."""
        runner = ScriptRunner()
        runner._current_process = mock_process
        
        # Connect signals
        runner.signals.process_output_received.connect(qt_signal_tester.slot)
        runner.signals.event_received.connect(qt_signal_tester.slot)
        
        # Mock stdout data
        mock_data = Mock()
        mock_data.data.return_value.decode.return_value = '{"ts": "2025-08-08T07:42:01Z", "stage": "extract", "type": "info", "msg": "Test message"}\n'
        mock_process.readAllStandardOutput.return_value = mock_data
        
        # Trigger stdout ready
        runner._on_stdout_ready()
        
        # Should have emitted signals
        assert len(qt_signal_tester.received_signals) >= 1
    
    def test_process_stderr_handling(self, qapp, temp_dir, mock_process, qt_signal_tester):
        """Test processing of stderr data from subprocess."""
        runner = ScriptRunner()
        runner._current_process = mock_process
        
        # Connect signals
        runner.signals.process_error_received.connect(qt_signal_tester.slot)
        
        # Mock stderr data
        mock_data = Mock()
        mock_data.data.return_value.decode.return_value = "Error message\n"
        mock_process.readAllStandardError.return_value = mock_data
        
        # Trigger stderr ready
        runner._on_stderr_ready()
        
        # Should have emitted error signal
        assert len(qt_signal_tester.received_signals) >= 1
        assert qt_signal_tester.received_signals[0][0] == ("Error message\n",)
    
    def test_process_finished_success(self, qapp, temp_dir, qt_signal_tester):
        """Test handling successful process completion."""
        runner = ScriptRunner()
        runner._current_stage = Stage.EXTRACT
        runner._process_start_time = datetime.now()
        
        # Connect signals
        runner.signals.process_finished.connect(qt_signal_tester.slot)
        
        # Mock successful completion
        exit_code = 0
        exit_status = QProcess.NormalExit
        
        runner._on_process_finished(exit_code, exit_status)
        
        # Should have emitted process finished signal with success
        assert len(qt_signal_tester.received_signals) == 1
        result = qt_signal_tester.received_signals[0][0][0]
        assert isinstance(result, ProcessResult)
        assert result.success is True
        assert result.exit_code == 0
        assert result.stage == Stage.EXTRACT
    
    def test_process_finished_failure(self, qapp, temp_dir, qt_signal_tester):
        """Test handling failed process completion."""
        runner = ScriptRunner()
        runner._current_stage = Stage.EXTRACT
        runner._process_start_time = datetime.now()
        
        # Connect signals
        runner.signals.process_finished.connect(qt_signal_tester.slot)
        
        # Mock failed completion
        exit_code = 1
        exit_status = QProcess.NormalExit
        
        runner._on_process_finished(exit_code, exit_status)
        
        # Should have emitted process finished signal with failure
        assert len(qt_signal_tester.received_signals) == 1
        result = qt_signal_tester.received_signals[0][0][0]
        assert isinstance(result, ProcessResult)
        assert result.success is False
        assert result.exit_code == 1
    
    def test_process_error_handling(self, qapp, temp_dir, qt_signal_tester):
        """Test handling process errors."""
        runner = ScriptRunner()
        runner._current_stage = Stage.EXTRACT
        
        # Connect signals
        runner.signals.process_failed.connect(qt_signal_tester.slot)
        
        # Mock process error
        error = QProcess.FailedToStart
        
        runner._on_process_error(error)
        
        # Should have emitted process failed signal
        assert len(qt_signal_tester.received_signals) == 1
        stage, error_msg = qt_signal_tester.received_signals[0][0]
        assert stage == Stage.EXTRACT
        assert "Failed to start process" in error_msg
    
    def test_event_handling_info(self, qapp, temp_dir, qt_signal_tester):
        """Test handling of info events."""
        runner = ScriptRunner()
        runner._current_stage = Stage.EXTRACT
        
        # Connect signals
        runner.signals.info_received.connect(qt_signal_tester.slot)
        
        # Create info event
        event = Event(
            timestamp=datetime.now(),
            stage=Stage.EXTRACT,
            event_type=EventType.INFO,
            message="Test info message"
        )
        
        runner._handle_event(event)
        
        # Should have emitted info signal
        assert len(qt_signal_tester.received_signals) == 1
        stage, message = qt_signal_tester.received_signals[0][0]
        assert stage == Stage.EXTRACT
        assert message == "Test info message"
    
    def test_event_handling_progress(self, qapp, temp_dir, qt_signal_tester):
        """Test handling of progress events."""
        runner = ScriptRunner()
        runner._current_stage = Stage.EXTRACT
        
        # Connect signals
        runner.signals.progress_updated.connect(qt_signal_tester.slot)
        
        # Create progress event
        event = Event(
            timestamp=datetime.now(),
            stage=Stage.EXTRACT,
            event_type=EventType.PROGRESS,
            message="Processing files",
            progress=50
        )
        
        runner._handle_event(event)
        
        # Should have emitted progress signal
        assert len(qt_signal_tester.received_signals) == 1
        stage, progress, message = qt_signal_tester.received_signals[0][0]
        assert stage == Stage.EXTRACT
        assert progress == 50
        assert message == "Processing files"
    
    def test_event_handling_result(self, qapp, temp_dir, qt_signal_tester):
        """Test handling of result events."""
        runner = ScriptRunner()
        runner._current_stage = Stage.EXTRACT
        
        # Connect signals
        runner.signals.result_received.connect(qt_signal_tester.slot)
        
        # Create result event
        result_data = {"files_processed": 5, "outputs": ["file1.srt", "file2.srt"]}
        event = Event(
            timestamp=datetime.now(),
            stage=Stage.EXTRACT,
            event_type=EventType.RESULT,
            message="Processing complete",
            data=result_data
        )
        
        runner._handle_event(event)
        
        # Should have emitted result signal
        assert len(qt_signal_tester.received_signals) == 1
        stage, data = qt_signal_tester.received_signals[0][0]
        assert stage == Stage.EXTRACT
        assert data == result_data
    
    def test_terminate_process_graceful(self, qapp, temp_dir, mock_process):
        """Test graceful process termination."""
        runner = ScriptRunner()
        runner._current_stage = Stage.EXTRACT
        
        # Mock running process
        mock_process.state.return_value = QProcess.Running
        mock_process.waitForFinished.return_value = True
        runner._current_process = mock_process
        
        success = runner.terminate_process(timeout=1)
        
        assert success is True
        mock_process.terminate.assert_called_once()
        mock_process.waitForFinished.assert_called_once()
    
    def test_terminate_process_force_kill(self, qapp, temp_dir, mock_process):
        """Test force killing process when graceful termination fails."""
        runner = ScriptRunner()
        runner._current_stage = Stage.EXTRACT
        
        # Mock running process that doesn't terminate gracefully
        mock_process.state.return_value = QProcess.Running
        mock_process.waitForFinished.side_effect = [False, True]  # First call fails, second succeeds
        runner._current_process = mock_process
        
        # Start termination - should trigger force kill via timer
        with patch.object(runner, '_force_kill_process') as mock_force_kill:
            mock_force_kill.return_value = True
            
            success = runner.terminate_process(timeout=1)
            
            # Should have attempted graceful termination
            mock_process.terminate.assert_called_once()
    
    def test_terminate_no_running_process(self, qapp, temp_dir):
        """Test termination when no process is running."""
        runner = ScriptRunner()
        
        success = runner.terminate_process()
        
        # Should return True (nothing to terminate)
        assert success is True
    
    def test_cancel_current_process(self, qapp, temp_dir, mock_process, qt_signal_tester):
        """Test cancelling current process."""
        runner = ScriptRunner()
        runner._current_stage = Stage.EXTRACT
        
        # Mock running process
        mock_process.state.return_value = QProcess.Running
        runner._current_process = mock_process
        
        # Connect signals
        runner.signals.process_cancelled.connect(qt_signal_tester.slot)
        
        with patch.object(runner, 'terminate_process') as mock_terminate:
            runner.cancel_current_process()
            
            # Should have emitted cancelled signal
            assert len(qt_signal_tester.received_signals) == 1
            stage = qt_signal_tester.received_signals[0][0][0]
            assert stage == Stage.EXTRACT
            
            # Should have attempted termination
            mock_terminate.assert_called_once()
    
    def test_get_process_info_not_running(self, qapp, temp_dir):
        """Test getting process info when not running."""
        runner = ScriptRunner()
        
        info = runner.get_process_info()
        
        assert info['running'] is False
        assert info['stage'] is None
        assert info['duration'] == 0
        assert info['progress'] == {}
    
    def test_get_process_info_running(self, qapp, temp_dir, mock_process):
        """Test getting process info when running."""
        runner = ScriptRunner()
        runner._current_stage = Stage.EXTRACT
        runner._process_start_time = datetime.now()
        
        # Mock running process
        mock_process.state.return_value = QProcess.Running
        runner._current_process = mock_process
        
        info = runner.get_process_info()
        
        assert info['running'] is True
        assert info['stage'] == 'extract'
        assert info['duration'] > 0
        assert 'progress' in info
        assert 'parser_stats' in info
    
    def test_cleanup_process(self, qapp, temp_dir, mock_process):
        """Test process cleanup functionality."""
        runner = ScriptRunner()
        runner._current_stage = Stage.EXTRACT
        runner._current_process = mock_process
        runner._process_start_time = datetime.now()
        
        # Mock aggregator
        mock_aggregator = Mock()
        runner._aggregator = mock_aggregator
        
        runner._cleanup_process()
        
        # Should clear all state
        assert runner._current_stage is None
        assert runner._current_process is None
        assert runner._current_config is None
        assert runner._aggregator is None
        assert runner._process_start_time is None
        
        # Should have called deleteLater on process
        mock_process.deleteLater.assert_called_once()


@pytest.mark.unit
@pytest.mark.gui
class TestScriptRunnerErrorScenarios:
    """Test suite for error scenarios and edge cases."""
    
    def test_jsonl_parsing_error_handling(self, qapp, temp_dir, mock_process, qt_signal_tester):
        """Test handling of JSONL parsing errors."""
        runner = ScriptRunner()
        runner._current_process = mock_process
        
        # Connect error signals
        runner.signals.parse_error.connect(qt_signal_tester.slot)
        
        # Mock stdout with invalid JSON
        mock_data = Mock()
        mock_data.data.return_value.decode.return_value = 'invalid json line\n'
        mock_process.readAllStandardOutput.return_value = mock_data
        
        # Should not crash
        runner._on_stdout_ready()
        
        # Should have emitted parse error
        assert len(qt_signal_tester.received_signals) >= 1
    
    def test_process_crash_handling(self, qapp, temp_dir, qt_signal_tester):
        """Test handling of process crashes."""
        runner = ScriptRunner()
        runner._current_stage = Stage.EXTRACT
        
        # Connect signals
        runner.signals.process_failed.connect(qt_signal_tester.slot)
        
        # Mock process crash
        error = QProcess.Crashed
        
        runner._on_process_error(error)
        
        # Should have emitted failure signal
        assert len(qt_signal_tester.received_signals) == 1
        stage, error_msg = qt_signal_tester.received_signals[0][0]
        assert stage == Stage.EXTRACT
        assert "crashed" in error_msg.lower()
    
    def test_stdout_decoding_error(self, qapp, temp_dir, mock_process):
        """Test handling of stdout decoding errors."""
        runner = ScriptRunner()
        runner._current_process = mock_process
        
        # Mock stdout data that raises decode error
        mock_data = Mock()
        mock_data.data.return_value.decode.side_effect = UnicodeDecodeError(
            'utf-8', b'\xff\xfe', 0, 1, 'invalid start byte'
        )
        mock_process.readAllStandardOutput.return_value = mock_data
        
        # Should handle gracefully using error replacement
        try:
            runner._on_stdout_ready()
        except Exception as e:
            pytest.fail(f"Should handle decode errors gracefully, but raised: {e}")
    
    def test_concurrent_process_start_attempts(self, qapp, temp_dir):
        """Test handling concurrent process start attempts."""
        runner = ScriptRunner()
        
        config = ExtractConfig(input_directory=str(temp_dir))
        
        # Mock first process as running
        with patch.object(runner, 'is_running', return_value=True):
            with pytest.raises(RuntimeError, match="Another process is already running"):
                runner.run_extract(config)
    
    def test_missing_script_files(self, qapp, temp_dir):
        """Test behavior when script files are missing."""
        runner = ScriptRunner()
        
        # Set script directory to empty directory
        empty_dir = temp_dir / "empty"
        empty_dir.mkdir()
        runner._script_dir = empty_dir
        
        config = ExtractConfig(input_directory=str(temp_dir))
        
        # Should still attempt to run (file existence checked during execution)
        with patch.object(runner, '_start_process') as mock_start:
            mock_start.side_effect = RuntimeError("Script not found")
            
            with pytest.raises(RuntimeError):
                runner.run_extract(config)
    
    def test_environment_variable_handling(self, qapp, temp_dir, mock_process):
        """Test environment variable handling in process execution."""
        runner = ScriptRunner()
        
        # Test with special characters in environment values
        env_vars = {
            "API_KEY": "key_with_special_chars_!@#$%",
            "UNICODE_VAR": "测试变量",
            "EMPTY_VAR": "",
            "SPACES_VAR": "value with spaces"
        }
        
        with patch('PySide6.QtCore.QProcess') as MockQProcess:
            MockQProcess.return_value = mock_process
            
            try:
                runner._start_process([sys.executable, "-c", "pass"], env_vars)
            except Exception as e:
                if "Failed to start process" not in str(e):
                    pytest.fail(f"Should handle environment variables gracefully: {e}")
    
    @pytest.mark.performance
    def test_high_frequency_stdout_handling(self, qapp, temp_dir, mock_process, performance_tracker):
        """Test performance with high-frequency stdout data."""
        runner = ScriptRunner()
        runner._current_process = mock_process
        
        performance_tracker.start_timer("high_frequency_stdout")
        
        # Simulate rapid stdout updates
        for i in range(100):
            mock_data = Mock()
            mock_data.data.return_value.decode.return_value = f'{{"ts": "2025-08-08T07:42:01Z", "stage": "extract", "type": "progress", "msg": "Processing {i}", "progress": {i}}}\n'
            mock_process.readAllStandardOutput.return_value = mock_data
            
            runner._on_stdout_ready()
        
        performance_tracker.end_timer("high_frequency_stdout")
        
        # Should handle high frequency updates efficiently (under 1 second)
        performance_tracker.assert_duration_under("high_frequency_stdout", 1.0)
    
    def test_memory_usage_with_large_output(self, qapp, temp_dir, mock_process):
        """Test memory usage with large stdout output."""
        runner = ScriptRunner()
        runner._current_process = mock_process
        
        # Simulate very large output
        large_json_line = '{"ts": "2025-08-08T07:42:01Z", "stage": "extract", "type": "info", "msg": "' + 'x' * 10000 + '"}\n'
        
        mock_data = Mock()
        mock_data.data.return_value.decode.return_value = large_json_line
        mock_process.readAllStandardOutput.return_value = mock_data
        
        # Should handle large output without memory issues
        try:
            runner._on_stdout_ready()
        except MemoryError:
            pytest.fail("Should handle large output without memory errors")
    
    def test_parser_state_consistency(self, qapp, temp_dir, mock_process):
        """Test parser state remains consistent across multiple operations."""
        runner = ScriptRunner()
        runner._current_process = mock_process
        runner._current_stage = Stage.EXTRACT
        
        # Send mixed valid and invalid JSON
        test_data = [
            '{"ts": "2025-08-08T07:42:01Z", "stage": "extract", "type": "info", "msg": "Valid 1"}\n',
            'invalid json\n',
            '{"ts": "2025-08-08T07:42:02Z", "stage": "extract", "type": "info", "msg": "Valid 2"}\n',
            'another invalid line\n',
            '{"ts": "2025-08-08T07:42:03Z", "stage": "extract", "type": "info", "msg": "Valid 3"}\n'
        ]
        
        for data in test_data:
            mock_data = Mock()
            mock_data.data.return_value.decode.return_value = data
            mock_process.readAllStandardOutput.return_value = mock_data
            
            # Should not affect parser state
            runner._on_stdout_ready()
        
        # Parser should still be functional
        stats = runner._parser.get_stats()
        assert stats['events_parsed'] >= 3  # Should have parsed the 3 valid events
        assert stats['parse_errors'] >= 2   # Should have recorded the 2 errors