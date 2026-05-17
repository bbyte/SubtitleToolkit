"""
PyInstaller optimization configuration for SubtitleToolkit

This module provides platform-specific optimization settings
for creating efficient application bundles.
"""

import platform
from pathlib import Path
from typing import Dict, List, Any


class OptimizationConfig:
    """Configuration for PyInstaller optimizations."""
    
    def __init__(self):
        self.platform = platform.system().lower()
        self.project_root = Path(__file__).parent.parent.parent
    
    def get_upx_config(self) -> Dict[str, Any]:
        """Get UPX compression configuration."""
        if self.platform == 'windows':
            return {
                'upx': True,
                'upx_exclude': [
                    # Exclude Qt libraries that may not work well with UPX
                    'Qt6Core.dll',
                    'Qt6Gui.dll',
                    'Qt6Widgets.dll',
                    # Exclude large libraries that compress poorly
                    'python*.dll',
                    'vcruntime*.dll',
                ]
            }
        elif self.platform == 'linux':
            return {
                'upx': True,
                'upx_exclude': [
                    # Exclude shared libraries that may cause issues
                    'libQt6*',
                    'libpython*',
                    'libssl*',
                    'libcrypto*',
                ]
            }
        else:  # macOS
            return {
                'upx': False,  # UPX can cause issues on macOS
                'upx_exclude': []
            }
    
    def get_exclusions(self) -> List[str]:
        """Get list of modules to exclude from the bundle."""
        base_exclusions = [
            # Development and testing
            'pytest', 'unittest', 'doctest', '_pytest',
            'test', 'tests', 'testing',
            
            # Documentation and help
            'pydoc', 'pydoc_data', 'help',
            'sphinx', 'docutils',
            
            # Unused GUI frameworks
            'tkinter', 'Tkinter',
            'wx', 'wxPython',
            'gtk', 'gi',
            
            # Data science (not needed)
            'numpy', 'scipy', 'pandas', 'matplotlib',
            'sklearn', 'seaborn', 'plotly',
            
            # Web frameworks
            'django', 'flask', 'fastapi', 'tornado',
            'requests_oauthlib', 'oauthlib',
            
            # Development tools
            'pip', 'setuptools', 'wheel', 'distutils',
            'pkg_resources',
            
            # Jupyter/IPython
            'IPython', 'ipython', 'jupyter',
            'notebook', 'qtconsole',
            
            # Networking (if not needed)
            'email', 'smtplib', 'poplib', 'imaplib',
            'ftplib', 'telnetlib',
            
            # Database (if not needed)
            'sqlite3', 'dbm', 'anydbm',
            
            # Multimedia (if not needed)
            'wave', 'sunau', 'aifc',
            'audioop', 'chunk',
            
            # Legacy modules
            'imp', 'importlib._bootstrap',
            'distutils', 'lib2to3',
        ]
        
        if self.platform == 'windows':
            base_exclusions.extend([
                # Unix-specific
                'pwd', 'grp', 'termios', 'tty', 'pty',
                'fcntl', 'resource', 'syslog',
                
                # macOS-specific
                'Foundation', 'AppKit', 'CoreFoundation',
                'Cocoa', 'PyObjC',
            ])
        elif self.platform == 'darwin':
            base_exclusions.extend([
                # Windows-specific
                'win32api', 'win32con', 'win32gui', 'win32service',
                'win32file', 'win32pipe', 'win32process', 'win32security',
                'winsound', 'msvcrt', 'winreg', '_winreg',
                
                # Linux-specific
                'linux_distribution',
            ])
        elif self.platform == 'linux':
            base_exclusions.extend([
                # Windows-specific
                'win32api', 'win32con', 'win32gui', 'win32service',
                'win32file', 'win32pipe', 'win32process', 'win32security',
                'winsound', 'msvcrt', 'winreg', '_winreg',
                
                # macOS-specific
                'Foundation', 'AppKit', 'CoreFoundation',
                'Cocoa', 'PyObjC',
            ])
        
        return base_exclusions
    
    def get_hidden_imports(self) -> List[str]:
        """Get list of modules that should be explicitly included."""
        base_imports = [
            # Core application modules
            'pathlib', 'json', 'subprocess', 'threading',
            'queue', 'datetime', 'typing', 'dataclasses',
            'enum', 'collections', 'itertools', 'functools',
            
            # PySide6 essentials
            'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets',
            'PySide6.QtSvg',
            
            # API clients
            'openai', 'anthropic',
            
            # Environment handling
            'dotenv', 'python-dotenv',
            
            # Progress bars
            'tqdm',
            
            # System integration
            'platform', 'shutil', 'tempfile',
            'os', 'sys', 'signal',
        ]
        
        # Platform-specific imports
        if self.platform == 'windows':
            base_imports.extend([
                'PySide6.QtWinExtras',
            ])
        elif self.platform == 'darwin':
            base_imports.extend([
                'PySide6.QtMacExtras',
                'Foundation', 'AppKit',  # For native integrations
            ])
        elif self.platform == 'linux':
            base_imports.extend([
                'PySide6.QtDBus',
                'pwd', 'grp',  # For Unix user/group info
            ])
        
        return base_imports
    
    def get_data_files(self) -> List[tuple]:
        """Get list of data files to include."""
        data_files = [
            # CLI scripts
            (str(self.project_root / 'scripts'), 'scripts'),
            
            # Requirements for reference
            (str(self.project_root / 'requirements.txt'), '.'),
        ]
        
        # Add resources if they exist
        resources_dir = self.project_root / 'app' / 'resources'
        if resources_dir.exists():
            data_files.append((str(resources_dir), 'resources'))
        
        # Platform-specific data files
        if self.platform == 'linux':
            desktop_file = self.project_root / 'build' / 'linux' / 'subtitletoolkit.desktop'
            if desktop_file.exists():
                data_files.append((str(desktop_file), '.'))
        
        return data_files
    
    def get_binaries(self) -> List[tuple]:
        """Get list of binary files to include."""
        binaries = []
        
        # Platform-specific binaries could go here
        # For example, if we needed to bundle ffmpeg:
        # if self.platform == 'windows':
        #     ffmpeg_path = find_ffmpeg_windows()
        #     if ffmpeg_path:
        #         binaries.append((ffmpeg_path, 'tools'))
        
        return binaries
    
    def get_runtime_hooks(self) -> List[str]:
        """Get list of runtime hook files."""
        hooks_dir = self.project_root / 'build' / 'hooks'
        runtime_hooks = []
        
        # Add custom runtime hooks if they exist
        for hook_file in hooks_dir.glob('rthook_*.py'):
            runtime_hooks.append(str(hook_file))
        
        return runtime_hooks
    
    def get_hookspath(self) -> List[str]:
        """Get list of directories containing PyInstaller hooks."""
        return [str(self.project_root / 'build' / 'hooks')]
    
    def get_cipher_key(self) -> str:
        """Get cipher key for bytecode encryption (optional)."""
        # For open source projects, usually no encryption
        # For commercial applications, generate a random key
        return None
    
    def should_use_onefile(self) -> bool:
        """Determine if one-file distribution should be used."""
        # One-file is convenient but slower startup
        # Directory distribution is faster but more files
        
        if self.platform == 'windows':
            return True  # Windows users prefer single .exe
        elif self.platform == 'darwin':
            return False  # macOS uses .app bundles anyway
        elif self.platform == 'linux':
            return False  # Linux users often prefer directory or AppImage
        
        return False
    
    def get_console_setting(self) -> bool:
        """Determine if console window should be shown."""
        # GUI applications typically don't need console
        return False
    
    def get_icon_path(self) -> str:
        """Get path to application icon."""
        icon_paths = {
            'windows': self.project_root / 'app' / 'resources' / 'icon.ico',
            'darwin': self.project_root / 'app' / 'resources' / 'icon.icns',
            'linux': self.project_root / 'app' / 'resources' / 'icon.png',
        }
        
        icon_path = icon_paths.get(self.platform)
        if icon_path and icon_path.exists():
            return str(icon_path)
        
        return None
    
    def generate_spec_options(self) -> Dict[str, Any]:
        """Generate complete PyInstaller spec options."""
        upx_config = self.get_upx_config()
        
        return {
            'pathex': [str(self.project_root)],
            'binaries': self.get_binaries(),
            'datas': self.get_data_files(),
            'hiddenimports': self.get_hidden_imports(),
            'hookspath': self.get_hookspath(),
            'hooksconfig': {},
            'runtime_hooks': self.get_runtime_hooks(),
            'excludes': self.get_exclusions(),
            'win_no_prefer_redirects': False,
            'win_private_assemblies': False,
            'cipher': self.get_cipher_key(),
            'noarchive': False,
            
            # EXE options
            'console': self.get_console_setting(),
            'disable_windowed_traceback': False,
            'argv_emulation': False,
            'target_arch': None,
            'codesign_identity': None,
            'entitlements_file': None,
            'icon': self.get_icon_path(),
            'debug': False,
            'bootloader_ignore_signals': False,
            'strip': False,
            
            # UPX options
            'upx': upx_config['upx'],
            'upx_exclude': upx_config['upx_exclude'],
            
            # Distribution type
            'onefile': self.should_use_onefile(),
        }


def get_optimization_config() -> OptimizationConfig:
    """Get optimization configuration for current platform."""
    return OptimizationConfig()


if __name__ == '__main__':
    # Test the configuration
    config = get_optimization_config()
    import pprint
    
    print(f"Platform: {config.platform}")
    print("\nOptimization Config:")
    pprint.pprint(config.generate_spec_options())