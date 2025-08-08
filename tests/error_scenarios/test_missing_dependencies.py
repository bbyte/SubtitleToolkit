"""
Error scenario tests for missing dependencies.

Tests application behavior when required tools and dependencies
are missing, misconfigured, or inaccessible.

Following TDD principles:
1. Test missing system dependencies (ffmpeg, ffprobe, mkvextract)
2. Test missing Python dependencies
3. Test invalid tool paths and configurations
4. Test graceful degradation and user guidance
5. Test recovery after dependency installation
"""

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from app.utils.dependency_checker import DependencyChecker
from app.utils.tool_status import ToolStatus, ToolInfo
from app.utils.platform_utils import PlatformUtils
from app.config.config_manager import ConfigManager
from app.runner.script_runner import ScriptRunner
from app.runner.config_models import ExtractConfig


@pytest.mark.error_scenario
class TestMissingSystemDependencies:
    """Test scenarios with missing system tools."""
    
    def test_missing_ffmpeg(self):
        """Test behavior when ffmpeg is not found."""
        checker = DependencyChecker()
        
        with patch.object(PlatformUtils, 'find_executables_in_path', return_value=[]):
            with patch.object(PlatformUtils, 'get_common_tool_paths', return_value=[]):
                tool_info = checker.detect_ffmpeg(use_cache=False)
                
                assert tool_info.status == ToolStatus.NOT_FOUND
                assert "ffmpeg not found" in tool_info.error_message.lower()
                assert tool_info.path is None
    
    def test_missing_ffprobe(self):
        """Test behavior when ffprobe is not found."""
        checker = DependencyChecker()
        
        with patch.object(PlatformUtils, 'find_executables_in_path', return_value=[]):
            with patch.object(PlatformUtils, 'get_common_tool_paths', return_value=[]):
                tool_info = checker.detect_ffprobe(use_cache=False)
                
                assert tool_info.status == ToolStatus.NOT_FOUND
                assert "ffprobe not found" in tool_info.error_message.lower()
    
    def test_missing_mkvextract(self):
        """Test behavior when mkvextract is not found.""" 
        checker = DependencyChecker()
        
        with patch.object(PlatformUtils, 'find_executables_in_path', return_value=[]):
            with patch.object(PlatformUtils, 'get_common_tool_paths', return_value=[]):
                tool_info = checker.detect_mkvextract(use_cache=False)
                
                assert tool_info.status == ToolStatus.NOT_FOUND
                assert "mkvextract not found" in tool_info.error_message.lower()
    
    def test_all_dependencies_missing(self):
        """Test when all required dependencies are missing."""
        checker = DependencyChecker()
        
        with patch.object(PlatformUtils, 'find_executables_in_path', return_value=[]):
            with patch.object(PlatformUtils, 'get_common_tool_paths', return_value=[]):
                results = checker.detect_all_tools(use_cache=False)
                
                # All tools should be not found
                for tool_name, tool_info in results.items():
                    assert tool_info.status == ToolStatus.NOT_FOUND
                    assert "not found" in tool_info.error_message.lower()
    
    def test_tool_not_executable(self, temp_dir):
        """Test behavior when tool exists but is not executable."""
        checker = DependencyChecker()
        
        # Create non-executable file
        fake_ffmpeg = temp_dir / "ffmpeg"
        fake_ffmpeg.write_text("#!/bin/sh\necho 'fake ffmpeg'")
        # Don't set executable permissions
        
        with patch.object(PlatformUtils, 'validate_path_security', return_value=(True, "")):
            tool_info = checker.validate_tool_path(str(fake_ffmpeg), "ffmpeg")
            
            # Should detect as invalid or error
            assert tool_info.status in [ToolStatus.INVALID, ToolStatus.ERROR]
    
    def test_tool_execution_failure(self):
        """Test behavior when tool exists but fails to execute."""
        checker = DependencyChecker()
        
        with patch('subprocess.run', side_effect=subprocess.SubprocessError("Execution failed")):
            tool_info = checker._validate_tool_execution("/usr/bin/ffmpeg", "ffmpeg")
            
            assert tool_info.status == ToolStatus.ERROR
            assert "Subprocess error" in tool_info.error_message
    
    def test_tool_permission_denied(self):
        """Test behavior when tool access is denied."""
        checker = DependencyChecker()
        
        with patch('subprocess.run', side_effect=PermissionError("Permission denied")):
            tool_info = checker._validate_tool_execution("/usr/bin/ffmpeg", "ffmpeg")
            
            assert tool_info.status == ToolStatus.ERROR
            assert "error" in tool_info.error_message.lower()
    
    def test_installation_guides_provided(self):
        """Test that helpful installation guides are provided."""
        checker = DependencyChecker()
        
        tools = ["ffmpeg", "ffprobe", "mkvextract"]
        
        for tool in tools:
            guide = checker.get_installation_guide(tool)
            
            assert isinstance(guide, str)
            assert len(guide) > 0
            assert tool.lower() in guide.lower()
            
            # Should contain platform-specific guidance
            assert any(keyword in guide.lower() for keyword in 
                      ["install", "download", "package", "homebrew", "apt", "choco"])


@pytest.mark.error_scenario
class TestInvalidToolPaths:
    """Test scenarios with invalid tool paths and configurations."""
    
    def test_nonexistent_tool_path(self):
        """Test validation of non-existent tool path."""
        checker = DependencyChecker()
        
        fake_path = "/nonexistent/path/to/ffmpeg"
        
        tool_info = checker.validate_tool_path(fake_path, "ffmpeg")
        
        assert tool_info.status == ToolStatus.NOT_FOUND
        assert "does not exist" in tool_info.error_message.lower()
        assert tool_info.path == fake_path
    
    def test_directory_as_tool_path(self, temp_dir):
        """Test validation when a directory is provided as tool path."""
        checker = DependencyChecker()
        
        tool_info = checker.validate_tool_path(str(temp_dir), "ffmpeg")
        
        assert tool_info.status == ToolStatus.INVALID
        assert "not a file" in tool_info.error_message.lower()
    
    def test_unsafe_tool_path(self):
        """Test validation rejects unsafe paths."""
        checker = DependencyChecker()
        
        unsafe_paths = [
            "../../etc/passwd",
            "/dev/null", 
            "C:\\Windows\\System32\\cmd.exe",
            "/tmp/../../../usr/bin/rm"
        ]
        
        for unsafe_path in unsafe_paths:
            with patch.object(PlatformUtils, 'validate_path_security', return_value=(False, "Unsafe path")):
                tool_info = checker.validate_tool_path(unsafe_path, "ffmpeg")
                
                assert tool_info.status == ToolStatus.ERROR
                assert "security validation failed" in tool_info.error_message.lower()
    
    def test_invalid_tool_version_output(self):
        """Test handling of tools that return invalid version info."""
        checker = DependencyChecker()
        
        # Mock tool that executes but returns garbage
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Invalid version output \x00\xff garbage"
        mock_result.stderr = ""
        
        with patch('subprocess.run', return_value=mock_result):
            tool_info = checker._validate_tool_execution("/usr/bin/ffmpeg", "ffmpeg")
            
            # Should succeed but with "Unknown" version
            assert tool_info.status == ToolStatus.FOUND
            assert tool_info.version == "Unknown" or tool_info.version is None
    
    def test_tool_wrong_binary(self, temp_dir):
        """Test when wrong binary is at expected path."""
        checker = DependencyChecker()
        
        # Create script that pretends to be different tool
        fake_ffmpeg = temp_dir / "ffmpeg"
        fake_ffmpeg.write_text("#!/bin/sh\necho 'This is actually wget'")
        fake_ffmpeg.chmod(0o755)
        
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "This is actually wget"
        mock_result.stderr = ""
        
        with patch('subprocess.run', return_value=mock_result):
            with patch.object(PlatformUtils, 'validate_path_security', return_value=(True, "")):
                tool_info = checker.validate_tool_path(str(fake_ffmpeg), "ffmpeg")
                
                # Should find tool but version will be "Unknown" or unexpected
                assert tool_info.status == ToolStatus.FOUND
                assert tool_info.version == "Unknown"


@pytest.mark.error_scenario  
class TestConfigurationErrors:
    """Test configuration-related error scenarios."""
    
    def test_config_manager_missing_dependencies(self, qapp, temp_dir):
        """Test ConfigManager behavior when dependencies are missing."""
        with patch('app.config.config_manager.QStandardPaths.writableLocation') as mock_location:
            mock_location.return_value = str(temp_dir)
            
            config_manager = ConfigManager()
            
            # Mock all tools as not found
            with patch.object(config_manager._dependency_checker, 'detect_ffmpeg') as mock_detect:
                mock_detect.return_value = ToolInfo(
                    status=ToolStatus.NOT_FOUND,
                    error_message="ffmpeg not found in PATH"
                )
                
                tool_info = config_manager.get_tool_info("ffmpeg")
                
                assert tool_info.status == ToolStatus.NOT_FOUND
                assert "not found" in tool_info.error_message.lower()
    
    def test_config_with_invalid_manual_paths(self, qapp, temp_dir):
        """Test configuration with manually set invalid tool paths."""
        with patch('app.config.config_manager.QStandardPaths.writableLocation') as mock_location:
            mock_location.return_value = str(temp_dir)
            
            config_manager = ConfigManager()
            
            # Set invalid manual path
            tools_settings = config_manager.get_settings('tools')
            tools_settings['ffmpeg_path'] = '/invalid/path/ffmpeg'
            config_manager.update_settings('tools', tools_settings)
            
            # Should validate the manual path and find it invalid
            tool_info = config_manager.get_tool_info("ffmpeg")
            
            assert tool_info.status in [ToolStatus.NOT_FOUND, ToolStatus.ERROR]
    
    def test_config_corrupted_cache(self, qapp, temp_dir):
        """Test behavior with corrupted tool detection cache."""
        with patch('app.config.config_manager.QStandardPaths.writableLocation') as mock_location:
            mock_location.return_value = str(temp_dir)
            
            config_manager = ConfigManager()
            
            # Create corrupted cache file
            cache_file = temp_dir / "tool_cache.json"
            cache_file.write_text("invalid json {")
            
            # Should handle gracefully and not crash
            try:
                config_manager._load_tool_detection_cache()
            except Exception as e:
                pytest.fail(f"Should handle corrupted cache gracefully: {e}")


@pytest.mark.error_scenario
class TestScriptExecutionErrors:
    """Test script execution errors due to missing dependencies."""
    
    def test_extract_script_missing_ffmpeg(self, qapp, temp_dir):
        """Test extraction script behavior when ffmpeg is missing."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        # Create extract script that checks for ffmpeg
        extract_script = temp_dir / "extract_mkv_subtitles.py"
        extract_script.write_text("""#!/usr/bin/env python3
import sys
import subprocess
try:
    subprocess.run(['ffmpeg', '-version'], capture_output=True)
except FileNotFoundError:
    print('{"ts": "2025-08-08T07:42:01Z", "stage": "extract", "type": "error", "msg": "ffmpeg not found"}')
    sys.exit(1)
""")
        
        mkv_file = temp_dir / "test.mkv"
        mkv_file.write_bytes(b"fake mkv")
        
        config = ExtractConfig(input_directory=str(temp_dir))
        
        # Mock process that fails due to missing ffmpeg
        with patch.object(runner, '_start_process') as mock_start:
            mock_process = Mock()
            mock_start.return_value = mock_process
            
            try:
                process = runner.run_extract(config)
                
                # Simulate error from script
                from app.runner.events import Event
                from datetime import datetime
                error_event = Event(
                    timestamp=datetime.now(),
                    stage=Stage.EXTRACT,
                    event_type=EventType.ERROR,
                    message="ffmpeg not found"
                )
                runner._handle_event(error_event)
                
                # Process should handle the dependency error gracefully
                assert process is not None
                
            except RuntimeError as e:
                # Acceptable to fail at config validation level
                assert "validation" in str(e).lower() or "dependency" in str(e).lower()
    
    def test_script_import_errors(self, qapp, temp_dir):
        """Test handling of Python import errors in scripts."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir
        
        # Create script with missing import
        bad_script = temp_dir / "extract_mkv_subtitles.py"
        bad_script.write_text("""#!/usr/bin/env python3
import nonexistent_module
print("This should never execute")
""")
        
        mkv_file = temp_dir / "test.mkv"
        mkv_file.write_bytes(b"fake mkv")
        
        config = ExtractConfig(input_directory=str(temp_dir))
        
        with patch.object(runner, '_start_process') as mock_start:
            # Mock process that fails to start due to import error
            mock_start.side_effect = RuntimeError("Failed to start process: Import error")
            
            with pytest.raises(RuntimeError, match="Failed to start process"):
                runner.run_extract(config)
    
    def test_missing_script_files(self, qapp, temp_dir):
        """Test behavior when script files are missing."""
        runner = ScriptRunner()
        runner._script_dir = temp_dir  # Empty directory
        
        mkv_file = temp_dir / "test.mkv"
        mkv_file.write_bytes(b"fake mkv")
        
        config = ExtractConfig(input_directory=str(temp_dir))
        
        # Script doesn't exist, should fail to start
        with patch.object(runner, '_start_process') as mock_start:
            mock_start.side_effect = RuntimeError("Script not found")
            
            with pytest.raises(RuntimeError, match="Script not found"):
                runner.run_extract(config)


@pytest.mark.error_scenario
class TestDependencyRecovery:
    """Test recovery scenarios after dependencies are installed."""
    
    def test_dependency_cache_invalidation(self):
        """Test that dependency cache is properly invalidated."""
        checker = DependencyChecker()
        
        # Initial detection - not found
        with patch.object(PlatformUtils, 'find_executables_in_path', return_value=[]):
            tool_info1 = checker.detect_ffmpeg(use_cache=False)
            assert tool_info1.status == ToolStatus.NOT_FOUND
        
        # Clear cache and simulate tool installation
        checker.clear_cache()
        
        with patch.object(PlatformUtils, 'find_executables_in_path', return_value=["/usr/bin/ffmpeg"]):
            with patch.object(checker, '_validate_tool_execution') as mock_validate:
                mock_validate.return_value = ToolInfo(
                    status=ToolStatus.FOUND,
                    path="/usr/bin/ffmpeg",
                    version="6.0.0"
                )
                
                tool_info2 = checker.detect_ffmpeg(use_cache=False)
                assert tool_info2.status == ToolStatus.FOUND
    
    def test_config_refresh_after_installation(self, qapp, temp_dir):
        """Test configuration refresh after tool installation."""
        with patch('app.config.config_manager.QStandardPaths.writableLocation') as mock_location:
            mock_location.return_value = str(temp_dir)
            
            config_manager = ConfigManager()
            
            # Initial state - tool not found
            with patch.object(config_manager._dependency_checker, 'detect_ffmpeg') as mock_detect:
                mock_detect.return_value = ToolInfo(status=ToolStatus.NOT_FOUND)
                
                tool_info1 = config_manager.get_tool_info("ffmpeg")
                assert tool_info1.status == ToolStatus.NOT_FOUND
            
            # Simulate tool installation and force refresh
            with patch.object(config_manager._dependency_checker, 'detect_ffmpeg') as mock_detect:
                mock_detect.return_value = ToolInfo(
                    status=ToolStatus.FOUND,
                    path="/usr/local/bin/ffmpeg",
                    version="6.0.0"
                )
                
                tool_info2 = config_manager.get_tool_info("ffmpeg", force_refresh=True)
                assert tool_info2.status == ToolStatus.FOUND
    
    def test_partial_dependency_availability(self):
        """Test when some dependencies are available but others are not."""
        checker = DependencyChecker()
        
        def mock_find_executable(tool_name):
            # Only ffmpeg is available
            if tool_name == "ffmpeg":
                return ["/usr/bin/ffmpeg"]
            return []
        
        with patch.object(PlatformUtils, 'find_executables_in_path', side_effect=mock_find_executable):
            with patch.object(checker, '_validate_tool_execution') as mock_validate:
                def mock_validation(path, tool_name):
                    if tool_name == "ffmpeg":
                        return ToolInfo(status=ToolStatus.FOUND, path=path, version="6.0.0")
                    return ToolInfo(status=ToolStatus.NOT_FOUND)
                
                mock_validate.side_effect = mock_validation
                
                results = checker.detect_all_tools(use_cache=False)
                
                # Should have mixed results
                assert results["ffmpeg"].status == ToolStatus.FOUND
                assert results["ffprobe"].status == ToolStatus.NOT_FOUND
                assert results["mkvextract"].status == ToolStatus.NOT_FOUND
    
    def test_version_requirements_after_upgrade(self):
        """Test version requirement checking after tool upgrade."""
        checker = DependencyChecker()
        
        # Simulate old version first
        mock_result_old = Mock()
        mock_result_old.returncode = 0
        mock_result_old.stdout = "ffmpeg version 3.4.0"
        mock_result_old.stderr = ""
        
        with patch('subprocess.run', return_value=mock_result_old):
            tool_info1 = checker._validate_tool_execution("/usr/bin/ffmpeg", "ffmpeg")
            
            # Might be version mismatch if minimum requirement is higher
            if tool_info1.minimum_version:
                if checker._compare_versions("3.4.0", tool_info1.minimum_version) < 0:
                    assert tool_info1.status == ToolStatus.VERSION_MISMATCH
        
        # Simulate upgrade
        mock_result_new = Mock()
        mock_result_new.returncode = 0
        mock_result_new.stdout = "ffmpeg version 6.0.0"
        mock_result_new.stderr = ""
        
        with patch('subprocess.run', return_value=mock_result_new):
            tool_info2 = checker._validate_tool_execution("/usr/bin/ffmpeg", "ffmpeg")
            
            # Should now meet requirements
            assert tool_info2.status == ToolStatus.FOUND
            assert tool_info2.meets_requirements is True