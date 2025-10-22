"""
Project Selector Widget

This widget provides a folder picker interface for selecting the project directory
that contains the video/subtitle files to be processed.
"""

from pathlib import Path
from typing import List, Tuple, Optional
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QFileDialog, QGroupBox, QFrame, QRadioButton, QButtonGroup
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont

from app.utils.mkv_language_detector import MKVLanguageDetector, LanguageDetectionResult


class ProjectSelector(QFrame):
    """
    Widget for selecting either a project directory or a single file.
    
    Provides a clean interface with:
    - Mode selection (Directory vs Single File)
    - Path display with appropriate placeholders
    - Browse button for folder/file selection
    - Visual feedback for valid/invalid paths
    """
    
    # Signals
    directory_selected = Signal(str)  # Emitted when a valid directory is selected
    file_selected = Signal(str)      # Emitted when a valid file is selected
    selection_cleared = Signal()     # Emitted when selection is cleared
    languages_detected = Signal(object)  # Emitted when subtitle languages are detected (LanguageDetectionResult)
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        
        self._selected_path = ""
        self._is_directory_mode = True  # Default to directory mode
        self._last_language_detection = None  # Store last language detection result
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        self.setFrameStyle(QFrame.StyledPanel)
        self.setLineWidth(1)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Title
        self.title_label = QLabel(self.tr("Select Project Folder"))
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        self.title_label.setFont(title_font)
        layout.addWidget(self.title_label)
        
        # Mode selection
        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(20)
        
        # Directory mode radio button
        self.directory_radio = QRadioButton(self.tr("Directory"))
        self.directory_radio.setChecked(True)  # Default to directory mode
        self.directory_radio.setToolTip(self.tr("Process all files in a directory"))
        mode_layout.addWidget(self.directory_radio)
        
        # Single file mode radio button  
        self.file_radio = QRadioButton(self.tr("Single File"))
        self.file_radio.setToolTip(self.tr("Process a single MKV or SRT file"))
        mode_layout.addWidget(self.file_radio)
        
        # Button group to make radio buttons mutually exclusive
        self.mode_group = QButtonGroup()
        self.mode_group.addButton(self.directory_radio, 0)  # Directory mode = 0
        self.mode_group.addButton(self.file_radio, 1)       # File mode = 1
        
        mode_layout.addStretch()
        layout.addLayout(mode_layout)
        
        # Directory selection layout
        dir_layout = QHBoxLayout()
        dir_layout.setSpacing(10)
        
        # Path input
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText(self.tr("Select a directory containing video/subtitle files..."))
        self.path_edit.setReadOnly(True)
        self.path_edit.setMinimumHeight(35)
        dir_layout.addWidget(self.path_edit)
        
        # Browse button
        self.browse_button = QPushButton(self.tr("Browse..."))
        self.browse_button.setMinimumHeight(35)
        self.browse_button.setMinimumWidth(100)
        dir_layout.addWidget(self.browse_button)
        
        # Clear button
        self.clear_button = QPushButton(self.tr("Clear"))
        self.clear_button.setMinimumHeight(35)
        self.clear_button.setMinimumWidth(80)
        self.clear_button.setEnabled(False)
        dir_layout.addWidget(self.clear_button)
        
        layout.addLayout(dir_layout)
        
        # Status label
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.hide()  # Initially hidden
        layout.addWidget(self.status_label)
    
    def _connect_signals(self) -> None:
        """Connect internal signals and slots."""
        self.browse_button.clicked.connect(self._browse_path)
        self.clear_button.clicked.connect(self._clear_selection)
        self.path_edit.textChanged.connect(self._on_path_changed)
        self.mode_group.buttonToggled.connect(self._on_mode_changed)
    
    def _on_mode_changed(self, button, checked: bool) -> None:
        """Handle mode change between directory and file selection."""
        if not checked:  # Only respond to button being checked, not unchecked
            return
            
        self._is_directory_mode = (button == self.directory_radio)
        
        # Clear current selection when switching modes
        self._clear_selection()
        
        # Update UI elements based on mode
        if self._is_directory_mode:
            self.title_label.setText(self.tr("Select Project Folder"))
            self.path_edit.setPlaceholderText(self.tr("Select a directory containing video/subtitle files..."))
        else:
            self.title_label.setText(self.tr("Select Single File"))
            self.path_edit.setPlaceholderText(self.tr("Select an MKV or SRT file to process..."))
    
    def _browse_path(self) -> None:
        """Open file dialog to select directory or file based on current mode."""
        if self._is_directory_mode:
            self._select_directory()
        else:
            self._select_file()
    
    def _select_directory(self) -> None:
        """Open file dialog to select project directory."""
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setOption(QFileDialog.ShowDirsOnly, True)
        dialog.setWindowTitle(self.tr("Select Project Folder"))
        
        # Set starting directory
        if self._selected_path and Path(self._selected_path).exists():
            if Path(self._selected_path).is_dir():
                dialog.setDirectory(self._selected_path)
            else:
                dialog.setDirectory(str(Path(self._selected_path).parent))
        else:
            dialog.setDirectory(str(Path.home()))
        
        if dialog.exec():
            selected_dirs = dialog.selectedFiles()
            if selected_dirs:
                self._set_directory(selected_dirs[0])
    
    def _select_file(self) -> None:
        """Open file dialog to select single file."""
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.ExistingFile)
        dialog.setWindowTitle(self.tr("Select File"))
        
        # Set file filters for supported formats
        dialog.setNameFilter(self.tr("Video and Subtitle Files (*.mkv *.mp4 *.avi *.srt);;MKV Files (*.mkv);;SRT Files (*.srt);;All Files (*)"))
        
        # Set starting directory
        if self._selected_path and Path(self._selected_path).exists():
            if Path(self._selected_path).is_file():
                dialog.setDirectory(str(Path(self._selected_path).parent))
                dialog.selectFile(str(Path(self._selected_path).name))
            else:
                dialog.setDirectory(self._selected_path)
        else:
            dialog.setDirectory(str(Path.home()))
        
        if dialog.exec():
            selected_files = dialog.selectedFiles()
            if selected_files:
                self._set_file(selected_files[0])
    
    def _set_directory(self, directory: str) -> None:
        """Set the selected directory and validate it."""
        directory_path = Path(directory)
        
        if not directory_path.exists():
            self._show_status("error", self.tr("Directory does not exist: {0}").format(directory))
            return
        
        if not directory_path.is_dir():
            self._show_status("error", self.tr("Path is not a directory: {0}").format(directory))
            return
        
        # Update internal state
        self._selected_path = str(directory_path.resolve())
        self.path_edit.setText(self._selected_path)
        self.clear_button.setEnabled(True)
        
        # Analyze directory contents
        self._analyze_directory(directory_path)
        
        # Emit signal
        self.directory_selected.emit(self._selected_path)
    
    def _set_file(self, file_path: str) -> None:
        """Set the selected file and validate it."""
        file_path_obj = Path(file_path)
        
        if not file_path_obj.exists():
            self._show_status("error", self.tr("File does not exist: {0}").format(file_path))
            return
        
        if not file_path_obj.is_file():
            self._show_status("error", self.tr("Path is not a file: {0}").format(file_path))
            return
        
        # Check if file has supported extension
        supported_extensions = {'.mkv', '.mp4', '.avi', '.srt'}
        if file_path_obj.suffix.lower() not in supported_extensions:
            self._show_status("warning", self.tr("File type may not be supported: {0}").format(file_path_obj.suffix))
        
        # Update internal state
        self._selected_path = str(file_path_obj.resolve())
        self.path_edit.setText(self._selected_path)
        self.clear_button.setEnabled(True)
        
        # Analyze single file
        self._analyze_file(file_path_obj)
        
        # Emit signal
        self.file_selected.emit(self._selected_path)
    
    def _analyze_file(self, file_path: Path) -> None:
        """Analyze the selected single file and show relevant information."""
        try:
            file_ext = file_path.suffix.lower()
            file_size = file_path.stat().st_size
            
            # Format file size
            if file_size < 1024 * 1024:  # Less than 1MB
                size_str = f"{file_size // 1024} KB"
            elif file_size < 1024 * 1024 * 1024:  # Less than 1GB
                size_str = f"{file_size // (1024 * 1024)} MB"
            else:
                size_str = f"{file_size // (1024 * 1024 * 1024):.1f} GB"
            
            # Create status message based on file type
            if file_ext == '.mkv':
                # For MKV files, detect available subtitle languages
                self._detect_languages_in_mkv(file_path, size_str)
            elif file_ext in ['.mp4', '.avi']:
                status_message = self.tr("{0} video file ({1}) - limited processing options").format(file_ext.upper(), size_str)
                self._show_status("warning", status_message)
            elif file_ext == '.srt':
                status_message = self.tr("SRT subtitle file ({0}) - can translate or sync names").format(size_str)
                self._show_status("info", status_message)
            else:
                status_message = self.tr("File selected ({0}) - type: {1}").format(size_str, file_ext)
                self._show_status("info", status_message)
                
        except Exception as e:
            self._show_status("error", self.tr("Error analyzing file: {0}").format(str(e)))
    
    # Public interface methods
    def get_selected_path(self) -> str:
        """Get the currently selected path (directory or file)."""
        return self._selected_path
    
    def is_directory_mode(self) -> bool:
        """Check if currently in directory selection mode."""
        return self._is_directory_mode
    
    def is_file_mode(self) -> bool:
        """Check if currently in file selection mode."""
        return not self._is_directory_mode
    
    def set_mode(self, directory_mode: bool) -> None:
        """Set the selection mode programmatically."""
        if directory_mode:
            self.directory_radio.setChecked(True)
        else:
            self.file_radio.setChecked(True)
    
    # Backwards compatibility properties
    @property
    def selected_directory(self) -> str:
        """Get selected directory (backwards compatibility)."""
        return self._selected_path if self._is_directory_mode else ""
    
    def select_directory(self) -> None:
        """Public method to open directory selection dialog (backwards compatibility)."""
        self.set_mode(True)  # Switch to directory mode
        self._select_directory()
    
    def clear_directory(self) -> None:
        """Clear selection (backwards compatibility)."""
        self._clear_selection()
    
    def _clear_selection(self) -> None:
        """Clear the selected path."""
        self._selected_path = ""
        self._last_language_detection = None  # Clear language detection result
        self.path_edit.clear()
        self.clear_button.setEnabled(False)
        self.status_label.hide()
        
        # Emit signal
        self.selection_cleared.emit()
    
    def _on_path_changed(self, text: str) -> None:
        """Handle manual path changes (though read-only, this handles programmatic changes)."""
        if not text:
            self.clear_button.setEnabled(False)
            self.status_label.hide()
    
    def _analyze_directory(self, directory_path: Path) -> None:
        """Analyze the selected directory and show relevant information."""
        try:
            # Count different file types
            mkv_files = list(directory_path.glob("*.mkv"))
            mp4_files = list(directory_path.glob("*.mp4"))
            avi_files = list(directory_path.glob("*.avi"))
            srt_files = list(directory_path.glob("*.srt"))
            
            video_files = mkv_files + mp4_files + avi_files
            
            # Create status message
            status_parts = []
            
            if video_files:
                video_count = len(video_files)
                mkv_count = len(mkv_files)
                status_parts.append(f"{video_count} video file(s)")
                if mkv_count > 0:
                    status_parts.append(f"{mkv_count} MKV file(s) for subtitle extraction")
            
            if srt_files:
                status_parts.append(f"{len(srt_files)} SRT file(s)")
            
            if status_parts:
                status_message = f"Found: {', '.join(status_parts)}"
                self._show_status("info", status_message)
                
                # If there are MKV files, detect available subtitle languages
                if mkv_files:
                    self._detect_languages_in_directory(directory_path)
            else:
                self._show_status("warning", 
                    "No video or subtitle files found. "
                    "This directory may not contain processable content.")
                
        except Exception as e:
            self._show_status("error", f"Error analyzing directory: {str(e)}")
    
    def _detect_languages_in_mkv(self, file_path: Path, size_str: str) -> None:
        """Detect available subtitle languages in a single MKV file."""
        try:
            # Perform language detection
            detection_result = MKVLanguageDetector.detect_languages_in_path(file_path)
            
            # Store the result
            self._last_language_detection = detection_result
            
            # Emit the detection result
            self.languages_detected.emit(detection_result)
            
            # Update status message based on detection results
            if detection_result.errors:
                error_msg = "; ".join(detection_result.errors[:2])  # Show first 2 errors
                status_message = self.tr("MKV file ({0}) - Error detecting languages: {1}").format(size_str, error_msg)
                self._show_status("warning", status_message)
            elif not detection_result.available_languages:
                status_message = self.tr("MKV file ({0}) - No subtitle tracks found").format(size_str)
                self._show_status("warning", status_message)
            else:
                # Format language list for display
                lang_names = [name for _, name in detection_result.available_languages[:5]]  # Show first 5
                if len(detection_result.available_languages) > 5:
                    lang_display = f"{', '.join(lang_names[:4])}, +{len(detection_result.available_languages)-4} more"
                else:
                    lang_display = ', '.join(lang_names)
                
                status_message = self.tr("MKV file ({0}) - Subtitles: {1}").format(size_str, lang_display)
                self._show_status("info", status_message)
                
        except Exception as e:
            error_msg = self.tr("Failed to detect languages: {0}").format(str(e))
            status_message = self.tr("MKV file ({0}) - {1}").format(size_str, error_msg)
            self._show_status("error", status_message)
    
    def _detect_languages_in_directory(self, directory_path: Path) -> None:
        """Detect available subtitle languages in all MKV files in a directory."""
        try:
            # Perform language detection across all MKV files
            detection_result = MKVLanguageDetector.detect_languages_in_path(directory_path)
            
            # Store the result
            self._last_language_detection = detection_result
            
            # Emit the detection result
            self.languages_detected.emit(detection_result)
            
            # Update status message to include language information
            if detection_result.errors:
                # Don't show language info if there were errors
                pass  # Keep the existing status message
            elif detection_result.available_languages:
                # Format language list for display
                lang_names = [name for _, name in detection_result.available_languages[:5]]  # Show first 5
                if len(detection_result.available_languages) > 5:
                    lang_display = f"{', '.join(lang_names[:4])}, +{len(detection_result.available_languages)-4} more"
                else:
                    lang_display = ', '.join(lang_names)
                
                # Append language info to existing status
                current_status = self.status_label.text()
                enhanced_status = f"{current_status} - Available subtitles: {lang_display}"
                self._show_status("info", enhanced_status)
                
        except Exception as e:
            # Don't fail the entire directory analysis if language detection fails
            # Just log the error silently - the basic file counting already succeeded
            pass
    
    def _show_status(self, level: str, message: str) -> None:
        """Show status message with appropriate styling."""
        self.status_label.setText(message)
        self.status_label.show()
        
        # Apply styling based on level
        if level == "error":
            self.status_label.setStyleSheet("color: #ff6b6b; font-weight: bold;")
        elif level == "warning":
            self.status_label.setStyleSheet("color: #ffa726; font-weight: bold;")
        elif level == "info":
            self.status_label.setStyleSheet("color: #66bb6a; font-weight: bold;")
        else:
            self.status_label.setStyleSheet("")
    
    def is_selection_valid(self) -> bool:
        """Check if the current selection is valid."""
        return bool(self._selected_path and Path(self._selected_path).exists())
    
    def get_detected_languages(self) -> List[Tuple[str, str]]:
        """
        Get the list of detected subtitle languages from the last analysis.
        
        Returns:
            List of (language_code, display_name) tuples, or empty list if no languages detected
        """
        if self._last_language_detection:
            return self._last_language_detection.available_languages
        return []
    
    def get_language_detection_result(self) -> Optional[LanguageDetectionResult]:
        """
        Get the complete language detection result from the last analysis.
        
        Returns:
            LanguageDetectionResult object or None if no detection has been performed
        """
        return self._last_language_detection