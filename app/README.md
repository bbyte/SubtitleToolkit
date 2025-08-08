# SubtitleToolkit Desktop Application

A modern, cross-platform desktop GUI for SubtitleToolkit built with PySide6.

## Features

- **Project Management**: Select and manage subtitle processing projects
- **Multi-Stage Processing**: Extract, Translate, and Sync operations
- **Real-time Progress**: Live progress tracking and logging
- **Configuration Management**: Expandable panels for stage-specific settings
- **Results Visualization**: Tabular results display with filtering
- **Cross-platform**: Works on Windows, macOS, and Linux

## Installation

### Prerequisites

- Python 3.8 or higher
- PySide6 (Qt6 for Python)

### Install Dependencies

```bash
# From the project root directory
pip install -r requirements.txt
```

### System Dependencies

For full functionality, you'll also need:

- **ffmpeg/ffprobe**: Required for video subtitle extraction
- **API Keys**: For translation services (OpenAI, Claude, or LM Studio)

## Usage

### Running the Application

```bash
# From the project root directory
python app/main.py
```

### Basic Workflow

1. **Select Project Directory**: Click "Browse..." to select a folder containing video/subtitle files
2. **Choose Processing Stages**: Check the boxes for Extract, Translate, and/or Sync
3. **Configure Stages**: Expand configuration panels to set options for each enabled stage
4. **Run Processing**: Click "Run Processing" to start the pipeline
5. **Monitor Progress**: Watch real-time progress in the Progress section and Log panel
6. **View Results**: Check the Results tab for detailed processing outcomes

## UI Components

### Main Layout

```
MainWindow
├── ProjectSelector (folder picker)
├── StageToggles (checkboxes for Extract/Translate/Sync)
├── StageConfigurators (expandable configuration panels)
│   ├── ExtractConfig (language selection, output directory)
│   ├── TranslateConfig (source/target lang, engine selection)
│   └── SyncConfig (naming template, dry-run toggle)
├── ProgressSection (progress bar, status text)
├── LogPanel (filterable by info/warn/error)
├── ResultsPanel (tabular results, rename preview)
└── ActionButtons (Run/Cancel/Open Output)
```

### Configuration Panels

#### Extract Configuration
- **Subtitle Language**: Target language for extraction
- **Output Directory**: Where to save extracted files
- **Output Format**: SRT, VTT, or ASS format
- **Advanced Options**: Extract all tracks, overwrite existing files

#### Translate Configuration
- **Source Language**: Auto-detect or specify source language
- **Target Language**: Desired translation target
- **Translation Engine**: OpenAI, Claude, or LM Studio
- **Model**: Engine-specific model selection
- **API Key**: Authentication for translation services
- **Advanced Options**: Chunk size, context information

#### Sync Configuration
- **Naming Template**: Template for renamed files (supports placeholders)
- **Dry Run**: Preview changes without applying them
- **Confidence Threshold**: Minimum confidence for automatic matching
- **Advanced Options**: Backup creation, case sensitivity

### Log Panel

The log panel provides real-time feedback with:
- **Color-coded Messages**: Info (blue), Warning (orange), Error (red)
- **Filtering**: Show/hide specific message types
- **Export**: Save logs to file
- **Auto-scroll**: Automatically scroll to latest messages

### Results Panel

Three tabs provide different views:
- **Results**: Tabular view of all processing results
- **Rename Preview**: Preview of filename changes (Sync stage)
- **Summary**: Statistical summary of processing outcomes

## Testing

Run the test suite to verify the application works correctly:

```bash
python test_app.py
```

This will:
1. Test all imports
2. Verify UI component creation
3. Test basic interactions
4. Optionally run a visual test

## Architecture

The application follows a modular architecture:

- **main.py**: Application entry point and styling
- **main_window.py**: Main window coordinator
- **widgets/**: Individual UI components
  - **project_selector.py**: Directory selection widget
  - **stage_toggles.py**: Processing stage checkboxes
  - **stage_configurators.py**: Configuration panels
  - **progress_section.py**: Progress display
  - **log_panel.py**: Logging interface
  - **results_panel.py**: Results visualization
  - **action_buttons.py**: Main control buttons

## Integration with CLI Scripts

This GUI is designed to integrate with the existing CLI scripts:
- `extract_mkv_subtitles.py`
- `srtTranslateWhole.py` 
- `srt_names_sync.py`

Phase 3 of development will add subprocess orchestration to run these scripts with JSONL output for real-time progress updates.

## Development Status

**Current Phase**: Phase 2 - Desktop Application Architecture ✅

**Completed Features**:
- ✅ Complete UI layout and components
- ✅ Professional styling and theming
- ✅ Signal/slot connections
- ✅ Configuration management
- ✅ Real-time logging and progress display
- ✅ Results visualization

**Next Phase**: Phase 3 - Backend Integration
- Subprocess orchestration
- JSONL stream parsing
- Real processing pipeline execution
- Dependency detection and validation

## Troubleshooting

### Common Issues

1. **"No module named 'PySide6'"**
   - Install PySide6: `pip install PySide6`

2. **Application doesn't start**
   - Check Python version (3.8+ required)
   - Verify all dependencies are installed
   - Run test script for detailed error information

3. **UI appears broken or unstyled**
   - This may indicate PySide6 version compatibility issues
   - Try updating PySide6: `pip install --upgrade PySide6`

### System-Specific Notes

#### macOS
- PySide6 works best on macOS 10.14 (Mojave) or later
- On Apple Silicon Macs, ensure you're using the correct Python architecture

#### Windows
- Windows 10 or later recommended
- Some antivirus software may flag the application during first run

#### Linux
- Qt libraries may need to be installed separately on some distributions
- Ubuntu/Debian: `sudo apt install python3-pyside6`
- Fedora: `sudo dnf install python3-pyside6`

## License

This desktop application is part of the SubtitleToolkit project.