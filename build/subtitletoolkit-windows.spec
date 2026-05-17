# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for SubtitleToolkit Windows distribution

This creates a single-file executable with embedded Python runtime
optimized for Windows deployment.
"""

import os
import sys
from pathlib import Path

# Add app directory to Python path for imports
# SPECPATH is provided by PyInstaller 6.x (replaces __file__ in spec context)
app_path = Path(SPECPATH).parent / 'app'
sys.path.insert(0, str(app_path))

# Application metadata
app_name = 'SubtitleToolkit'
app_version = '1.0.0'

# Platform-specific settings
block_cipher = None
console = False  # Set to True for debugging
onefile = True   # Single executable file

# Project root is one level above the spec file (build/ → project root)
project_root = Path(SPECPATH).parent

# Data files to include (source paths must be absolute for PyInstaller 6.x)
datas = [
    # Include CLI scripts (source files; compiled executables are added by build.py)
    (str(project_root / 'scripts'), 'scripts'),
    # Include any UI resources if they exist
    (str(project_root / 'app' / 'resources'), 'resources') if (project_root / 'app' / 'resources').exists() else None,
    # Include requirements file for reference
    (str(project_root / 'requirements.txt'), '.'),
    # Include compiled translation files for i18n support
    (str(project_root / 'app' / 'i18n' / 'translations'), str(Path('app') / 'i18n' / 'translations')),
]
# Filter out None entries
datas = [item for item in datas if item is not None]

# Binary dependencies (will be detected automatically for most cases)
binaries = []

# Hidden imports required for the application
hiddenimports = [
    # PySide6 modules
    'PySide6.QtCore',
    'PySide6.QtGui', 
    'PySide6.QtWidgets',
    'PySide6.QtSvg',
    
    # AI provider libraries
    'openai',
    'openai.resources',
    'anthropic',
    'anthropic.resources',
    
    # Other dependencies
    'python-dotenv',
    'dotenv',
    'tqdm',
    'pathlib',
    'json',
    'subprocess',
    'threading',
    'queue',
    'datetime',
    'typing',
    
    # Platform-specific modules
    'platform',
    'shutil',
    'tempfile',
    'os',
    'sys',

    # Video preview widget (mpv-based)
    'PySide6.QtOpenGLWidgets',
]

# Modules to exclude (reduces size)
excludes = [
    # Development and testing modules
    'pytest',
    'unittest',
    'doctest',
    
    # Unused GUI toolkits
    'tkinter',
    'wx',
    'gtk',
    
    # Jupyter/IPython
    'IPython',
    'jupyter',
    
    # Data science libraries (if not needed)
    'numpy',
    'pandas',
    'matplotlib',
    'scipy',
    
    # Web frameworks
    'django',
    'flask',
    'fastapi',
    
    # Documentation tools
    'sphinx',
    'pydoc',
]

a = Analysis(
    [str(project_root / 'app' / 'main.py')],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

if onefile:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name=app_name,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,  # Enable UPX compression if available
        upx_exclude=[],
        runtime_tmpdir=None,
        console=console,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        # Windows-specific options
        version=str(Path(SPECPATH) / 'version_info.txt') if (Path(SPECPATH) / 'version_info.txt').exists() else None,
        icon=str(project_root / 'app' / 'resources' / 'icon.ico') if (project_root / 'app' / 'resources' / 'icon.ico').exists() else None,
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name=app_name,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=console,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        version=str(Path(SPECPATH) / 'version_info.txt') if (Path(SPECPATH) / 'version_info.txt').exists() else None,
        icon=str(project_root / 'app' / 'resources' / 'icon.ico') if (project_root / 'app' / 'resources' / 'icon.ico').exists() else None,
    )
    
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name=app_name,
    )