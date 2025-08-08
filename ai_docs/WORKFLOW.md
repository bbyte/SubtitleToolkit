# SubtitleToolkit Desktop Application - Multi-Agent Implementation Workflow

## Overview

This workflow defines the implementation strategy for building a cross-platform PySide6 desktop application that provides a GUI interface for the existing SubtitleToolkit CLI scripts. The implementation uses specialized AI agents, each expert in their domain, to ensure high-quality deliverables across all aspects of the project.

## Agent Roles & Responsibilities

### 🐍 Python Backend Agent
**Expertise**: Python development, CLI modification, subprocess management, data structures
**Responsibilities**: Script enhancement, backend logic, subprocess orchestration, configuration management

### 🖥️ PySide6 UI Agent  
**Expertise**: Desktop UI development, Qt framework, cross-platform GUI design, user experience
**Responsibilities**: Interface design, UI components, user interactions, visual feedback systems

### 🧪 QA Agent
**Expertise**: Testing strategies, quality assurance, edge case handling, cross-platform validation
**Responsibilities**: Test development, validation scripts, error scenario testing, quality gates

### 📦 Packaging Agent
**Expertise**: Application packaging, cross-platform distribution, build systems, deployment
**Responsibilities**: PyInstaller configuration, platform-specific builds, distribution packages

---

## Implementation Phases

### Phase 1: Script Enhancement & JSONL Integration

**Lead Agent**: 🐍 **Python Backend Agent**

#### 1.1 Add JSONL Output Mode to CLI Scripts

**Tasks**:
- Modify `extract_mkv_subtitles.py` to support `--jsonl` flag
- Modify `srtTranslateWhole.py` to support `--jsonl` flag  
- Modify `srt_names_sync.py` to support `--jsonl` flag
- Preserve existing CLI behavior when `--jsonl` is not present

**JSONL Event Schema Implementation**:
```python
{
  "ts": "2025-08-08T07:42:01Z",           # ISO 8601 UTC timestamp
  "stage": "extract|translate|sync",       # Pipeline stage identifier
  "type": "info|progress|warning|error|result",  # Event type
  "msg": "human-readable message",         # User-facing message
  "progress": 0,                          # Integer 0-100 (optional)
  "data": {}                              # Stage-specific payload
}
```

**Deliverables**:
- [ ] Enhanced `extract_mkv_subtitles.py` with JSONL mode
- [ ] Enhanced `srtTranslateWhole.py` with JSONL mode
- [ ] Enhanced `srt_names_sync.py` with JSONL mode
- [ ] JSONL event schema documentation
- [ ] Backward compatibility validation

**Testing Criteria**:
- All existing CLI functionality preserved
- JSONL output is valid, parseable JSON per line
- Progress events accurately reflect actual progress
- Error events include appropriate context data

---

### Phase 2: Desktop Application Architecture

**Lead Agent**: 🖥️ **PySide6 UI Agent**

#### 2.1 Main Application Structure

**Tasks**:
- Create main application window layout
- Design project folder selection interface
- Implement stage selection UI (Extract/Translate/Sync toggles)
- Build stage configuration panels with expandable sections

**UI Components**:
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

#### 2.2 Settings and Configuration UI

**Tasks**:
- Create settings dialog window
- Implement tool path detection UI with status indicators
- Build API key management interface
- Design language defaults configuration

**Settings Structure**:
- **Tools Tab**: ffmpeg/mkvextract detection, manual path overrides, test buttons
- **Translators Tab**: API key fields, model selection, engine-specific options
- **Languages Tab**: default source/target language selection
- **Advanced Tab**: concurrency settings, log levels, temp file handling

**Deliverables**:
- [ ] Complete PySide6 main window implementation
- [ ] Settings dialog with all configuration options
- [ ] Responsive UI design with proper layouts
- [ ] Real-time status updates and visual feedback
- [ ] Cross-platform UI consistency

---

### Phase 3: Backend Integration & Process Management

**Lead Agent**: 🐍 **Python Backend Agent**

#### 3.1 Subprocess Orchestration System

**Tasks**:
- Build `Runner` module for QProcess management
- Implement JSONL stream parser for real-time event processing
- Create subprocess lifecycle management (start/stop/cancel)
- Develop progress aggregation and status tracking

**Runner Architecture**:
```python
class ScriptRunner:
    def run_extract(self, config: ExtractConfig) -> QProcess
    def run_translate(self, config: TranslateConfig) -> QProcess
    def run_sync(self, config: SyncConfig) -> QProcess
    def parse_jsonl_stream(self, process: QProcess) -> Iterator[Event]
    def terminate_process(self, process: QProcess, timeout: int = 5)
```

#### 3.2 Dependency Detection & Management

**Tasks**:
- Implement PATH scanning for ffmpeg/mkvextract
- Create version detection and validation
- Build platform-specific installation guidance
- Develop configuration persistence system

**Detection Logic**:
```python
class DependencyChecker:
    def detect_ffmpeg(self) -> ToolStatus
    def detect_mkvextract(self) -> ToolStatus  
    def validate_tool_path(self, path: str, tool: str) -> bool
    def get_installation_guide(self, platform: str, tool: str) -> str
```

#### 3.3 Configuration Management

**Tasks**:
- Implement JSON-based configuration storage
- Create platform-appropriate config directory handling
- Build configuration validation and schema enforcement
- Develop secure API key storage

**Deliverables**:
- [ ] Complete subprocess orchestration system
- [ ] Dependency detection with status reporting
- [ ] Configuration management with validation
- [ ] Secure credential storage
- [ ] Error handling and recovery mechanisms

---

### Phase 4: Quality Assurance & Testing

**Lead Agent**: 🧪 **QA Agent**

#### 4.1 Unit Testing Strategy

**Test Categories**:
- **JSONL Parser Tests**: Malformed JSON, partial lines, stream interruptions
- **Configuration Tests**: Invalid values, missing fields, schema validation
- **Dependency Tests**: Missing tools, invalid paths, version parsing
- **UI Component Tests**: Widget interactions, state management, signal/slot connections

#### 4.2 Integration Testing

**Test Scenarios**:
- **Extract Only**: Process MKV files, validate SRT output
- **Translate Only**: Process existing SRT files, validate translations
- **Sync Only**: Dry-run and apply rename operations
- **Full Pipeline**: End-to-end Extract → Translate → Sync workflow

#### 4.3 Error Scenario Testing

**Error Cases**:
- Missing dependencies (ffmpeg/mkvextract not found)
- Invalid API credentials (rate limits, quota exceeded)
- Malformed input files (corrupted MKV, invalid SRT)
- Process interruption (user cancellation, system shutdown)
- Network failures (translation API unavailable)

#### 4.4 Cross-Platform Validation

**Platform Testing**:
- **Windows 10/11**: Path handling, executable detection, subprocess spawning
- **macOS** (Intel/Apple Silicon): Bundle permissions, dependency paths
- **Linux**: Distribution-specific PATH handling, desktop integration

**Deliverables**:
- [ ] Comprehensive unit test suite (90%+ coverage)
- [ ] Integration test scenarios with sample data
- [ ] Error case validation scripts
- [ ] Cross-platform smoke test automation
- [ ] Performance benchmarking suite

---

### Phase 5: Packaging & Distribution

**Lead Agent**: 📦 **Packaging Agent**

#### 5.1 PyInstaller Configuration

**Platform-Specific Builds**:
- **Windows**: Single executable with embedded Python runtime
- **macOS**: Application bundle (.app) with proper code signing preparation
- **Linux**: AppImage or standalone executable with dependency bundling

**Build Configuration**:
```python
# pyinstaller.spec template
a = Analysis(['app/main.py'],
    pathex=[],
    binaries=[],
    datas=[('app/ui', 'ui'), ('app/resources', 'resources')],
    hiddenimports=['pyside6', 'openai', 'anthropic'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False)
```

#### 5.2 Build Automation

**Tasks**:
- Create platform-specific build scripts
- Set up automated testing on packaged binaries
- Implement version management and release tagging
- Generate installation packages and documentation

**Build Pipeline**:
```bash
# Cross-platform build script structure
scripts/
├── build-windows.bat     # Windows build automation
├── build-macos.sh       # macOS build and bundle creation
├── build-linux.sh       # Linux build and AppImage generation
└── test-package.py      # Automated testing of packaged apps
```

#### 5.3 Distribution Preparation

**Tasks**:
- Generate platform-specific installation instructions
- Create dependency installation guides
- Prepare release documentation and changelog
- Set up distribution channels (GitHub Releases, etc.)

**Deliverables**:
- [ ] PyInstaller configurations for all platforms
- [ ] Automated build pipeline scripts
- [ ] Platform-specific installation packages
- [ ] Distribution documentation and guides
- [ ] Release automation workflows

---

## Agent Collaboration Patterns

### Sequential Handoffs
1. **Python Backend Agent** enhances scripts → **QA Agent** validates functionality
2. **PySide6 UI Agent** builds interface → **Python Backend Agent** integrates backend
3. **QA Agent** validates integration → **Packaging Agent** creates distributions

### Parallel Development
- **PySide6 UI Agent** works on interface while **Python Backend Agent** builds orchestration
- **QA Agent** develops tests alongside feature development
- **Packaging Agent** prepares build infrastructure during development phases

### Quality Gates
Each phase requires **QA Agent** validation before proceeding:
- ✅ JSONL output validation before UI integration
- ✅ Backend integration testing before packaging
- ✅ Cross-platform validation before distribution

---

## Success Metrics

### Functional Requirements
- [ ] All CLI scripts support JSONL mode without breaking existing functionality
- [ ] Desktop application successfully orchestrates subprocess execution
- [ ] Real-time progress tracking works accurately across all stages
- [ ] Dependency detection and configuration management work on all platforms

### Quality Requirements  
- [ ] 90%+ test coverage across all modules
- [ ] Zero crashes during normal operation workflows
- [ ] Graceful error handling for all identified failure scenarios
- [ ] Cross-platform UI consistency and responsiveness

### Distribution Requirements
- [ ] Packaged applications launch successfully on target platforms
- [ ] Installation process requires no technical expertise
- [ ] Application works out-of-the-box when dependencies are properly installed
- [ ] Performance matches or exceeds CLI script execution times

---

## Risk Mitigation

### Technical Risks
- **JSONL Stream Parsing**: Implement robust line buffering and partial JSON handling
- **Cross-Platform Paths**: Use pathlib and platform-specific path resolution
- **Subprocess Management**: Implement proper cleanup and timeout handling
- **UI Responsiveness**: Use Qt threading for all blocking operations

### Integration Risks
- **Script Compatibility**: Maintain comprehensive regression test suite
- **API Changes**: Mock translation services for testing scenarios
- **Platform Differences**: Extensive cross-platform testing and CI/CD validation

This workflow ensures systematic development with clear responsibilities, comprehensive quality assurance, and successful cross-platform deployment of the SubtitleToolkit desktop application.