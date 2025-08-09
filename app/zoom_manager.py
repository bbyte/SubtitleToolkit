"""
ZoomManager for SubtitleToolkit Desktop Application.

Provides browser-style zoom functionality with font scaling, UI element scaling,
and persistent state management.
"""

from typing import Dict, List, Optional
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QStatusBar
from PySide6.QtCore import QObject, Signal, QSettings, QTimer
from PySide6.QtGui import QFont, QAction, QKeySequence

from app.config.config_manager import ConfigManager


class ZoomManager(QObject):
    """
    Manages zoom functionality for the entire application.
    
    Features:
    - Browser-style zoom controls (Ctrl/Cmd +, -, 0)
    - Font and UI scaling from 50% to 200% in 10% increments
    - Persistent zoom level storage
    - Smooth transitions between zoom levels
    - Status bar display of current zoom level
    """
    
    # Signals
    zoom_changed = Signal(float)  # New zoom factor
    zoom_reset = Signal()  # Zoom was reset to default
    
    # Zoom constants
    MIN_ZOOM = 0.5   # 50%
    MAX_ZOOM = 2.0   # 200%
    DEFAULT_ZOOM = 1.0  # 100%
    ZOOM_STEP = 0.1  # 10% increments
    
    def __init__(self, config_manager: ConfigManager, parent: QWidget = None):
        super().__init__(parent)
        self.config_manager = config_manager
        self._current_zoom = self.DEFAULT_ZOOM
        self._base_font_size = None
        self._status_label = None
        
        # Store original font sizes for proper scaling
        self._original_fonts: Dict[QWidget, QFont] = {}
        self._tracked_widgets: List[QWidget] = []
        
        # Timer for smooth transitions
        self._transition_timer = QTimer()
        self._transition_timer.timeout.connect(self._update_zoom_display)
        self._transition_timer.setSingleShot(True)
        
        # Load saved zoom level
        self._load_zoom_from_settings()
        
        # Store the base application font size
        self._base_font_size = QApplication.font().pointSize()
    
    def _load_zoom_from_settings(self) -> None:
        """Load zoom level from application settings."""
        ui_settings = self.config_manager.get_settings("ui")
        saved_zoom = ui_settings.get("zoom_level", self.DEFAULT_ZOOM)
        
        # Validate saved zoom level
        if self.MIN_ZOOM <= saved_zoom <= self.MAX_ZOOM:
            self._current_zoom = saved_zoom
        else:
            self._current_zoom = self.DEFAULT_ZOOM
    
    def _save_zoom_to_settings(self) -> None:
        """Save current zoom level to application settings."""
        ui_settings = self.config_manager.get_settings("ui")
        ui_settings["zoom_level"] = self._current_zoom
        self.config_manager.update_settings("ui", ui_settings)
    
    @property
    def current_zoom(self) -> float:
        """Get the current zoom factor."""
        return self._current_zoom
    
    @property
    def current_zoom_percentage(self) -> int:
        """Get the current zoom level as a percentage."""
        return int(self._current_zoom * 100)
    
    def zoom_in(self) -> bool:
        """
        Increase zoom level by one step.
        
        Returns:
            bool: True if zoom was increased, False if already at maximum
        """
        new_zoom = min(self._current_zoom + self.ZOOM_STEP, self.MAX_ZOOM)
        if new_zoom != self._current_zoom:
            self._set_zoom(new_zoom)
            return True
        return False
    
    def zoom_out(self) -> bool:
        """
        Decrease zoom level by one step.
        
        Returns:
            bool: True if zoom was decreased, False if already at minimum
        """
        new_zoom = max(self._current_zoom - self.ZOOM_STEP, self.MIN_ZOOM)
        if new_zoom != self._current_zoom:
            self._set_zoom(new_zoom)
            return True
        return False
    
    def reset_zoom(self) -> None:
        """Reset zoom to default level (100%)."""
        if self._current_zoom != self.DEFAULT_ZOOM:
            self._set_zoom(self.DEFAULT_ZOOM)
            self.zoom_reset.emit()
    
    def set_zoom(self, zoom_factor: float) -> bool:
        """
        Set zoom to a specific factor.
        
        Args:
            zoom_factor: Zoom factor between MIN_ZOOM and MAX_ZOOM
            
        Returns:
            bool: True if zoom was set, False if factor was invalid
        """
        if self.MIN_ZOOM <= zoom_factor <= self.MAX_ZOOM:
            self._set_zoom(zoom_factor)
            return True
        return False
    
    def _set_zoom(self, zoom_factor: float) -> None:
        """Internal method to set zoom and update UI."""
        old_zoom = self._current_zoom
        self._current_zoom = zoom_factor
        
        # Apply zoom to all tracked widgets
        self._apply_zoom_to_widgets()
        
        # Update application font
        self._apply_zoom_to_application_font()
        
        # Save to settings
        self._save_zoom_to_settings()
        
        # Update status display
        self._update_zoom_display()
        
        # Emit signal
        self.zoom_changed.emit(zoom_factor)
    
    def register_widget(self, widget: QWidget) -> None:
        """
        Register a widget for zoom scaling.
        
        Args:
            widget: Widget to be scaled with zoom changes
        """
        if widget not in self._tracked_widgets:
            self._tracked_widgets.append(widget)
            # Store original font
            self._original_fonts[widget] = widget.font()
            
            # Apply current zoom immediately
            self._apply_zoom_to_widget(widget)
    
    def unregister_widget(self, widget: QWidget) -> None:
        """
        Unregister a widget from zoom scaling.
        
        Args:
            widget: Widget to remove from zoom tracking
        """
        if widget in self._tracked_widgets:
            self._tracked_widgets.remove(widget)
            if widget in self._original_fonts:
                del self._original_fonts[widget]
    
    def register_status_label(self, label: QLabel) -> None:
        """
        Register a status label to display current zoom level.
        
        Args:
            label: QLabel widget to display zoom percentage
        """
        self._status_label = label
        self._update_zoom_display()
    
    def _apply_zoom_to_widgets(self) -> None:
        """Apply current zoom factor to all registered widgets."""
        for widget in self._tracked_widgets[:]:  # Copy list to avoid modification during iteration
            if widget.isVisible():  # Only apply to visible widgets
                self._apply_zoom_to_widget(widget)
    
    def _apply_zoom_to_widget(self, widget: QWidget) -> None:
        """Apply zoom to a specific widget."""
        if widget not in self._original_fonts:
            return
        
        original_font = self._original_fonts[widget]
        zoomed_font = QFont(original_font)
        
        # Calculate new font size
        new_size = int(original_font.pointSize() * self._current_zoom)
        new_size = max(6, new_size)  # Minimum font size of 6pt
        zoomed_font.setPointSize(new_size)
        
        widget.setFont(zoomed_font)
    
    def _apply_zoom_to_application_font(self) -> None:
        """Apply zoom to the default application font."""
        if self._base_font_size is None:
            return
        
        app_font = QApplication.font()
        new_size = int(self._base_font_size * self._current_zoom)
        new_size = max(6, new_size)  # Minimum font size
        app_font.setPointSize(new_size)
        QApplication.setFont(app_font)
    
    def _update_zoom_display(self) -> None:
        """Update the status label with current zoom level."""
        if self._status_label:
            percentage = self.current_zoom_percentage
            self._status_label.setText(f"Zoom: {percentage}%")
            
            # Add visual indicator for non-default zoom
            if percentage != 100:
                self._status_label.setStyleSheet("font-weight: bold; color: #0066cc;")
            else:
                self._status_label.setStyleSheet("")
    
    def create_zoom_actions(self, parent: QWidget) -> Dict[str, QAction]:
        """
        Create zoom-related QAction objects for menu integration.
        
        Args:
            parent: Parent widget for the actions
            
        Returns:
            Dict containing zoom actions keyed by action name
        """
        actions = {}
        
        # Zoom In action
        zoom_in_action = QAction("Zoom &In", parent)
        zoom_in_action.setShortcut(QKeySequence.ZoomIn)
        zoom_in_action.setStatusTip("Increase zoom level")
        zoom_in_action.triggered.connect(self.zoom_in)
        actions["zoom_in"] = zoom_in_action
        
        # Zoom Out action
        zoom_out_action = QAction("Zoom &Out", parent)
        zoom_out_action.setShortcut(QKeySequence.ZoomOut)
        zoom_out_action.setStatusTip("Decrease zoom level")
        zoom_out_action.triggered.connect(self.zoom_out)
        actions["zoom_out"] = zoom_out_action
        
        # Reset Zoom action
        reset_zoom_action = QAction("&Reset Zoom", parent)
        reset_zoom_action.setShortcut(QKeySequence("Ctrl+0"))
        reset_zoom_action.setStatusTip("Reset zoom to 100%")
        reset_zoom_action.triggered.connect(self.reset_zoom)
        actions["reset_zoom"] = reset_zoom_action
        
        return actions
    
    def get_zoom_info(self) -> Dict[str, any]:
        """
        Get information about current zoom state.
        
        Returns:
            Dict containing zoom state information
        """
        return {
            "current_zoom": self._current_zoom,
            "percentage": self.current_zoom_percentage,
            "can_zoom_in": self._current_zoom < self.MAX_ZOOM,
            "can_zoom_out": self._current_zoom > self.MIN_ZOOM,
            "is_default": self._current_zoom == self.DEFAULT_ZOOM,
            "min_zoom": self.MIN_ZOOM,
            "max_zoom": self.MAX_ZOOM,
            "zoom_step": self.ZOOM_STEP
        }
    
    def auto_register_children(self, parent: QWidget, recursive: bool = True) -> int:
        """
        Automatically register all child widgets for zoom scaling.
        
        Args:
            parent: Parent widget whose children should be registered
            recursive: Whether to recursively register all descendants
            
        Returns:
            int: Number of widgets registered
        """
        registered_count = 0
        
        for child in parent.findChildren(QWidget):
            if child not in self._tracked_widgets:
                self.register_widget(child)
                registered_count += 1
        
        return registered_count
    
    def apply_initial_zoom(self) -> None:
        """Apply the initial zoom level to all registered widgets."""
        if self._current_zoom != self.DEFAULT_ZOOM:
            self._apply_zoom_to_widgets()
            self._apply_zoom_to_application_font()
            self._update_zoom_display()