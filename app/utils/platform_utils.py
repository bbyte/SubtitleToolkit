"""
Platform-specific utilities for cross-platform tool detection and management.

Handles platform differences in PATH resolution, executable detection,
and installation guidance across Windows, macOS, and Linux.
"""

import os
import platform
import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import glob


class PlatformUtils:
    """Platform-specific utilities for tool detection and system interaction."""
    
    @staticmethod
    def get_platform() -> str:
        """Get normalized platform identifier."""
        system = platform.system().lower()
        if system == "darwin":
            return "macos"
        return system
    
    @staticmethod
    def get_platform_info() -> Dict[str, str]:
        """Get detailed platform information."""
        system = platform.system()
        release = platform.release()
        machine = platform.machine()
        
        info = {
            "system": system,
            "release": release,
            "machine": machine,
            "platform": PlatformUtils.get_platform()
        }
        
        # Add platform-specific details
        if system == "Linux":
            info.update(PlatformUtils._get_linux_distro_info())
        elif system == "Darwin":
            info.update(PlatformUtils._get_macos_version_info())
        elif system == "Windows":
            info.update(PlatformUtils._get_windows_version_info())
        
        return info
    
    @staticmethod
    def _get_linux_distro_info() -> Dict[str, str]:
        """Get Linux distribution information."""
        info = {}
        try:
            # Try reading /etc/os-release (modern distributions)
            if Path("/etc/os-release").exists():
                with open("/etc/os-release", 'r') as f:
                    for line in f:
                        if line.startswith("ID="):
                            info["distro"] = line.split("=")[1].strip().strip('"')
                        elif line.startswith("VERSION_ID="):
                            info["distro_version"] = line.split("=")[1].strip().strip('"')
                        elif line.startswith("NAME="):
                            info["distro_name"] = line.split("=")[1].strip().strip('"')
        except Exception:
            # Fallback to platform module
            info["distro"] = "unknown"
        
        return info
    
    @staticmethod
    def _get_macos_version_info() -> Dict[str, str]:
        """Get macOS version information."""
        info = {}
        try:
            # Get macOS version
            result = subprocess.run(
                ["sw_vers", "-productVersion"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                info["macos_version"] = result.stdout.strip()
            
            # Detect if running on Apple Silicon
            if platform.machine() == "arm64":
                info["architecture"] = "apple_silicon"
                info["default_homebrew_path"] = "/opt/homebrew"
            else:
                info["architecture"] = "intel"
                info["default_homebrew_path"] = "/usr/local"
                
        except Exception:
            info["macos_version"] = "unknown"
        
        return info
    
    @staticmethod
    def _get_windows_version_info() -> Dict[str, str]:
        """Get Windows version information."""
        info = {}
        try:
            import winreg
            
            # Get Windows version from registry
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                               r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
            
            try:
                info["windows_version"] = winreg.QueryValueEx(key, "DisplayVersion")[0]
            except FileNotFoundError:
                info["windows_version"] = winreg.QueryValueEx(key, "ReleaseId")[0]
            
            winreg.CloseKey(key)
        except Exception:
            info["windows_version"] = "unknown"
        
        return info
    
    @staticmethod
    def get_executable_name(tool_name: str) -> str:
        """Get platform-appropriate executable name."""
        if PlatformUtils.get_platform() == "windows":
            return f"{tool_name}.exe"
        return tool_name
    
    @staticmethod
    def get_common_tool_paths(tool_name: str) -> List[str]:
        """Get comprehensive list of common installation paths for a tool."""
        platform_name = PlatformUtils.get_platform()
        executable_name = PlatformUtils.get_executable_name(tool_name)
        paths = []
        
        if platform_name == "windows":
            paths.extend(PlatformUtils._get_windows_tool_paths(tool_name, executable_name))
        elif platform_name == "macos":
            paths.extend(PlatformUtils._get_macos_tool_paths(tool_name, executable_name))
        else:  # Linux and other Unix-like
            paths.extend(PlatformUtils._get_linux_tool_paths(tool_name, executable_name))
        
        # Add user-specific paths that are common across platforms
        home = Path.home()
        paths.extend([
            str(home / "bin" / executable_name),
            str(home / ".local" / "bin" / executable_name),
            str(home / f".{tool_name}" / executable_name),
        ])
        
        return paths
    
    @staticmethod
    def _get_windows_tool_paths(tool_name: str, executable_name: str) -> List[str]:
        """Get Windows-specific tool paths."""
        paths = []
        
        # Program Files directories
        program_files_dirs = [
            os.environ.get("ProgramFiles", r"C:\Program Files"),
            os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
            os.environ.get("ProgramW6432", r"C:\Program Files"),
        ]
        
        for pf_dir in program_files_dirs:
            if not pf_dir:
                continue
                
            if tool_name in ["ffmpeg", "ffprobe"]:
                # Common FFmpeg installation paths
                paths.extend([
                    f"{pf_dir}\\ffmpeg\\bin\\{executable_name}",
                    f"{pf_dir}\\FFmpeg\\bin\\{executable_name}",
                    f"{pf_dir}\\ffmpeg-master-latest-win64-gpl\\bin\\{executable_name}",
                ])
            elif tool_name == "mkvextract":
                # Common MKVToolNix installation paths
                paths.extend([
                    f"{pf_dir}\\MKVToolNix\\{executable_name}",
                    f"{pf_dir}\\mkvtoolnix\\{executable_name}",
                ])
        
        # Chocolatey paths
        choco_bin = r"C:\ProgramData\chocolatey\bin"
        paths.append(f"{choco_bin}\\{executable_name}")
        
        # Scoop paths
        scoop_apps = Path.home() / "scoop" / "apps"
        if tool_name in ["ffmpeg", "ffprobe"]:
            paths.extend([
                str(scoop_apps / "ffmpeg" / "current" / "bin" / executable_name),
            ])
        elif tool_name == "mkvextract":
            paths.extend([
                str(scoop_apps / "mkvtoolnix" / "current" / executable_name),
            ])
        
        return paths
    
    @staticmethod
    def _get_macos_tool_paths(tool_name: str, executable_name: str) -> List[str]:
        """Get macOS-specific tool paths."""
        paths = []
        platform_info = PlatformUtils.get_platform_info()
        
        # Homebrew paths (different for Intel vs Apple Silicon)
        homebrew_prefix = platform_info.get("default_homebrew_path", "/usr/local")
        paths.append(f"{homebrew_prefix}/bin/{executable_name}")
        
        # Check both Intel and Apple Silicon Homebrew paths
        for brew_path in ["/usr/local", "/opt/homebrew"]:
            paths.append(f"{brew_path}/bin/{executable_name}")
        
        # MacPorts
        paths.append(f"/opt/local/bin/{executable_name}")
        
        # Application bundles for GUI tools
        if tool_name == "mkvextract":
            # MKVToolNix app bundle
            app_pattern = "/Applications/MKVToolNix-*.app/Contents/MacOS/mkvextract"
            paths.extend(glob.glob(app_pattern))
            paths.append("/Applications/MKVToolNix.app/Contents/MacOS/mkvextract")
        
        # System paths
        paths.extend([
            f"/usr/bin/{executable_name}",
            f"/usr/local/bin/{executable_name}",
        ])
        
        return paths
    
    @staticmethod
    def _get_linux_tool_paths(tool_name: str, executable_name: str) -> List[str]:
        """Get Linux-specific tool paths."""
        paths = []
        
        # Standard system paths
        system_paths = [
            "/usr/bin",
            "/usr/local/bin", 
            "/opt/bin",
            "/bin",
            "/usr/sbin",
            "/usr/local/sbin"
        ]
        
        for sys_path in system_paths:
            paths.append(f"{sys_path}/{executable_name}")
        
        # Snap packages
        paths.append(f"/snap/bin/{executable_name}")
        
        # Flatpak
        paths.append(f"/var/lib/flatpak/exports/bin/{executable_name}")
        
        # AppImage locations
        appimage_dirs = [
            str(Path.home() / "Applications"),
            str(Path.home() / "appimages"),
            "/opt/appimages"
        ]
        
        for appimage_dir in appimage_dirs:
            if Path(appimage_dir).exists():
                # Look for AppImages
                pattern = f"{appimage_dir}/*{tool_name}*.AppImage"
                paths.extend(glob.glob(pattern))
        
        return paths
    
    @staticmethod
    def get_installation_guide(tool_name: str) -> str:
        """Get platform-specific installation guide for a tool."""
        platform_name = PlatformUtils.get_platform()
        platform_info = PlatformUtils.get_platform_info()
        
        if platform_name == "windows":
            return PlatformUtils._get_windows_installation_guide(tool_name)
        elif platform_name == "macos":
            return PlatformUtils._get_macos_installation_guide(tool_name, platform_info)
        else:  # Linux
            return PlatformUtils._get_linux_installation_guide(tool_name, platform_info)
    
    @staticmethod
    def _get_windows_installation_guide(tool_name: str) -> str:
        """Get Windows installation guide."""
        if tool_name in ["ffmpeg", "ffprobe"]:
            return """FFmpeg Installation for Windows:

Option 1: Download Pre-built Binaries (Recommended)
1. Go to https://ffmpeg.org/download.html#build-windows
2. Download the latest 'release' build
3. Extract the ZIP file to C:\\ffmpeg
4. Add C:\\ffmpeg\\bin to your system PATH:
   - Open System Properties → Advanced → Environment Variables
   - Edit PATH variable and add C:\\ffmpeg\\bin
   - Restart the application

Option 2: Package Manager
- Chocolatey: choco install ffmpeg
- Scoop: scoop install ffmpeg"""
            
        elif tool_name == "mkvextract":
            return """MKVToolNix Installation for Windows:

Option 1: Official Installer (Recommended)
1. Go to https://mkvtoolnix.download/downloads.html
2. Download the Windows installer
3. Run the installer and follow the setup wizard
4. The tools will be installed to Program Files\\MKVToolNix

Option 2: Package Manager
- Chocolatey: choco install mkvtoolnix"""
        
        return f"Please install {tool_name} for Windows"
    
    @staticmethod
    def _get_macos_installation_guide(tool_name: str, platform_info: Dict[str, str]) -> str:
        """Get macOS installation guide."""
        arch_note = ""
        if platform_info.get("architecture") == "apple_silicon":
            arch_note = "\nNote: You're using Apple Silicon (M1/M2). Homebrew installs to /opt/homebrew"
        
        if tool_name in ["ffmpeg", "ffprobe"]:
            return f"""FFmpeg Installation for macOS:

Option 1: Homebrew (Recommended)
1. Install Homebrew from https://brew.sh if you haven't already
2. Run: brew install ffmpeg
3. FFmpeg will be available in your PATH{arch_note}

Option 2: MacPorts
1. Install MacPorts from https://www.macports.org
2. Run: sudo port install ffmpeg

Option 3: Pre-built Binaries
1. Download from https://evermeet.cx/ffmpeg/
2. Copy to /usr/local/bin or add to PATH"""
            
        elif tool_name == "mkvextract":
            return f"""MKVToolNix Installation for macOS:

Option 1: Homebrew (Recommended)
1. Install Homebrew from https://brew.sh if you haven't already  
2. Run: brew install mkvtoolnix
3. MKVextract will be available in your PATH{arch_note}

Option 2: Application Bundle
1. Download from https://mkvtoolnix.download/downloads.html
2. Install the .dmg file
3. Tools will be in /Applications/MKVToolNix.app/Contents/MacOS/"""
        
        return f"Please install {tool_name} for macOS"
    
    @staticmethod 
    def _get_linux_installation_guide(tool_name: str, platform_info: Dict[str, str]) -> str:
        """Get Linux installation guide."""
        distro = platform_info.get("distro", "unknown").lower()
        
        # Common package manager commands by distribution family
        if distro in ["ubuntu", "debian", "mint", "pop"]:
            pkg_cmd = "sudo apt install"
        elif distro in ["fedora", "rhel", "centos", "rocky", "alma"]:
            pkg_cmd = "sudo dnf install"  # or yum for older versions
        elif distro in ["arch", "manjaro", "endeavour"]:
            pkg_cmd = "sudo pacman -S"
        elif distro in ["opensuse", "suse"]:
            pkg_cmd = "sudo zypper install"
        else:
            pkg_cmd = "# Use your distribution's package manager to install"
        
        if tool_name in ["ffmpeg", "ffprobe"]:
            return f"""FFmpeg Installation for Linux ({platform_info.get('distro_name', 'Linux')}):

Option 1: Package Manager (Recommended)
{pkg_cmd} ffmpeg

Option 2: Snap Package
sudo snap install ffmpeg

Option 3: Flatpak
flatpak install flathub org.freedesktop.Platform.ffmpeg-full

Option 4: Build from Source
1. Download from https://ffmpeg.org/download.html
2. Follow the compilation guide for your distribution"""
            
        elif tool_name == "mkvextract":
            pkg_name = "mkvtoolnix" if distro not in ["arch", "manjaro"] else "mkvtoolnix-cli"
            
            return f"""MKVToolNix Installation for Linux ({platform_info.get('distro_name', 'Linux')}):

Option 1: Package Manager (Recommended)
{pkg_cmd} {pkg_name}

Option 2: Official Repository (Latest Version)
1. Add the official MKVToolNix repository
2. Follow instructions at https://mkvtoolnix.download/downloads.html

Option 3: AppImage
1. Download from https://mkvtoolnix.download/downloads.html
2. Make executable: chmod +x MKVToolNix-*.AppImage"""
        
        return f"Please install {tool_name} for Linux"
    
    @staticmethod
    def find_executables_in_path(tool_name: str) -> List[str]:
        """Find all instances of an executable in PATH."""
        executable_name = PlatformUtils.get_executable_name(tool_name)
        executables = []
        
        # Get PATH environment variable
        path_env = os.environ.get("PATH", "")
        path_dirs = path_env.split(os.pathsep)
        
        for path_dir in path_dirs:
            if not path_dir:
                continue
                
            try:
                exe_path = Path(path_dir) / executable_name
                if exe_path.exists() and exe_path.is_file():
                    # Check if executable
                    if os.access(str(exe_path), os.X_OK):
                        executables.append(str(exe_path))
            except (OSError, PermissionError):
                # Skip directories we can't access
                continue
        
        return executables
    
    @staticmethod
    def validate_path_security(path: str) -> Tuple[bool, str]:
        """Validate that a path is safe to execute."""
        try:
            path_obj = Path(path).resolve()
            
            # Check if path exists
            if not path_obj.exists():
                return False, "Path does not exist"
            
            # Check if it's a file
            if not path_obj.is_file():
                return False, "Path is not a file"
            
            # Check if executable
            if not os.access(str(path_obj), os.X_OK):
                return False, "File is not executable"
            
            # Basic security checks
            path_str = str(path_obj)
            
            # Reject paths with suspicious patterns
            suspicious_patterns = ["../", "..\\", "~", "$"]
            if any(pattern in path_str for pattern in suspicious_patterns):
                return False, "Path contains suspicious characters"
            
            # Ensure path is absolute after resolution
            if not path_obj.is_absolute():
                return False, "Path must be absolute"
            
            return True, "Path is valid"
            
        except Exception as e:
            return False, f"Path validation error: {str(e)}"