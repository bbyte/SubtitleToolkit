"""
Progress Dialog for SubtitleToolkit.

Modal dialog that displays processing progress with real-time updates,
log output, and cancel functionality.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QTextEdit, QFrame, QSizePolicy
)
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QFont, QTextCursor


class ProgressDialog(QDialog):
    """
    Modal dialog for displaying processing progress.

    Features:
    - Progress bar with stage indication
    - Real-time log output
    - Cancel button with confirmation
    - Auto-closes on completion (optional)
    - Prevents user from closing during critical operations

    Signals:
        cancel_requested: Emitted when user clicks Cancel button
        dialog_closed: Emitted when dialog is closed (by user or programmatically)
    """

    # Signals
    cancel_requested = Signal()
    dialog_closed = Signal()

    def __init__(self, parent=None, auto_close_on_success: bool = False):
        """
        Initialize the progress dialog.

        Args:
            parent: Parent widget
            auto_close_on_success: If True, dialog auto-closes on successful completion
        """
        super().__init__(parent)

        self._is_processing = False
        self._is_cancelling = False
        self._current_stage = ""
        self._current_progress = 0
        self._auto_close = auto_close_on_success
        self._success = False

        self._setup_ui()
        self._setup_animation()

        # Prevent closing during processing (until cancel is confirmed)
        self.setWindowFlags(
            Qt.Window |
            Qt.WindowTitleHint |
            Qt.CustomizeWindowHint
        )

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        self.setWindowTitle(self.tr("Processing"))
        self.setModal(True)
        self.setMinimumSize(500, 250)
        self.resize(600, 280)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title and stage section
        title_layout = QVBoxLayout()

        # Main title
        self.title_label = QLabel(self.tr("Processing Progress"))
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(14)
        self.title_label.setFont(title_font)
        title_layout.addWidget(self.title_label)

        # Current stage
        self.stage_label = QLabel(self.tr("Initializing..."))
        self.stage_label.setStyleSheet("font-weight: bold; color: #2a82da; font-size: 12pt;")
        title_layout.addWidget(self.stage_label)

        layout.addLayout(title_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedHeight(30)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #555;
                border-radius: 8px;
                text-align: center;
                font-weight: bold;
                font-size: 13px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2a82da, stop:1 #4dabf7);
                border-radius: 6px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Status message
        self.status_label = QLabel(self.tr("Starting processing..."))
        self.status_label.setStyleSheet("color: #bbb; font-size: 11pt;")
        self.status_label.setWordWrap(True)
        self.status_label.setMinimumHeight(40)
        layout.addWidget(self.status_label)

        # Add spacer to push buttons to bottom
        layout.addStretch()

        # Button layout
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # Cancel button
        self.cancel_button = QPushButton(self.tr("Cancel"))
        self.cancel_button.setMinimumWidth(120)
        self.cancel_button.setMinimumHeight(35)
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover {
                background-color: #e53935;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #999;
            }
        """)
        button_layout.addWidget(self.cancel_button)

        # Close button (hidden initially, shown on completion)
        self.close_button = QPushButton(self.tr("Close"))
        self.close_button.setMinimumWidth(120)
        self.close_button.setMinimumHeight(35)
        self.close_button.clicked.connect(self.accept)
        self.close_button.setVisible(False)
        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: #1976d2;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover {
                background-color: #2196f3;
            }
            QPushButton:pressed {
                background-color: #0d47a1;
            }
        """)
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)


    def _setup_animation(self) -> None:
        """Set up processing animation."""
        self._animation_timer = QTimer()
        self._animation_timer.timeout.connect(self._animate_processing)
        self._animation_frame = 0

    def _animate_processing(self) -> None:
        """Animate the stage label with dots."""
        if self._is_processing and not self._is_cancelling:
            dots = "." * (self._animation_frame % 4)
            base_text = self._current_stage or "Processing"
            self.stage_label.setText(f"{base_text}{dots}")
            self._animation_frame += 1

    def start_processing(self, stages: list = None) -> None:
        """
        Start processing mode.

        Args:
            stages: List of stages that will be processed
        """
        self._is_processing = True
        self._is_cancelling = False
        self._success = False
        self._current_progress = 0
        self._animation_frame = 0

        # Update UI
        self.progress_bar.setValue(0)
        self._current_stage = self.tr("Initializing")
        self.stage_label.setText(self.tr("Initializing..."))
        self.stage_label.setStyleSheet("font-weight: bold; color: #ffa726; font-size: 12pt;")
        self.status_label.setText(self.tr("Starting processing pipeline..."))

        # Show cancel button, hide close button
        self.cancel_button.setVisible(True)
        self.cancel_button.setEnabled(True)
        self.close_button.setVisible(False)

        # Start animation
        self._animation_timer.start(500)

    def stop_processing(self, success: bool = True, message: str = "") -> None:
        """
        Stop processing mode.

        Args:
            success: Whether processing completed successfully
            message: Final status message
        """
        self._is_processing = False
        self._is_cancelling = False
        self._success = success
        self._animation_timer.stop()

        if success:
            self.stage_label.setText(self.tr("Completed Successfully"))
            self.stage_label.setStyleSheet("font-weight: bold; color: #66bb6a; font-size: 12pt;")
            self.progress_bar.setValue(100)
            self.status_label.setText(message or self.tr("Processing completed successfully"))

            # Auto-close if configured
            if self._auto_close:
                QTimer.singleShot(2000, self.accept)  # Close after 2 seconds
        else:
            self.stage_label.setText(self.tr("Failed") if not self._is_cancelling else self.tr("Cancelled"))
            self.stage_label.setStyleSheet("font-weight: bold; color: #ff6b6b; font-size: 12pt;")
            self.status_label.setText(message or self.tr("Processing failed"))

        # Show close button, hide cancel button
        self.cancel_button.setVisible(False)
        self.close_button.setVisible(True)

    def update_progress(self, progress: int, stage: str = "", message: str = "") -> None:
        """
        Update progress information.

        Args:
            progress: Progress percentage (0-100)
            stage: Current stage name
            message: Status message
        """
        if not self._is_processing:
            return

        # Update progress
        self._current_progress = max(0, min(100, progress))
        self.progress_bar.setValue(self._current_progress)

        # Update stage if provided
        if stage:
            self._current_stage = stage.title()
            # Don't update label here - let animation handle it

        # Update status message if provided
        if message:
            self.status_label.setText(message)

    def update_stage(self, stage: str, message: str = "") -> None:
        """
        Update the current processing stage.

        Args:
            stage: Stage name
            message: Status message
        """
        if not self._is_processing:
            return

        self._current_stage = stage.title()

        if message:
            self.status_label.setText(message)

    def add_log_message(self, level: str, message: str) -> None:
        """
        Add a message to the log output.

        Note: Log output has been removed from the progress dialog.
        This method is kept for compatibility but does nothing.

        Args:
            level: Message level (debug, info, warning, error, success)
            message: Message text
        """
        # Log output removed - messages only go to main window log panel
        pass

    def set_indeterminate(self, indeterminate: bool = True) -> None:
        """
        Set progress bar to indeterminate mode.

        Args:
            indeterminate: If True, show indeterminate progress
        """
        if indeterminate:
            self.progress_bar.setRange(0, 0)  # Indeterminate mode
        else:
            self.progress_bar.setRange(0, 100)  # Normal mode

    def is_processing(self) -> bool:
        """Check if currently in processing mode."""
        return self._is_processing

    def is_cancelling(self) -> bool:
        """Check if cancellation is in progress."""
        return self._is_cancelling

    def _on_cancel_clicked(self) -> None:
        """Handle cancel button click."""
        if self._is_cancelling:
            return  # Already cancelling

        # Confirm cancellation
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            self.tr("Confirm Cancellation"),
            self.tr("Are you sure you want to cancel the current operation?"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self._is_cancelling = True
            self.cancel_button.setEnabled(False)
            self.cancel_button.setText(self.tr("Cancelling..."))
            self.stage_label.setText(self.tr("Cancelling..."))
            self.stage_label.setStyleSheet("font-weight: bold; color: #ff9800; font-size: 12pt;")
            self.status_label.setText(self.tr("Cancellation requested, please wait..."))

            # Emit signal to notify main window
            self.cancel_requested.emit()

    def closeEvent(self, event) -> None:
        """Handle dialog close event."""
        # Allow closing only if not processing or if processing is complete
        if self._is_processing and not self._is_cancelling:
            # Ask for confirmation if still processing
            from PySide6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self,
                self.tr("Confirm Close"),
                self.tr("Processing is still in progress. Closing will cancel the operation.\n\nAre you sure?"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.No:
                event.ignore()
                return

            # User confirmed - trigger cancellation
            self._is_cancelling = True
            self.cancel_requested.emit()

        # Emit closed signal
        self.dialog_closed.emit()

        event.accept()
