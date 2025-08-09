"""
Action Buttons Widget

This widget provides the main action buttons for controlling the processing pipeline:
- Run: Start processing
- Cancel: Stop/cancel processing  
- Open Output: Open the output directory
"""

from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QFrame, QLabel
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont, QIcon


class ActionButtons(QFrame):
    """
    Widget containing the main action buttons for the application.
    
    Provides:
    - Run button (start processing)
    - Cancel button (stop processing)
    - Open Output button (open results directory)
    - Visual feedback for different states
    """
    
    # Signals
    run_clicked = Signal()
    cancel_clicked = Signal()
    open_output_clicked = Signal()
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        
        self._is_running = False
        self._run_enabled = False
        self._output_directory = ""
        
        self._setup_ui()
        self._connect_signals()
        self._update_button_states()
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        self.setFrameStyle(QFrame.StyledPanel)
        self.setLineWidth(1)
        self.setFixedHeight(80)
        
        # Main layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # Status indicator (left side)
        self.status_label = QLabel(self.tr("Ready to process"))
        self.status_label.setStyleSheet("color: #bbb; font-style: italic;")
        layout.addWidget(self.status_label)
        
        # Spacer to push buttons to the right
        layout.addStretch()
        
        # Run button
        self.run_button = QPushButton(self.tr("Run"))
        self.run_button.setMinimumSize(120, 40)
        self.run_button.setStyleSheet("""
            QPushButton {
                background-color: #2a82da;
                color: white;
                font-weight: bold;
                font-size: 12px;
                border: 2px solid #2a82da;
                border-radius: 8px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #4dabf7;
                border-color: #4dabf7;
            }
            QPushButton:pressed {
                background-color: #1976d2;
                border-color: #1976d2;
            }
            QPushButton:disabled {
                background-color: #555;
                border-color: #555;
                color: #999;
            }
        """)
        layout.addWidget(self.run_button)
        
        # Cancel button
        self.cancel_button = QPushButton(self.tr("Cancel"))
        self.cancel_button.setMinimumSize(100, 40)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #666;
                color: white;
                font-weight: bold;
                font-size: 12px;
                border: 2px solid #666;
                border-radius: 8px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #ff6b6b;
                border-color: #ff6b6b;
            }
            QPushButton:pressed {
                background-color: #f03e3e;
                border-color: #f03e3e;
            }
            QPushButton:disabled {
                background-color: #333;
                border-color: #333;
                color: #666;
            }
        """)
        self.cancel_button.setEnabled(False)
        layout.addWidget(self.cancel_button)
        
        # Open Output button
        self.open_output_button = QPushButton("Open Output")
        self.open_output_button.setMinimumSize(100, 40)
        self.open_output_button.setStyleSheet("""
            QPushButton {
                background-color: #666;
                color: white;
                font-weight: bold;
                font-size: 12px;
                border: 2px solid #666;
                border-radius: 8px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #777;
                border-color: #777;
            }
            QPushButton:pressed {
                background-color: #555;
                border-color: #555;
            }
            QPushButton:disabled {
                background-color: #333;
                border-color: #333;
                color: #666;
            }
        """)
        self.open_output_button.setEnabled(False)
        layout.addWidget(self.open_output_button)
    
    def _connect_signals(self) -> None:
        """Connect internal signals."""
        self.run_button.clicked.connect(self._on_run_clicked)
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        self.open_output_button.clicked.connect(self._on_open_output_clicked)
    
    def _on_run_clicked(self) -> None:
        """Handle run button click."""
        if not self._is_running:
            self.run_clicked.emit()
    
    def _on_cancel_clicked(self) -> None:
        """Handle cancel button click."""
        if self._is_running:
            self.cancel_clicked.emit()
    
    def _on_open_output_clicked(self) -> None:
        """Handle open output button click."""
        self.open_output_clicked.emit()
    
    def set_running_state(self, running: bool) -> None:
        """Set the running state and update button states accordingly."""
        self._is_running = running
        self._update_button_states()
        
        if running:
            self.status_label.setText("Processing...")
            self.status_label.setStyleSheet("color: #ffa726; font-style: italic; font-weight: bold;")
        else:
            self.status_label.setText("Ready to process")
            self.status_label.setStyleSheet("color: #bbb; font-style: italic;")
    
    def set_run_enabled(self, enabled: bool) -> None:
        """Enable or disable the run button."""
        self._run_enabled = enabled
        self._update_button_states()
    
    def set_output_directory(self, directory: str) -> None:
        """Set the output directory and enable the open output button."""
        self._output_directory = directory
        has_output = bool(directory and Path(directory).exists())
        self.open_output_button.setEnabled(has_output)
        
        if has_output:
            self.open_output_button.setToolTip(f"Open {directory}")
        else:
            self.open_output_button.setToolTip("No output directory available")
    
    def set_processing_complete(self, success: bool = True, message: str = "") -> None:
        """Set the state to indicate processing completion."""
        self._is_running = False
        self._update_button_states()
        
        if success:
            self.status_label.setText(message or "Processing completed successfully")
            self.status_label.setStyleSheet("color: #66bb6a; font-style: italic; font-weight: bold;")
            
            # Flash the button green briefly
            self.run_button.setStyleSheet("""
                QPushButton {
                    background-color: #66bb6a;
                    color: white;
                    font-weight: bold;
                    font-size: 12px;
                    border: 2px solid #66bb6a;
                    border-radius: 8px;
                    padding: 8px 16px;
                }
            """)
            
            # Reset button style after 2 seconds
            from PySide6.QtCore import QTimer
            QTimer.singleShot(2000, self._reset_run_button_style)
            
        else:
            self.status_label.setText(message or "Processing failed")
            self.status_label.setStyleSheet("color: #ff6b6b; font-style: italic; font-weight: bold;")
            
            # Flash the button red briefly
            self.run_button.setStyleSheet("""
                QPushButton {
                    background-color: #ff6b6b;
                    color: white;
                    font-weight: bold;
                    font-size: 12px;
                    border: 2px solid #ff6b6b;
                    border-radius: 8px;
                    padding: 8px 16px;
                }
            """)
            
            # Reset button style after 2 seconds
            from PySide6.QtCore import QTimer
            QTimer.singleShot(2000, self._reset_run_button_style)
    
    def _reset_run_button_style(self) -> None:
        """Reset the run button to its default style."""
        self.run_button.setStyleSheet("""
            QPushButton {
                background-color: #2a82da;
                color: white;
                font-weight: bold;
                font-size: 12px;
                border: 2px solid #2a82da;
                border-radius: 8px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #4dabf7;
                border-color: #4dabf7;
            }
            QPushButton:pressed {
                background-color: #1976d2;
                border-color: #1976d2;
            }
            QPushButton:disabled {
                background-color: #555;
                border-color: #555;
                color: #999;
            }
        """)
    
    def _update_button_states(self) -> None:
        """Update button enabled states based on current conditions."""
        # Run button: enabled if not running and configuration is valid
        self.run_button.setEnabled(not self._is_running and self._run_enabled)
        
        # Cancel button: enabled only when running
        self.cancel_button.setEnabled(self._is_running)
        
        # Update button text based on running state
        if self._is_running:
            self.run_button.setText(self.tr("Running..."))
        else:
            self.run_button.setText(self.tr("Run"))
    
    def reset_status(self) -> None:
        """Reset to initial status."""
        self._is_running = False
        self.status_label.setText(self.tr("Ready to process"))
        self.status_label.setStyleSheet("color: #bbb; font-style: italic;")
        self._update_button_states()
        self._reset_run_button_style()
    
    @property
    def is_running(self) -> bool:
        """Check if processing is currently running."""
        return self._is_running
    
    @property
    def run_enabled(self) -> bool:
        """Check if the run button is enabled."""
        return self._run_enabled
    
    def set_status_message(self, message: str, level: str = "info") -> None:
        """Set a custom status message with styling."""
        self.status_label.setText(message)
        
        if level == "error":
            self.status_label.setStyleSheet("color: #ff6b6b; font-style: italic; font-weight: bold;")
        elif level == "warning":
            self.status_label.setStyleSheet("color: #ffa726; font-style: italic; font-weight: bold;")
        elif level == "success":
            self.status_label.setStyleSheet("color: #66bb6a; font-style: italic; font-weight: bold;")
        else:  # info
            self.status_label.setStyleSheet("color: #bbb; font-style: italic;")
    
    def get_button_states(self) -> dict:
        """Get the current state of all buttons."""
        return {
            "is_running": self._is_running,
            "run_enabled": self._run_enabled,
            "cancel_enabled": self.cancel_button.isEnabled(),
            "open_output_enabled": self.open_output_button.isEnabled()
        }