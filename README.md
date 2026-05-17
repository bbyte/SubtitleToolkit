# SubtitleToolkit Desktop Application

A professional cross-platform desktop application for subtitle processing, built with PySide6. Transform your video subtitle workflows with an intuitive GUI that orchestrates extraction, translation, and synchronization of subtitle files.

![Platform Support](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-blue)
![Python Version](https://img.shields.io/badge/Python-3.11%2B-green)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen)

## 🎯 Features

### ✅ Core Functionality (Production Ready)
- **🎬 Subtitle Extraction**: Extract subtitle tracks from MKV, MP4, AVI, MOV, WebM and other video formats with language selection
- **🌐 AI Translation**: Translate subtitles using OpenAI, Anthropic Claude, OpenRouter, xAI, Mistral, Groq, DeepSeek, Kimi, Gemini, Z.ai, or local LM Studio
- **🔄 File Synchronization**: Intelligently match and rename subtitle files to video files with preview mode
- **⚡ Pipeline Orchestration**: Complete Extract → Translate → Sync workflows with real-time progress tracking
- **📋 JSONL Integration**: All scripts support structured JSON Lines output for automation and integration
- **🎞️ FPS Conversion**: Convert subtitle timecodes between frame rates (e.g. 25 fps PAL → 23.976 fps NTSC)

### ✅ Desktop Experience (Fully Working)
- **🖥️ Modern GUI**: Professional PySide6 interface with dark theme
- **🔍 Browser-style Zoom**: Ctrl/Cmd +/- zoom controls (50%-200%) with persistent state
- **📐 Window State Memory**: Automatic save/restore of window size and position
- **📊 Real-time Progress**: Live progress tracking and logging for all operations
- **⚙️ Comprehensive Settings**: Tool detection, API management, and workflow configuration
- **🔍 Dependency Detection**: Automatic detection of ffmpeg/mkvextract with installation guidance
- **📱 Cross-platform**: Native support for Windows, macOS, and Linux
- **🌍 Multilingual UI**: Interface available in English, Bulgarian, German, and Spanish

### ✅ Subtitle Finder (New in dev)
- **🔍 Online subtitle search**: Search OpenSubtitles, Subscene, YTS, YIFY-Subtitles, and more from within the app
- **🎬 NFO-aware identification**: Reads `.nfo` files (with AI + ffprobe fallback) to identify movies accurately
- **⚡ Parallel provider queries**: All configured providers queried simultaneously for fast results
- **📥 One-click download**: Pick the best match from the results table and download directly

### ✅ Recent Improvements
- **📁 Multi-format support**: Extraction and language detection now work with MP4, AVI, MOV, M4V, WebM, TS, M2TS in addition to MKV
- **🏷️ Language-coded output filenames**: Extracted subtitles are named `movie.en.srt`; translated files use the target language code (e.g. `movie.bg.srt`)
- **🎯 Target language remembered**: Last-used translation target language is restored automatically on next launch
- **⚠️ Same-language warning**: Warns before starting a translation where source and target language are the same
- **🔒 Write-permission pre-flight**: Checks output directory writability before starting; offers a folder picker if not writable
- **✅ Per-file selection**: "Filter files…" button lets you include/exclude individual files from a directory before processing
- **🌐 Full Bulgarian translation**: All UI strings are now fully translated into Bulgarian (215 translations)

## 📋 Prerequisites

### Required
- **Python 3.11 or higher**
- **Virtual environment** (recommended)

### Optional Dependencies
- **ffmpeg & ffprobe**: For subtitle extraction from video files
- **API Keys**: For translation services (OpenAI, Anthropic Claude, etc.)
- **requests / beautifulsoup4 / lxml**: For the subtitle finder (included in `requirements.txt`)

### Platform-Specific Installation

#### macOS
```bash
brew install ffmpeg
```

#### Windows
```powershell
choco install ffmpeg
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt update && sudo apt install ffmpeg
```

## 🚀 Quick Start

### 1. Clone and Setup
```bash
git clone <repository-url>
cd SubtitleToolkit

python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Configure API Keys (Optional)
Create a `.env` file in the project root:
```bash
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_claude_api_key_here
```

Or configure them through the GUI: **File → Settings → Translators**.

### 3. Launch the Application
```bash
source venv/bin/activate
python3 launch_app.py
```

## 📖 User Guide

### Desktop Application Workflow

#### 1. Project Setup
1. Launch the application: `python3 launch_app.py`
2. Select **Directory** or **Single File** mode
3. Click **Browse…** to choose your folder or file
4. Optionally click **Filter files…** to include/exclude specific files from the directory

#### 2. Configure Processing Stages
Toggle and configure the stages you need:

**📥 Extract Stage**
- Select subtitle language (English, Bulgarian, German, Spanish, etc.)
- Choose output directory (optional — defaults to same folder as the video)
- Output files are named `{video}.{lang}.srt` (e.g. `movie.en.srt`)

**🎞️ FPS Convert Stage**
- Specify source FPS manually or auto-detect from paired video
- Specify target FPS or auto-detect
- Optionally overwrite the original SRT in-place

**🌐 Translate Stage**
- Select source language (or "Auto-detect")
- Select target language — your last choice is remembered across sessions
- Choose translation provider and model
- Output files use the target language code (e.g. `movie.bg.srt`)
- A warning is shown if source and target language are the same

**🔄 Sync Stage**
- Enable to intelligently rename SRT files to match video filenames
- Preview operations before executing

#### 3. Run Processing
1. Click **Run** to start the selected stages
2. Monitor real-time progress and logs
3. Review results in the results panel

#### 4. Per-file Selection (Filter files…)
When a directory is selected, click **Filter files…** to open a checklist of all processable files. All files are checked by default. Uncheck any files you want to skip. The button label updates to show the active filter count (e.g. *Filter files… (3/24)*).

#### 5. Accessibility & Zoom Controls
- **Zoom In**: `Ctrl/Cmd +`
- **Zoom Out**: `Ctrl/Cmd -`
- **Reset Zoom**: `Ctrl/Cmd 0`
- Range: 50%–200% in 10% steps, persisted across sessions

#### 6. Settings Configuration
Access **File → Settings** for:

- **Tools**: ffmpeg path detection and overrides
- **Translators**: API keys and model defaults per provider
- **Languages**: Interface language (English, Bulgarian, German, Spanish)
- **Advanced**: Concurrency, logging, and other preferences

### Command Line Interface

#### Extract Subtitles
```bash
# Extract from a directory (all supported video formats)
python3 scripts/extract_mkv_subtitles.py /path/to/videos

# Specific language
python3 scripts/extract_mkv_subtitles.py /path/to/videos -l eng

# Specific files only
python3 scripts/extract_mkv_subtitles.py /path/to/videos \
  --files "/path/to/video1.mp4,/path/to/video2.mkv"

# JSONL output for automation
python3 scripts/extract_mkv_subtitles.py /path/to/videos --jsonl
```

Output filenames include the language code: `movie.en.srt`, `movie.bg.srt`, etc.

#### Translate Subtitles
```bash
# Translate a single file to Bulgarian
python3 scripts/srtTranslateWhole.py -f input.en.srt -p openai \
  --source-lang English --target-lang Bulgarian

# Translate a directory
python3 scripts/srtTranslateWhole.py -d /path/to/srt/files \
  -p claude --source-lang English --target-lang Bulgarian

# JSONL output for automation
python3 scripts/srtTranslateWhole.py -f input.srt -p openai --jsonl
```

Output filename uses the target language code: `input.bg.srt`.

#### Synchronize Names
```bash
# Dry run (preview only)
python3 scripts/srt_names_sync.py /path/to/files --provider openai

# Execute rename operations
python3 scripts/srt_names_sync.py /path/to/files --provider openai --execute

# JSONL output for automation
python3 scripts/srt_names_sync.py /path/to/files --provider openai --jsonl
```

#### Find Subtitles Online
```bash
# Search all providers for a Bulgarian subtitle
python3 scripts/find_subtitles.py /path/to/movies -l bg

# Search for a single file
python3 scripts/find_subtitles.py /path/to/movie.mkv -l en

# Only read .nfo metadata (no network requests)
python3 scripts/find_subtitles.py /path/to/movies --nfo-only

# JSONL output for automation
python3 scripts/find_subtitles.py /path/to/movies -l bg --jsonl
```

## 🔧 Development

### Project Structure
```
SubtitleToolkit/
├── scripts/                    # CLI scripts
│   ├── extract_mkv_subtitles.py   # Subtitle extraction (MKV/MP4/AVI/MOV/…)
│   ├── srtTranslateWhole.py        # AI translation
│   ├── srt_names_sync.py           # Filename synchronization
│   ├── find_subtitles.py           # Online subtitle search
│   └── lib/
│       └── subtitle_finder/        # Subtitle finder library (providers, NFO parsing)
├── app/                        # PySide6 desktop application
│   ├── main.py                 # Application entry point
│   ├── main_window.py          # Main window
│   ├── widgets/                # UI components
│   ├── dialogs/                # Settings and dialogs
│   │   ├── file_filter_dialog.py   # Per-file selection dialog
│   │   └── find_subtitles_dialog.py # Online subtitle search dialog
│   ├── runner/                 # Subprocess orchestration
│   ├── config/                 # Configuration management
│   ├── i18n/                   # Translations (bg, de, es)
│   └── utils/                  # Utilities and helpers
├── requirements.txt
├── launch_app.py
└── README.md
```

### Adding a New Translation Provider
1. Add a client getter function following the pattern in `srtTranslateWhole.py`
2. Add the provider name to the `engine_combo` in `stage_configurators.py`
3. Add a default model to `_provider_defaults` in the script's `__main__` block

### Adding UI Translations
```bash
source venv/bin/activate

# Extract new strings from Python source
pyside6-lupdate app/**/*.py app/*.py -ts app/i18n/translations/subtitletoolkit_bg.ts

# Edit the .ts file to fill in translations, then compile
pyside6-lrelease app/i18n/translations/subtitletoolkit_bg.ts
```

## ❓ Troubleshooting

### "ffmpeg not found"
```bash
ffmpeg -version   # verify installation
# Or set a custom path in Settings → Tools
```

### "API key not set"
```bash
export OPENAI_API_KEY=your_key_here
# Or configure in Settings → Translators
```

### "Output directory is not writable"
The app will automatically open a folder picker — choose a writable location and processing will continue.

### Import errors
```bash
source venv/bin/activate
pip install -r requirements.txt
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **PySide6**: Modern Qt framework for Python
- **OpenAI / Anthropic / and others**: AI translation services
- **ffmpeg**: Video and subtitle processing
