"""
Pytest configuration and shared fixtures for SubtitleToolkit tests.

This module provides common test fixtures, mock objects, and test data
for comprehensive testing of the SubtitleToolkit desktop application.
"""

import os
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock
from datetime import datetime
from typing import Dict, Any, List, Optional

import pytest
from PySide6.QtCore import QObject, QTimer, QEventLoop
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtTest import QTest

# Add the project root to sys.path for imports
import sys
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.runner.events import Event, EventType, Stage, ProcessResult
from app.utils.tool_status import ToolStatus, ToolInfo
from app.config.settings_schema import SettingsSchema


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication for GUI tests."""
    if not QApplication.instance():
        app = QApplication([])
        yield app
        app.quit()
    else:
        yield QApplication.instance()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_process():
    """Mock QProcess for testing subprocess orchestration."""
    from PySide6.QtCore import QProcess
    
    process = Mock(spec=QProcess)
    process.state.return_value = QProcess.NotRunning
    process.exitCode.return_value = 0
    process.exitStatus.return_value = QProcess.NormalExit
    process.readAllStandardOutput.return_value = Mock()
    process.readAllStandardError.return_value = Mock()
    process.waitForStarted.return_value = True
    process.waitForFinished.return_value = True
    
    return process


@pytest.fixture
def sample_jsonl_events():
    """Sample JSONL event data for testing parser."""
    return [
        '{"ts": "2025-08-08T07:42:01Z", "stage": "extract", "type": "info", "msg": "Starting extraction"}',
        '{"ts": "2025-08-08T07:42:02Z", "stage": "extract", "type": "progress", "msg": "Processing files", "progress": 25}',
        '{"ts": "2025-08-08T07:42:03Z", "stage": "extract", "type": "warning", "msg": "No subtitles found in file"}',
        '{"ts": "2025-08-08T07:42:04Z", "stage": "extract", "type": "error", "msg": "Failed to process file"}',
        '{"ts": "2025-08-08T07:42:05Z", "stage": "extract", "type": "result", "msg": "Extraction complete", "data": {"files_processed": 5, "files_successful": 4, "outputs": ["file1.srt", "file2.srt"]}}',
    ]


@pytest.fixture
def malformed_jsonl_data():
    """Malformed JSONL data for robustness testing."""
    return [
        '{"ts": "2025-08-08T07:42:01Z", "stage": "extract"',  # Incomplete JSON
        '{"ts": "invalid-timestamp", "stage": "extract", "type": "info", "msg": "test"}',  # Invalid timestamp
        '{"stage": "extract", "type": "info", "msg": "test"}',  # Missing required field
        '{"ts": "2025-08-08T07:42:01Z", "stage": "invalid", "type": "info", "msg": "test"}',  # Invalid stage
        '{"ts": "2025-08-08T07:42:01Z", "stage": "extract", "type": "progress", "msg": "test", "progress": 150}',  # Invalid progress value
        'not json at all',  # Not JSON
        '',  # Empty line
        '{"ts": "2025-08-08T07:42:01Z", "stage": "extract", "type": "info", "msg": "test", "unexpected_field": "value"}',  # Unexpected field
    ]


@pytest.fixture
def sample_events():
    """Create sample Event objects for testing."""
    return [
        Event(
            timestamp=datetime.now(),
            stage=Stage.EXTRACT,
            event_type=EventType.INFO,
            message="Starting extraction"
        ),
        Event(
            timestamp=datetime.now(),
            stage=Stage.EXTRACT,
            event_type=EventType.PROGRESS,
            message="Processing files",
            progress=50
        ),
        Event(
            timestamp=datetime.now(),
            stage=Stage.EXTRACT,
            event_type=EventType.RESULT,
            message="Extraction complete",
            data={"files_processed": 5, "outputs": ["file1.srt"]}
        ),
    ]


@pytest.fixture
def default_settings():
    """Get default application settings."""
    return SettingsSchema.get_default_settings()


@pytest.fixture
def sample_config_file(temp_dir):
    """Create a sample configuration file for testing."""
    config_data = {
        "ui": {
            "theme": "dark",
            "remember_window_size": True,
            "last_project_directory": str(temp_dir)
        },
        "tools": {
            "auto_detect_tools": True,
            "ffmpeg_path": "",
            "ffprobe_path": "",
            "mkvextract_path": ""
        },
        "translators": {
            "openai": {
                "model": "gpt-4o-mini",
                "temperature": 0.3,
                "max_tokens": 4000
            },
            "anthropic": {
                "model": "claude-3-haiku-20240307",
                "temperature": 0.3,
                "max_tokens": 4000
            }
        },
        "languages": {
            "source_language": "auto",
            "target_language": "en"
        },
        "advanced": {
            "max_workers": 3,
            "log_level": "INFO",
            "retain_intermediate_files": False
        }
    }
    
    config_file = temp_dir / "test_config.json"
    with open(config_file, 'w') as f:
        json.dump(config_data, f, indent=2)
    
    return config_file


@pytest.fixture
def mock_tool_info():
    """Create mock ToolInfo objects for testing."""
    return {
        "ffmpeg_found": ToolInfo(
            status=ToolStatus.FOUND,
            path="/usr/local/bin/ffmpeg",
            version="6.0.0",
            minimum_version="4.0.0",
            meets_requirements=True,
            installation_method="homebrew"
        ),
        "ffmpeg_not_found": ToolInfo(
            status=ToolStatus.NOT_FOUND,
            error_message="ffmpeg not found in PATH"
        ),
        "ffmpeg_version_mismatch": ToolInfo(
            status=ToolStatus.VERSION_MISMATCH,
            path="/usr/bin/ffmpeg",
            version="3.4.0",
            minimum_version="4.0.0",
            meets_requirements=False,
            error_message="Version 3.4.0 does not meet minimum requirement 4.0.0"
        ),
        "ffmpeg_error": ToolInfo(
            status=ToolStatus.ERROR,
            path="/invalid/path",
            error_message="Permission denied"
        )
    }


@pytest.fixture
def sample_mkv_file(temp_dir):
    """Create a fake MKV file for testing."""
    mkv_file = temp_dir / "test_video.mkv"
    # Create empty file (tests will mock actual processing)
    mkv_file.write_bytes(b"fake mkv content")
    return mkv_file


@pytest.fixture
def sample_srt_files(temp_dir):
    """Create sample SRT files for testing."""
    srt_content = """1
00:00:01,000 --> 00:00:03,000
This is a test subtitle

2
00:00:04,000 --> 00:00:06,000
Another test subtitle
"""
    
    files = []
    for i in range(3):
        srt_file = temp_dir / f"test_{i}.srt"
        srt_file.write_text(srt_content, encoding='utf-8')
        files.append(srt_file)
    
    return files


@pytest.fixture
def malformed_srt_files(temp_dir):
    """Create malformed SRT files for error testing."""
    files = {}
    
    # Invalid timestamp format
    files["invalid_timestamp"] = temp_dir / "invalid_timestamp.srt"
    files["invalid_timestamp"].write_text("""1
00:00:01,000 -> 00:00:03,000
Invalid timestamp format
""", encoding='utf-8')
    
    # Missing sequence number
    files["missing_sequence"] = temp_dir / "missing_sequence.srt"
    files["missing_sequence"].write_text("""00:00:01,000 --> 00:00:03,000
Missing sequence number
""", encoding='utf-8')
    
    # Encoding issues (binary content)
    files["encoding_issues"] = temp_dir / "encoding_issues.srt"
    files["encoding_issues"].write_bytes(b'\xff\xfe\x00Invalid encoding content')
    
    return files


@pytest.fixture
def mock_api_responses():
    """Mock API responses for translation services."""
    return {
        "openai_success": {
            "choices": [
                {
                    "message": {
                        "content": "Translated subtitle text here"
                    }
                }
            ]
        },
        "openai_error": {
            "error": {
                "message": "Rate limit exceeded",
                "code": "rate_limit_exceeded"
            }
        },
        "anthropic_success": {
            "content": [
                {
                    "text": "Translated subtitle text here"
                }
            ]
        },
        "anthropic_error": {
            "error": {
                "message": "Invalid API key",
                "type": "authentication_error"
            }
        }
    }


@pytest.fixture
def mock_subprocess_outputs():
    """Mock subprocess outputs for script testing."""
    return {
        "extract_success": """{"ts": "2025-08-08T07:42:01Z", "stage": "extract", "type": "info", "msg": "Starting MKV subtitle extraction"}
{"ts": "2025-08-08T07:42:02Z", "stage": "extract", "type": "progress", "msg": "Processing video.mkv", "progress": 50}
{"ts": "2025-08-08T07:42:03Z", "stage": "extract", "type": "result", "msg": "Extraction complete", "data": {"files_processed": 1, "outputs": ["video.srt"]}}
""",
        "extract_no_subtitles": """{"ts": "2025-08-08T07:42:01Z", "stage": "extract", "type": "info", "msg": "Starting MKV subtitle extraction"}
{"ts": "2025-08-08T07:42:02Z", "stage": "extract", "type": "warning", "msg": "No subtitle tracks found in video.mkv"}
{"ts": "2025-08-08T07:42:03Z", "stage": "extract", "type": "result", "msg": "Extraction complete", "data": {"files_processed": 1, "outputs": []}}
""",
        "translate_success": """{"ts": "2025-08-08T07:42:01Z", "stage": "translate", "type": "info", "msg": "Starting translation"}
{"ts": "2025-08-08T07:42:02Z", "stage": "translate", "type": "progress", "msg": "Translating chunks", "progress": 75}
{"ts": "2025-08-08T07:42:03Z", "stage": "translate", "type": "result", "msg": "Translation complete", "data": {"files_processed": 1, "outputs": ["video_translated.srt"]}}
""",
        "sync_success": """{"ts": "2025-08-08T07:42:01Z", "stage": "sync", "type": "info", "msg": "Starting file synchronization"}
{"ts": "2025-08-08T07:42:02Z", "stage": "sync", "type": "progress", "msg": "Analyzing filenames", "progress": 90}
{"ts": "2025-08-08T07:42:03Z", "stage": "sync", "type": "result", "msg": "Sync complete", "data": {"files_processed": 3, "files_renamed": 2}}
"""
    }


@pytest.fixture
def qt_signal_tester():
    """Helper for testing Qt signals."""
    class SignalTester(QObject):
        def __init__(self):
            super().__init__()
            self.received_signals = []
            
        def slot(self, *args, **kwargs):
            self.received_signals.append((args, kwargs))
            
        def wait_for_signal(self, signal, timeout=1000):
            """Wait for a signal to be emitted."""
            loop = QEventLoop()
            timer = QTimer()
            timer.setSingleShot(True)
            timer.timeout.connect(loop.quit)
            signal.connect(loop.quit)
            timer.start(timeout)
            loop.exec()
            
        def clear(self):
            self.received_signals.clear()
    
    return SignalTester()


@pytest.fixture
def mock_environment_variables(monkeypatch):
    """Mock environment variables for API testing."""
    test_env = {
        "OPENAI_API_KEY": "test-openai-key-123",
        "ANTHROPIC_API_KEY": "test-anthropic-key-456",
        "LM_STUDIO_BASE_URL": "http://localhost:1234/v1"
    }
    
    for key, value in test_env.items():
        monkeypatch.setenv(key, value)
    
    return test_env


@pytest.fixture
def cross_platform_paths():
    """Platform-specific paths for cross-platform testing."""
    import platform
    system = platform.system().lower()
    
    paths = {
        "windows": {
            "ffmpeg": r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
            "common_locations": [
                r"C:\Program Files\ffmpeg\bin",
                r"C:\ProgramData\chocolatey\bin",
                r"C:\Users\%USERNAME%\scoop\apps\ffmpeg\current\bin"
            ],
            "config_dir": r"C:\Users\%USERNAME%\AppData\Roaming\SubtitleToolkit"
        },
        "darwin": {  # macOS
            "ffmpeg": "/opt/homebrew/bin/ffmpeg",
            "common_locations": [
                "/opt/homebrew/bin",
                "/usr/local/bin",
                "/opt/local/bin"
            ],
            "config_dir": "~/Library/Application Support/SubtitleToolkit"
        },
        "linux": {
            "ffmpeg": "/usr/bin/ffmpeg",
            "common_locations": [
                "/usr/bin",
                "/usr/local/bin",
                "/snap/bin",
                "~/.local/bin"
            ],
            "config_dir": "~/.config/SubtitleToolkit"
        }
    }
    
    return paths.get(system, paths["linux"])  # Default to linux


@pytest.fixture
def performance_tracker():
    """Track performance metrics during tests."""
    class PerformanceTracker:
        def __init__(self):
            self.metrics = {}
            
        def start_timer(self, name: str):
            self.metrics[name] = {"start": datetime.now()}
            
        def end_timer(self, name: str):
            if name in self.metrics:
                self.metrics[name]["end"] = datetime.now()
                self.metrics[name]["duration"] = (
                    self.metrics[name]["end"] - self.metrics[name]["start"]
                ).total_seconds()
                
        def get_duration(self, name: str) -> float:
            return self.metrics.get(name, {}).get("duration", 0.0)
            
        def assert_duration_under(self, name: str, max_seconds: float):
            duration = self.get_duration(name)
            assert duration < max_seconds, f"{name} took {duration}s, expected under {max_seconds}s"
    
    return PerformanceTracker()


# Helper functions for test data generation
def create_test_mkv_metadata():
    """Create mock MKV metadata for testing."""
    return {
        "streams": [
            {
                "index": 0,
                "codec_type": "video",
                "codec_name": "h264"
            },
            {
                "index": 1,
                "codec_type": "audio",
                "codec_name": "aac"
            },
            {
                "index": 2,
                "codec_type": "subtitle",
                "codec_name": "subrip",
                "tags": {"language": "eng", "title": "English"}
            },
            {
                "index": 3,
                "codec_type": "subtitle", 
                "codec_name": "subrip",
                "tags": {"language": "spa", "title": "Spanish"}
            }
        ]
    }


def create_progress_sequence(stage: str, steps: List[tuple]) -> List[str]:
    """Create a sequence of progress events for testing."""
    events = []
    for i, (progress, message) in enumerate(steps):
        timestamp = f"2025-08-08T07:42:{i+1:02d}Z"
        event = {
            "ts": timestamp,
            "stage": stage,
            "type": "progress",
            "msg": message,
            "progress": progress
        }
        events.append(json.dumps(event))
    return events