"""
Window state persistence manager for SubtitleToolkit.

Handles saving and restoring window geometry, position, and state
with cross-platform compatibility and multi-monitor support.
"""

from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal, QTimer, QRect, QPoint, QSize, Qt
from PySide6.QtGui import QScreen
from PySide6.QtWidgets import QMainWindow, QApplication

from app.config.config_manager import ConfigManager


@dataclass
class WindowGeometry:
    """Window geometry data structure."""
    x: int
    y: int
    width: int
    height: int
    is_maximized: bool = False
    is_minimized: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "is_maximized": self.is_maximized,
            "is_minimized": self.is_minimized
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WindowGeometry":
        """Create from dictionary."""
        return cls(
            x=data.get("x", 100),
            y=data.get("y", 100),
            width=data.get("width", 1200),
            height=data.get("height", 800),
            is_maximized=data.get("is_maximized", False),
            is_minimized=data.get("is_minimized", False)
        )
    
    def to_qrect(self) -> QRect:
        """Convert to QRect."""
        return QRect(self.x, self.y, self.width, self.height)


class WindowStateManager(QObject):
    """
    Manages window state persistence with cross-platform support.
    
    Features:
    - Automatic saving of window position and size changes
    - Throttled saving to avoid excessive disk I/O
    - Screen boundary validation for restored positions
    - Multi-monitor setup handling
    - Window state tracking (maximized, minimized, normal)
    """
    
    # Signals
    state_saved = Signal(WindowGeometry)
    state_restored = Signal(WindowGeometry)
    validation_failed = Signal(str)  # error message
    
    def __init__(self, window: QMainWindow, config_manager: ConfigManager, parent: Optional[QObject] = None):
        super().__init__(parent)
        
        self.window = window
        self.config_manager = config_manager
        
        # Timer for throttled saving
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._save_window_state_now)
        
        # Throttle settings
        self.save_delay_ms = 500  # Wait 500ms after last change before saving
        
        # Current state tracking
        self._last_saved_geometry: Optional[WindowGeometry] = None
        self._is_restoring = False
        
        # Connect window events
        self._connect_window_events()
    
    def _connect_window_events(self) -> None:
        """Connect to window events for automatic state tracking."""
        # Note: QMainWindow doesn't have direct resize/move signals,
        # so we'll use event filters and periodic checking
        self.window.installEventFilter(self)
        
        # Set up periodic state checking
        self._check_timer = QTimer(self)
        self._check_timer.timeout.connect(self._check_state_changes)
        self._check_timer.start(200)  # Check every 200ms during window operations
    
    def eventFilter(self, source, event) -> bool:
        """Filter window events to detect geometry changes."""
        if source == self.window and not self._is_restoring:
            # Check for window state change events
            if event.type() in [event.Type.Resize, event.Type.Move, event.Type.WindowStateChange]:
                self._schedule_save()
        
        return super().eventFilter(source, event)
    
    def _check_state_changes(self) -> None:
        """Periodically check for window state changes."""
        if self._is_restoring:
            return
        
        current_geometry = self._get_current_geometry()
        if self._last_saved_geometry is None or self._geometry_changed(current_geometry, self._last_saved_geometry):
            self._schedule_save()
    
    def _geometry_changed(self, current: WindowGeometry, last: WindowGeometry) -> bool:
        """Check if geometry has changed significantly."""
        return (
            abs(current.x - last.x) > 5 or
            abs(current.y - last.y) > 5 or
            abs(current.width - last.width) > 5 or
            abs(current.height - last.height) > 5 or
            current.is_maximized != last.is_maximized or
            current.is_minimized != last.is_minimized
        )
    
    def _schedule_save(self) -> None:
        """Schedule a throttled save operation."""
        if not self._should_save_state():
            return
        
        # Reset the timer - this implements the throttling
        self._save_timer.stop()
        self._save_timer.start(self.save_delay_ms)
    
    def _should_save_state(self) -> bool:
        """Check if we should save the current window state."""
        ui_settings = self.config_manager.get_settings("ui")
        
        # Check if window state persistence is enabled
        remember_size = ui_settings.get("remember_window_size", True)
        remember_position = ui_settings.get("remember_window_position", True)
        
        return remember_size or remember_position
    
    def _get_current_geometry(self) -> WindowGeometry:
        """Get current window geometry."""
        geometry = self.window.geometry()
        window_state = self.window.windowState()
        
        return WindowGeometry(
            x=geometry.x(),
            y=geometry.y(),
            width=geometry.width(),
            height=geometry.height(),
            is_maximized=bool(window_state & Qt.WindowState.WindowMaximized),
            is_minimized=bool(window_state & Qt.WindowState.WindowMinimized)
        )
    
    def _save_window_state_now(self) -> None:
        """Save the current window state immediately."""
        try:
            current_geometry = self._get_current_geometry()
            
            # Get current UI settings
            ui_settings = self.config_manager.get_settings("ui")
            
            # Update window geometry in settings
            ui_settings["window_geometry"] = current_geometry.to_dict()
            
            # Save settings
            validation_result = self.config_manager.update_settings("ui", ui_settings, save=True)
            
            if validation_result.is_valid:
                self._last_saved_geometry = current_geometry
                self.state_saved.emit(current_geometry)
            else:
                error_msg = f"Failed to save window state: {validation_result.error_message}"
                self.validation_failed.emit(error_msg)
                
        except Exception as e:
            error_msg = f"Error saving window state: {str(e)}"
            self.validation_failed.emit(error_msg)
    
    def save_window_state(self) -> None:
        """Manually save the current window state."""
        self._save_window_state_now()
    
    def restore_window_state(self) -> bool:
        """
        Restore the saved window state.
        
        Returns:
            bool: True if state was successfully restored, False otherwise.
        """
        try:
            self._is_restoring = True
            
            ui_settings = self.config_manager.get_settings("ui")
            
            # Check if persistence is enabled
            remember_size = ui_settings.get("remember_window_size", True)
            remember_position = ui_settings.get("remember_window_position", True)
            
            if not (remember_size or remember_position):
                return False
            
            # Get saved geometry
            geometry_data = ui_settings.get("window_geometry")
            if not geometry_data:
                return False
            
            saved_geometry = WindowGeometry.from_dict(geometry_data)
            
            # Validate the saved geometry
            validated_geometry = self._validate_geometry(saved_geometry)
            if not validated_geometry:
                return False
            
            # Apply the geometry
            self._apply_geometry(validated_geometry, remember_size, remember_position)
            
            # Update tracking
            self._last_saved_geometry = validated_geometry
            self.state_restored.emit(validated_geometry)
            
            return True
            
        except Exception as e:
            error_msg = f"Error restoring window state: {str(e)}"
            self.validation_failed.emit(error_msg)
            return False
        
        finally:
            self._is_restoring = False
    
    def _validate_geometry(self, geometry: WindowGeometry) -> Optional[WindowGeometry]:
        """
        Validate window geometry against current screen setup.
        
        Args:
            geometry: The geometry to validate
            
        Returns:
            WindowGeometry: Validated geometry or None if invalid
        """
        # Get all available screens
        screens = QApplication.screens()
        if not screens:
            return None
        
        # Create rect for the window
        window_rect = geometry.to_qrect()
        
        # Check if window is visible on any screen
        is_visible_on_screen = False
        best_screen = screens[0]  # Primary screen as fallback
        
        for screen in screens:
            screen_geometry = screen.geometry()
            
            # Check if window intersects with this screen
            if screen_geometry.intersects(window_rect):
                is_visible_on_screen = True
                best_screen = screen
                break
        
        # If not visible on any screen, move to primary screen
        if not is_visible_on_screen:
            primary_screen = QApplication.primaryScreen()
            if primary_screen:
                best_screen = primary_screen
        
        # Ensure window is within screen bounds (with some margin)
        screen_geometry = best_screen.geometry()
        
        # Adjust position if needed
        adjusted_x = max(0, min(geometry.x, screen_geometry.width() - 200))  # At least 200px visible
        adjusted_y = max(0, min(geometry.y, screen_geometry.height() - 100))  # At least 100px visible
        
        # Ensure minimum and maximum window size
        min_width, min_height = 800, 600  # Reasonable minimums
        max_width = screen_geometry.width()
        max_height = screen_geometry.height()
        
        adjusted_width = max(min_width, min(geometry.width, max_width))
        adjusted_height = max(min_height, min(geometry.height, max_height))
        
        return WindowGeometry(
            x=adjusted_x,
            y=adjusted_y,
            width=adjusted_width,
            height=adjusted_height,
            is_maximized=geometry.is_maximized,
            is_minimized=geometry.is_minimized
        )
    
    def _apply_geometry(self, geometry: WindowGeometry, remember_size: bool, remember_position: bool) -> None:
        """Apply validated geometry to the window."""
        # First set window to normal state
        self.window.setWindowState(Qt.WindowState.WindowNoState)
        
        # Apply position if enabled
        if remember_position:
            self.window.move(geometry.x, geometry.y)
        
        # Apply size if enabled
        if remember_size:
            self.window.resize(geometry.width, geometry.height)
        
        # Apply window state (maximized, minimized)
        if geometry.is_maximized and not geometry.is_minimized:
            self.window.setWindowState(Qt.WindowState.WindowMaximized)
        elif geometry.is_minimized:
            self.window.setWindowState(Qt.WindowState.WindowMinimized)
    
    def get_default_geometry(self) -> WindowGeometry:
        """Get default window geometry for first-time users."""
        # Try to center window on primary screen
        primary_screen = QApplication.primaryScreen()
        if primary_screen:
            screen_geometry = primary_screen.geometry()
            
            # Default size
            default_width = 1200
            default_height = 800
            
            # Center on screen
            default_x = (screen_geometry.width() - default_width) // 2
            default_y = (screen_geometry.height() - default_height) // 2
            
            return WindowGeometry(
                x=max(0, default_x),
                y=max(0, default_y),
                width=default_width,
                height=default_height,
                is_maximized=False,
                is_minimized=False
            )
        else:
            # Fallback for systems without screen info
            return WindowGeometry(
                x=100, y=100, width=1200, height=800,
                is_maximized=False, is_minimized=False
            )
    
    def reset_to_defaults(self) -> None:
        """Reset window to default geometry."""
        default_geometry = self.get_default_geometry()
        self._apply_geometry(default_geometry, remember_size=True, remember_position=True)
        
        # Update settings
        ui_settings = self.config_manager.get_settings("ui")
        ui_settings["window_geometry"] = default_geometry.to_dict()
        self.config_manager.update_settings("ui", ui_settings, save=True)
        
        self._last_saved_geometry = default_geometry
    
    def cleanup(self) -> None:
        """Clean up resources and save final state."""
        if self._save_timer.isActive():
            self._save_timer.stop()
            self._save_window_state_now()
        
        if hasattr(self, '_check_timer'):
            self._check_timer.stop()