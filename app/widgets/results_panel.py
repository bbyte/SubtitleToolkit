"""
Results Panel Widget

This widget displays processing results in a tabular format, including:
- File processing results
- Rename previews for sync operations
- Error summaries and statistics
"""

from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QLabel, QPushButton, QComboBox, QFrame, QTabWidget,
    QTextEdit, QSplitter
)
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QFont, QColor


class ResultType(Enum):
    """Types of processing results."""
    EXTRACT = "extract"
    TRANSLATE = "translate"
    SYNC = "sync"


@dataclass
class ProcessingResult:
    """Represents a single processing result."""
    file_path: str
    result_type: ResultType
    status: str  # success, warning, error
    message: str
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


class ResultsPanel(QFrame):
    """
    Widget for displaying processing results and rename previews.
    
    Features:
    - Tabular display of results
    - Filtering by result type and status
    - Rename preview for sync operations
    - Export functionality
    - Statistics summary
    """
    
    # Signals
    result_selected = Signal(str)  # file path
    open_file_requested = Signal(str)  # file path
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        
        self._results: List[ProcessingResult] = []
        self._current_filter = "all"
        
        self._setup_ui()
        self._connect_signals()
        self._setup_table_styling()
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Controls layout
        controls_layout = QHBoxLayout()
        
        # Filter controls
        filter_label = QLabel("Show:")
        controls_layout.addWidget(filter_label)
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "All Results", "Extract Results", "Translate Results", 
            "Sync Results", "Successful Only", "Errors Only"
        ])
        controls_layout.addWidget(self.filter_combo)
        
        controls_layout.addStretch()
        
        # Statistics
        self.stats_label = QLabel("0 results")
        self.stats_label.setStyleSheet("color: #bbb; font-weight: bold;")
        controls_layout.addWidget(self.stats_label)
        
        # Refresh button
        self.refresh_button = QPushButton("Refresh")
        controls_layout.addWidget(self.refresh_button)
        
        # Export button
        self.export_button = QPushButton("Export...")
        controls_layout.addWidget(self.export_button)
        
        layout.addLayout(controls_layout)
        
        # Create tab widget for different result views
        self.tab_widget = QTabWidget()
        
        # Main results table tab
        self._create_results_table()
        self.tab_widget.addTab(self.table_widget, "Results")
        
        # Rename preview tab (for sync operations)
        self._create_rename_preview()
        self.tab_widget.addTab(self.rename_widget, "Rename Preview")
        
        # Summary tab
        self._create_summary_view()
        self.tab_widget.addTab(self.summary_widget, "Summary")
        
        layout.addWidget(self.tab_widget)
    
    def _create_results_table(self) -> None:
        """Create the main results table."""
        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(5)
        self.table_widget.setHorizontalHeaderLabels([
            "File", "Type", "Status", "Message", "Details"
        ])
        
        # Configure table properties
        self.table_widget.setAlternatingRowColors(True)
        self.table_widget.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_widget.setSortingEnabled(True)
        
        # Set column widths
        header = self.table_widget.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # File column
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Type
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Status
        header.setSectionResizeMode(3, QHeaderView.Stretch)  # Message
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Details
    
    def _create_rename_preview(self) -> None:
        """Create the rename preview widget."""
        self.rename_widget = QWidget()
        layout = QVBoxLayout(self.rename_widget)
        
        # Description
        desc_label = QLabel("Preview of filename changes (Sync stage only):")
        desc_label.setStyleSheet("font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(desc_label)
        
        # Rename table
        self.rename_table = QTableWidget()
        self.rename_table.setColumnCount(3)
        self.rename_table.setHorizontalHeaderLabels([
            "Original Name", "New Name", "Status"
        ])
        
        # Configure rename table
        self.rename_table.setAlternatingRowColors(True)
        rename_header = self.rename_table.horizontalHeader()
        rename_header.setSectionResizeMode(0, QHeaderView.Stretch)
        rename_header.setSectionResizeMode(1, QHeaderView.Stretch)
        rename_header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        
        layout.addWidget(self.rename_table)
        
        # Rename controls
        rename_controls = QHBoxLayout()
        
        self.apply_renames_button = QPushButton("Apply Renames")
        self.apply_renames_button.setEnabled(False)
        self.apply_renames_button.setStyleSheet("font-weight: bold;")
        rename_controls.addWidget(self.apply_renames_button)
        
        rename_controls.addStretch()
        
        self.dry_run_label = QLabel("Dry run mode - no files will be modified")
        self.dry_run_label.setStyleSheet("color: #ffa726; font-style: italic;")
        rename_controls.addWidget(self.dry_run_label)
        
        layout.addLayout(rename_controls)
    
    def _create_summary_view(self) -> None:
        """Create the summary view widget."""
        self.summary_widget = QWidget()
        layout = QVBoxLayout(self.summary_widget)
        
        # Summary text
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setStyleSheet("""
            QTextEdit {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #555;
                font-family: 'Courier New', monospace;
                font-size: 11px;
            }
        """)
        layout.addWidget(self.summary_text)
    
    def _setup_table_styling(self) -> None:
        """Set up custom styling for the results table."""
        self.table_widget.setStyleSheet("""
            QTableWidget {
                gridline-color: #555;
                selection-background-color: #2a82da;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #333;
            }
            QHeaderView::section {
                background-color: #404040;
                color: white;
                padding: 8px;
                border: 1px solid #555;
                font-weight: bold;
            }
        """)
    
    def _connect_signals(self) -> None:
        """Connect internal signals."""
        self.filter_combo.currentTextChanged.connect(self._on_filter_changed)
        self.refresh_button.clicked.connect(self._refresh_display)
        self.export_button.clicked.connect(self._export_results)
        self.table_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.apply_renames_button.clicked.connect(self._on_apply_renames)
    
    def _on_filter_changed(self, filter_text: str) -> None:
        """Handle filter selection change."""
        filter_map = {
            "All Results": "all",
            "Extract Results": "extract",
            "Translate Results": "translate",
            "Sync Results": "sync",
            "Successful Only": "success",
            "Errors Only": "error"
        }
        
        self._current_filter = filter_map.get(filter_text, "all")
        self._refresh_display()
    
    def _on_item_double_clicked(self, item: QTableWidgetItem) -> None:
        """Handle double-click on table item."""
        row = item.row()
        if row < len(self._get_filtered_results()):
            result = self._get_filtered_results()[row]
            self.open_file_requested.emit(result.file_path)
    
    def _on_apply_renames(self) -> None:
        """Handle apply renames button click."""
        # This would be connected to the backend in Phase 3
        pass
    
    def _refresh_display(self) -> None:
        """Refresh the results display."""
        filtered_results = self._get_filtered_results()
        
        # Update main results table
        self.table_widget.setRowCount(len(filtered_results))
        
        for row, result in enumerate(filtered_results):
            # File path (shortened)
            file_item = QTableWidgetItem(Path(result.file_path).name)
            file_item.setToolTip(result.file_path)
            self.table_widget.setItem(row, 0, file_item)
            
            # Type
            type_item = QTableWidgetItem(result.result_type.value.title())
            self.table_widget.setItem(row, 1, type_item)
            
            # Status
            status_item = QTableWidgetItem(result.status.title())
            self._style_status_item(status_item, result.status)
            self.table_widget.setItem(row, 2, status_item)
            
            # Message
            message_item = QTableWidgetItem(result.message)
            self.table_widget.setItem(row, 3, message_item)
            
            # Details button
            details_item = QTableWidgetItem("View")
            self.table_widget.setItem(row, 4, details_item)
        
        # Update statistics
        self._update_statistics()
        
        # Update summary
        self._update_summary()
    
    def _style_status_item(self, item: QTableWidgetItem, status: str) -> None:
        """Apply styling to status items based on status value."""
        if status.lower() == "success":
            item.setBackground(QColor("#2d5016"))  # Dark green
            item.setForeground(QColor("#66bb6a"))
        elif status.lower() == "warning":
            item.setBackground(QColor("#3d2914"))  # Dark orange
            item.setForeground(QColor("#ffa726"))
        elif status.lower() == "error":
            item.setBackground(QColor("#3d1a1a"))  # Dark red
            item.setForeground(QColor("#ff6b6b"))
        else:
            item.setBackground(QColor("#2a2a2a"))  # Default
            item.setForeground(QColor("#ffffff"))
    
    def _get_filtered_results(self) -> List[ProcessingResult]:
        """Get results filtered by current filter."""
        if self._current_filter == "all":
            return self._results
        elif self._current_filter in ["extract", "translate", "sync"]:
            return [r for r in self._results if r.result_type.value == self._current_filter]
        elif self._current_filter == "success":
            return [r for r in self._results if r.status.lower() == "success"]
        elif self._current_filter == "error":
            return [r for r in self._results if r.status.lower() == "error"]
        else:
            return self._results
    
    def _update_statistics(self) -> None:
        """Update the statistics display."""
        total = len(self._results)
        filtered = len(self._get_filtered_results())
        success = len([r for r in self._results if r.status.lower() == "success"])
        errors = len([r for r in self._results if r.status.lower() == "error"])
        warnings = len([r for r in self._results if r.status.lower() == "warning"])
        
        if filtered == total:
            stats_text = f"{total} results ({success} success, {warnings} warnings, {errors} errors)"
        else:
            stats_text = f"{filtered} of {total} results shown"
        
        self.stats_label.setText(stats_text)
    
    def _update_summary(self) -> None:
        """Update the summary view."""
        if not self._results:
            self.summary_text.setPlainText("No results to display.")
            return
        
        summary_lines = []
        summary_lines.append("PROCESSING RESULTS SUMMARY")
        summary_lines.append("=" * 50)
        summary_lines.append("")
        
        # Overall statistics
        total = len(self._results)
        success = len([r for r in self._results if r.status.lower() == "success"])
        warnings = len([r for r in self._results if r.status.lower() == "warning"])
        errors = len([r for r in self._results if r.status.lower() == "error"])
        
        summary_lines.append(f"Total files processed: {total}")
        summary_lines.append(f"Successful: {success}")
        summary_lines.append(f"Warnings: {warnings}")
        summary_lines.append(f"Errors: {errors}")
        summary_lines.append("")
        
        # By stage
        for result_type in ResultType:
            stage_results = [r for r in self._results if r.result_type == result_type]
            if stage_results:
                summary_lines.append(f"{result_type.value.upper()} STAGE:")
                summary_lines.append(f"  Files processed: {len(stage_results)}")
                stage_success = len([r for r in stage_results if r.status.lower() == "success"])
                stage_errors = len([r for r in stage_results if r.status.lower() == "error"])
                summary_lines.append(f"  Success rate: {stage_success}/{len(stage_results)} ({100*stage_success/len(stage_results):.1f}%)")
                
                if stage_errors > 0:
                    summary_lines.append("  Errors:")
                    error_results = [r for r in stage_results if r.status.lower() == "error"]
                    for error_result in error_results[:5]:  # Limit to first 5 errors
                        summary_lines.append(f"    - {Path(error_result.file_path).name}: {error_result.message}")
                    if len(error_results) > 5:
                        summary_lines.append(f"    ... and {len(error_results) - 5} more errors")
                
                summary_lines.append("")
        
        self.summary_text.setPlainText("\\n".join(summary_lines))
    
    def add_result(self, file_path: str, result_type: str, status: str, message: str, details: Dict[str, Any] = None) -> None:
        """Add a new processing result."""
        try:
            result_type_enum = ResultType(result_type.lower())
        except ValueError:
            result_type_enum = ResultType.EXTRACT  # Default
        
        result = ProcessingResult(
            file_path=file_path,
            result_type=result_type_enum,
            status=status,
            message=message,
            details=details or {}
        )
        
        self._results.append(result)
        self._refresh_display()
    
    def add_rename_preview(self, original_name: str, new_name: str, status: str = "pending") -> None:
        """Add a rename preview entry."""
        row = self.rename_table.rowCount()
        self.rename_table.insertRow(row)
        
        self.rename_table.setItem(row, 0, QTableWidgetItem(original_name))
        self.rename_table.setItem(row, 1, QTableWidgetItem(new_name))
        
        status_item = QTableWidgetItem(status.title())
        self._style_status_item(status_item, status)
        self.rename_table.setItem(row, 2, status_item)
        
        # Enable apply button if there are pending renames
        if status.lower() == "pending":
            self.apply_renames_button.setEnabled(True)
    
    def clear(self) -> None:
        """Clear all results."""
        self._results.clear()
        self.table_widget.setRowCount(0)
        self.rename_table.setRowCount(0)
        self.apply_renames_button.setEnabled(False)
        self._update_statistics()
        self._update_summary()
    
    def _export_results(self) -> None:
        """Export results to file."""
        from PySide6.QtWidgets import QFileDialog
        from datetime import datetime
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Results",
            f"subtitletoolkit_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv);;Text Files (*.txt);;All Files (*)"
        )
        
        if filename:
            try:
                import csv
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(["File Path", "Type", "Status", "Message", "Details"])
                    
                    for result in self._results:
                        writer.writerow([
                            result.file_path,
                            result.result_type.value,
                            result.status,
                            result.message,
                            str(result.details) if result.details else ""
                        ])
                
                # Add success message to log (would connect to log panel)
                print(f"Results exported to {filename}")
                
            except Exception as e:
                print(f"Failed to export results: {str(e)}")
    
    def get_results_summary(self) -> Dict[str, int]:
        """Get a summary of results counts."""
        return {
            "total": len(self._results),
            "success": len([r for r in self._results if r.status.lower() == "success"]),
            "warnings": len([r for r in self._results if r.status.lower() == "warning"]),
            "errors": len([r for r in self._results if r.status.lower() == "error"])
        }