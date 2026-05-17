"""
File Filter Dialog

Allows users to select which files in a directory will be included in processing.
"""

from pathlib import Path
from typing import List

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QPushButton, QDialogButtonBox, QWidget
)
from PySide6.QtCore import Qt


# Extensions treated as processable
VIDEO_EXTENSIONS = {'.mkv', '.mp4', '.avi', '.mov', '.m4v', '.webm', '.ts', '.m2ts'}
SUBTITLE_EXTENSIONS = {'.srt', '.ass', '.ssa'}


class FileFilterDialog(QDialog):
    """
    Dialog that lists all processable files in a directory as checkboxes.

    All items are checked by default. The user can deselect items to exclude
    them from processing.
    """

    def __init__(self, directory: str, parent: QWidget = None):
        super().__init__(parent)
        self._directory = directory
        self._setup_ui()
        self._populate_files()

    def _setup_ui(self) -> None:
        """Build the dialog UI."""
        self.setWindowTitle("Filter Files")
        self.setMinimumSize(500, 400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Header label
        header = QLabel("Select files to include in processing:")
        layout.addWidget(header)

        # Select All / Deselect All toolbar
        toolbar_layout = QHBoxLayout()
        self.select_all_button = QPushButton("Select All")
        self.deselect_all_button = QPushButton("Deselect All")
        self.select_all_button.clicked.connect(self._select_all)
        self.deselect_all_button.clicked.connect(self._deselect_all)
        toolbar_layout.addWidget(self.select_all_button)
        toolbar_layout.addWidget(self.deselect_all_button)
        toolbar_layout.addStretch()
        layout.addLayout(toolbar_layout)

        # File list
        self.file_list = QListWidget()
        self.file_list.itemChanged.connect(self._update_count_label)
        layout.addWidget(self.file_list)

        # Count label
        self.count_label = QLabel()
        layout.addWidget(self.count_label)

        # OK / Cancel buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _populate_files(self) -> None:
        """Scan the directory and populate the list widget."""
        directory_path = Path(self._directory)

        video_files = sorted(
            p for p in directory_path.iterdir()
            if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS
        )
        subtitle_files = sorted(
            p for p in directory_path.iterdir()
            if p.is_file() and p.suffix.lower() in SUBTITLE_EXTENSIONS
        )

        for file_path in video_files + subtitle_files:
            item = QListWidgetItem(file_path.name)
            item.setData(Qt.UserRole, str(file_path))
            item.setToolTip(str(file_path))
            item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setCheckState(Qt.Checked)
            self.file_list.addItem(item)

        self._update_count_label()

    def _select_all(self) -> None:
        """Check all items."""
        for i in range(self.file_list.count()):
            self.file_list.item(i).setCheckState(Qt.Checked)

    def _deselect_all(self) -> None:
        """Uncheck all items."""
        for i in range(self.file_list.count()):
            self.file_list.item(i).setCheckState(Qt.Unchecked)

    def _update_count_label(self) -> None:
        """Refresh the 'X of Y files selected' label."""
        total = self.file_list.count()
        checked = sum(
            1 for i in range(total)
            if self.file_list.item(i).checkState() == Qt.Checked
        )
        self.count_label.setText(f"{checked} of {total} files selected")

    def get_selected_files(self) -> List[str]:
        """Return absolute paths of all checked files."""
        selected = []
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item.checkState() == Qt.Checked:
                selected.append(item.data(Qt.UserRole))
        return selected
