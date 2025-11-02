"""
Video Preview Dialog for SubtitleToolkit.

Provides an embedded video player with subtitle preview functionality.
Uses mpv for video playback with subtitle overlay.
"""

import sys
import locale
import threading
from pathlib import Path
from typing import Optional, List
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QSlider, QLabel, QWidget, QComboBox, QMessageBox
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread, QObject
from PySide6.QtGui import QCloseEvent
from PySide6.QtOpenGLWidgets import QOpenGLWidget

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


class MpvPlayerWorker(QObject):
    """Worker that handles mpv operations in a separate thread."""

    ready = Signal()
    position_changed = Signal(float)  # current position
    duration_changed = Signal(float)  # total duration
    error_occurred = Signal(str)

    def __init__(self, wid: int, video_path: str, subtitle_paths: List[str] = None):
        super().__init__()
        self.wid = wid
        self.video_path = video_path
        self.subtitle_paths = subtitle_paths or []
        self.player = None
        self._lock = threading.Lock()

    def initialize(self):
        """Initialize the mpv player."""
        try:
            # Set locale in thread
            try:
                locale.setlocale(locale.LC_NUMERIC, 'C')
            except Exception:
                pass

            # Create mpv player with event-driven approach
            self.player = mpv.MPV(
                wid=str(self.wid),
                keep_open='yes',
                osc='no',
                input_default_bindings='no',
                input_vo_keyboard='no',
                ytdl=False,
                vo='gpu',
                hwdec='auto',
                pause=True,
                log_handler=self._log_handler,
                msg_level='all=no',
                force_window='yes',
                idle='yes',
                # Set window title
                title=f'SubtitleToolkit - {Path(self.video_path).name}',
                # Keep window on top initially so it's visible
                ontop='yes',
                # Disable terminal usage
                terminal='no',
                # Ensure it quits when told
                input_terminal='no'
            )

            # Register event callbacks
            @self.player.property_observer('time-pos')
            def time_observer(_name, value):
                if value is not None:
                    self.position_changed.emit(value)

            @self.player.property_observer('duration')
            def duration_observer(_name, value):
                if value is not None:
                    self.duration_changed.emit(value)

            # Load video
            self.player.play(str(self.video_path))

            # Set initial volume
            self.player.volume = 70

            # Load subtitles after a delay using threading.Timer
            import time
            def load_subs_delayed():
                time.sleep(0.5)
                self._load_subtitles()
            threading.Timer(0.5, load_subs_delayed).start()

            # Emit ready signal after a short delay
            def emit_ready():
                time.sleep(0.2)
                self.ready.emit()
            threading.Timer(0.2, emit_ready).start()

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error_occurred.emit(str(e))

    def _log_handler(self, level, component, message):
        """Suppress mpv logs."""
        pass

    def _load_subtitles(self):
        """Load subtitle files."""
        if self.player and self.subtitle_paths:
            try:
                self.player.sub_add(str(self.subtitle_paths[0]))
            except Exception as e:
                print(f"Error loading subtitles: {e}")

    def toggle_pause(self):
        """Toggle play/pause state."""
        if self.player:
            with self._lock:
                try:
                    # Use command instead of property for non-blocking
                    self.player.command('cycle', 'pause')
                except Exception as e:
                    print(f"Error toggling pause: {e}")

    def seek(self, position: float):
        """Seek to position."""
        if self.player:
            with self._lock:
                try:
                    self.player.command('seek', str(position), 'absolute')
                except Exception as e:
                    print(f"Error seeking: {e}")

    def set_volume(self, value: int):
        """Set volume."""
        if self.player:
            with self._lock:
                try:
                    self.player.volume = value
                except Exception as e:
                    print(f"Error setting volume: {e}")

    def change_subtitle(self, subtitle_path: Optional[str]):
        """Change subtitle track."""
        if self.player:
            with self._lock:
                try:
                    if subtitle_path:
                        self.player.command('sub-remove')
                        self.player.sub_add(subtitle_path)
                    else:
                        self.player.command('sub-remove')
                except Exception as e:
                    print(f"Error changing subtitle: {e}")

    def set_subtitle_visibility(self, visible: bool):
        """Set subtitle visibility."""
        if self.player:
            with self._lock:
                try:
                    self.player.sub_visibility = visible
                except Exception as e:
                    print(f"Error setting subtitle visibility: {e}")

    def cleanup(self):
        """Clean up the player - non-blocking."""
        if self.player:
            player_ref = self.player
            self.player = None  # Clear reference immediately

            # Run cleanup in background thread to avoid blocking
            def do_cleanup():
                try:
                    # Send quit command
                    player_ref.command('quit')
                except Exception:
                    pass

                # Small delay to let quit process
                import time
                time.sleep(0.1)

                # Force terminate if still alive
                try:
                    if hasattr(player_ref, '_MPV__handle') and player_ref._MPV__handle:
                        import mpv as mpv_module
                        mpv_module._mpv_terminate_destroy(player_ref._MPV__handle)
                        player_ref._MPV__handle = None
                except Exception:
                    pass

            # Run in daemon thread so it doesn't block
            threading.Thread(target=do_cleanup, daemon=True).start()


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
        self.worker = None
        self.worker_thread = None
        self.is_playing = False
        self.duration = 0.0
        self.position = 0.0
        self.player_initialized = False

        # Check if mpv is available
        if not MPV_AVAILABLE:
            self._show_mpv_error()
            self.reject()
            return

        self._setup_ui()
        self._connect_signals()

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
        self.resize(800, 200)  # Smaller window since video opens separately

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Video container - hidden since video opens in separate window
        # But still needed for window ID
        self.video_container = QOpenGLWidget()
        self.video_container.setFixedSize(1, 1)  # Minimal size
        self.video_container.setAttribute(Qt.WA_DontCreateNativeAncestors)
        self.video_container.setAttribute(Qt.WA_NativeWindow)
        self.video_container.hide()  # Hide it completely
        layout.addWidget(self.video_container)

        # Info label
        info_label = QLabel(f"<b>Video:</b> {self.video_path.name}")
        info_label.setStyleSheet("color: #fff; font-size: 12px;")
        layout.addWidget(info_label)

        # Controls container
        controls_widget = QWidget()
        controls_widget.setStyleSheet("background-color: #2a2a2a; padding: 15px; border-radius: 8px;")
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

        # Playback controls - split into two rows for better spacing
        playback_row1 = QHBoxLayout()

        self.play_pause_btn = QPushButton("▶ Play")
        self.play_pause_btn.setMinimumWidth(120)
        self.play_pause_btn.setMinimumHeight(40)
        self.play_pause_btn.setEnabled(False)  # Disable until player is ready
        playback_row1.addWidget(self.play_pause_btn)

        playback_row1.addSpacing(15)

        # Volume control with more space
        volume_label = QLabel("Volume:")
        volume_label.setStyleSheet("color: #fff;")
        playback_row1.addWidget(volume_label)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.setMinimumWidth(200)
        playback_row1.addWidget(self.volume_slider)

        self.volume_label = QLabel("70%")
        self.volume_label.setMinimumWidth(40)
        self.volume_label.setStyleSheet("color: #fff;")
        playback_row1.addWidget(self.volume_label)

        playback_row1.addStretch()

        # Close button
        close_btn = QPushButton("Close")
        close_btn.setMinimumWidth(100)
        close_btn.setMinimumHeight(40)
        close_btn.clicked.connect(self.close)
        playback_row1.addWidget(close_btn)

        controls_layout.addLayout(playback_row1)

        # Second row for subtitle controls if available
        if self.subtitle_paths:
            playback_row2 = QHBoxLayout()

            subtitle_label = QLabel("Subtitle:")
            subtitle_label.setStyleSheet("color: #fff;")
            playback_row2.addWidget(subtitle_label)

            self.subtitle_combo = QComboBox()
            self.subtitle_combo.addItem("No subtitles", None)
            for sub_path in self.subtitle_paths:
                self.subtitle_combo.addItem(sub_path.name, str(sub_path))
            self.subtitle_combo.setCurrentIndex(1 if self.subtitle_paths else 0)
            self.subtitle_combo.setMinimumWidth(300)
            playback_row2.addWidget(self.subtitle_combo)

            self.subtitle_visible_btn = QPushButton("Hide Subs")
            self.subtitle_visible_btn.setCheckable(True)
            self.subtitle_visible_btn.setChecked(False)
            self.subtitle_visible_btn.setMinimumWidth(120)
            playback_row2.addWidget(self.subtitle_visible_btn)

            playback_row2.addStretch()

            controls_layout.addLayout(playback_row2)

        layout.addWidget(controls_widget)

    def _init_player(self) -> None:
        """Initialize mpv player in worker thread."""
        try:
            # Ensure the widget is visible and has a valid window ID
            self.video_container.show()
            self.video_container.repaint()

            # Get window ID for embedding
            wid = int(self.video_container.winId())

            # Create worker thread
            self.worker_thread = QThread()
            self.worker = MpvPlayerWorker(wid, str(self.video_path), [str(p) for p in self.subtitle_paths])

            # Move worker to thread
            self.worker.moveToThread(self.worker_thread)

            # Connect signals
            self.worker.ready.connect(self._on_player_ready)
            self.worker.position_changed.connect(self._on_position_changed)
            self.worker.duration_changed.connect(self._on_duration_changed)
            self.worker.error_occurred.connect(self._on_player_error)

            # Start thread and initialize player
            self.worker_thread.started.connect(self.worker.initialize)
            self.worker_thread.start()

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            QMessageBox.critical(
                self,
                "Player Error",
                f"Failed to initialize video player:\n{str(e)}\n\nDetails:\n{error_details}"
            )
            self.reject()

    def _on_player_ready(self):
        """Called when player is ready."""
        self.play_pause_btn.setEnabled(True)

    def _on_position_changed(self, position: float):
        """Called when playback position changes."""
        self.position = position
        self.time_label.setText(self._format_time(position))

        # Update progress slider (without triggering seek)
        if self.duration > 0 and not self.progress_slider.isSliderDown():
            progress = int((position / self.duration) * 1000)
            self.progress_slider.setValue(progress)

    def _on_duration_changed(self, duration: float):
        """Called when duration is known."""
        self.duration = duration
        self.duration_label.setText(self._format_time(duration))

    def _on_player_error(self, error: str):
        """Called when player error occurs."""
        QMessageBox.critical(self, "Player Error", f"Player error: {error}")

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
        if not self.worker:
            return

        self.is_playing = not self.is_playing
        self.worker.toggle_pause()

        if self.is_playing:
            self.play_pause_btn.setText("⏸ Pause")
        else:
            self.play_pause_btn.setText("▶ Play")

    def _seek(self, position: int) -> None:
        """Seek to position in video."""
        if not self.worker or self.duration == 0:
            return

        # Convert slider position (0-1000) to time
        time_pos = (position / 1000.0) * self.duration
        self.worker.seek(time_pos)

    def _change_volume(self, value: int) -> None:
        """Change player volume."""
        if self.worker:
            self.worker.set_volume(value)
        # Update volume label
        self.volume_label.setText(f"{value}%")

    def _change_subtitle(self, index: int) -> None:
        """Change subtitle track."""
        if not self.worker:
            return

        subtitle_path = self.subtitle_combo.itemData(index)
        self.worker.change_subtitle(subtitle_path)

    def _toggle_subtitle_visibility(self, checked: bool) -> None:
        """Toggle subtitle visibility."""
        if not self.worker:
            return

        self.worker.set_subtitle_visibility(not checked)
        self.subtitle_visible_btn.setText("Show Subs" if checked else "Hide Subs")

    def _format_time(self, seconds: float) -> str:
        """Format time in seconds to MM:SS."""
        if seconds is None:
            return "00:00"
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"

    def showEvent(self, event) -> None:
        """Initialize player when dialog is shown."""
        super().showEvent(event)

        # Initialize player only once, after the dialog is visible
        if not self.player_initialized:
            self.player_initialized = True
            # Delay initialization slightly to ensure window is fully rendered
            QTimer.singleShot(100, self._init_player)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Clean up when dialog closes."""
        # Clean up worker - this is now non-blocking
        if self.worker:
            self.worker.cleanup()

        # Stop worker thread without blocking
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.quit()
            # Don't wait - let it terminate on its own

        # Accept immediately
        event.accept()
