# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SubtitleToolkit is a Python-based collection of scripts for working with video subtitles. The toolkit provides three main utilities:

1. **MKV Subtitle Extractor** (`extract_mkv_subtitles.py`) - Extracts subtitle tracks from MKV video files
2. **SRT Translation Tool** (`srtTranslateWhole.py`) - Translates SRT subtitle files using AI providers (OpenAI, Claude, or local LM Studio)
3. **SRT Name Synchronizer** (`srt_names_sync.py`) - Uses AI to intelligently match and rename SRT files to correspond with MKV video files

## Dependencies and Environment Setup

The project uses several third-party Python libraries:

### Core Dependencies
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
pip install openai anthropic python-dotenv tqdm
```

## Script Architecture and Usage

### extract_mkv_subtitles.py
- **Purpose**: Extract subtitle tracks from MKV files using ffmpeg
- **Usage**: `python extract_mkv_subtitles.py [directory] [-l language_code]`
- **Architecture**: 
  - Uses ffprobe to analyze MKV files and detect subtitle tracks
  - Supports progress tracking with colored output
  - Multi-threaded processing with progress animations
  - Automatically finds English subtitles by default, with language selection support

### srtTranslateWhole.py  
- **Purpose**: Translate SRT files between languages using AI providers
- **Usage**: `python srtTranslateWhole.py -f input.srt [-o output.srt] -p provider -m model`
- **Architecture**:
  - Chunk-based processing for large subtitle files
  - Concurrent translation with configurable worker threads
  - SRT format validation and normalization
  - Provider abstraction supporting OpenAI, Claude, and LM Studio
  - Retry mechanisms with automatic chunk splitting on failures
  - Context-aware translation with film/show context support

### srt_names_sync.py
- **Purpose**: AI-powered matching and renaming of SRT files to match MKV files
- **Usage**: `python srt_names_sync.py [directory] --provider openai/claude [--execute]`
- **Architecture**:
  - Uses LLM providers to analyze filename patterns
  - Confidence-based matching with configurable thresholds  
  - Dry-run mode by default with `--execute` flag for actual renaming
  - Recursive directory scanning
  - JSON-based LLM communication with response parsing

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

### Testing Scripts
```bash
# Test MKV extraction (dry run)
python scripts/extract_mkv_subtitles.py /path/to/mkv/files

# Test translation with small file
python scripts/srtTranslateWhole.py -f sample.srt -p openai -m gpt-4o-mini

# Test name sync (dry run)
python scripts/srt_names_sync.py /path/to/files --provider openai
```

### Environment Setup
Create a `.env` file in the project root:
```
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_claude_key
```