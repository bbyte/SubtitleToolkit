"""
Video Preview Dialog for SubtitleToolkit.

Provides an embedded video player with subtitle preview functionality.
Uses mpv for video playback with subtitle overlay.
"""

import sys
import locale
from pathlib import Path
from typing import Optional, List
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QSlider, QLabel, QWidget, QComboBox, QMessageBox
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QCloseEvent

# Fix locale issue for mpv
try:
    locale.setlocale(locale.LC_NUMERIC, 'C')
except Exception:
    pass

try:
    import mpv
    MPV_AVAILABLE = True
except (ImportError, OSError) as e:
    MPV_AVAILABLE = False
    MPV_ERROR = str(e)


class VideoPreviewDialog(QDialog):
    """
    Dialog for previewing video with subtitles using embedded mpv player.

    Features:
    - Embedded mpv video player
    - Play/pause, seek, volume controls
    - Subtitle visibility toggle
    - Multiple subtitle track selection
    - Subtitle position and size adjustment
    """

    def __init__(self, video_path: str, subtitle_paths: List[str] = None, parent=None):
        """
        Initialize video preview dialog.

        Args:
            video_path: Path to video file
            subtitle_paths: List of subtitle file paths (optional)
            parent: Parent widget
        """
        super().__init__(parent)

        self.video_path = Path(video_path)
        self.subtitle_paths = [Path(p) for p in (subtitle_paths or [])]
        self.player = None
        self.is_playing = False

        # Check if mpv is available
        if not MPV_AVAILABLE:
            self._show_mpv_error()
            self.reject()
            return

        self._setup_ui()
        self._init_player()
        self._connect_signals()

        # Start update timer for playback position
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_position)
        self.update_timer.start(100)  # Update every 100ms

    def _show_mpv_error(self) -> None:
        """Show error message if mpv is not available."""
        QMessageBox.critical(
            self.parent(),
            "MPV Not Available",
            f"Video preview requires mpv to be installed.\n\n"
            f"Error: {MPV_ERROR}\n\n"
            f"Please install:\n"
            f"  macOS: brew install mpv\n"
            f"  Ubuntu: sudo apt install libmpv-dev mpv\n"
            f"  Windows: choco install mpv"
        )

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        self.setWindowTitle(f"Preview: {self.video_path.name}")
        self.setModal(False)
        self.resize(1024, 700)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Video container (mpv will be embedded here)
        self.video_container = QWidget()
        self.video_container.setMinimumSize(640, 480)
        self.video_container.setStyleSheet("background-color: black;")
        layout.addWidget(self.video_container, 1)

        # Controls container
        controls_widget = QWidget()
        controls_widget.setStyleSheet("background-color: #2a2a2a; padding: 10px;")
        controls_layout = QVBoxLayout(controls_widget)

        # Progress bar
        progress_layout = QHBoxLayout()
        self.time_label = QLabel("00:00")
        self.time_label.setMinimumWidth(50)
        progress_layout.addWidget(self.time_label)

        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 1000)
        self.progress_slider.setValue(0)
        progress_layout.addWidget(self.progress_slider, 1)

        self.duration_label = QLabel("00:00")
        self.duration_label.setMinimumWidth(50)
        progress_layout.addWidget(self.duration_label)

        controls_layout.addLayout(progress_layout)

        # Playback controls
        playback_layout = QHBoxLayout()

        self.play_pause_btn = QPushButton("▶ Play")
        self.play_pause_btn.setMinimumWidth(100)
        playback_layout.addWidget(self.play_pause_btn)

        playback_layout.addSpacing(20)

        # Volume control
        volume_label = QLabel("Volume:")
        playback_layout.addWidget(volume_label)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.setMaximumWidth(150)
        playback_layout.addWidget(self.volume_slider)

        playback_layout.addStretch()

        # Subtitle controls
        if self.subtitle_paths:
            subtitle_label = QLabel("Subtitle:")
            playback_layout.addWidget(subtitle_label)

            self.subtitle_combo = QComboBox()
            self.subtitle_combo.addItem("No subtitles", None)
            for sub_path in self.subtitle_paths:
                self.subtitle_combo.addItem(sub_path.name, str(sub_path))
            self.subtitle_combo.setCurrentIndex(1 if self.subtitle_paths else 0)
            self.subtitle_combo.setMinimumWidth(200)
            playback_layout.addWidget(self.subtitle_combo)

            self.subtitle_visible_btn = QPushButton("Hide Subs")
            self.subtitle_visible_btn.setCheckable(True)
            self.subtitle_visible_btn.setChecked(False)
            playback_layout.addWidget(self.subtitle_visible_btn)

        playback_layout.addSpacing(20)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        playback_layout.addWidget(close_btn)

        controls_layout.addLayout(playback_layout)

        layout.addWidget(controls_widget)

    def _init_player(self) -> None:
        """Initialize mpv player."""
        try:
            # Ensure the widget is visible and has a valid window ID
            self.video_container.show()
            self.video_container.repaint()

            # Get window ID for embedding
            wid = int(self.video_container.winId())

            # Create mpv player instance with safe defaults
            self.player = mpv.MPV(
                wid=str(wid),
                vo='libmpv',
                keep_open='yes',
                osc='no',  # Disable on-screen controller (we have our own)
                input_default_bindings='no',
                input_vo_keyboard='no',
                ytdl=False,  # Disable youtube-dl
                log_handler=lambda level, component, message: None  # Suppress mpv logs
            )

            # Load video
            self.player.play(str(self.video_path))
            self.player.pause = True  # Start paused

            # Load first subtitle if available
            if self.subtitle_paths:
                self.player.sub_add(str(self.subtitle_paths[0]))

            # Set initial volume
            self.player.volume = 70

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            QMessageBox.critical(
                self,
                "Player Error",
                f"Failed to initialize video player:\n{str(e)}\n\nDetails:\n{error_details}"
            )
            self.reject()

    def _connect_signals(self) -> None:
        """Connect UI signals."""
        self.play_pause_btn.clicked.connect(self._toggle_play_pause)
        self.progress_slider.sliderMoved.connect(self._seek)
        self.volume_slider.valueChanged.connect(self._change_volume)

        if self.subtitle_paths:
            self.subtitle_combo.currentIndexChanged.connect(self._change_subtitle)
            self.subtitle_visible_btn.clicked.connect(self._toggle_subtitle_visibility)

    def _toggle_play_pause(self) -> None:
        """Toggle play/pause state."""
        if not self.player:
            return

        self.is_playing = not self.is_playing
        self.player.pause = not self.is_playing

        if self.is_playing:
            self.play_pause_btn.setText("⏸ Pause")
        else:
            self.play_pause_btn.setText("▶ Play")

    def _seek(self, position: int) -> None:
        """Seek to position in video."""
        if not self.player or not self.player.duration:
            return

        # Convert slider position (0-1000) to time
        time_pos = (position / 1000.0) * self.player.duration
        self.player.seek(time_pos, reference='absolute')

    def _change_volume(self, value: int) -> None:
        """Change player volume."""
        if self.player:
            self.player.volume = value

    def _change_subtitle(self, index: int) -> None:
        """Change subtitle track."""
        if not self.player:
            return

        subtitle_path = self.subtitle_combo.itemData(index)

        if subtitle_path:
            # Remove all subtitle tracks
            while self.player.sub:
                self.player.sub_remove()
            # Add selected subtitle
            self.player.sub_add(subtitle_path)
        else:
            # Remove all subtitles
            while self.player.sub:
                self.player.sub_remove()

    def _toggle_subtitle_visibility(self, checked: bool) -> None:
        """Toggle subtitle visibility."""
        if not self.player:
            return

        self.player.sub_visibility = not checked
        self.subtitle_visible_btn.setText("Show Subs" if checked else "Hide Subs")

    def _update_position(self) -> None:
        """Update playback position display."""
        if not self.player:
            return

        try:
            # Update time labels
            if self.player.time_pos is not None:
                current_time = self._format_time(self.player.time_pos)
                self.time_label.setText(current_time)

            if self.player.duration is not None:
                duration = self._format_time(self.player.duration)
                self.duration_label.setText(duration)

                # Update progress slider (without triggering seek)
                if not self.progress_slider.isSliderDown():
                    progress = int((self.player.time_pos / self.player.duration) * 1000)
                    self.progress_slider.setValue(progress)
        except Exception:
            pass  # Ignore errors during position update

    def _format_time(self, seconds: float) -> str:
        """Format time in seconds to MM:SS."""
        if seconds is None:
            return "00:00"
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"

    def closeEvent(self, event: QCloseEvent) -> None:
        """Clean up when dialog closes."""
        self.update_timer.stop()

        if self.player:
            try:
                self.player.terminate()
            except Exception:
                pass

        event.accept()
