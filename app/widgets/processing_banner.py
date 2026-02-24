"""
Processing Banner for SubtitleToolkit.

Inline, non-modal progress widget embedded directly in the main window.
Replaces the modal ProgressDialog so the user can still interact with the
Log and Results tabs while a stage is running.
"""

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QSizePolicy, QMessageBox
)
from PySide6.QtCore import Signal, Qt, QTimer


class ProcessingBanner(QFrame):
    """
    Compact inline progress widget embedded in the main window layout.

    Shows stage name, a progress bar, a status message and a Cancel button.
    Visibility is controlled via start_processing() / stop_processing() —
    no modal blocking, so all other window controls remain accessible.

    Public API mirrors ProgressDialog so existing call sites need no changes.

    Signals:
        cancel_requested: Emitted when the user confirms cancellation.
    """

    cancel_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._is_processing = False
        self._is_cancelling = False
        self._current_stage = ""
        self._animation_frame = 0

        self._setup_ui()
        self._setup_animation()

    # ── Setup ────────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.setStyleSheet("""
            ProcessingBanner {
                background-color: #1a1a2e;
                border: 1px solid #3a3a5a;
                border-radius: 6px;
            }
        """)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 8, 12, 8)
        outer.setSpacing(5)

        # Row 1: stage label + cancel button
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        self.stage_label = QLabel(self.tr("Initializing..."))
        self.stage_label.setStyleSheet(
            "font-weight: bold; color: #ffa726; font-size: 11pt;"
        )
        top_row.addWidget(self.stage_label, 1)

        self.cancel_button = QPushButton(self.tr("Cancel"))
        self.cancel_button.setMinimumWidth(90)
        self.cancel_button.setFixedHeight(26)
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 3px 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #e53935; }
            QPushButton:pressed { background-color: #b71c1c; }
            QPushButton:disabled { background-color: #555; color: #999; }
        """)
        top_row.addWidget(self.cancel_button)
        outer.addLayout(top_row)

        # Row 2: progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedHeight(16)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #555;
                border-radius: 4px;
                text-align: center;
                font-weight: bold;
                font-size: 10px;
                background: #2a2a3a;
                color: white;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2a82da, stop:1 #4dabf7);
                border-radius: 3px;
            }
        """)
        outer.addWidget(self.progress_bar)

        # Row 3: status message
        self.status_label = QLabel(self.tr("Starting..."))
        self.status_label.setStyleSheet("color: #aaa; font-size: 10pt;")
        self.status_label.setWordWrap(True)
        outer.addWidget(self.status_label)

        # Hidden until processing starts
        self.setVisible(False)

    def _setup_animation(self) -> None:
        self._animation_timer = QTimer(self)
        self._animation_timer.timeout.connect(self._animate)

    def _animate(self) -> None:
        if self._is_processing and not self._is_cancelling:
            dots = "." * (self._animation_frame % 4)
            base = self._current_stage or "Processing"
            self.stage_label.setText(f"{base}{dots}")
            self._animation_frame += 1

    # ── Public API (mirrors ProgressDialog) ──────────────────────────────────

    def start_processing(self, stages: list = None) -> None:
        """Show the banner and enter processing mode."""
        self._is_processing = True
        self._is_cancelling = False
        self._animation_frame = 0

        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self._current_stage = self.tr("Initializing")
        self.stage_label.setText(self.tr("Initializing..."))
        self.stage_label.setStyleSheet(
            "font-weight: bold; color: #ffa726; font-size: 11pt;"
        )
        self.status_label.setText(self.tr("Starting processing pipeline..."))

        self.cancel_button.setText(self.tr("Cancel"))
        self.cancel_button.setEnabled(True)
        self.cancel_button.setVisible(True)

        self.setVisible(True)
        self._animation_timer.start(500)

    def stop_processing(self, success: bool = True, message: str = "") -> None:
        """Stop processing mode and show completion state briefly."""
        self._is_processing = False
        self._animation_timer.stop()

        if success:
            self.stage_label.setText(self.tr("Completed Successfully"))
            self.stage_label.setStyleSheet(
                "font-weight: bold; color: #66bb6a; font-size: 11pt;"
            )
            self.progress_bar.setValue(100)
            self.status_label.setText(
                message or self.tr("Processing completed successfully")
            )
        else:
            label_text = (
                self.tr("Cancelled") if self._is_cancelling else self.tr("Failed")
            )
            self.stage_label.setText(label_text)
            self.stage_label.setStyleSheet(
                "font-weight: bold; color: #ff6b6b; font-size: 11pt;"
            )
            self.status_label.setText(message or self.tr("Processing failed"))

        self._is_cancelling = False
        self.cancel_button.setVisible(False)

        # Auto-hide after 3 seconds
        QTimer.singleShot(3000, self._auto_hide)

    def _auto_hide(self) -> None:
        if not self._is_processing:
            self.setVisible(False)

    def update_progress(self, progress: int, stage: str = "", message: str = "") -> None:
        if not self._is_processing:
            return
        self.progress_bar.setValue(max(0, min(100, progress)))
        if stage:
            self._current_stage = stage.title()
        if message:
            self.status_label.setText(message)

    def update_stage(self, stage: str, message: str = "") -> None:
        if not self._is_processing:
            return
        self._current_stage = stage.title()
        if message:
            self.status_label.setText(message)

    def add_log_message(self, level: str, message: str) -> None:
        """No-op — log messages go to the main window's Log tab."""
        pass

    def set_indeterminate(self, indeterminate: bool = True) -> None:
        if indeterminate:
            self.progress_bar.setRange(0, 0)
        else:
            self.progress_bar.setRange(0, 100)

    def is_processing(self) -> bool:
        return self._is_processing

    def is_cancelling(self) -> bool:
        return self._is_cancelling

    # ── Internal ─────────────────────────────────────────────────────────────

    def _on_cancel_clicked(self) -> None:
        if self._is_cancelling:
            return

        reply = QMessageBox.question(
            self,
            self.tr("Confirm Cancellation"),
            self.tr("Are you sure you want to cancel the current operation?"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self._is_cancelling = True
            self.cancel_button.setEnabled(False)
            self.cancel_button.setText(self.tr("Cancelling..."))
            self._current_stage = self.tr("Cancelling")
            self.stage_label.setText(self.tr("Cancelling..."))
            self.stage_label.setStyleSheet(
                "font-weight: bold; color: #ff9800; font-size: 11pt;"
            )
            self.status_label.setText(
                self.tr("Cancellation requested, please wait...")
            )
            self.cancel_requested.emit()
