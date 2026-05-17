# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for SubtitleToolkit macOS distribution

This creates a macOS application bundle (.app) with proper structure
and codesigning preparation for distribution.
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
bundle_identifier = 'com.subtitletoolkit.app'

# Platform-specific settings
block_cipher = None
console = False
create_app_bundle = True

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

# Binary dependencies
binaries = []

# Hidden imports required for the application
hiddenimports = [
    # PySide6 modules
    'PySide6.QtCore',
    'PySide6.QtGui', 
    'PySide6.QtWidgets',
    'PySide6.QtSvg',
    'PySide6.QtMacExtras',
    
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

    # macOS specific
    'Foundation',
    'AppKit',
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
    
    # Windows-specific modules
    'win32api',
    'win32con',
    'win32gui',
    'winsound',
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

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX can cause issues on macOS
    console=console,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,  # Only needed for notarized/App Store builds
    icon=str(project_root / 'app' / 'resources' / 'icon.icns') if (project_root / 'app' / 'resources' / 'icon.icns').exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=app_name,
)

app = BUNDLE(
    coll,
    name=f'{app_name}.app',
    icon=str(project_root / 'app' / 'resources' / 'icon.icns') if (project_root / 'app' / 'resources' / 'icon.icns').exists() else None,
    bundle_identifier=bundle_identifier,
    version=app_version,
    info_plist={
        'CFBundleDisplayName': app_name,
        'CFBundleName': app_name,
        'CFBundleVersion': app_version,
        'CFBundleShortVersionString': app_version,
        'CFBundleIdentifier': bundle_identifier,
        'CFBundleExecutable': app_name,
        'CFBundlePackageType': 'APPL',
        'CFBundleSignature': '????',
        'NSHumanReadableCopyright': f'Copyright © 2024 {app_name}',
        'NSPrincipalClass': 'NSApplication',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.15.0',
        'LSApplicationCategoryType': 'public.app-category.utilities',
        'NSRequiresAquaSystemAppearance': False,
        # Permissions that might be needed
        'NSAppleEventsUsageDescription': 'This app needs to run external tools for subtitle processing.',
        'NSDocumentsFolderUsageDescription': 'This app needs access to documents to process subtitle files.',
        'NSDownloadsFolderUsageDescription': 'This app may save processed files to Downloads.',
        # Security settings
        'NSAppTransportSecurity': {
            'NSAllowsArbitraryLoads': True,  # Needed for API calls
        },
        # File associations (optional)
        'CFBundleDocumentTypes': [
            {
                'CFBundleTypeExtensions': ['mkv', 'mp4', 'avi'],
                'CFBundleTypeName': 'Video File',
                'CFBundleTypeRole': 'Viewer',
                'LSHandlerRank': 'Alternate',
            },
            {
                'CFBundleTypeExtensions': ['srt', 'ass', 'vtt'],
                'CFBundleTypeName': 'Subtitle File',
                'CFBundleTypeRole': 'Editor',
                'LSHandlerRank': 'Owner',
            }
        ]
    },
)