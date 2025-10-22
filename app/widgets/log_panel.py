"""
Log Panel Widget

This widget provides a filterable log display for monitoring processing operations.
Supports different log levels (info, warning, error) with color coding and filtering.
"""

from datetime import datetime
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QComboBox,
    QLabel, QCheckBox, QFrame, QScrollArea
)
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QFont, QTextCharFormat, QColor, QTextCursor


class LogLevel(Enum):
    """Log message levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class LogMessage:
    """Represents a single log message."""
    timestamp: datetime
    level: LogLevel
    message: str
    source: str = "System"


class LogPanel(QFrame):
    """
    Widget for displaying filtered log messages.
    
    Features:
    - Color-coded messages by level
    - Real-time filtering by level
    - Auto-scroll to latest messages
    - Clear and export functionality
    - Message search capability
    """
    
    # Signals
    message_logged = Signal(str, str)  # level, message
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        
        self._messages: List[LogMessage] = []
        self._filter_levels = {level: True for level in LogLevel}
        self._auto_scroll = True
        self._max_messages = 1000  # Limit to prevent memory issues
        
        self._setup_ui()
        self._connect_signals()
        self._setup_colors()
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Controls layout
        controls_layout = QHBoxLayout()
        
        # Filter label
        filter_label = QLabel("Show:")
        controls_layout.addWidget(filter_label)
        
        # Level filter checkboxes
        self.level_checkboxes = {}
        for level in LogLevel:
            checkbox = QCheckBox(level.value.title())
            checkbox.setChecked(True)
            checkbox.toggled.connect(lambda checked, l=level: self._on_filter_changed(l, checked))
            self.level_checkboxes[level] = checkbox
            controls_layout.addWidget(checkbox)
        
        controls_layout.addStretch()
        
        # Auto-scroll checkbox
        self.auto_scroll_checkbox = QCheckBox("Auto-scroll")
        self.auto_scroll_checkbox.setChecked(True)
        self.auto_scroll_checkbox.toggled.connect(self._on_auto_scroll_toggled)
        controls_layout.addWidget(self.auto_scroll_checkbox)
        
        # Clear button
        self.clear_button = QPushButton(self.tr("Clear"))
        self.clear_button.clicked.connect(self.clear)
        controls_layout.addWidget(self.clear_button)
        
        layout.addLayout(controls_layout)
        
        # Log display
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setFont(QFont("Consolas", 16))
        self.log_display.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #555;
                selection-background-color: #2a82da;
            }
        """)
        layout.addWidget(self.log_display)
        
        # Status layout
        status_layout = QHBoxLayout()
        
        # Message count
        self.count_label = QLabel("0 messages")
        self.count_label.setStyleSheet("color: #bbb; font-size: 10px;")
        status_layout.addWidget(self.count_label)
        
        status_layout.addStretch()
        
        # Last update time
        self.last_update_label = QLabel("")
        self.last_update_label.setStyleSheet("color: #bbb; font-size: 10px;")
        status_layout.addWidget(self.last_update_label)
        
        layout.addLayout(status_layout)
        
        # Auto-refresh timer for relative timestamps
        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self._update_timestamps)
        self._refresh_timer.start(60000)  # Update every minute
    
    def _setup_colors(self) -> None:
        """Set up color schemes for different log levels."""
        self._level_colors = {
            LogLevel.DEBUG: QColor("#808080"),    # Gray
            LogLevel.INFO: QColor("#87CEEB"),     # Light blue
            LogLevel.WARNING: QColor("#FFA500"),  # Orange
            LogLevel.ERROR: QColor("#FF6B6B"),    # Red
        }
        
        self._level_prefixes = {
            LogLevel.DEBUG: "[DEBUG]",
            LogLevel.INFO: "[INFO] ",
            LogLevel.WARNING: "[WARN] ",
            LogLevel.ERROR: "[ERROR]",
        }
    
    def _connect_signals(self) -> None:
        """Connect internal signals."""
        pass
    
    def _on_filter_changed(self, level: LogLevel, enabled: bool) -> None:
        """Handle filter level changes."""
        self._filter_levels[level] = enabled
        self._refresh_display()
    
    def _on_auto_scroll_toggled(self, enabled: bool) -> None:
        """Handle auto-scroll toggle."""
        self._auto_scroll = enabled
        if enabled:
            self._scroll_to_bottom()
    
    def add_message(self, level: str, message: str, source: str = "System") -> None:
        """Add a new log message."""
        try:
            log_level = LogLevel(level.lower())
        except ValueError:
            log_level = LogLevel.INFO
        
        log_message = LogMessage(
            timestamp=datetime.now(),
            level=log_level,
            message=message,
            source=source
        )
        
        self._messages.append(log_message)
        
        # Trim messages if over limit
        if len(self._messages) > self._max_messages:
            self._messages = self._messages[-self._max_messages:]
        
        # Update display if this level is visible
        if self._filter_levels[log_level]:
            self._append_message_to_display(log_message)
        
        # Update status
        self._update_status()
        
        # Emit signal
        self.message_logged.emit(level, message)
    
    def _append_message_to_display(self, message: LogMessage) -> None:
        """Append a single message to the display."""
        cursor = self.log_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        # Format timestamp
        timestamp_str = message.timestamp.strftime("%H:%M:%S")
        
        # Format message parts
        prefix = self._level_prefixes[message.level]
        full_message = f"[{timestamp_str}] {prefix} {message.message}\n"
        
        # Set color for the message
        format = QTextCharFormat()
        format.setForeground(self._level_colors[message.level])
        
        cursor.setCharFormat(format)
        cursor.insertText(full_message)
        
        # Auto-scroll if enabled
        if self._auto_scroll:
            self._scroll_to_bottom()
    
    def _refresh_display(self) -> None:
        """Refresh the entire log display based on current filters."""
        self.log_display.clear()
        
        for message in self._messages:
            if self._filter_levels[message.level]:
                self._append_message_to_display(message)
        
        self._update_status()
    
    def _scroll_to_bottom(self) -> None:
        """Scroll the log display to the bottom."""
        scrollbar = self.log_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def _update_status(self) -> None:
        """Update the status bar with current information."""
        visible_count = sum(1 for msg in self._messages if self._filter_levels[msg.level])
        total_count = len(self._messages)
        
        if visible_count == total_count:
            self.count_label.setText(f"{total_count} messages")
        else:
            self.count_label.setText(f"{visible_count} of {total_count} messages")
        
        if self._messages:
            last_message_time = self._messages[-1].timestamp.strftime("%H:%M:%S")
            self.last_update_label.setText(f"Last: {last_message_time}")
        else:
            self.last_update_label.setText("")
    
    def _update_timestamps(self) -> None:
        """Update relative timestamps (called periodically)."""
        # For now, we use absolute timestamps
        # This could be extended to show relative times like "2 minutes ago"
        pass
    
    def clear(self) -> None:
        """Clear all log messages."""
        self._messages.clear()
        self.log_display.clear()
        self._update_status()
        
        self.add_message("info", "Log cleared")
    
    def set_level_visible(self, level: str, visible: bool) -> None:
        """Programmatically set level visibility."""
        try:
            log_level = LogLevel(level.lower())
            if log_level in self.level_checkboxes:
                self.level_checkboxes[log_level].setChecked(visible)
        except ValueError:
            pass
    
    def get_message_count(self, level: str = None) -> int:
        """Get the count of messages, optionally filtered by level."""
        if level is None:
            return len(self._messages)
        
        try:
            log_level = LogLevel(level.lower())
            return sum(1 for msg in self._messages if msg.level == log_level)
        except ValueError:
            return 0
    
    def get_recent_messages(self, count: int = 10, level: str = None) -> List[LogMessage]:
        """Get recent messages, optionally filtered by level."""
        messages = self._messages
        
        if level is not None:
            try:
                log_level = LogLevel(level.lower())
                messages = [msg for msg in messages if msg.level == log_level]
            except ValueError:
                pass
        
        return messages[-count:] if messages else []