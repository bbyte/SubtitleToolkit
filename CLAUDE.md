# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SubtitleToolkit is a Python-based collection of scripts for working with video subtitles. The toolkit provides three main utilities:

1. **MKV Subtitle Extractor** (`extract_mkv_subtitles.py`) - Extracts subtitle tracks from MKV video files
2. **SRT Translation Tool** (`srtTranslateWhole.py`) - Translates SRT subtitle files using AI providers (OpenAI, Claude, or local LM Studio)
3. **SRT Name Synchronizer** (`srt_names_sync.py`) - Uses AI to intelligently match and rename SRT files to correspond with MKV video files

## Dependencies and Environment Setup

**IMPORTANT**: This project uses a Python virtual environment (venv). All Python commands should be run within the activated virtual environment.

### Virtual Environment Setup
```bash
# Create virtual environment (if not exists)
python3 -m venv venv

# Activate virtual environment (required for all operations)
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate     # On Windows
```

### Core Dependencies
- `PySide6` - Qt6 bindings for the desktop GUI application
- `openai` - OpenAI API client for translation services
- `anthropic` - Claude API client for translation services  
- `python-dotenv` - Environment variable loading from .env files
- `tqdm` - Progress bars for long-running operations
- `pathlib` - Modern path handling (Python 3.4+)

### System Dependencies
- `ffmpeg` and `ffprobe` - Required for MKV subtitle extraction
- Environment variables: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` for AI services

### Installation
```bash
# Always activate venv first!
source venv/bin/activate

# Install all dependencies
pip install -r requirements.txt

# Or install individually:
pip install PySide6 openai anthropic python-dotenv tqdm
```

## Script Architecture and Usage

## Desktop Application

### launch_app.py (Main Desktop GUI)
- **Purpose**: Launch the PySide6 desktop application with full GUI
- **Usage**: `python3 launch_app.py` (with venv activated)
- **Architecture**:
  - Multi-language interface (English, Bulgarian, German, Spanish)
  - Project folder selection and stage configuration
  - Real-time progress monitoring with JSONL stream parsing
  - Settings management with API key storage
  - Zoom functionality and window state persistence

### extract_mkv_subtitles.py
- **Purpose**: Extract subtitle tracks from MKV files using ffmpeg
- **Usage**: `python3 scripts/extract_mkv_subtitles.py [directory] [-l language_code]`
- **Architecture**: 
  - Uses ffprobe to analyze MKV files and detect subtitle tracks
  - Supports progress tracking with colored output
  - Multi-threaded processing with progress animations
  - Automatically finds English subtitles by default, with language selection support
  - JSONL output mode for desktop GUI integration

### srtTranslateWhole.py  
- **Purpose**: Translate SRT files between languages using AI providers
- **Usage**: `python3 scripts/srtTranslateWhole.py -f input.srt [-o output.srt] -p provider -m model`
- **Architecture**:
  - Chunk-based processing for large subtitle files
  - Concurrent translation with configurable worker threads
  - SRT format validation and normalization
  - Provider abstraction supporting OpenAI, Claude, and LM Studio
  - Retry mechanisms with automatic chunk splitting on failures
  - Context-aware translation with film/show context support
  - JSONL output mode for desktop GUI integration

### srt_names_sync.py
- **Purpose**: AI-powered matching and renaming of SRT files to match MKV files
- **Usage**: `python3 scripts/srt_names_sync.py [directory] --provider openai/claude [--execute]`
- **Architecture**:
  - Uses LLM providers to analyze filename patterns
  - Confidence-based matching with configurable thresholds  
  - Dry-run mode by default with `--execute` flag for actual renaming
  - Recursive directory scanning
  - JSON-based LLM communication with response parsing
  - JSONL output mode for desktop GUI integration

## Key Patterns and Conventions

### Error Handling
- All scripts use colored console output for status indication (red for errors, green for success, yellow for warnings)
- Graceful fallbacks and user-friendly error messages
- API rate limiting with delays between requests

### Configuration
- Environment variables loaded via python-dotenv
- Command-line argument parsing with argparse
- Default model selection per provider

### File Processing
- Pathlib used consistently for cross-platform path handling
- Unicode encoding detection and handling for subtitle files
- Progress tracking with tqdm for long-running operations
- Concurrent processing where applicable (translation chunks, file processing)

## Common Development Tasks

### Adding New Translation Providers
1. Add provider to `LLMProvider` enum in srt_names_sync.py or provider choices in srtTranslateWhole.py
2. Implement provider-specific client initialization
3. Add provider-specific prompt formatting in `get_system_prompt()`
4. Implement translation function following existing patterns

### Running the Application
```bash
# ALWAYS activate venv first!
source venv/bin/activate

# Launch the desktop GUI application
python3 launch_app.py

# Or run CLI scripts individually:
# Test MKV extraction (dry run)
python3 scripts/extract_mkv_subtitles.py /path/to/mkv/files

# Test translation with small file
python3 scripts/srtTranslateWhole.py -f sample.srt -p openai -m gpt-4o-mini

# Test name sync (dry run)
python3 scripts/srt_names_sync.py /path/to/files --provider openai
```

### Testing and Development
```bash
# Activate venv first
source venv/bin/activate

# Run translation system tests
python3 test_translations_working.py

# Compile translation files after updates
python3 compile_translations.py

# Test individual components
python3 -m pytest tests/ (if tests exist)
```

### Environment Setup
```bash
# 1. Activate virtual environment
source venv/bin/activate

# 2. Create a `.env` file in the project root:
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_claude_key

# 3. Or configure API keys through the desktop GUI:
# Launch app -> File -> Settings -> Translators -> Enter API keys
```

## Important Commands Reference

**NEVER run Python commands without first activating the virtual environment:**

```bash
# ✅ CORRECT - Always do this first:
source venv/bin/activate
python3 launch_app.py

# ❌ INCORRECT - Will fail with module errors:  
python3 launch_app.py
```

**All development commands require venv activation:**
- Running the desktop app: `source venv/bin/activate && python3 launch_app.py`
- Running CLI scripts: `source venv/bin/activate && python3 scripts/script_name.py`
- Installing dependencies: `source venv/bin/activate && pip install package_name`
- Testing: `source venv/bin/activate && python3 test_translations_working.py`