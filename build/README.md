# SubtitleToolkit Build System

This directory contains the complete build automation and packaging system for SubtitleToolkit, enabling cross-platform distribution as standalone executables.

## Overview

The build system supports creating distributable packages for:
- **Windows**: Single executable (.exe) with optional installer
- **macOS**: Application bundle (.app) with DMG distribution
- **Linux**: Directory package and/or AppImage with desktop integration

## Directory Structure

```
build/
├── README.md                     # This file
├── config/
│   └── optimization.py           # PyInstaller optimization settings
├── hooks/                        # PyInstaller custom hooks
│   ├── hook-openai.py            # OpenAI package bundling
│   ├── hook-anthropic.py         # Anthropic package bundling  
│   └── hook-PySide6.py           # PySide6 optimization
├── installers/                   # Installer creation tools
│   ├── windows_installer.iss     # Inno Setup script for Windows
│   └── create_dmg.py             # macOS DMG creation script
├── linux/                       # Linux-specific assets
│   └── subtitletoolkit.desktop   # Desktop integration file
├── scripts/                      # Build automation scripts
│   ├── build.py                  # Universal build script
│   ├── build-windows.bat         # Windows build automation
│   ├── build-macos.sh            # macOS build automation
│   ├── build-linux.sh            # Linux build automation
│   ├── test-package.py           # Cross-platform testing framework
│   ├── test-package-windows.bat  # Windows-specific tests
│   ├── test-package-macos.sh     # macOS-specific tests
│   ├── test-package-linux.sh     # Linux-specific tests
│   └── release.py                # Complete release automation
├── entitlements.plist            # macOS code signing entitlements
├── version_info.txt              # Windows version information
├── subtitletoolkit-windows.spec  # PyInstaller spec for Windows
├── subtitletoolkit-macos.spec    # PyInstaller spec for macOS
└── subtitletoolkit-linux.spec    # PyInstaller spec for Linux
```

## Quick Start

### Build for Current Platform

```bash
# Using the universal build script (recommended)
python build/scripts/build.py

# Or run platform-specific scripts directly:

# Windows
build\\scripts\\build-windows.bat

# macOS  
bash build/scripts/build-macos.sh

# Linux
bash build/scripts/build-linux.sh
```

### Create Release Package

```bash
# Create a complete release with testing and packaging
python build/scripts/release.py 1.0.0

# Build for specific platform only
python build/scripts/release.py 1.0.0 --platform windows
```

## Prerequisites

### All Platforms
- Python 3.8 or later
- Git (for version management)
- PyInstaller: `pip install pyinstaller`

### Windows
- Visual C++ Build Tools (for native extensions)
- Inno Setup (optional, for installer creation)

### macOS
- Xcode Command Line Tools: `xcode-select --install`
- Homebrew (recommended for dependencies)

### Linux
- Build essentials: `sudo apt install build-essential` (Ubuntu/Debian)
- Qt development packages: `sudo apt install qt6-base-dev qt6-svg-dev`

## Build Process Details

### PyInstaller Configuration

Each platform has its own optimized PyInstaller spec file:

- **Windows**: Creates single executable with embedded runtime
- **macOS**: Creates proper application bundle with Info.plist
- **Linux**: Creates directory distribution optimized for AppImage

### Optimization Features

1. **Size Optimization**:
   - Excludes unused modules (testing, documentation, etc.)
   - Platform-specific exclusions
   - UPX compression (where supported)

2. **Dependency Management**:
   - Automatic detection of hidden imports
   - Custom hooks for AI provider libraries
   - Proper Qt plugin bundling

3. **Cross-Platform Compatibility**:
   - Platform-specific icon formats
   - Native system integration
   - Proper file associations

### Testing Framework

The build system includes comprehensive testing:

```bash
# Test packaged application
python build/scripts/test-package.py

# Platform-specific tests
bash build/scripts/test-package-macos.sh    # macOS
build\\scripts\\test-package-windows.bat    # Windows  
bash build/scripts/test-package-linux.sh     # Linux
```

Test categories:
- **Smoke Tests**: Basic application startup
- **Dependency Tests**: Required libraries bundled
- **Platform Tests**: OS-specific functionality
- **Integration Tests**: File associations, desktop integration

## Distribution Formats

### Windows
- **Single Executable**: `SubtitleToolkit.exe`
- **ZIP Archive**: `SubtitleToolkit-1.0.0-Windows.zip`
- **Installer**: `SubtitleToolkit-1.0.0-Windows-Setup.exe` (optional)

### macOS
- **Application Bundle**: `SubtitleToolkit.app`
- **DMG Distribution**: `SubtitleToolkit-1.0.0.dmg`
- **Archive**: `SubtitleToolkit-1.0.0-macOS.tar.gz`

### Linux
- **Directory Package**: `SubtitleToolkit-1.0.0-Linux.tar.gz`
- **AppImage**: `SubtitleToolkit-1.0.0-x86_64.AppImage`
- **Desktop Integration**: Included `.desktop` file

## Advanced Usage

### Custom Build Configuration

Edit the optimization settings:

```python
# build/config/optimization.py
config = OptimizationConfig()
options = config.generate_spec_options()
```

### Adding Dependencies

Update PyInstaller hooks in `build/hooks/` to ensure proper bundling of new dependencies.

### Platform-Specific Customization

Modify spec files in `build/` directory:
- `subtitletoolkit-windows.spec`
- `subtitletoolkit-macos.spec`  
- `subtitletoolkit-linux.spec`

### Code Signing (macOS)

```bash
# Sign the application bundle
codesign --force --deep --sign "Developer ID Application: Your Name" \\
         --entitlements build/entitlements.plist \\
         --options runtime \\
         dist/SubtitleToolkit.app

# Verify signature
codesign --verify --deep --strict dist/SubtitleToolkit.app
spctl -a -v dist/SubtitleToolkit.app
```

### Creating Installers

**Windows (Inno Setup)**:
```bash
# Compile installer script
"C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe" build\\installers\\windows_installer.iss
```

**macOS (DMG)**:
```bash
# Create styled DMG
python build/installers/create_dmg.py \\
  --app dist/SubtitleToolkit.app \\
  --output dist/SubtitleToolkit-1.0.0.dmg
```

## Troubleshooting

### Common Issues

1. **Missing Dependencies**:
   - Ensure all requirements are installed: `pip install -r requirements.txt`
   - Install PyInstaller: `pip install pyinstaller`

2. **Import Errors**:
   - Add missing modules to hiddenimports in spec files
   - Create custom hooks in `build/hooks/`

3. **Size Issues**:
   - Review exclusions in optimization config
   - Enable UPX compression where appropriate

4. **Platform-Specific Problems**:
   - **Windows**: Install Visual C++ redistributables
   - **macOS**: Install Xcode command line tools
   - **Linux**: Install Qt development packages

### Debug Mode

Enable debug mode in spec files for troubleshooting:

```python
exe = EXE(
    # ...
    debug=True,        # Enable debug output
    console=True,      # Show console window
    # ...
)
```

### Logs and Output

Build logs are saved to:
- `build/build.log` (general build output)
- `dist/` (built applications)
- `dist/release/` (release packages)

## Performance Notes

### Build Times
- **Windows**: 2-5 minutes
- **macOS**: 3-7 minutes  
- **Linux**: 3-6 minutes

### Package Sizes
- **Windows**: ~80-120 MB (single executable)
- **macOS**: ~90-130 MB (application bundle)
- **Linux**: ~85-125 MB (directory package)

### Optimization Tips

1. Use UPX compression (reduces size by ~30-40%)
2. Exclude unused Qt modules
3. Enable bytecode optimization
4. Consider one-directory vs one-file trade-offs

## Contributing

When adding new dependencies or features:

1. Update PyInstaller hooks if needed
2. Test on all target platforms
3. Update optimization exclusions
4. Run full test suite before release

## Support

For build system issues:
1. Check the troubleshooting section above
2. Review build logs in `build/build.log`
3. Test with debug mode enabled
4. Report issues with platform details and error logs