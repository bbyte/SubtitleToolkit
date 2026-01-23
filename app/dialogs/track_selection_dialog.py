"""
Track Selection Dialog for SubtitleToolkit.

Shows a dialog allowing the user to select which subtitle track(s)
to extract when multiple tracks of the same language exist.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QFrame, QScrollArea, QWidget, QButtonGroup
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from typing import List, Optional

from ..utils.mkv_language_detector import SubtitleTrack


class TrackSelectionDialog(QDialog):
    """
    Dialog for selecting subtitle tracks when multiple tracks
    of the same language are available.
    """

    def __init__(self, tracks: List[SubtitleTrack], language_name: str, parent=None):
        """
        Initialize the track selection dialog.

        Args:
            tracks: List of SubtitleTrack objects to choose from
            language_name: Display name of the language (e.g., "English")
            parent: Parent widget
        """
        super().__init__(parent)

        self.tracks = tracks
        self.language_name = language_name
        self.selected_track_indices: List[int] = []

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        self.setWindowTitle(self.tr("Select Subtitle Track"))
        self.setModal(True)
        self.setMinimumWidth(450)
        self.setMaximumWidth(600)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel(self.tr(f"Multiple {self.language_name} Subtitle Tracks Found"))
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title.setFont(title_font)
        layout.addWidget(title)

        # Description
        desc = QLabel(self.tr(
            "The selected files contain multiple subtitle tracks for this language.\n"
            "Please select which track(s) to extract:"
        ))
        desc.setStyleSheet("color: #bbb;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Track selection area
        tracks_frame = QFrame()
        tracks_frame.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border: 1px solid #555;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        tracks_layout = QVBoxLayout(tracks_frame)
        tracks_layout.setSpacing(8)

        # Create checkboxes for each track
        self.track_checkboxes: List[QCheckBox] = []

        for i, track in enumerate(self.tracks):
            checkbox = QCheckBox()

            # Build track label with available info
            label_parts = [f"Track {i + 1}"]

            if track.title:
                label_parts.append(f'"{track.title}"')

            # Add flags
            flags = []
            if track.default:
                flags.append("Default")
            if track.forced:
                flags.append("Forced")
            if flags:
                label_parts.append(f"({', '.join(flags)})")

            # Add codec info
            if track.codec:
                label_parts.append(f"[{track.codec}]")

            checkbox.setText(" ".join(label_parts))
            checkbox.setProperty("track_index", track.index)

            # Style the checkbox
            checkbox.setStyleSheet("""
                QCheckBox {
                    color: #e0e0e0;
                    font-size: 11pt;
                    padding: 5px;
                }
                QCheckBox:hover {
                    background-color: #3a3a3a;
                    border-radius: 4px;
                }
            """)

            # Select first track by default, or default track if available
            if i == 0 or track.default:
                checkbox.setChecked(True)

            self.track_checkboxes.append(checkbox)
            tracks_layout.addWidget(checkbox)

        layout.addWidget(tracks_frame)

        # Select all checkbox
        self.select_all_checkbox = QCheckBox(self.tr("Select all tracks"))
        self.select_all_checkbox.setStyleSheet("color: #888; font-style: italic;")
        self.select_all_checkbox.toggled.connect(self._on_select_all_toggled)
        layout.addWidget(self.select_all_checkbox)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_button = QPushButton(self.tr("Cancel"))
        self.cancel_button.setMinimumWidth(100)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        self.ok_button = QPushButton(self.tr("OK"))
        self.ok_button.setMinimumWidth(100)
        self.ok_button.setDefault(True)
        self.ok_button.clicked.connect(self._on_ok_clicked)
        self.ok_button.setStyleSheet("""
            QPushButton {
                background-color: #2a82da;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #3a92ea;
            }
            QPushButton:pressed {
                background-color: #1a72ca;
            }
        """)
        button_layout.addWidget(self.ok_button)

        layout.addLayout(button_layout)

        # Update select all state based on initial selection (after buttons are created)
        self._update_select_all_state()

        # Connect individual checkboxes to update select all state
        for checkbox in self.track_checkboxes:
            checkbox.toggled.connect(self._update_select_all_state)

    def _on_select_all_toggled(self, checked: bool) -> None:
        """Handle select all checkbox toggle."""
        # Temporarily disconnect to avoid recursive updates
        for checkbox in self.track_checkboxes:
            checkbox.blockSignals(True)
            checkbox.setChecked(checked)
            checkbox.blockSignals(False)

    def _update_select_all_state(self) -> None:
        """Update select all checkbox based on individual selections."""
        all_checked = all(cb.isChecked() for cb in self.track_checkboxes)
        self.select_all_checkbox.blockSignals(True)
        self.select_all_checkbox.setChecked(all_checked)
        self.select_all_checkbox.blockSignals(False)

        # Disable OK if nothing selected
        any_checked = any(cb.isChecked() for cb in self.track_checkboxes)
        self.ok_button.setEnabled(any_checked)

    def _on_ok_clicked(self) -> None:
        """Handle OK button click."""
        # Collect selected track indices
        self.selected_track_indices = []
        for checkbox in self.track_checkboxes:
            if checkbox.isChecked():
                track_index = checkbox.property("track_index")
                self.selected_track_indices.append(track_index)

        self.accept()

    def get_selected_indices(self) -> List[int]:
        """
        Get the list of selected track indices.

        Returns:
            List of ffmpeg stream indices for selected tracks
        """
        return self.selected_track_indices

    @staticmethod
    def select_tracks(tracks: List[SubtitleTrack], language_name: str, parent=None) -> Optional[List[int]]:
        """
        Static convenience method to show dialog and get selection.

        Args:
            tracks: List of SubtitleTrack objects
            language_name: Display name of the language
            parent: Parent widget

        Returns:
            List of selected track indices, or None if cancelled
        """
        dialog = TrackSelectionDialog(tracks, language_name, parent)
        if dialog.exec() == QDialog.Accepted:
            return dialog.get_selected_indices()
        return None
