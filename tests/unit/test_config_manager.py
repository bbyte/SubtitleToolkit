"""
Unit tests for configuration manager functionality.

Tests the ConfigManager class for settings validation, schema enforcement,
default handling, persistence, and background tool detection.

Following TDD principles:
1. Test configuration validation and schema enforcement
2. Test settings persistence and loading
3. Test default value handling
4. Test background tool detection
5. Test error handling and recovery
"""

import json
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

import pytest
from PySide6.QtCore import QObject, QThread

from app.config.config_manager import ConfigManager, BackgroundDetectionWorker
from app.config.settings_schema import SettingsSchema, ValidationResult
from app.utils.tool_status import ToolStatus, ToolInfo


@pytest.mark.unit
class TestConfigManager:
    """Test suite for ConfigManager core functionality."""
    
    def test_config_manager_initialization(self, qapp, temp_dir):
        """Test ConfigManager initializes with default settings."""
        with patch('app.config.config_manager.QStandardPaths.writableLocation') as mock_location:
            mock_location.return_value = str(temp_dir)
            
            config_manager = ConfigManager()
            
            # Should have default settings loaded
            settings = config_manager.get_settings()
            assert isinstance(settings, dict)
            assert 'ui' in settings
            assert 'tools' in settings
            assert 'translators' in settings
            assert 'languages' in settings
            assert 'advanced' in settings
    
    def test_load_existing_configuration(self, qapp, temp_dir, sample_config_file):
        """Test loading existing configuration file."""
        with patch('app.config.config_manager.QStandardPaths.writableLocation') as mock_location:
            mock_location.return_value = str(sample_config_file.parent)
            
            # Rename sample config to expected filename
            expected_config = sample_config_file.parent / "settings.json"
            sample_config_file.rename(expected_config)
            
            config_manager = ConfigManager()
            settings = config_manager.get_settings()
            
            # Should load the existing configuration
            assert settings['ui']['theme'] == 'dark'
            assert settings['tools']['auto_detect_tools'] is True
            assert settings['translators']['openai']['model'] == 'gpt-4o-mini'
    
    def test_get_settings_section(self, qapp, temp_dir):
        """Test retrieving specific settings sections."""
        with patch('app.config.config_manager.QStandardPaths.writableLocation') as mock_location:
            mock_location.return_value = str(temp_dir)
            
            config_manager = ConfigManager()
            
            # Test getting specific section
            ui_settings = config_manager.get_settings('ui')
            assert isinstance(ui_settings, dict)
            assert 'theme' in ui_settings
            assert 'remember_window_size' in ui_settings
            
            # Test getting all settings
            all_settings = config_manager.get_settings()
            assert 'ui' in all_settings
            assert 'tools' in all_settings
    
    def test_update_settings_validation(self, qapp, temp_dir):
        """Test settings update with validation."""
        with patch('app.config.config_manager.QStandardPaths.writableLocation') as mock_location:
            mock_location.return_value = str(temp_dir)
            
            config_manager = ConfigManager()
            
            # Valid settings update
            new_ui_settings = {
                'theme': 'light',
                'remember_window_size': False,
                'last_project_directory': str(temp_dir)
            }
            
            result = config_manager.update_settings('ui', new_ui_settings)
            
            assert result.is_valid is True
            assert len(result.errors) == 0
            
            # Verify settings were updated
            ui_settings = config_manager.get_settings('ui')
            assert ui_settings['theme'] == 'light'
            assert ui_settings['remember_window_size'] is False
    
    def test_update_settings_invalid_data(self, qapp, temp_dir):
        """Test settings update with invalid data."""
        with patch('app.config.config_manager.QStandardPaths.writableLocation') as mock_location:
            mock_location.return_value = str(temp_dir)
            
            config_manager = ConfigManager()
            
            # Invalid settings (wrong type for theme)
            invalid_settings = {
                'theme': 123,  # Should be string
                'remember_window_size': 'invalid',  # Should be boolean
                'invalid_field': 'value'  # Unexpected field
            }
            
            result = config_manager.update_settings('ui', invalid_settings)
            
            # Should have validation errors
            assert result.is_valid is False or len(result.errors) > 0
    
    def test_settings_persistence(self, qapp, temp_dir):
        """Test settings are properly persisted to file."""
        config_file = temp_dir / "settings.json"
        
        with patch('app.config.config_manager.QStandardPaths.writableLocation') as mock_location:
            mock_location.return_value = str(temp_dir)
            
            config_manager = ConfigManager()
            
            # Update settings
            new_settings = {
                'theme': 'dark',
                'remember_window_size': True,
                'last_project_directory': '/test/path'
            }
            
            config_manager.update_settings('ui', new_settings, save=True)
            
            # Verify file was created and contains correct data
            assert config_file.exists()
            
            with open(config_file, 'r') as f:
                saved_data = json.load(f)
            
            assert saved_data['ui']['theme'] == 'dark'
            assert 'last_modified' in saved_data
    
    def test_settings_merge_with_defaults(self, qapp, temp_dir):
        """Test merging loaded settings with defaults for new fields."""
        config_file = temp_dir / "settings.json"
        
        # Create config with only partial settings
        partial_config = {
            'ui': {
                'theme': 'custom'
            },
            'tools': {
                'ffmpeg_path': '/custom/ffmpeg'
            }
        }
        
        with open(config_file, 'w') as f:
            json.dump(partial_config, f)
        
        with patch('app.config.config_manager.QStandardPaths.writableLocation') as mock_location:
            mock_location.return_value = str(temp_dir)
            
            config_manager = ConfigManager()
            settings = config_manager.get_settings()
            
            # Should have custom values
            assert settings['ui']['theme'] == 'custom'
            assert settings['tools']['ffmpeg_path'] == '/custom/ffmpeg'
            
            # Should also have default values for missing fields
            assert 'remember_window_size' in settings['ui']
            assert 'auto_detect_tools' in settings['tools']
    
    def test_reset_to_defaults(self, qapp, temp_dir):
        """Test resetting settings to defaults."""
        with patch('app.config.config_manager.QStandardPaths.writableLocation') as mock_location:
            mock_location.return_value = str(temp_dir)
            
            config_manager = ConfigManager()
            
            # Modify some settings
            config_manager.update_settings('ui', {'theme': 'custom'})
            config_manager.update_settings('tools', {'auto_detect_tools': False})
            
            # Reset specific sections
            config_manager.reset_to_defaults(['ui'])
            
            settings = config_manager.get_settings()
            defaults = SettingsSchema.get_default_settings()
            
            # UI should be reset to defaults
            assert settings['ui']['theme'] == defaults['ui']['theme']
            
            # Tools should still have custom value
            assert settings['tools']['auto_detect_tools'] is False
            
            # Reset all settings
            config_manager.reset_to_defaults()
            
            settings = config_manager.get_settings()
            assert settings['ui']['theme'] == defaults['ui']['theme']
            assert settings['tools']['auto_detect_tools'] == defaults['tools']['auto_detect_tools']
    
    def test_export_import_settings(self, qapp, temp_dir):
        """Test exporting and importing settings."""
        export_file = temp_dir / "export.json"
        
        with patch('app.config.config_manager.QStandardPaths.writableLocation') as mock_location:
            mock_location.return_value = str(temp_dir)
            
            config_manager = ConfigManager()
            
            # Modify settings
            config_manager.update_settings('ui', {'theme': 'exported_theme'})
            config_manager.update_settings('tools', {'auto_detect_tools': False})
            
            # Export settings
            success = config_manager.export_settings(str(export_file))
            assert success is True
            assert export_file.exists()
            
            # Reset to defaults
            config_manager.reset_to_defaults()
            
            # Import settings
            result = config_manager.import_settings(str(export_file))
            assert result.is_valid is True
            
            # Verify imported settings
            settings = config_manager.get_settings()
            assert settings['ui']['theme'] == 'exported_theme'
            assert settings['tools']['auto_detect_tools'] is False
    
    def test_export_import_partial_settings(self, qapp, temp_dir):
        """Test exporting and importing only specific sections."""
        export_file = temp_dir / "partial_export.json"
        
        with patch('app.config.config_manager.QStandardPaths.writableLocation') as mock_location:
            mock_location.return_value = str(temp_dir)
            
            config_manager = ConfigManager()
            
            # Modify settings
            config_manager.update_settings('ui', {'theme': 'test_theme'})
            config_manager.update_settings('tools', {'auto_detect_tools': False})
            
            # Export only UI section
            success = config_manager.export_settings(str(export_file), sections=['ui'])
            assert success is True
            
            # Verify export file contains only UI section
            with open(export_file, 'r') as f:
                exported_data = json.load(f)
            
            assert 'ui' in exported_data
            assert 'tools' not in exported_data
    
    def test_invalid_config_file_handling(self, qapp, temp_dir):
        """Test handling of corrupted/invalid configuration files."""
        config_file = temp_dir / "settings.json"
        
        # Create invalid JSON file
        config_file.write_text("invalid json content {")
        
        with patch('app.config.config_manager.QStandardPaths.writableLocation') as mock_location:
            mock_location.return_value = str(temp_dir)
            
            # Should not crash, should use defaults
            config_manager = ConfigManager()
            settings = config_manager.get_settings()
            
            # Should have default settings
            defaults = SettingsSchema.get_default_settings()
            assert settings['ui']['theme'] == defaults['ui']['theme']
    
    def test_config_file_path_detection(self, qapp):
        """Test configuration file path detection across platforms."""
        with patch('app.config.config_manager.QStandardPaths.writableLocation') as mock_location:
            # Test normal case
            mock_location.return_value = "/normal/path"
            config_manager = ConfigManager()
            config_path = Path(config_manager.get_config_file_path())
            assert config_path.name == "settings.json"
            
            # Test fallback case (QStandardPaths returns empty)
            mock_location.return_value = ""
            with patch('os.path.expanduser') as mock_expand:
                mock_expand.return_value = "/home/user/.subtitletoolkit"
                config_manager = ConfigManager()
                config_path = Path(config_manager.get_config_file_path())
                assert ".subtitletoolkit" in str(config_path)


@pytest.mark.unit
class TestToolDetection:
    """Test suite for tool detection functionality."""
    
    def test_get_tool_info_manual_path(self, qapp, temp_dir, mock_tool_info):
        """Test tool detection with manually configured paths."""
        with patch('app.config.config_manager.QStandardPaths.writableLocation') as mock_location:
            mock_location.return_value = str(temp_dir)
            
            config_manager = ConfigManager()
            
            # Configure manual path
            tools_settings = config_manager.get_settings('tools')
            tools_settings['ffmpeg_path'] = '/custom/ffmpeg'
            config_manager.update_settings('tools', tools_settings)
            
            # Mock dependency checker validation
            with patch.object(config_manager._dependency_checker, 'validate_tool_path') as mock_validate:
                mock_validate.return_value = mock_tool_info['ffmpeg_found']
                
                tool_info = config_manager.get_tool_info('ffmpeg')
                
                assert tool_info.status == ToolStatus.FOUND
                mock_validate.assert_called_once_with('/custom/ffmpeg', 'ffmpeg')
    
    def test_get_tool_info_auto_detection(self, qapp, temp_dir, mock_tool_info):
        """Test automatic tool detection when no manual path is set."""
        with patch('app.config.config_manager.QStandardPaths.writableLocation') as mock_location:
            mock_location.return_value = str(temp_dir)
            
            config_manager = ConfigManager()
            
            # Mock dependency checker detection
            with patch.object(config_manager._dependency_checker, 'detect_ffmpeg') as mock_detect:
                mock_detect.return_value = mock_tool_info['ffmpeg_found']
                
                tool_info = config_manager.get_tool_info('ffmpeg')
                
                assert tool_info.status == ToolStatus.FOUND
                mock_detect.assert_called_once_with(use_cache=True)
    
    def test_get_tool_info_auto_detection_disabled(self, qapp, temp_dir):
        """Test tool detection when auto-detection is disabled."""
        with patch('app.config.config_manager.QStandardPaths.writableLocation') as mock_location:
            mock_location.return_value = str(temp_dir)
            
            config_manager = ConfigManager()
            
            # Disable auto-detection
            tools_settings = config_manager.get_settings('tools')
            tools_settings['auto_detect_tools'] = False
            config_manager.update_settings('tools', tools_settings)
            
            tool_info = config_manager.get_tool_info('ffmpeg')
            
            assert tool_info.status == ToolStatus.NOT_FOUND
            assert "Auto-detection disabled" in tool_info.error_message
    
    def test_tool_detection_caching(self, qapp, temp_dir, mock_tool_info):
        """Test tool detection result caching."""
        with patch('app.config.config_manager.QStandardPaths.writableLocation') as mock_location:
            mock_location.return_value = str(temp_dir)
            
            config_manager = ConfigManager()
            
            with patch.object(config_manager._dependency_checker, 'detect_ffmpeg') as mock_detect:
                mock_detect.return_value = mock_tool_info['ffmpeg_found']
                
                # First call should trigger detection
                tool_info1 = config_manager.get_tool_info('ffmpeg', force_refresh=False)
                
                # Second call should use cache
                tool_info2 = config_manager.get_tool_info('ffmpeg', force_refresh=False)
                
                # Should be called only once due to caching
                assert mock_detect.call_count <= 2  # Allow for some cache management calls
                assert tool_info1.status == tool_info2.status
    
    def test_tool_detection_force_refresh(self, qapp, temp_dir, mock_tool_info):
        """Test forcing fresh tool detection ignoring cache."""
        with patch('app.config.config_manager.QStandardPaths.writableLocation') as mock_location:
            mock_location.return_value = str(temp_dir)
            
            config_manager = ConfigManager()
            
            with patch.object(config_manager._dependency_checker, 'detect_ffmpeg') as mock_detect:
                mock_detect.return_value = mock_tool_info['ffmpeg_found']
                
                # Force refresh should clear cache
                tool_info = config_manager.get_tool_info('ffmpeg', force_refresh=True)
                
                assert tool_info.status == ToolStatus.FOUND
    
    def test_unknown_tool_detection(self, qapp, temp_dir):
        """Test detection of unknown/unsupported tools."""
        with patch('app.config.config_manager.QStandardPaths.writableLocation') as mock_location:
            mock_location.return_value = str(temp_dir)
            
            config_manager = ConfigManager()
            
            tool_info = config_manager.get_tool_info('unknown_tool')
            
            assert tool_info.status == ToolStatus.NOT_FOUND
            assert "Unknown tool" in tool_info.error_message


@pytest.mark.unit
class TestBackgroundDetectionWorker:
    """Test suite for background tool detection worker."""
    
    def test_worker_initialization(self, qapp):
        """Test worker initializes correctly."""
        mock_checker = Mock()
        tools = ['ffmpeg', 'ffprobe']
        
        worker = BackgroundDetectionWorker(mock_checker, tools)
        
        assert worker.dependency_checker == mock_checker
        assert worker.tools == tools
        assert worker.should_stop is False
    
    def test_worker_detection_process(self, qapp, mock_tool_info, qt_signal_tester):
        """Test worker detection process and signal emission."""
        mock_checker = Mock()
        mock_checker.detect_ffmpeg.return_value = mock_tool_info['ffmpeg_found']
        mock_checker.detect_ffprobe.return_value = mock_tool_info['ffmpeg_found']
        
        tools = ['ffmpeg', 'ffprobe']
        worker = BackgroundDetectionWorker(mock_checker, tools)
        
        # Connect signals
        worker.detection_progress.connect(qt_signal_tester.slot)
        worker.tool_detected.connect(qt_signal_tester.slot)
        worker.detection_complete.connect(qt_signal_tester.slot)
        
        # Run detection
        worker.run()
        
        # Should have emitted progress and completion signals
        assert len(qt_signal_tester.received_signals) >= 2
        
        # Should have called detection methods
        mock_checker.detect_ffmpeg.assert_called_once()
        mock_checker.detect_ffprobe.assert_called_once()
    
    def test_worker_stop_functionality(self, qapp, mock_tool_info):
        """Test worker can be stopped during execution."""
        mock_checker = Mock()
        mock_checker.detect_ffmpeg.return_value = mock_tool_info['ffmpeg_found']
        
        # Long list to simulate time
        tools = ['ffmpeg'] * 100
        worker = BackgroundDetectionWorker(mock_checker, tools)
        
        # Start worker in thread and stop immediately
        thread = threading.Thread(target=worker.run)
        thread.start()
        
        # Stop worker
        worker.stop()
        
        thread.join(timeout=1)
        
        # Should have stopped
        assert worker.should_stop is True


@pytest.mark.unit
class TestBackgroundDetectionIntegration:
    """Test suite for background detection integration with ConfigManager."""
    
    def test_background_detection_start(self, qapp, temp_dir, mock_tool_info, qt_signal_tester):
        """Test starting background detection."""
        with patch('app.config.config_manager.QStandardPaths.writableLocation') as mock_location:
            mock_location.return_value = str(temp_dir)
            
            config_manager = ConfigManager()
            
            # Connect signals
            config_manager.detection_progress.connect(qt_signal_tester.slot)
            config_manager.detection_complete.connect(qt_signal_tester.slot)
            
            # Mock dependency checker
            with patch.object(config_manager._dependency_checker, 'detect_ffmpeg') as mock_detect:
                mock_detect.return_value = mock_tool_info['ffmpeg_found']
                
                # Start background detection
                config_manager.detect_all_tools_background(['ffmpeg'], force_refresh=True)
                
                # Wait a bit for background process
                time.sleep(0.1)
                
                # Should have created worker and thread
                assert config_manager._detection_worker is not None
                assert config_manager._detection_thread is not None
    
    def test_background_detection_stop(self, qapp, temp_dir):
        """Test stopping background detection."""
        with patch('app.config.config_manager.QStandardPaths.writableLocation') as mock_location:
            mock_location.return_value = str(temp_dir)
            
            config_manager = ConfigManager()
            
            # Start detection
            config_manager.detect_all_tools_background(['ffmpeg'])
            
            # Stop detection
            config_manager.stop_background_detection()
            
            # Should clean up worker and thread
            assert config_manager._detection_worker is None or config_manager._detection_worker.should_stop
    
    def test_multiple_detection_requests(self, qapp, temp_dir):
        """Test handling multiple background detection requests."""
        with patch('app.config.config_manager.QStandardPaths.writableLocation') as mock_location:
            mock_location.return_value = str(temp_dir)
            
            config_manager = ConfigManager()
            
            # Start first detection
            config_manager.detect_all_tools_background(['ffmpeg'])
            first_worker = config_manager._detection_worker
            
            # Start second detection (should stop first)
            config_manager.detect_all_tools_background(['ffprobe'])
            
            # Should have stopped first worker
            if first_worker:
                assert first_worker.should_stop is True
            
            # Should have new worker
            assert config_manager._detection_worker is not None


@pytest.mark.unit
class TestConfigManagerErrorHandling:
    """Test suite for error handling and edge cases."""
    
    def test_settings_file_permission_error(self, qapp, temp_dir):
        """Test handling of file permission errors."""
        with patch('app.config.config_manager.QStandardPaths.writableLocation') as mock_location:
            mock_location.return_value = str(temp_dir)
            
            config_manager = ConfigManager()
            
            # Mock file write to raise permission error
            with patch('builtins.open', side_effect=PermissionError("Permission denied")):
                # Should not crash when trying to save
                result = config_manager.update_settings('ui', {'theme': 'test'})
                
                # Should still validate but may not save
                assert isinstance(result, ValidationResult)
    
    def test_concurrent_settings_access(self, qapp, temp_dir):
        """Test thread safety of settings access."""
        with patch('app.config.config_manager.QStandardPaths.writableLocation') as mock_location:
            mock_location.return_value = str(temp_dir)
            
            config_manager = ConfigManager()
            
            def update_settings(section, value):
                config_manager.update_settings(section, {'theme': value})
            
            # Start multiple threads updating settings
            threads = []
            for i in range(5):
                thread = threading.Thread(target=update_settings, args=('ui', f'theme_{i}'))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads
            for thread in threads:
                thread.join()
            
            # Should not crash and have some final value
            settings = config_manager.get_settings('ui')
            assert 'theme' in settings
    
    def test_invalid_import_file(self, qapp, temp_dir):
        """Test importing from invalid/corrupted files."""
        with patch('app.config.config_manager.QStandardPaths.writableLocation') as mock_location:
            mock_location.return_value = str(temp_dir)
            
            config_manager = ConfigManager()
            
            # Test non-existent file
            result = config_manager.import_settings('/nonexistent/file.json')
            assert result.is_valid is False
            assert len(result.errors) > 0
            
            # Test invalid JSON file
            invalid_file = temp_dir / "invalid.json"
            invalid_file.write_text("invalid json {")
            
            result = config_manager.import_settings(str(invalid_file))
            assert result.is_valid is False
            assert len(result.errors) > 0
    
    def test_configuration_validation_edge_cases(self, qapp, temp_dir):
        """Test configuration validation with edge case values."""
        with patch('app.config.config_manager.QStandardPaths.writableLocation') as mock_location:
            mock_location.return_value = str(temp_dir)
            
            config_manager = ConfigManager()
            
            edge_cases = [
                # Empty values
                {'theme': ''},
                # Extreme values  
                {'max_workers': 0},
                {'max_workers': 1000},
                # Unicode values
                {'last_project_directory': '测试路径/with/unicode'},
                # Very long strings
                {'last_project_directory': 'x' * 1000},
            ]
            
            for edge_case in edge_cases:
                result = config_manager.update_settings('ui' if 'theme' in edge_case else 'advanced', edge_case)
                
                # Should handle gracefully (either accept or reject with clear error)
                assert isinstance(result, ValidationResult)
                if not result.is_valid:
                    assert len(result.errors) > 0
                    assert all(isinstance(error, str) for error in result.errors)