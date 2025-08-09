"""
Project Selector Widget

This widget provides a folder picker interface for selecting the project directory
that contains the video/subtitle files to be processed.
"""

from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QFileDialog, QGroupBox, QFrame
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont


class ProjectSelector(QFrame):
    """
    Widget for selecting the project directory.
    
    Provides a clean interface with:
    - Directory path display
    - Browse button for folder selection
    - Visual feedback for valid/invalid paths
    """
    
    # Signals
    directory_selected = Signal(str)  # Emitted when a valid directory is selected
    directory_cleared = Signal()     # Emitted when directory is cleared
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        
        self._selected_directory = ""
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
        title_label = QLabel(self.tr("Select Project Folder"))
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Directory selection layout
        dir_layout = QHBoxLayout()
        dir_layout.setSpacing(10)
        
        # Directory path input
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Select a directory containing video/subtitle files...")
        self.path_edit.setReadOnly(True)
        self.path_edit.setMinimumHeight(35)
        dir_layout.addWidget(self.path_edit)
        
        # Browse button
        self.browse_button = QPushButton("Browse...")
        self.browse_button.setMinimumHeight(35)
        self.browse_button.setMinimumWidth(100)
        dir_layout.addWidget(self.browse_button)
        
        # Clear button
        self.clear_button = QPushButton("Clear")
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
        self.browse_button.clicked.connect(self.select_directory)
        self.clear_button.clicked.connect(self.clear_directory)
        self.path_edit.textChanged.connect(self._on_path_changed)
    
    def select_directory(self) -> None:
        """Open file dialog to select project directory."""
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setOption(QFileDialog.ShowDirsOnly, True)
        dialog.setWindowTitle(self.tr("Select Project Folder"))
        
        # Set starting directory
        if self._selected_directory and Path(self._selected_directory).exists():
            dialog.setDirectory(self._selected_directory)
        else:
            dialog.setDirectory(str(Path.home()))
        
        if dialog.exec():
            selected_dirs = dialog.selectedFiles()
            if selected_dirs:
                self.set_directory(selected_dirs[0])
    
    def set_directory(self, directory: str) -> None:
        """Set the selected directory and validate it."""
        directory_path = Path(directory)
        
        if not directory_path.exists():
            self._show_status("error", f"Directory does not exist: {directory}")
            return
        
        if not directory_path.is_dir():
            self._show_status("error", f"Path is not a directory: {directory}")
            return
        
        # Update internal state
        self._selected_directory = str(directory_path.resolve())
        self.path_edit.setText(self._selected_directory)
        self.clear_button.setEnabled(True)
        
        # Analyze directory contents
        self._analyze_directory(directory_path)
        
        # Emit signal
        self.directory_selected.emit(self._selected_directory)
    
    def clear_directory(self) -> None:
        """Clear the selected directory."""
        self._selected_directory = ""
        self.path_edit.clear()
        self.clear_button.setEnabled(False)
        self.status_label.hide()
        
        # Emit signal
        self.directory_cleared.emit()
    
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
            else:
                self._show_status("warning", 
                    "No video or subtitle files found. "
                    "This directory may not contain processable content.")
                
        except Exception as e:
            self._show_status("error", f"Error analyzing directory: {str(e)}")
    
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
    
    @property
    def selected_directory(self) -> str:
        """Get the currently selected directory."""
        return self._selected_directory
    
    def is_directory_selected(self) -> bool:
        """Check if a valid directory is selected."""
        return bool(self._selected_directory and Path(self._selected_directory).exists())