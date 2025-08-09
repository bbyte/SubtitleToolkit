# Window State Persistence

## Overview

The SubtitleToolkit desktop application now includes comprehensive window state persistence that remembers and restores the window size, position, and state (maximized/minimized) when the user resizes or moves the window.

## Features

### 🔧 **Core Functionality**
- **Automatic saving**: Window geometry is saved automatically when changed
- **Throttled saving**: Uses a 500ms delay to avoid excessive disk I/O during window operations  
- **Real-time tracking**: Changes are detected in real-time through event filtering
- **Cross-platform support**: Works correctly on Windows, macOS, and Linux
- **Multi-monitor handling**: Validates window positions across multiple screen setups

### 📐 **What is Persisted**
- **Window position** (x, y coordinates)
- **Window size** (width, height)
- **Window state** (normal, maximized, minimized)
- **User preferences** (enable/disable persistence per aspect)

### 🛡️ **Validation & Safety**
- **Screen boundary checking**: Ensures restored windows are visible on current screen setup
- **Monitor removal handling**: Gracefully handles cases where saved position is off-screen
- **Size validation**: Enforces minimum and maximum reasonable window sizes
- **Fallback positioning**: Uses sensible defaults for first-time users or invalid saved states

## Architecture

### Classes

#### `WindowStateManager`
The core class responsible for managing window state persistence.

**Key Methods:**
- `restore_window_state()`: Restores saved window state on application startup
- `save_window_state()`: Manually saves current window state  
- `reset_to_defaults()`: Resets window to default geometry
- `cleanup()`: Cleans up resources and saves final state

**Key Signals:**
- `state_saved(WindowGeometry)`: Emitted when state is successfully saved
- `state_restored(WindowGeometry)`: Emitted when state is restored
- `validation_failed(str)`: Emitted when validation fails with error message

#### `WindowGeometry`
Data class representing window geometry and state.

**Properties:**
- `x, y`: Window position coordinates
- `width, height`: Window dimensions  
- `is_maximized`: Whether window is maximized
- `is_minimized`: Whether window is minimized

**Methods:**
- `to_dict()`: Serialize to dictionary for settings storage
- `from_dict()`: Create from dictionary data
- `to_qrect()`: Convert to Qt QRect object

### Settings Integration

Window state is stored in the application settings under the `ui` section:

```json
{
  "ui": {
    "remember_window_size": true,
    "remember_window_position": true,
    "window_geometry": {
      "x": 100,
      "y": 100,
      "width": 1200,
      "height": 800,
      "is_maximized": false,
      "is_minimized": false
    }
  }
}
```

### Event Handling

The system uses multiple approaches to detect window changes:

1. **Event Filter**: Captures Qt resize, move, and window state change events
2. **Periodic Checking**: Uses a 200ms timer to detect changes not caught by events
3. **Throttled Saving**: Implements a 500ms delay before saving to disk

## User Settings

Users can control window state persistence through the settings:

- **`remember_window_size`**: Enable/disable saving window size
- **`remember_window_position`**: Enable/disable saving window position

Both settings are independent, allowing users to choose what to persist.

## Implementation Details

### Screen Validation Process

When restoring window state, the system:

1. **Checks screen visibility**: Verifies window intersects with at least one screen
2. **Adjusts position**: Moves window to primary screen if off-screen
3. **Validates bounds**: Ensures at least 200px width and 100px height are visible
4. **Enforces limits**: Applies minimum (800x600) and maximum (screen size) constraints

### Error Handling

The system gracefully handles various error conditions:

- **Missing settings**: Uses default geometry for first-time users
- **Invalid geometry**: Validates and corrects impossible values
- **Screen changes**: Adapts to monitor configuration changes
- **Corrupted data**: Falls back to defaults when settings are corrupted

### Performance Considerations

- **Throttled saving**: 500ms delay prevents excessive disk writes during window drags
- **Event filtering**: Minimal overhead event processing
- **Memory efficient**: Lightweight geometry tracking with minimal state

## Usage Examples

### Integration in Main Window

```python
# In MainWindow.__init__()
self.window_state_manager = WindowStateManager(self, self.config_manager, self)

# Connect error handling
self.window_state_manager.validation_failed.connect(self._on_window_state_error)

# Restore state on startup
if not self.window_state_manager.restore_window_state():
    self.resize(1200, 800)  # Fallback size

# In closeEvent()
self.window_state_manager.cleanup()
```

### Manual State Management

```python
# Save current state immediately
window_state_manager.save_window_state()

# Reset to default position and size
window_state_manager.reset_to_defaults()

# Get current geometry info
current_geometry = window_state_manager._get_current_geometry()
```

## Testing

### Test Script

A test script (`test_window_state.py`) is provided to verify functionality:

```bash
python3 test_window_state.py
```

The test script provides:
- Visual feedback on state changes
- Manual save/restore controls
- Current geometry display
- Screen information logging

### Test Scenarios

1. **Basic persistence**: Resize/move window, restart application
2. **Maximized state**: Maximize window, restart, verify maximized restoration  
3. **Multi-monitor**: Move to secondary monitor, disconnect monitor, verify fallback
4. **Edge cases**: Move window off-screen, change resolution, verify correction
5. **Settings integration**: Toggle persistence settings, verify behavior changes

## Debugging

Window state events are logged to help with debugging:

```python
# Error messages appear in application log
self._on_window_state_error("Window validation failed: ...")

# State changes can be tracked via signals
def _on_state_saved(self, geometry):
    print(f"Saved: {geometry.width}x{geometry.height} at ({geometry.x}, {geometry.y})")
```

## Future Enhancements

Potential improvements for future versions:

- **Per-monitor DPI awareness**: Handle high-DPI scaling more precisely
- **Window state history**: Remember last few positions for quick switching  
- **Workspace integration**: Save/restore window positions per virtual desktop
- **Profile-based geometry**: Different window layouts for different use cases
- **Advanced validation**: More sophisticated multi-monitor geometry validation