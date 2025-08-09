# SubtitleToolkit Desktop Application

A professional cross-platform desktop application for subtitle processing, built with PySide6. Transform your video subtitle workflows with an intuitive GUI that orchestrates extraction, translation, and synchronization of subtitle files.

![Platform Support](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-blue)
![Python Version](https://img.shields.io/badge/Python-3.11%2B-green)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen)

## 🎯 Features

### Core Functionality
- **🎬 Subtitle Extraction**: Extract subtitle tracks from MKV files with language selection
- **🌐 AI Translation**: Translate subtitles using OpenAI, Anthropic Claude, or local LM Studio
- **🔄 File Synchronization**: Intelligently match and rename subtitle files to video files
- **⚡ Pipeline Orchestration**: Run complete Extract → Translate → Sync workflows

### Desktop Experience  
- **🖥️ Modern GUI**: Professional PySide6 interface with dark theme
- **📊 Real-time Progress**: Live progress tracking and logging for all operations
- **⚙️ Comprehensive Settings**: Tool detection, API management, and workflow configuration
- **🔍 Dependency Detection**: Automatic detection of ffmpeg/mkvextract with installation guidance
- **📱 Cross-platform**: Native support for Windows, macOS, and Linux

## 📋 Prerequisites

### Required
- **Python 3.11 or higher**
- **Virtual environment** (recommended)

### Optional Dependencies
- **ffmpeg & ffprobe**: For MKV subtitle extraction
- **mkvextract** (MKVToolNix): Alternative for MKV processing  
- **API Keys**: For translation services (OpenAI, Anthropic Claude)

### Platform-Specific Installation

#### macOS
```bash
# Install ffmpeg and MKVToolNix via Homebrew
brew install ffmpeg mkvtoolnix

# Or install manually:
# - ffmpeg: https://ffmpeg.org/download.html
# - MKVToolNix: https://mkvtoolnix.download/
```

#### Windows
```powershell
# Install via Chocolatey (recommended)
choco install ffmpeg mkvtoolnix

# Or install manually:
# - ffmpeg: https://ffmpeg.org/download.html  
# - MKVToolNix: https://mkvtoolnix.download/
# - Add installation directories to your PATH
```

#### Linux (Ubuntu/Debian)
```bash
# Install via package manager
sudo apt update
sudo apt install ffmpeg mkvtoolnix

# For other distributions:
# - Fedora: sudo dnf install ffmpeg mkvtoolnix
# - Arch: sudo pacman -S ffmpeg mkvtoolnix
```

## 🚀 Quick Start

### 1. Clone and Setup
```bash
# Clone the repository
git clone <repository-url>
cd SubtitleToolkit

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure API Keys (Optional)
Create a `.env` file in the project root:
```bash
# API keys for translation services
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_claude_api_key_here

# Optional: Local LM Studio endpoint
LM_STUDIO_BASE_URL=http://localhost:1234/v1
```

### 3. Launch the Application
```bash
# Launch desktop GUI
python3 launch_app.py

# Or use CLI scripts directly
python3 scripts/extract_mkv_subtitles.py --help
python3 scripts/srtTranslateWhole.py --help
python3 scripts/srt_names_sync.py --help
```

## 📖 User Guide

### Desktop Application Workflow

#### 1. Project Setup
1. Launch the application: `python3 launch_app.py`
2. Click **"Select Project Folder"** to choose your working directory
3. The app will auto-detect existing MKV and SRT files

#### 2. Configure Processing Stages
Toggle and configure the stages you need:

**📥 Extract Stage**
- Select subtitle language (English, Spanish, French, etc.)
- Choose output directory
- Configure subtitle format preferences

**🌐 Translate Stage**  
- Select source and target languages
- Choose translation provider (OpenAI, Claude, LM Studio)
- Configure model and translation parameters
- Set API keys in Settings if not using environment variables

**🔄 Sync Stage**
- Enable dry-run mode to preview changes
- Set confidence threshold for matching
- Configure naming template (`{base}.{lang}.srt`)

#### 3. Run Processing
1. Click **"Run"** to start the selected stages
2. Monitor real-time progress in the progress bar
3. View detailed logs in the log panel  
4. Review results in the results panel

#### 4. Settings Configuration
Access **File → Settings** (Ctrl+,) for:

**🔧 Tools Tab**
- Automatic detection of ffmpeg/mkvextract
- Manual path overrides if needed
- Test tool functionality

**🤖 Translators Tab**  
- API key management with secure storage
- Model selection per provider
- Connection testing

**🌍 Languages Tab**
- Default source/target language preferences
- Language detection settings

**⚙️ Advanced Tab**
- Performance settings (concurrency)
- Logging levels and cleanup options
- Application behavior preferences

### Command Line Interface

All three CLI scripts support both traditional output and structured JSONL output for automation:

#### Extract Subtitles
```bash
# Basic extraction
python3 scripts/extract_mkv_subtitles.py /path/to/videos

# With language selection
python3 scripts/extract_mkv_subtitles.py /path/to/videos -l eng

# JSONL output for automation
python3 scripts/extract_mkv_subtitles.py /path/to/videos --jsonl
```

#### Translate Subtitles
```bash
# Translate with OpenAI
python3 scripts/srtTranslateWhole.py -f input.srt -p openai -m gpt-4o-mini

# Translate directory of files
python3 scripts/srtTranslateWhole.py -d /path/to/srt/files -p claude

# JSONL output for automation
python3 scripts/srtTranslateWhole.py -f input.srt -p openai --jsonl
```

#### Synchronize Names
```bash
# Dry run (preview only)
python3 scripts/srt_names_sync.py /path/to/files --provider openai

# Execute rename operations
python3 scripts/srt_names_sync.py /path/to/files --provider openai --execute

# JSONL output for automation  
python3 scripts/srt_names_sync.py /path/to/files --provider openai --jsonl
```

## 🧪 Testing

### Run Test Suite
```bash
# Activate virtual environment
source venv/bin/activate

# Run comprehensive tests
python3 run_comprehensive_tests.py

# Quick validation tests only
python3 run_comprehensive_tests.py --quick

# Run specific test categories
python3 run_comprehensive_tests.py --unit-only
python3 run_comprehensive_tests.py --integration-only
```

### Test Categories
- **Unit Tests**: Individual component testing (90%+ coverage)
- **Integration Tests**: Full workflow validation
- **Error Scenarios**: Failure condition handling
- **Cross-Platform**: Platform-specific functionality
- **Performance**: Benchmarking and optimization

### Manual Testing
```bash
# Test CLI scripts
python3 tests/manual_test_cli.py

# Test JSONL output
python3 tests/validate_jsonl_output.py

# Test dependency detection
python3 tests/test_dependency_detection.py
```

## 🔧 Development

### Project Structure
```
SubtitleToolkit/
├── scripts/                    # Enhanced CLI scripts
│   ├── extract_mkv_subtitles.py
│   ├── srtTranslateWhole.py
│   └── srt_names_sync.py
├── app/                        # PySide6 desktop application
│   ├── main.py                 # Application entry point
│   ├── main_window.py          # Main window
│   ├── widgets/                # UI components
│   ├── dialogs/                # Settings and dialogs
│   ├── runner/                 # Subprocess orchestration
│   ├── config/                 # Configuration management
│   └── utils/                  # Utilities and helpers
├── tests/                      # Comprehensive test suite
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   ├── error_scenarios/        # Error handling tests
│   └── platform/               # Cross-platform tests
├── build/                      # Build and packaging
│   ├── scripts/                # Build automation
│   ├── installers/             # Platform installers
│   └── *.spec                  # PyInstaller configurations
├── requirements.txt            # Python dependencies
├── launch_app.py              # Application launcher
└── README.md                  # This file
```

### Adding Features
1. **UI Components**: Add to `app/widgets/` with proper signal/slot connections
2. **CLI Enhancements**: Modify scripts while maintaining JSONL compatibility  
3. **New Workflows**: Extend `app/runner/` for additional processing stages
4. **Tests**: Add corresponding tests for all new functionality

### Code Style
- **Type Hints**: Use type annotations throughout
- **Documentation**: Comprehensive docstrings for all functions
- **Error Handling**: Graceful degradation and user-friendly messages
- **Qt Best Practices**: Proper signal/slot usage and memory management

## 📦 Building and Distribution

### Development Build
```bash
# Build for current platform
python3 build/scripts/build.py

# Clean build
python3 build/scripts/build.py --clean

# Validation only (no actual build)
python3 build/scripts/build.py --validate-only
```

### Production Release
```bash
# Create complete release package
python3 build/scripts/release.py 1.0.0

# Platform-specific builds
bash build/scripts/build-macos.sh     # macOS
build/scripts/build-windows.bat       # Windows  
bash build/scripts/build-linux.sh     # Linux
```

### Distribution Packages
- **Windows**: `.exe` executable, ZIP archive, optional installer
- **macOS**: `.app` bundle, professional DMG, compressed archive
- **Linux**: Directory package, AppImage, desktop integration

## ❓ Troubleshooting

### Common Issues

#### "ffmpeg not found"
```bash
# Check if ffmpeg is installed
ffmpeg -version

# Install via package manager (see Prerequisites)
# Or set custom path in Settings → Tools tab
```

#### "API key not set"  
```bash
# Set environment variables
export OPENAI_API_KEY=your_key_here
export ANTHROPIC_API_KEY=your_key_here

# Or configure in Settings → Translators tab
```

#### "Import errors"
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

#### "GUI not launching"
```bash
# Check Qt installation
python3 -c "from PySide6.QtWidgets import QApplication; print('Qt OK')"

# Use launcher script
python3 launch_app.py

# Check for display issues on Linux
export DISPLAY=:0
```

### Debug Mode
```bash
# Enable debug logging
export SUBTITLE_TOOLKIT_DEBUG=1
python3 launch_app.py

# Verbose CLI output
python3 scripts/extract_mkv_subtitles.py /path/to/files --verbose
```

### Performance Issues
- **Large Files**: Adjust concurrency in Settings → Advanced
- **Memory Usage**: Monitor system resources during processing
- **Network Timeouts**: Configure API timeouts in settings

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Set up development environment: `pip install -r requirements.txt`
4. Run tests: `python3 run_comprehensive_tests.py`
5. Make changes with proper tests
6. Commit: `git commit -m 'Add amazing feature'`
7. Push: `git push origin feature/amazing-feature`
8. Create Pull Request

### Code Guidelines
- Follow PEP 8 style guidelines
- Add type hints for all functions
- Include comprehensive docstrings
- Write tests for new functionality
- Ensure cross-platform compatibility

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **PySide6**: Modern Qt framework for Python
- **OpenAI/Anthropic**: AI translation services
- **ffmpeg/MKVToolNix**: Video processing tools
- **Python Community**: Excellent libraries and ecosystem

## 📞 Support

- **Issues**: Report bugs and request features via GitHub Issues
- **Documentation**: Additional docs in `/docs` directory
- **Community**: Join discussions in GitHub Discussions

---

**🎉 Happy subtitle processing with SubtitleToolkit! 🎉**