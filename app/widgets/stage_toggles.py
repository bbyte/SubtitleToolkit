"""
Stage Toggles Widget

This widget provides checkboxes for enabling/disabling the three main processing stages:
Extract, Translate, and Sync.
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QCheckBox, QLabel, QFrame, QGroupBox
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont


class StageToggles(QFrame):
    """
    Widget for toggling processing stages on/off.
    
    Provides checkboxes for:
    - Extract: Extract subtitles from MKV files
    - Translate: Translate SRT files
    - Sync: Synchronize SRT filenames with MKV files
    """
    
    # Signals
    stages_changed = Signal(dict)  # Emitted when stage selection changes: {stage: bool}
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        
        self._stages = {
            'extract': False,
            'translate': False,
            'sync': False
        }
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        self.setFrameStyle(QFrame.StyledPanel)
        self.setLineWidth(1)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Title
        title_label = QLabel("Processing Stages")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel("Select which stages to run in the processing pipeline:")
        desc_label.setStyleSheet("color: #bbb;")
        layout.addWidget(desc_label)
        
        # Checkboxes layout
        checkboxes_layout = QHBoxLayout()
        checkboxes_layout.setSpacing(30)
        
        # Extract checkbox
        self.extract_checkbox = QCheckBox(self.tr("Extract Subtitles"))
        self.extract_checkbox.setToolTip(self.tr(
            "Extract subtitle tracks from MKV video files\n"
            "Requires: ffmpeg/ffprobe\n"
            "Output: .srt files"
        ))
        checkboxes_layout.addWidget(self.extract_checkbox)
        
        # Translate checkbox
        self.translate_checkbox = QCheckBox(self.tr("Translate Subtitles"))
        self.translate_checkbox.setToolTip(self.tr(
            "Translate SRT subtitle files using AI services\n"
            "Requires: API keys (OpenAI/Claude/LM Studio)\n"
            "Output: Translated .srt files"
        ))
        checkboxes_layout.addWidget(self.translate_checkbox)
        
        # Sync checkbox
        self.sync_checkbox = QCheckBox(self.tr("Sync Subtitle Names"))
        self.sync_checkbox.setToolTip(self.tr(
            "Intelligently rename SRT files to match video files\n"
            "Requires: AI service for name matching\n"
            "Output: Renamed subtitle files"
        ))
        checkboxes_layout.addWidget(self.sync_checkbox)
        
        # Add stretch to push checkboxes to the left
        checkboxes_layout.addStretch()
        
        layout.addLayout(checkboxes_layout)
        
        # Pipeline flow visualization
        self._create_pipeline_flow(layout)
    
    def _create_pipeline_flow(self, parent_layout: QVBoxLayout) -> None:
        """Create a visual representation of the processing pipeline."""
        flow_frame = QFrame()
        flow_frame.setFrameStyle(QFrame.Box)
        flow_frame.setLineWidth(1)
        flow_frame.setStyleSheet("background-color: #2a2a2a; border: 1px solid #555;")
        
        flow_layout = QHBoxLayout(flow_frame)
        flow_layout.setContentsMargins(15, 10, 15, 10)
        
        # Pipeline flow label
        flow_label = QLabel("Pipeline Flow:")
        flow_label.setStyleSheet("font-weight: bold; color: #ddd;")
        flow_layout.addWidget(flow_label)
        
        # Flow visualization
        self.flow_display = QLabel("Select stages above to see pipeline flow")
        self.flow_display.setStyleSheet("color: #bbb; font-family: monospace;")
        flow_layout.addWidget(self.flow_display)
        
        flow_layout.addStretch()
        
        parent_layout.addWidget(flow_frame)
        
        # Initially update flow
        self._update_flow_display()
    
    def _connect_signals(self) -> None:
        """Connect internal signals and slots."""
        self.extract_checkbox.toggled.connect(lambda checked: self._on_stage_toggled('extract', checked))
        self.translate_checkbox.toggled.connect(lambda checked: self._on_stage_toggled('translate', checked))
        self.sync_checkbox.toggled.connect(lambda checked: self._on_stage_toggled('sync', checked))
    
    def _on_stage_toggled(self, stage: str, checked: bool) -> None:
        """Handle individual stage toggle."""
        self._stages[stage] = checked
        self._update_flow_display()
        self.stages_changed.emit(self._stages.copy())
    
    def _update_flow_display(self) -> None:
        """Update the pipeline flow visualization."""
        enabled_stages = [stage for stage, enabled in self._stages.items() if enabled]
        
        if not enabled_stages:
            self.flow_display.setText("Select stages above to see pipeline flow")
            return
        
        # Create flow representation
        flow_parts = []
        stage_names = {
            'extract': 'Extract',
            'translate': 'Translate', 
            'sync': 'Sync'
        }
        
        for stage in ['extract', 'translate', 'sync']:
            if stage in enabled_stages:
                flow_parts.append(stage_names[stage])
        
        if len(flow_parts) == 1:
            flow_text = f"[{flow_parts[0]}]"
        else:
            flow_text = " → ".join(f"[{part}]" for part in flow_parts)
        
        self.flow_display.setText(flow_text)
    
    def get_enabled_stages(self) -> dict:
        """Get the current stage enablement state."""
        return self._stages.copy()
    
    def set_stage_enabled(self, stage: str, enabled: bool) -> None:
        """Programmatically set a stage's enabled state."""
        if stage not in self._stages:
            return
        
        # Update checkbox without triggering signal recursion
        checkbox_map = {
            'extract': self.extract_checkbox,
            'translate': self.translate_checkbox,
            'sync': self.sync_checkbox
        }
        
        checkbox = checkbox_map[stage]
        checkbox.blockSignals(True)
        checkbox.setChecked(enabled)
        checkbox.blockSignals(False)
        
        # Update internal state
        self._stages[stage] = enabled
        self._update_flow_display()
        
        # Emit signal
        self.stages_changed.emit(self._stages.copy())
    
    def set_all_stages_enabled(self, enabled: bool) -> None:
        """Enable or disable all stages."""
        for stage in self._stages:
            self.set_stage_enabled(stage, enabled)
    
    def get_enabled_stage_count(self) -> int:
        """Get the number of enabled stages."""
        return sum(1 for enabled in self._stages.values() if enabled)
    
    def is_any_stage_enabled(self) -> bool:
        """Check if any stage is enabled."""
        return any(self._stages.values())
    
    def get_stage_order(self) -> list:
        """Get enabled stages in their logical processing order."""
        order = ['extract', 'translate', 'sync']
        return [stage for stage in order if self._stages[stage]]