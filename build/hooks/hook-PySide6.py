# PyInstaller hook for PySide6
# This optimizes PySide6 bundling and includes necessary plugins

from PyInstaller.utils.hooks import (
    collect_data_files, 
    collect_submodules,
    collect_system_data_files
)
import os

# Collect all data files from PySide6
datas = collect_data_files('PySide6', includes=['**/*'])

# Collect system data files for Qt plugins
try:
    datas += collect_system_data_files('PySide6', 'plugins')
except Exception:
    pass

# Hidden imports for PySide6 modules
hiddenimports = [
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.QtSvg',
    'PySide6.QtPrintSupport',
    'PySide6.QtNetwork',
    'PySide6.QtOpenGLWidgets',  # Used by video_preview_dialog.py

    # Platform-specific modules
    'PySide6.QtWinExtras',  # Windows
    'PySide6.QtMacExtras',  # macOS
    'PySide6.QtDBus',       # Linux

    # Qt plugins (dynamically loaded)
    'PySide6.QtSvg',
    'PySide6.QtOpenGL',
]

# Exclude unused PySide6 modules to reduce size
excludedimports = [
    'PySide6.Qt3DAnimation',
    'PySide6.Qt3DCore',
    'PySide6.Qt3DExtras',
    'PySide6.Qt3DInput',
    'PySide6.Qt3DLogic',
    'PySide6.Qt3DRender',
    'PySide6.QtBluetooth',
    'PySide6.QtCharts',
    'PySide6.QtConcurrent',
    'PySide6.QtDataVisualization',
    'PySide6.QtDesigner',
    'PySide6.QtHelp',
    'PySide6.QtLocation',
    'PySide6.QtMultimedia',
    'PySide6.QtMultimediaWidgets',
    'PySide6.QtNfc',
    'PySide6.QtPositioning',
    'PySide6.QtQml',
    'PySide6.QtQuick',
    'PySide6.QtQuick3D',
    'PySide6.QtQuickControls2',
    'PySide6.QtQuickWidgets',
    'PySide6.QtRemoteObjects',
    'PySide6.QtScxml',
    'PySide6.QtSensors',
    'PySide6.QtSerialPort',
    'PySide6.QtSql',
    'PySide6.QtStateMachine',
    'PySide6.QtTest',
    'PySide6.QtTextToSpeech',
    'PySide6.QtUiTools',
    'PySide6.QtWebChannel',
    'PySide6.QtWebEngine',
    'PySide6.QtWebEngineCore',
    'PySide6.QtWebEngineWidgets',
    'PySide6.QtWebSockets',
]