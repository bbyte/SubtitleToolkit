"""
Find Subtitles dialog.

Searches subtitle sites for a selected directory, shows results in a table,
and lets the user choose which subtitle to download.
"""

import json
import sys
from pathlib import Path
from typing import List, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QProgressBar, QComboBox, QGroupBox, QSplitter, QTextEdit,
    QDialogButtonBox, QMessageBox, QFrame, QWidget,
)
from PySide6.QtCore import Qt, Signal, QThread, QObject
from PySide6.QtGui import QFont, QColor

from app.config import ConfigManager


# ── Background worker ────────────────────────────────────────────────────────

class SubtitleSearchWorker(QObject):
    """Run find_subtitles.py in-process using the library directly."""

    progress = Signal(str)           # log message
    results_ready = Signal(list)     # list of result dicts
    movie_info_ready = Signal(dict)  # parsed movie info
    finished = Signal()
    error = Signal(str)

    def __init__(
        self,
        directory: str,
        language: str,
        fallback_language: str,
        provider_configs: list,
        ai_config: Optional[dict],
    ):
        super().__init__()
        self.directory = directory
        self.language = language
        self.fallback_language = fallback_language
        self.provider_configs = provider_configs
        self.ai_config = ai_config
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

            from scripts.lib.subtitle_finder import (
                SubtitleFinder, parse_nfo, parse_video_with_ffprobe,
                find_nfo_for_video,
            )
            from scripts.lib.subtitle_finder.nfo_parser import find_nfos_in_directory

            target = Path(self.directory)
            video_exts = {".mkv", ".mp4", ".avi", ".m4v", ".mov", ".wmv", ".ts", ".m2ts"}

            # Collect video files
            if target.is_file():
                videos = [target] if target.suffix.lower() in video_exts else []
            else:
                videos = sorted(p for p in target.iterdir()
                                if p.is_file() and p.suffix.lower() in video_exts)

            if not videos:
                self.error.emit("No video files found in the selected directory.")
                self.finished.emit()
                return

            finder = SubtitleFinder(self.provider_configs)
            all_results = []

            for video in videos:
                if self._cancelled:
                    break

                self.progress.emit(f"Processing: {video.name}")

                # Resolve movie info
                nfo = find_nfo_for_video(video)
                movie = None
                if nfo:
                    self.progress.emit(f"  Parsing NFO: {nfo.name}")
                    movie = parse_nfo(nfo, self.ai_config)
                    if movie:
                        movie.source_file = str(video)

                if not movie:
                    self.progress.emit(f"  Using ffprobe on: {video.name}")
                    movie = parse_video_with_ffprobe(video)

                if not movie:
                    from scripts.lib.subtitle_finder import MovieInfo
                    movie = MovieInfo(title=video.stem, source_file=str(video))

                self.movie_info_ready.emit({
                    "title": movie.title,
                    "original_title": movie.original_title,
                    "year": movie.year,
                    "imdb_id": movie.imdb_id,
                    "fps": movie.fps,
                    "original_language": movie.original_language,
                    "video_path": str(video),
                })

                self.progress.emit(
                    f"  Searching for '{movie.display_name()}' "
                    f"({self.language or 'any language'})…"
                )

                def _cb(msg: str) -> None:
                    self.progress.emit(f"    {msg}")

                results = finder.search(
                    movie,
                    language=self.language,
                    fallback_language=self.fallback_language if self.fallback_language != self.language else None,
                    progress_cb=_cb,
                    max_per_provider=10,
                )

                for r in results:
                    all_results.append({
                        "title": r.title,
                        "language": r.language,
                        "provider": r.provider,
                        "provider_id": r.provider_id,
                        "download_url": r.download_url,
                        "fps": r.fps,
                        "download_count": r.download_count,
                        "rating": r.rating,
                        "is_hearing_impaired": r.is_hearing_impaired,
                        "release_name": r.release_name,
                        "format": r.format,
                        "video_path": str(video),
                        "movie_title": movie.display_name(),
                    })

            self.results_ready.emit(all_results)

        except Exception as exc:
            self.error.emit(str(exc))
        finally:
            self.finished.emit()


# ── Download worker ──────────────────────────────────────────────────────────

class SubtitleDownloadWorker(QObject):
    finished = Signal(bool, str)  # success, message

    def __init__(self, result_dict: dict, dest_path: str, provider_configs: list):
        super().__init__()
        self.result_dict = result_dict
        self.dest_path = dest_path
        self.provider_configs = provider_configs

    def run(self):
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
            from scripts.lib.subtitle_finder import SubtitleFinder, SubtitleResult
            from scripts.lib.subtitle_finder.movie_info import ProviderConfig

            finder = SubtitleFinder(self.provider_configs)
            r = self.result_dict
            result = SubtitleResult(
                title=r["title"],
                language=r["language"],
                provider=r["provider"],
                provider_id=r["provider_id"],
                download_url=r.get("download_url"),
                fps=r.get("fps"),
                format=r.get("format", "srt"),
            )
            ok = finder.download(result, self.dest_path)
            if ok:
                self.finished.emit(True, f"Saved: {self.dest_path}")
            else:
                self.finished.emit(False, "Download failed — provider returned no data.")
        except Exception as exc:
            self.finished.emit(False, str(exc))


# ── Main dialog ──────────────────────────────────────────────────────────────

class FindSubtitlesDialog(QDialog):
    """
    Dialog for searching and downloading subtitles.

    Opens when the user clicks "Find Subtitles" in the main window.
    Runs the search in a background thread and presents results in a table.
    """

    def __init__(self, directory: str, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.directory = directory
        self.config_manager = config_manager
        self._results: List[dict] = []
        self._worker: Optional[SubtitleSearchWorker] = None
        self._thread: Optional[QThread] = None
        self._dl_thread: Optional[QThread] = None

        self.setWindowTitle("Find Subtitles")
        self.setMinimumSize(900, 650)
        self.resize(1100, 720)
        self.setModal(True)

        self._init_ui()
        self._start_search()

    # ── UI ───────────────────────────────────────────────────────────────────

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Header
        hdr = QLabel(f"<b>Searching subtitles in:</b> {self.directory}")
        hdr.setWordWrap(True)
        layout.addWidget(hdr)

        splitter = QSplitter(Qt.Vertical)

        # Results table
        results_widget = QWidget()
        results_layout = QVBoxLayout(results_widget)
        results_layout.setContentsMargins(0, 0, 0, 0)

        results_label = QLabel("Found subtitles:")
        results_label.setStyleSheet("font-weight: bold;")
        results_layout.addWidget(results_label)

        self.results_table = QTableWidget(0, 6)
        self.results_table.setHorizontalHeaderLabels(
            ["Language", "Provider", "Title / Release", "FPS", "Downloads", "HI"]
        )
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.results_table.itemDoubleClicked.connect(self._on_download_selected)
        results_layout.addWidget(self.results_table)

        splitter.addWidget(results_widget)

        # Log panel
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        log_layout.setContentsMargins(0, 0, 0, 0)
        log_label = QLabel("Search log:")
        log_label.setStyleSheet("font-weight: bold;")
        log_layout.addWidget(log_label)
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setMaximumHeight(140)
        self.log_edit.setStyleSheet("font-family: monospace; font-size: 11px;")
        log_layout.addWidget(self.log_edit)
        splitter.addWidget(log_widget)

        splitter.setSizes([480, 140])
        layout.addWidget(splitter)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # indeterminate
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximumHeight(6)
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("Searching…")
        self.status_label.setStyleSheet("color: #aaa; font-style: italic;")
        layout.addWidget(self.status_label)

        # Buttons
        btn_layout = QHBoxLayout()
        self.cancel_search_btn = QPushButton("Cancel Search")
        self.cancel_search_btn.clicked.connect(self._cancel_search)

        self.download_btn = QPushButton("Download Selected")
        self.download_btn.setEnabled(False)
        self.download_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a82da; color: white;
                font-weight: bold; border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #4dabf7; }
            QPushButton:disabled { background-color: #555; color: #999; }
        """)
        self.download_btn.clicked.connect(self._on_download_selected)

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.reject)

        btn_layout.addWidget(self.cancel_search_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.download_btn)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

        self.results_table.itemSelectionChanged.connect(self._on_selection_changed)

    # ── Search ───────────────────────────────────────────────────────────────

    def _start_search(self):
        sf_settings = self.config_manager.get_settings("subtitle_finder")
        provider_configs = sf_settings.get("providers", [])
        language = sf_settings.get("default_language", "")
        fallback_language = sf_settings.get("fallback_language", "")

        # Build AI config from translators settings
        ai_config = None
        if sf_settings.get("nfo_ai_fallback"):
            prov = sf_settings.get("nfo_ai_provider", "openai")
            model = sf_settings.get("nfo_ai_model", "gpt-4o-mini")
            translators = self.config_manager.get_settings("translators")
            api_key = translators.get(prov, {}).get("api_key", "")
            if api_key:
                ai_config = {"enabled": True, "provider": prov, "model": model, "api_key": api_key}

        self._worker = SubtitleSearchWorker(
            self.directory, language, fallback_language, provider_configs, ai_config
        )
        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_log)
        self._worker.results_ready.connect(self._on_results)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._on_search_finished)

        self._thread.start()

    def _cancel_search(self):
        if self._worker:
            self._worker.cancel()
        self.cancel_search_btn.setEnabled(False)
        self.status_label.setText("Cancelling…")

    def _on_log(self, msg: str):
        self.log_edit.append(msg)
        cursor = self.log_edit.textCursor()
        cursor.movePosition(cursor.End)
        self.log_edit.setTextCursor(cursor)

    def _on_results(self, results: list):
        self._results = results
        self.results_table.setRowCount(0)

        from scripts.lib.subtitle_finder.language_map import language_name

        for r in results:
            row = self.results_table.rowCount()
            self.results_table.insertRow(row)

            lang = language_name(r.get("language", ""))
            provider = r.get("provider", "")
            title = r.get("release_name") or r.get("title", "")
            fps = f"{r['fps']:.3f}" if r.get("fps") else ""
            dl = str(r.get("download_count", "")) if r.get("download_count") else ""
            hi = "HI" if r.get("is_hearing_impaired") else ""

            self.results_table.setItem(row, 0, self._cell(lang))
            self.results_table.setItem(row, 1, self._cell(provider))
            self.results_table.setItem(row, 2, self._cell(title))
            self.results_table.setItem(row, 3, self._cell(fps))
            self.results_table.setItem(row, 4, self._cell(dl))
            self.results_table.setItem(row, 5, self._cell(hi))

            # Colour preferred language rows
            sf = self.config_manager.get_settings("subtitle_finder")
            preferred = sf.get("default_language", "")
            if preferred and r.get("language") == preferred:
                for col in range(6):
                    item = self.results_table.item(row, col)
                    if item:
                        item.setBackground(QColor(30, 60, 30))

    def _on_error(self, msg: str):
        self._on_log(f"ERROR: {msg}")
        self.status_label.setText(f"Error: {msg}")
        self.status_label.setStyleSheet("color: #ff6b6b;")

    def _on_search_finished(self):
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1)
        self.cancel_search_btn.setEnabled(False)
        count = len(self._results)
        if count:
            self.status_label.setText(f"Found {count} subtitle(s). Double-click or select and click Download.")
            self.status_label.setStyleSheet("color: #66bb6a;")
        else:
            self.status_label.setText("No subtitles found.")
            self.status_label.setStyleSheet("color: #ffa726;")

        if self._thread:
            self._thread.quit()
            self._thread.wait()

    def _on_selection_changed(self):
        self.download_btn.setEnabled(bool(self.results_table.selectedItems()))

    @staticmethod
    def _cell(text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        return item

    # ── Download ─────────────────────────────────────────────────────────────

    def _on_download_selected(self):
        rows = self.results_table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        if row >= len(self._results):
            return

        result = self._results[row]
        video_path = Path(result.get("video_path", self.directory))
        lang = result.get("language", "xx")
        dest = str(video_path.with_suffix(f".{lang}.srt"))

        if Path(dest).exists():
            reply = QMessageBox.question(
                self, "Overwrite?",
                f"{Path(dest).name} already exists. Overwrite?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        self.download_btn.setEnabled(False)
        self.status_label.setText("Downloading…")
        self.status_label.setStyleSheet("color: #ffa726;")
        self.progress_bar.setRange(0, 0)

        sf_settings = self.config_manager.get_settings("subtitle_finder")
        provider_configs = sf_settings.get("providers", [])

        dl_worker = SubtitleDownloadWorker(result, dest, provider_configs)
        self._dl_thread = QThread(self)
        dl_worker.moveToThread(self._dl_thread)
        self._dl_thread.started.connect(dl_worker.run)
        dl_worker.finished.connect(self._on_download_finished)
        dl_worker.finished.connect(self._dl_thread.quit)
        self._dl_thread.start()

    def _on_download_finished(self, success: bool, message: str):
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1)
        self.download_btn.setEnabled(True)

        if success:
            self.status_label.setText(message)
            self.status_label.setStyleSheet("color: #66bb6a;")
            self._on_log(f"✓ {message}")
            QMessageBox.information(self, "Downloaded", message)
        else:
            self.status_label.setText(f"Download failed: {message}")
            self.status_label.setStyleSheet("color: #ff6b6b;")
            self._on_log(f"✗ {message}")
            QMessageBox.warning(self, "Download Failed", message)

    def closeEvent(self, event):
        if self._worker:
            self._worker.cancel()
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(2000)
        super().closeEvent(event)
