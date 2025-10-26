"""
Sync Confirmation Dialog for SubtitleToolkit.

Shows a confirmation dialog with the list of file operations
before actually executing the sync/rename operations.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QFrame, QScrollArea, QWidget
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from typing import List, Dict


class SyncConfirmationDialog(QDialog):
    """
    Confirmation dialog for sync operations.

    Shows the list of operations that will be performed:
    - Files that will be backed up
    - Files that will be renamed
    - Files that will be skipped
    """

    def __init__(self, operations: List[Dict], parent=None):
        """
        Initialize the confirmation dialog.

        Args:
            operations: List of operation dictionaries with:
                - action: 'backup', 'rename', 'skip'
                - from_file: source filename
                - to_file: target filename
                - reason: reason for action
            parent: Parent widget
        """
        super().__init__(parent)

        self.operations = operations
        self.confirmed = False

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        self.setWindowTitle(self.tr("Confirm Sync Operations"))
        self.setModal(True)
        self.setMinimumSize(700, 500)
        self.resize(800, 600)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel(self.tr("⚠️  Confirm File Operations"))
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(14)
        title.setFont(title_font)
        layout.addWidget(title)

        # Summary
        backup_count = sum(1 for op in self.operations if op.get('action') == 'backup')
        rename_count = sum(1 for op in self.operations if op.get('action') == 'rename')
        skip_count = sum(1 for op in self.operations if op.get('action') == 'skip')

        summary_text = self.tr(
            f"The following operations will be performed:\n"
            f"• {backup_count} file(s) will be backed up to .original.srt\n"
            f"• {rename_count} file(s) will be renamed\n"
            f"• {skip_count} file(s) will be skipped"
        )

        summary = QLabel(summary_text)
        summary.setStyleSheet("color: #bbb; font-size: 11pt; padding: 10px; background: #2a2a2a; border-radius: 4px;")
        summary.setWordWrap(True)
        layout.addWidget(summary)

        # Operations list
        list_label = QLabel(self.tr("Detailed Operations:"))
        list_font = QFont()
        list_font.setBold(True)
        list_label.setFont(list_font)
        layout.addWidget(list_label)

        # Text area for operations
        self.operations_text = QTextEdit()
        self.operations_text.setReadOnly(True)
        self.operations_text.setLineWrapMode(QTextEdit.NoWrap)
        self.operations_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Courier New', monospace;
                font-size: 10pt;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 8px;
            }
        """)

        # Populate operations
        self._populate_operations()

        layout.addWidget(self.operations_text)

        # Warning message
        warning = QLabel(self.tr("⚠️  This action cannot be undone. Make sure you have backups!"))
        warning.setStyleSheet("color: #ff9800; font-weight: bold; font-size: 11pt; padding: 10px;")
        warning.setWordWrap(True)
        layout.addWidget(warning)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # Cancel button
        cancel_btn = QPushButton(self.tr("Cancel"))
        cancel_btn.setMinimumWidth(120)
        cancel_btn.setMinimumHeight(40)
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #555;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-size: 11pt;
            }
            QPushButton:hover {
                background-color: #666;
            }
        """)
        button_layout.addWidget(cancel_btn)

        # Confirm button
        confirm_btn = QPushButton(self.tr("✓ Confirm & Execute"))
        confirm_btn.setMinimumWidth(180)
        confirm_btn.setMinimumHeight(40)
        confirm_btn.clicked.connect(self.accept)
        confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover {
                background-color: #66bb6a;
            }
            QPushButton:pressed {
                background-color: #388e3c;
            }
        """)
        button_layout.addWidget(confirm_btn)

        layout.addLayout(button_layout)

    def _populate_operations(self) -> None:
        """Populate the operations text area."""
        html_parts = []

        # Group operations by type
        backups = [op for op in self.operations if op.get('action') == 'backup']
        renames = [op for op in self.operations if op.get('action') == 'rename']
        skips = [op for op in self.operations if op.get('action') == 'skip']

        # Backups
        if backups:
            html_parts.append('<span style="color: #ffa726; font-weight: bold;">📦 BACKUPS (existing files will be renamed):</span><br>')
            for op in backups:
                from_file = op.get('from', op.get('from_file', 'unknown'))
                to_file = op.get('to', op.get('to_file', 'unknown'))
                html_parts.append(
                    f'<span style="color: #ff9800;">  ➜</span> '
                    f'<span style="color: #ffcc80;">{from_file}</span> → '
                    f'<span style="color: #ffe082;">{to_file}</span><br>'
                )
            html_parts.append('<br>')

        # Renames
        if renames:
            html_parts.append('<span style="color: #66bb6a; font-weight: bold;">✏️  RENAMES (subtitle files will be renamed):</span><br>')
            for op in renames:
                from_file = op.get('from', op.get('from_file', 'unknown'))
                to_file = op.get('to', op.get('to_file', 'unknown'))
                html_parts.append(
                    f'<span style="color: #4caf50;">  ➜</span> '
                    f'<span style="color: #a5d6a7;">{from_file}</span> → '
                    f'<span style="color: #c8e6c9;">{to_file}</span><br>'
                )
            html_parts.append('<br>')

        # Skips
        if skips:
            html_parts.append('<span style="color: #90caf9; font-weight: bold;">⊘ SKIPPED (no action needed):</span><br>')
            for op in skips:
                file_name = op.get('file', op.get('from_file', 'unknown'))
                reason = op.get('reason', 'unknown')
                html_parts.append(
                    f'<span style="color: #64b5f6;">  ⊙</span> '
                    f'<span style="color: #bbdefb;">{file_name}</span> '
                    f'<span style="color: #888;">({reason})</span><br>'
                )

        self.operations_text.setHtml(''.join(html_parts))

    def is_confirmed(self) -> bool:
        """Check if user confirmed the operations."""
        return self.result() == QDialog.Accepted
