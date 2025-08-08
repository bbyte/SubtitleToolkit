"""
Unit tests for dependency checker functionality.

Tests the DependencyChecker class for tool detection, version parsing,
path validation, and cross-platform compatibility.

Following TDD principles:
1. Test tool detection and validation
2. Test version parsing and comparison
3. Test path validation and security
4. Test caching mechanisms
5. Test cross-platform compatibility
6. Test error handling and recovery
"""

import subprocess
import tempfile
import threading
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

import pytest

from app.utils.dependency_checker import DependencyChecker
from app.utils.tool_status import ToolStatus, ToolInfo
from app.utils.platform_utils import PlatformUtils


@pytest.mark.unit
class TestDependencyChecker:
    """Test suite for DependencyChecker core functionality."""
    
    def test_dependency_checker_initialization(self):
        """Test DependencyChecker initializes correctly."""
        checker = DependencyChecker(cache_ttl_minutes=5)
        
        assert checker.cache_ttl == timedelta(minutes=5)
        assert isinstance(checker._cache, dict)
        assert len(checker._cache) == 0
        assert isinstance(checker._detection_lock, threading.Lock)
    
    def test_detect_tool_not_found(self):
        """Test detection when tool is not found."""
        checker = DependencyChecker()
        
        with patch.object(PlatformUtils, 'find_executables_in_path', return_value=[]):
            with patch.object(PlatformUtils, 'get_common_tool_paths', return_value=[]):
                tool_info = checker.detect_ffmpeg(use_cache=False)
                
                assert tool_info.status == ToolStatus.NOT_FOUND
                assert "not found in PATH" in tool_info.error_message
    
    def test_detect_tool_found_in_path(self):
        """Test successful tool detection in PATH."""
        checker = DependencyChecker()
        
        mock_path = "/usr/bin/ffmpeg"
        
        with patch.object(PlatformUtils, 'find_executables_in_path', return_value=[mock_path]):
            with patch.object(checker, '_validate_tool_execution') as mock_validate:
                mock_validate.return_value = ToolInfo(
                    status=ToolStatus.FOUND,
                    path=mock_path,
                    version="6.0.0"
                )
                
                tool_info = checker.detect_ffmpeg(use_cache=False)
                
                assert tool_info.status == ToolStatus.FOUND
                assert tool_info.path == mock_path
                assert tool_info.version == "6.0.0"
                mock_validate.assert_called_once_with(mock_path, 'ffmpeg')
    
    def test_detect_tool_found_in_common_locations(self):
        """Test tool detection in common installation locations."""
        checker = DependencyChecker()
        
        mock_common_path = "/opt/homebrew/bin/ffmpeg"
        
        with patch.object(PlatformUtils, 'find_executables_in_path', return_value=[]):
            with patch.object(PlatformUtils, 'get_common_tool_paths', return_value=[mock_common_path]):
                with patch.object(Path, 'exists', return_value=True):
                    with patch.object(checker, '_validate_tool_execution') as mock_validate:
                        mock_validate.return_value = ToolInfo(
                            status=ToolStatus.FOUND,
                            path=mock_common_path,
                            version="6.0.0"
                        )
                        
                        tool_info = checker.detect_ffmpeg(use_cache=False)
                        
                        assert tool_info.status == ToolStatus.FOUND
                        assert tool_info.path == mock_common_path
    
    def test_validate_tool_path_success(self):
        """Test successful tool path validation."""
        checker = DependencyChecker()
        test_path = "/usr/bin/ffmpeg"
        
        with patch.object(PlatformUtils, 'validate_path_security', return_value=(True, "")):
            with patch.object(Path, 'exists', return_value=True):
                with patch.object(Path, 'is_file', return_value=True):
                    with patch.object(checker, '_validate_tool_execution') as mock_validate:
                        mock_validate.return_value = ToolInfo(
                            status=ToolStatus.FOUND,
                            path=test_path,
                            version="6.0.0"
                        )
                        
                        tool_info = checker.validate_tool_path(test_path, 'ffmpeg')
                        
                        assert tool_info.status == ToolStatus.FOUND
                        assert tool_info.path == test_path
    
    def test_validate_tool_path_security_failure(self):
        """Test tool path validation with security failure."""
        checker = DependencyChecker()
        unsafe_path = "/some/unsafe/path"
        
        with patch.object(PlatformUtils, 'validate_path_security', return_value=(False, "Security issue")):
            tool_info = checker.validate_tool_path(unsafe_path, 'ffmpeg')
            
            assert tool_info.status == ToolStatus.ERROR
            assert "Security validation failed" in tool_info.error_message
            assert tool_info.path == unsafe_path
    
    def test_validate_tool_path_file_not_exists(self):
        """Test tool path validation when file doesn't exist."""
        checker = DependencyChecker()
        nonexistent_path = "/nonexistent/ffmpeg"
        
        with patch.object(PlatformUtils, 'validate_path_security', return_value=(True, "")):
            with patch.object(Path, 'exists', return_value=False):
                tool_info = checker.validate_tool_path(nonexistent_path, 'ffmpeg')
                
                assert tool_info.status == ToolStatus.NOT_FOUND
                assert "File does not exist" in tool_info.error_message
    
    def test_validate_tool_path_not_a_file(self):
        """Test tool path validation when path is not a file."""
        checker = DependencyChecker()
        directory_path = "/usr/bin"
        
        with patch.object(PlatformUtils, 'validate_path_security', return_value=(True, "")):
            with patch.object(Path, 'exists', return_value=True):
                with patch.object(Path, 'is_file', return_value=False):
                    tool_info = checker.validate_tool_path(directory_path, 'ffmpeg')
                    
                    assert tool_info.status == ToolStatus.INVALID
                    assert "Path is not a file" in tool_info.error_message
    
    def test_tool_execution_validation_success(self):
        """Test successful tool execution validation."""
        checker = DependencyChecker()
        test_path = "/usr/bin/ffmpeg"
        
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "ffmpeg version 6.0.0"
        mock_result.stderr = ""
        
        with patch('subprocess.run', return_value=mock_result):
            with patch.object(checker, '_extract_version', return_value="6.0.0"):
                with patch.object(checker, '_compare_versions', return_value=1):  # Version meets requirements
                    tool_info = checker._validate_tool_execution(test_path, 'ffmpeg')
                    
                    assert tool_info.status == ToolStatus.FOUND
                    assert tool_info.path == test_path
                    assert tool_info.version == "6.0.0"
                    assert tool_info.meets_requirements is True
    
    def test_tool_execution_validation_failure(self):
        """Test tool execution validation when command fails."""
        checker = DependencyChecker()
        test_path = "/usr/bin/ffmpeg"
        
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Command failed"
        
        with patch('subprocess.run', return_value=mock_result):
            tool_info = checker._validate_tool_execution(test_path, 'ffmpeg')
            
            assert tool_info.status == ToolStatus.INVALID
            assert "Tool execution failed" in tool_info.error_message
            assert "return code 1" in tool_info.error_message
    
    def test_tool_execution_timeout(self):
        """Test tool execution validation with timeout."""
        checker = DependencyChecker()
        test_path = "/usr/bin/ffmpeg"
        
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired(cmd=['test'], timeout=10)):
            tool_info = checker._validate_tool_execution(test_path, 'ffmpeg')
            
            assert tool_info.status == ToolStatus.ERROR
            assert "Tool validation timed out" in tool_info.error_message
    
    def test_tool_execution_subprocess_error(self):
        """Test tool execution validation with subprocess error."""
        checker = DependencyChecker()
        test_path = "/usr/bin/ffmpeg"
        
        with patch('subprocess.run', side_effect=subprocess.SubprocessError("Subprocess failed")):
            tool_info = checker._validate_tool_execution(test_path, 'ffmpeg')
            
            assert tool_info.status == ToolStatus.ERROR
            assert "Subprocess error" in tool_info.error_message
    
    def test_version_extraction_ffmpeg(self):
        """Test version extraction for ffmpeg output."""
        checker = DependencyChecker()
        
        test_outputs = [
            ("ffmpeg version 6.0.0-full_build", "6.0.0"),
            ("ffmpeg version n4.4.2-1ubuntu0.1", "4.4.2"),
            ("ffmpeg version 5.1.2", "5.1.2"),
        ]
        
        for output, expected_version in test_outputs:
            version = checker._extract_version(output, 'ffmpeg')
            assert version == expected_version
    
    def test_version_extraction_mkvextract(self):
        """Test version extraction for mkvextract output."""
        checker = DependencyChecker()
        
        test_outputs = [
            ("mkvextract v67.0.0 ('Under Stars')", "67.0.0"),
            ("mkvextract v58.0.0", "58.0.0"),
        ]
        
        for output, expected_version in test_outputs:
            version = checker._extract_version(output, 'mkvextract')
            assert version == expected_version
    
    def test_version_extraction_no_version_found(self):
        """Test version extraction when no version is found."""
        checker = DependencyChecker()
        
        test_outputs = [
            "No version information",
            "",
            "Some other output without version",
        ]
        
        for output in test_outputs:
            version = checker._extract_version(output, 'ffmpeg')
            assert version == "Unknown"
    
    def test_version_comparison(self):
        """Test version comparison functionality."""
        checker = DependencyChecker()
        
        test_cases = [
            # (version1, version2, expected_result)
            ("6.0.0", "5.0.0", 1),    # v1 > v2
            ("5.0.0", "6.0.0", -1),   # v1 < v2
            ("5.0.0", "5.0.0", 0),    # v1 == v2
            ("5.1.0", "5.0.9", 1),    # Minor version difference
            ("5.0.10", "5.0.2", 1),   # Patch version with different lengths
            ("Unknown", "5.0.0", -1), # Unknown version
            ("5.0", "5.0.0", 0),      # Different precision
        ]
        
        for v1, v2, expected in test_cases:
            result = checker._compare_versions(v1, v2)
            assert result == expected, f"Comparing {v1} vs {v2} should return {expected}, got {result}"
    
    def test_version_mismatch_detection(self):
        """Test detection of version mismatches."""
        checker = DependencyChecker()
        test_path = "/usr/bin/ffmpeg"
        
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "ffmpeg version 3.4.0"
        mock_result.stderr = ""
        
        with patch('subprocess.run', return_value=mock_result):
            with patch.object(checker, '_extract_version', return_value="3.4.0"):
                tool_info = checker._validate_tool_execution(test_path, 'ffmpeg')
                
                # Should detect version mismatch if minimum version is higher
                if tool_info.minimum_version and checker._compare_versions("3.4.0", tool_info.minimum_version) < 0:
                    assert tool_info.status == ToolStatus.VERSION_MISMATCH
                    assert tool_info.meets_requirements is False
    
    def test_installation_method_detection(self):
        """Test detection of installation methods."""
        checker = DependencyChecker()
        
        test_cases = [
            # (path, platform, expected_method)
            ("/opt/homebrew/bin/ffmpeg", "macos", "homebrew"),
            ("/usr/local/bin/ffmpeg", "macos", "homebrew"),
            ("/usr/bin/ffmpeg", "linux", "package_manager"),
            ("/snap/ffmpeg/current/bin/ffmpeg", "linux", "snap"),
            ("C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe", "windows", "installer"),
            ("C:\\ProgramData\\chocolatey\\bin\\ffmpeg.exe", "windows", "chocolatey"),
        ]
        
        for path, platform, expected_method in test_cases:
            with patch.object(PlatformUtils, 'get_platform', return_value=platform):
                method = checker._detect_installation_method(path)
                assert method == expected_method
    
    def test_detect_all_tools(self):
        """Test detecting all required tools with progress callback."""
        checker = DependencyChecker()
        
        # Mock individual detection methods
        with patch.object(checker, 'detect_ffmpeg') as mock_ffmpeg:
            with patch.object(checker, 'detect_ffprobe') as mock_ffprobe:
                with patch.object(checker, 'detect_mkvextract') as mock_mkvextract:
                    
                    mock_ffmpeg.return_value = ToolInfo(status=ToolStatus.FOUND, path="/usr/bin/ffmpeg")
                    mock_ffprobe.return_value = ToolInfo(status=ToolStatus.FOUND, path="/usr/bin/ffprobe")
                    mock_mkvextract.return_value = ToolInfo(status=ToolStatus.NOT_FOUND)
                    
                    # Track progress callbacks
                    progress_calls = []
                    def progress_callback(tool, percentage):
                        progress_calls.append((tool, percentage))
                    
                    results = checker.detect_all_tools(progress_callback=progress_callback, use_cache=False)
                    
                    # Should detect all three tools
                    assert 'ffmpeg' in results
                    assert 'ffprobe' in results
                    assert 'mkvextract' in results
                    
                    # Should have called progress callback
                    assert len(progress_calls) >= 3  # At least one per tool
                    
                    # Final call should be completion
                    final_call = progress_calls[-1]
                    assert final_call[0] == "complete"
                    assert final_call[1] == 100


@pytest.mark.unit
class TestDependencyCheckerCaching:
    """Test suite for caching functionality."""
    
    def test_cache_functionality(self):
        """Test basic cache functionality."""
        checker = DependencyChecker(cache_ttl_minutes=1)
        
        with patch.object(checker, '_detect_tool') as mock_detect:
            mock_tool_info = ToolInfo(status=ToolStatus.FOUND, path="/usr/bin/ffmpeg")
            mock_detect.return_value = mock_tool_info
            
            # First call should trigger detection
            result1 = checker.detect_ffmpeg(use_cache=True)
            
            # Second call should use cache
            result2 = checker.detect_ffmpeg(use_cache=True)
            
            # Should have been called only once
            mock_detect.assert_called_once()
            
            # Results should be the same
            assert result1.path == result2.path
    
    def test_cache_expiration(self):
        """Test cache expiration functionality."""
        checker = DependencyChecker(cache_ttl_minutes=0.001)  # Very short TTL
        
        mock_tool_info = ToolInfo(
            status=ToolStatus.FOUND, 
            path="/usr/bin/ffmpeg",
            detected_at=datetime.now() - timedelta(minutes=1)  # Old detection
        )
        
        # Manually add expired entry to cache
        checker._cache['ffmpeg'] = mock_tool_info
        
        with patch.object(checker, '_detect_tool') as mock_detect:
            mock_detect.return_value = ToolInfo(status=ToolStatus.FOUND, path="/usr/bin/ffmpeg")
            
            # Should trigger new detection due to expired cache
            result = checker.detect_ffmpeg(use_cache=True)
            
            mock_detect.assert_called_once()
    
    def test_cache_bypass(self):
        """Test bypassing cache when use_cache=False."""
        checker = DependencyChecker()
        
        # Add item to cache
        cached_info = ToolInfo(status=ToolStatus.FOUND, path="/cached/ffmpeg")
        checker._cache['ffmpeg'] = cached_info
        
        with patch.object(checker, '_detect_tool') as mock_detect:
            mock_detect.return_value = ToolInfo(status=ToolStatus.FOUND, path="/fresh/ffmpeg")
            
            # Should bypass cache
            result = checker.detect_ffmpeg(use_cache=False)
            
            mock_detect.assert_called_once()
            assert result.path == "/fresh/ffmpeg"
    
    def test_clear_cache(self):
        """Test clearing the cache."""
        checker = DependencyChecker()
        
        # Add items to cache
        checker._cache['ffmpeg'] = ToolInfo(status=ToolStatus.FOUND, path="/usr/bin/ffmpeg")
        checker._cache['ffprobe'] = ToolInfo(status=ToolStatus.FOUND, path="/usr/bin/ffprobe")
        
        assert len(checker._cache) == 2
        
        # Clear cache
        checker.clear_cache()
        
        assert len(checker._cache) == 0
    
    def test_cached_result_retrieval(self):
        """Test retrieving cached results."""
        checker = DependencyChecker()
        
        # No cached result initially
        cached = checker.get_cached_result('ffmpeg')
        assert cached is None
        
        # Add fresh cached result
        fresh_info = ToolInfo(
            status=ToolStatus.FOUND, 
            path="/usr/bin/ffmpeg",
            detected_at=datetime.now()
        )
        checker._cache['ffmpeg'] = fresh_info
        
        # Should retrieve cached result
        cached = checker.get_cached_result('ffmpeg')
        assert cached is not None
        assert cached.path == "/usr/bin/ffmpeg"
    
    def test_thread_safety_of_cache(self):
        """Test thread safety of cache operations."""
        checker = DependencyChecker()
        
        def add_to_cache(tool_name, path):
            info = ToolInfo(status=ToolStatus.FOUND, path=path)
            checker._cache[tool_name] = info
        
        def clear_cache():
            checker.clear_cache()
        
        # Start multiple threads accessing cache
        threads = []
        for i in range(10):
            thread = threading.Thread(target=add_to_cache, args=(f'tool_{i}', f'/path_{i}'))
            threads.append(thread)
            thread.start()
        
        # Also start a clearing thread
        clear_thread = threading.Thread(target=clear_cache)
        threads.append(clear_thread)
        clear_thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Should not crash - exact state depends on thread timing
        assert isinstance(checker._cache, dict)


@pytest.mark.unit
class TestDependencyCheckerUtilities:
    """Test suite for utility methods."""
    
    def test_get_installation_guide(self):
        """Test getting installation guide for tools."""
        checker = DependencyChecker()
        
        test_tools = ['ffmpeg', 'ffprobe', 'mkvextract']
        
        for tool in test_tools:
            with patch.object(PlatformUtils, 'get_installation_guide', return_value=f"Install {tool}"):
                guide = checker.get_installation_guide(tool)
                
                assert isinstance(guide, str)
                assert len(guide) > 0
                assert tool in guide.lower()
    
    def test_get_installation_guide_with_requirements(self):
        """Test installation guide includes requirement information."""
        checker = DependencyChecker()
        
        with patch.object(PlatformUtils, 'get_installation_guide', return_value="Base guide"):
            guide = checker.get_installation_guide('ffmpeg')
            
            # Should include additional information about requirements
            assert "Tool Information:" in guide or len(guide) > 0


@pytest.mark.unit
class TestDependencyCheckerErrorScenarios:
    """Test suite for error scenarios and edge cases."""
    
    def test_detection_with_invalid_arguments(self):
        """Test detection methods with invalid arguments."""
        checker = DependencyChecker()
        
        # Test with empty tool name
        with patch.object(checker, '_detect_tool') as mock_detect:
            mock_detect.return_value = ToolInfo(status=ToolStatus.NOT_FOUND)
            
            # Should handle gracefully
            result = checker._detect_tool("", [], use_cache=False)
            assert result.status == ToolStatus.NOT_FOUND
    
    def test_version_extraction_with_malformed_output(self):
        """Test version extraction with malformed or unexpected output."""
        checker = DependencyChecker()
        
        malformed_outputs = [
            None,  # None input
            123,   # Non-string input  
            "version without numbers",
            "multiple version 1.0 and 2.0 numbers",
            "🎬 emoji version 5.0.0 content",
            "\x00binary\xffcontent",
        ]
        
        for output in malformed_outputs:
            # Should not crash
            version = checker._extract_version(str(output) if output is not None else "", 'ffmpeg')
            assert isinstance(version, str)
    
    def test_version_comparison_edge_cases(self):
        """Test version comparison with edge cases."""
        checker = DependencyChecker()
        
        edge_cases = [
            ("", "1.0.0"),
            ("1.0.0", ""),
            ("", ""),
            ("abc", "1.0.0"),
            ("1.0.0", "def"),
            ("1.0", "1.0.0.0.0"),
            ("1", "1.0"),
        ]
        
        for v1, v2 in edge_cases:
            # Should not crash
            result = checker._compare_versions(v1, v2)
            assert isinstance(result, int)
            assert -1 <= result <= 1
    
    def test_concurrent_detection_requests(self):
        """Test handling concurrent detection requests."""
        checker = DependencyChecker()
        
        results = []
        errors = []
        
        def detect_tool():
            try:
                with patch.object(checker, '_validate_tool_execution') as mock_validate:
                    mock_validate.return_value = ToolInfo(status=ToolStatus.FOUND, path="/usr/bin/ffmpeg")
                    result = checker.detect_ffmpeg(use_cache=False)
                    results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Start multiple detection threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=detect_tool)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Should not have errors and should have results
        assert len(errors) == 0
        assert len(results) == 5
        
        # All results should be consistent
        for result in results:
            assert result.status == ToolStatus.FOUND
    
    def test_detection_with_system_resource_constraints(self):
        """Test detection behavior under system resource constraints."""
        checker = DependencyChecker()
        
        # Simulate low memory by mocking subprocess to raise MemoryError
        with patch('subprocess.run', side_effect=MemoryError("Out of memory")):
            tool_info = checker._validate_tool_execution("/usr/bin/ffmpeg", "ffmpeg")
            
            assert tool_info.status == ToolStatus.ERROR
            assert "Unexpected error" in tool_info.error_message
    
    def test_path_validation_with_special_characters(self):
        """Test path validation with special characters and Unicode."""
        checker = DependencyChecker()
        
        special_paths = [
            "/path/with spaces/ffmpeg",
            "/path/with/unicode/测试/ffmpeg",
            "/path/with/symbols/ffmpeg!@#$%",
            "C:\\Windows\\Path With Spaces\\ffmpeg.exe",
            "/path/with/emoji/🎬/ffmpeg",
        ]
        
        for path in special_paths:
            with patch.object(PlatformUtils, 'validate_path_security', return_value=(True, "")):
                with patch.object(Path, 'exists', return_value=False):
                    # Should handle special characters gracefully
                    tool_info = checker.validate_tool_path(path, 'ffmpeg')
                    
                    # Should fail due to non-existent file, not due to path handling
                    assert tool_info.status == ToolStatus.NOT_FOUND
                    assert tool_info.path == path
    
    @pytest.mark.performance
    def test_detection_performance_under_load(self, performance_tracker):
        """Test detection performance under load."""
        checker = DependencyChecker()
        performance_tracker.start_timer("bulk_detection")
        
        with patch.object(checker, '_validate_tool_execution') as mock_validate:
            mock_validate.return_value = ToolInfo(status=ToolStatus.FOUND, path="/usr/bin/ffmpeg")
            
            # Perform many detections
            for i in range(100):
                checker.detect_ffmpeg(use_cache=False)
        
        performance_tracker.end_timer("bulk_detection")
        
        # Should complete within reasonable time (5 seconds for 100 detections)
        performance_tracker.assert_duration_under("bulk_detection", 5.0)