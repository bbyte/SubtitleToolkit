"""
Progress Section Widget

This widget displays real-time progress information during processing operations.
Includes progress bars, status text, and stage indicators.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QFrame
)
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QFont, QMovie


class ProgressSection(QFrame):
    """
    Widget for displaying processing progress and status.
    
    Shows:
    - Overall progress bar
    - Current stage indicator
    - Status messages
    - Processing animation
    """
    
    # Signals
    progress_updated = Signal(int)  # Progress percentage (0-100)
    status_updated = Signal(str)   # Status message
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        
        self._current_stage = ""
        self._current_progress = 0
        self._is_processing = False
        
        self._setup_ui()
        self._setup_animation()
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        self.setFrameStyle(QFrame.StyledPanel)
        self.setLineWidth(1)
        self.setFixedHeight(120)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Title
        title_label = QLabel("Processing Progress")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #555;
                border-radius: 8px;
                text-align: center;
                font-weight: bold;
                font-size: 12px;
                height: 25px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2a82da, stop:1 #4dabf7);
                border-radius: 6px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Status layout
        status_layout = QHBoxLayout()
        
        # Current stage indicator
        self.stage_label = QLabel("Ready")
        self.stage_label.setStyleSheet("font-weight: bold; color: #2a82da;")
        status_layout.addWidget(self.stage_label)
        
        # Spacer
        status_layout.addStretch()
        
        # Processing indicator (animated dots)
        self.processing_label = QLabel("")
        self.processing_label.setStyleSheet("color: #bbb;")
        status_layout.addWidget(self.processing_label)
        
        layout.addLayout(status_layout)
        
        # Detailed status message
        self.status_label = QLabel("Select a project and stages to begin processing")
        self.status_label.setStyleSheet("color: #bbb; font-size: 11px;")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
    
    def _setup_animation(self) -> None:
        """Set up processing animation."""
        self._animation_timer = QTimer()
        self._animation_timer.timeout.connect(self._animate_processing)
        self._animation_frame = 0
        self._animation_patterns = ["", ".", "..", "..."]
    
    def _animate_processing(self) -> None:
        """Animate the processing indicator."""
        if self._is_processing:
            pattern = self._animation_patterns[self._animation_frame % len(self._animation_patterns)]
            self.processing_label.setText(f"Processing{pattern}")
            self._animation_frame += 1
        else:
            self.processing_label.setText("")
    
    def start_processing(self, stages: list = None) -> None:
        """Start processing mode with optional stage list."""
        self._is_processing = True
        self._current_progress = 0
        self._animation_frame = 0
        
        # Update UI
        self.progress_bar.setValue(0)
        self.stage_label.setText("Initializing...")
        self.status_label.setText("Starting processing pipeline...")
        
        # Start animation
        self._animation_timer.start(500)  # Update every 500ms
        
        # Apply processing styles
        self.stage_label.setStyleSheet("font-weight: bold; color: #ffa726;")
        self.setStyleSheet("border: 2px solid #ffa726;")
    
    def stop_processing(self, success: bool = True, message: str = "") -> None:
        """Stop processing mode."""
        self._is_processing = False
        self._animation_timer.stop()
        
        if success:
            self.stage_label.setText("Completed")
            self.stage_label.setStyleSheet("font-weight: bold; color: #66bb6a;")
            self.progress_bar.setValue(100)
            self.status_label.setText(message or "Processing completed successfully")
            self.setStyleSheet("border: 2px solid #66bb6a;")
        else:
            self.stage_label.setText("Failed")
            self.stage_label.setStyleSheet("font-weight: bold; color: #ff6b6b;")
            self.status_label.setText(message or "Processing failed")
            self.setStyleSheet("border: 2px solid #ff6b6b;")
        
        self.processing_label.setText("")
    
    def reset(self) -> None:
        """Reset to initial state."""
        self._is_processing = False
        self._current_progress = 0
        self._animation_timer.stop()
        
        # Reset UI
        self.progress_bar.setValue(0)
        self.stage_label.setText("Ready")
        self.stage_label.setStyleSheet("font-weight: bold; color: #2a82da;")
        self.status_label.setText("Select a project and stages to begin processing")
        self.processing_label.setText("")
        self.setStyleSheet("")
    
    def update_progress(self, progress: int, stage: str = "", message: str = "") -> None:
        """Update progress information."""
        if not self._is_processing:
            return
        
        # Update progress
        self._current_progress = max(0, min(100, progress))
        self.progress_bar.setValue(self._current_progress)
        
        # Update stage if provided
        if stage:
            self._current_stage = stage
            self.stage_label.setText(f"{stage.title()} Stage")
        
        # Update status message if provided
        if message:
            self.status_label.setText(message)
        
        # Emit signal
        self.progress_updated.emit(self._current_progress)
        if message:
            self.status_updated.emit(message)
    
    def update_stage(self, stage: str, message: str = "") -> None:
        """Update the current processing stage."""
        if not self._is_processing:
            return
        
        self._current_stage = stage
        self.stage_label.setText(f"{stage.title()} Stage")
        
        if message:
            self.status_label.setText(message)
            self.status_updated.emit(message)
    
    def set_indeterminate(self, indeterminate: bool = True) -> None:
        """Set progress bar to indeterminate mode."""
        if indeterminate:
            self.progress_bar.setRange(0, 0)  # Indeterminate mode
        else:
            self.progress_bar.setRange(0, 100)  # Normal mode
    
    def get_current_progress(self) -> int:
        """Get the current progress percentage."""
        return self._current_progress
    
    def get_current_stage(self) -> str:
        """Get the current processing stage."""
        return self._current_stage
    
    def is_processing(self) -> bool:
        """Check if currently in processing mode."""
        return self._is_processing