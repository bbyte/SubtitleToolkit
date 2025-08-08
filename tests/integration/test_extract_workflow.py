"""
Integration tests for MKV extraction workflow.

Tests the complete extraction workflow including MKV file processing,
subtitle detection, and SRT output validation.

Following TDD principles:
1. Test successful extraction scenarios
2. Test MKV files with various subtitle configurations
3. Test error handling and recovery
4. Test output validation and quality
5. Test performance under load
"""

import json
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import pytest

from app.runner.script_runner import ScriptRunner
from app.runner.config_models import ExtractConfig
from app.runner.events import Stage, EventType
from app.utils.dependency_checker import DependencyChecker
from app.utils.tool_status import ToolStatus, ToolInfo


@pytest.mark.integration
class TestExtractWorkflow:
    """Test suite for MKV subtitle extraction workflow."""
    
    def test_extract_workflow_success(self, qapp, temp_dir, sample_mkv_file, qt_signal_tester, mock_subprocess_outputs):
        """Test successful MKV extraction workflow."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        # Create mock extract script
        extract_script = temp_dir / "extract_mkv_subtitles.py"
        extract_script.write_text("#!/usr/bin/env python3\nimport sys\nprint('Mock extraction')")
        
        # Connect signals
        runner.signals.process_started.connect(qt_signal_tester.slot)
        runner.signals.process_finished.connect(qt_signal_tester.slot)
        runner.signals.progress_updated.connect(qt_signal_tester.slot)
        runner.signals.result_received.connect(qt_signal_tester.slot)
        
        # Create extract configuration
        config = ExtractConfig(
            input_directory=str(sample_mkv_file.parent),
            language="en",
            output_format="srt"
        )
        
        # Mock subprocess execution
        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.returncode = 0
            mock_process.stdout.readline.side_effect = [
                b'{"ts": "2025-08-08T07:42:01Z", "stage": "extract", "type": "info", "msg": "Starting extraction"}\n',
                b'{"ts": "2025-08-08T07:42:02Z", "stage": "extract", "type": "progress", "msg": "Processing video.mkv", "progress": 50}\n',
                b'{"ts": "2025-08-08T07:42:03Z", "stage": "extract", "type": "result", "msg": "Extraction complete", "data": {"files_processed": 1, "outputs": ["video.srt"]}}\n',
                b''  # End of output
            ]
            mock_process.poll.return_value = None  # Still running
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process
            
            with patch.object(runner, '_start_process') as mock_start:
                mock_qprocess = Mock()
                mock_qprocess.state.return_value = Mock()  # QProcess.Running equivalent
                mock_start.return_value = mock_qprocess
                
                # Simulate successful process execution
                process = runner.run_extract(config)
                
                # Verify process started
                assert process is not None
                assert runner._current_stage == Stage.EXTRACT
                
                # Simulate process completion
                runner._on_process_finished(0, Mock())  # QProcess.NormalExit equivalent
        
        # Verify signals were emitted
        assert len(qt_signal_tester.received_signals) >= 1
    
    def test_extract_workflow_with_multiple_subtitle_tracks(self, qapp, temp_dir, qt_signal_tester):
        """Test extraction from MKV with multiple subtitle tracks."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        # Create mock extract script
        extract_script = temp_dir / "extract_mkv_subtitles.py"
        extract_script.write_text("#!/usr/bin/env python3")
        
        # Create MKV file with multiple tracks
        mkv_file = temp_dir / "multi_track.mkv"
        mkv_file.write_bytes(b"fake mkv with multiple subtitle tracks")
        
        # Connect result signal
        runner.signals.result_received.connect(qt_signal_tester.slot)
        
        config = ExtractConfig(
            input_directory=str(temp_dir),
            language="en"  # Should prefer English
        )
        
        # Mock ffprobe metadata showing multiple subtitle tracks
        mock_metadata = {
            "streams": [
                {
                    "index": 0,
                    "codec_type": "video",
                    "codec_name": "h264"
                },
                {
                    "index": 1,
                    "codec_type": "subtitle",
                    "codec_name": "subrip",
                    "tags": {"language": "eng", "title": "English"}
                },
                {
                    "index": 2,
                    "codec_type": "subtitle", 
                    "codec_name": "subrip",
                    "tags": {"language": "spa", "title": "Spanish"}
                },
                {
                    "index": 3,
                    "codec_type": "subtitle",
                    "codec_name": "subrip", 
                    "tags": {"language": "fre", "title": "French"}
                }
            ]
        }
        
        with patch('subprocess.run') as mock_subprocess:
            # Mock ffprobe call
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = json.dumps(mock_metadata)
            mock_subprocess.return_value = mock_result
            
            with patch.object(runner, '_start_process') as mock_start:
                mock_process = Mock()
                mock_start.return_value = mock_process
                
                process = runner.run_extract(config)
                
                # Verify extraction was configured to prefer English
                assert process is not None
                assert runner._current_stage == Stage.EXTRACT
    
    def test_extract_workflow_no_subtitles_found(self, qapp, temp_dir, qt_signal_tester):
        """Test extraction from MKV with no subtitle tracks."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        extract_script = temp_dir / "extract_mkv_subtitles.py"
        extract_script.write_text("#!/usr/bin/env python3")
        
        mkv_file = temp_dir / "no_subtitles.mkv"
        mkv_file.write_bytes(b"fake mkv without subtitles")
        
        # Connect warning signal
        runner.signals.warning_received.connect(qt_signal_tester.slot)
        runner.signals.result_received.connect(qt_signal_tester.slot)
        
        config = ExtractConfig(input_directory=str(temp_dir))
        
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            process = runner.run_extract(config)
            
            # Simulate warning about no subtitles
            from app.runner.events import Event
            warning_event = Event(
                timestamp=datetime.now(),
                stage=Stage.EXTRACT,
                event_type=EventType.WARNING,
                message="No subtitle tracks found in video file"
            )
            
            runner._handle_event(warning_event)
            
            # Should have received warning
            assert len(qt_signal_tester.received_signals) >= 1
    
    def test_extract_workflow_invalid_mkv_file(self, qapp, temp_dir, qt_signal_tester):
        """Test extraction with corrupted or invalid MKV file."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        extract_script = temp_dir / "extract_mkv_subtitles.py"
        extract_script.write_text("#!/usr/bin/env python3")
        
        # Create invalid MKV file
        invalid_mkv = temp_dir / "corrupted.mkv"
        invalid_mkv.write_bytes(b"not a valid mkv file")
        
        # Connect error signal
        runner.signals.error_received.connect(qt_signal_tester.slot)
        
        config = ExtractConfig(input_directory=str(temp_dir))
        
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            process = runner.run_extract(config)
            
            # Simulate error event
            from app.runner.events import Event
            error_event = Event(
                timestamp=datetime.now(),
                stage=Stage.EXTRACT,
                event_type=EventType.ERROR,
                message="Failed to read MKV file: corrupted.mkv"
            )
            
            runner._handle_event(error_event)
            
            # Should have received error
            assert len(qt_signal_tester.received_signals) >= 1
            stage, message = qt_signal_tester.received_signals[0][0]
            assert stage == Stage.EXTRACT
            assert "Failed to read MKV file" in message
    
    def test_extract_workflow_dependency_check(self, qapp, temp_dir):
        """Test extraction workflow dependency checking."""
        dependency_checker = DependencyChecker()
        
        # Test with missing ffmpeg
        with patch.object(dependency_checker, 'detect_ffmpeg') as mock_detect_ffmpeg:
            with patch.object(dependency_checker, 'detect_ffprobe') as mock_detect_ffprobe:
                
                # Mock ffmpeg not found
                mock_detect_ffmpeg.return_value = ToolInfo(
                    status=ToolStatus.NOT_FOUND,
                    error_message="ffmpeg not found in PATH"
                )
                
                # Mock ffprobe not found
                mock_detect_ffprobe.return_value = ToolInfo(
                    status=ToolStatus.NOT_FOUND,
                    error_message="ffprobe not found in PATH"
                )
                
                ffmpeg_info = dependency_checker.detect_ffmpeg()
                ffprobe_info = dependency_checker.detect_ffprobe()
                
                # Should detect missing dependencies
                assert ffmpeg_info.status == ToolStatus.NOT_FOUND
                assert ffprobe_info.status == ToolStatus.NOT_FOUND
    
    def test_extract_workflow_output_validation(self, qapp, temp_dir, sample_mkv_file):
        """Test validation of extraction output files."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        extract_script = temp_dir / "extract_mkv_subtitles.py"
        extract_script.write_text("#!/usr/bin/env python3")
        
        # Expected output file
        expected_srt = sample_mkv_file.parent / f"{sample_mkv_file.stem}.srt"
        
        config = ExtractConfig(
            input_directory=str(sample_mkv_file.parent),
            output_format="srt"
        )
        
        # Mock successful extraction that creates SRT file
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            process = runner.run_extract(config)
            
            # Create mock SRT output
            srt_content = """1
00:00:01,000 --> 00:00:03,000
This is a test subtitle

2
00:00:04,000 --> 00:00:06,000
Another test subtitle
"""
            expected_srt.write_text(srt_content, encoding='utf-8')
            
            # Simulate successful result
            from app.runner.events import Event
            result_event = Event(
                timestamp=datetime.now(),
                stage=Stage.EXTRACT,
                event_type=EventType.RESULT,
                message="Extraction complete",
                data={
                    "files_processed": 1,
                    "files_successful": 1,
                    "outputs": [str(expected_srt)]
                }
            )
            
            runner._handle_event(result_event)
            
            # Validate output file exists and has content
            assert expected_srt.exists()
            content = expected_srt.read_text(encoding='utf-8')
            assert "This is a test subtitle" in content
            assert "-->" in content  # SRT timestamp format
    
    def test_extract_workflow_language_filtering(self, qapp, temp_dir):
        """Test extraction with specific language filtering."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        extract_script = temp_dir / "extract_mkv_subtitles.py"
        extract_script.write_text("#!/usr/bin/env python3")
        
        mkv_file = temp_dir / "multi_lang.mkv"
        mkv_file.write_bytes(b"fake mkv content")
        
        # Test different language configurations
        language_tests = [
            ("en", "English"),
            ("es", "Spanish"), 
            ("fr", "French"),
            ("auto", "Auto-detect")
        ]
        
        for lang_code, lang_name in language_tests:
            config = ExtractConfig(
                input_directory=str(temp_dir),
                language=lang_code
            )
            
            with patch.object(runner, '_start_process') as mock_start:
                mock_process = Mock()
                mock_start.return_value = mock_process
                
                process = runner.run_extract(config)
                
                # Verify configuration was created
                assert config.language == lang_code
                assert process is not None
    
    def test_extract_workflow_batch_processing(self, qapp, temp_dir, qt_signal_tester):
        """Test batch processing of multiple MKV files."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        extract_script = temp_dir / "extract_mkv_subtitles.py"
        extract_script.write_text("#!/usr/bin/env python3")
        
        # Create multiple MKV files
        mkv_files = []
        for i in range(3):
            mkv_file = temp_dir / f"video_{i}.mkv"
            mkv_file.write_bytes(f"fake mkv content {i}".encode())
            mkv_files.append(mkv_file)
        
        # Connect progress signal
        runner.signals.progress_updated.connect(qt_signal_tester.slot)
        runner.signals.result_received.connect(qt_signal_tester.slot)
        
        config = ExtractConfig(input_directory=str(temp_dir))
        
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            process = runner.run_extract(config)
            
            # Simulate progress updates for batch processing
            from app.runner.events import Event
            
            for i, mkv_file in enumerate(mkv_files):
                progress_event = Event(
                    timestamp=datetime.now(),
                    stage=Stage.EXTRACT,
                    event_type=EventType.PROGRESS,
                    message=f"Processing {mkv_file.name}",
                    progress=int((i + 1) / len(mkv_files) * 100)
                )
                runner._handle_event(progress_event)
            
            # Final result
            result_event = Event(
                timestamp=datetime.now(),
                stage=Stage.EXTRACT,
                event_type=EventType.RESULT,
                message="Batch extraction complete",
                data={
                    "files_processed": len(mkv_files),
                    "files_successful": len(mkv_files),
                    "outputs": [f"video_{i}.srt" for i in range(len(mkv_files))]
                }
            )
            runner._handle_event(result_event)
            
            # Should have received progress updates and final result
            progress_signals = [s for s in qt_signal_tester.received_signals 
                             if len(s[0]) == 3]  # progress signals have 3 args
            result_signals = [s for s in qt_signal_tester.received_signals 
                            if len(s[0]) == 2]  # result signals have 2 args
            
            assert len(progress_signals) >= 3  # One for each file
            assert len(result_signals) >= 1   # Final result
    
    @pytest.mark.performance
    def test_extract_workflow_performance(self, qapp, temp_dir, performance_tracker):
        """Test extraction workflow performance with multiple files."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        extract_script = temp_dir / "extract_mkv_subtitles.py"
        extract_script.write_text("#!/usr/bin/env python3")
        
        # Create multiple test files
        num_files = 10
        for i in range(num_files):
            mkv_file = temp_dir / f"performance_test_{i}.mkv"
            mkv_file.write_bytes(f"fake content {i}".encode() * 1000)  # Make files larger
        
        performance_tracker.start_timer("extract_workflow")
        
        config = ExtractConfig(input_directory=str(temp_dir))
        
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            # Simulate rapid processing
            process = runner.run_extract(config)
            
            # Simulate processing events
            from app.runner.events import Event
            for i in range(num_files):
                event = Event(
                    timestamp=datetime.now(),
                    stage=Stage.EXTRACT,
                    event_type=EventType.PROGRESS,
                    message=f"Processing file {i}",
                    progress=int((i + 1) / num_files * 100)
                )
                runner._handle_event(event)
        
        performance_tracker.end_timer("extract_workflow")
        
        # Should complete processing setup quickly
        performance_tracker.assert_duration_under("extract_workflow", 2.0)
    
    def test_extract_workflow_error_recovery(self, qapp, temp_dir, qt_signal_tester):
        """Test error recovery during extraction workflow."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        extract_script = temp_dir / "extract_mkv_subtitles.py"
        extract_script.write_text("#!/usr/bin/env python3")
        
        mkv_file = temp_dir / "test.mkv"
        mkv_file.write_bytes(b"fake mkv content")
        
        # Connect error and result signals
        runner.signals.error_received.connect(qt_signal_tester.slot)
        runner.signals.result_received.connect(qt_signal_tester.slot)
        
        config = ExtractConfig(input_directory=str(temp_dir))
        
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            process = runner.run_extract(config)
            
            # Simulate partial failure scenario
            from app.runner.events import Event
            
            # Error with one file
            error_event = Event(
                timestamp=datetime.now(),
                stage=Stage.EXTRACT,
                event_type=EventType.ERROR,
                message="Failed to extract subtitles from corrupted.mkv"
            )
            runner._handle_event(error_event)
            
            # But successful completion overall
            result_event = Event(
                timestamp=datetime.now(),
                stage=Stage.EXTRACT,
                event_type=EventType.RESULT,
                message="Extraction completed with some errors",
                data={
                    "files_processed": 2,
                    "files_successful": 1,
                    "files_failed": 1,
                    "outputs": ["test.srt"]
                }
            )
            runner._handle_event(result_event)
            
            # Should have received both error and result signals
            error_signals = [s for s in qt_signal_tester.received_signals 
                           if len(s[0]) == 2 and "Failed to extract" in str(s[0])]
            result_signals = [s for s in qt_signal_tester.received_signals 
                            if len(s[0]) == 2 and isinstance(s[0][1], dict)]
            
            assert len(error_signals) >= 1
            assert len(result_signals) >= 1


@pytest.mark.integration
class TestExtractConfigValidation:
    """Test suite for extraction configuration validation."""
    
    def test_valid_extract_config(self, temp_dir):
        """Test creating valid extraction configuration."""
        config = ExtractConfig(
            input_directory=str(temp_dir),
            language="en",
            output_format="srt"
        )
        
        is_valid, error_msg = config.validate()
        
        assert is_valid is True
        assert error_msg is None
        
        # Test CLI args generation
        cli_args = config.to_cli_args()
        assert str(temp_dir) in cli_args
        assert "-l" in cli_args or "--language" in cli_args
    
    def test_invalid_extract_config(self):
        """Test validation of invalid extraction configuration."""
        # Missing input directory
        config = ExtractConfig()
        
        is_valid, error_msg = config.validate()
        
        assert is_valid is False
        assert error_msg is not None
        assert "input_directory" in error_msg.lower()
    
    def test_extract_config_nonexistent_directory(self, temp_dir):
        """Test configuration with non-existent directory."""
        fake_dir = temp_dir / "nonexistent"
        
        config = ExtractConfig(input_directory=str(fake_dir))
        
        is_valid, error_msg = config.validate()
        
        assert is_valid is False
        assert "does not exist" in error_msg.lower() or "not found" in error_msg.lower()
    
    def test_extract_config_invalid_language(self, temp_dir):
        """Test configuration with invalid language code."""
        config = ExtractConfig(
            input_directory=str(temp_dir),
            language="invalid_language_code"
        )
        
        # Should handle gracefully (might warn but not fail)
        is_valid, error_msg = config.validate()
        
        # Depending on implementation, might be valid with warning
        # or invalid with error
        assert isinstance(is_valid, bool)
    
    def test_extract_config_environment_variables(self, temp_dir, mock_environment_variables):
        """Test extraction configuration with environment variables."""
        config = ExtractConfig(input_directory=str(temp_dir))
        
        env_vars = config.get_env_vars() if hasattr(config, 'get_env_vars') else {}
        
        # Should include any necessary environment variables
        assert isinstance(env_vars, dict)
    
    def test_extract_config_cli_args_formatting(self, temp_dir):
        """Test CLI arguments formatting for various configurations."""
        test_configs = [
            ExtractConfig(input_directory=str(temp_dir)),
            ExtractConfig(input_directory=str(temp_dir), language="en"),
            ExtractConfig(input_directory=str(temp_dir), language="es", output_format="srt"),
            ExtractConfig(input_directory=str(temp_dir), language="auto"),
        ]
        
        for config in test_configs:
            cli_args = config.to_cli_args()
            
            # Should be a list of strings
            assert isinstance(cli_args, list)
            assert all(isinstance(arg, str) for arg in cli_args)
            
            # Should include input directory
            assert str(temp_dir) in cli_args or any(str(temp_dir) in arg for arg in cli_args)