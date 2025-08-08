# Product Requirements Document (PRD) — Subtitle Toolkit MVP

## 1. Product Summary

A cross-platform desktop application for managing subtitles: extracting from MKV files, translating via existing AI-based scripts, and renaming/synchronizing to match video files. The application will use the current working scripts without altering their core logic, adding only a JSONL output mode for GUI integration.

## 2. Objectives

* Create a PySide6 GUI for a simple Extract → Translate → Name Sync pipeline.
* Support Windows, macOS, and Linux.
* Maintain original script behavior while enabling structured JSONL output.
* Run each step in isolated subprocesses.
* Detect dependencies (`ffmpeg`, `mkvextract`) and allow manual path overrides.
* Ship as an open-source application.

## 3. Key Features

* **Folder-based workflow**: select a folder, auto-detect subtitles and MKVs.
* **Stage selection**: choose which steps to run (Extract, Translate, Sync).
* **Configuration per stage**: language settings, translation engine, naming template.
* **Live progress tracking**: parse JSONL events for logs, progress, warnings, errors.
* **Dependency checks**: detect required tools, display OS-specific install instructions.
* **Results preview**: especially for rename step (dry-run).

## 4. User Stories

1. As a user, I can select a project folder so that the app detects existing subtitles or MKVs.
2. As a user, I can extract subtitles from MKV files using my preferred language track.
3. As a user, I can translate subtitles using my preferred translation engine.
4. As a user, I can preview subtitle renaming before applying changes.
5. As a user, I can run the full pipeline with live progress and logs.
6. As a user, I can configure tool paths and API keys in settings.

## 5. Functional Requirements

* **FR1**: Add `--jsonl` flag to each script to output JSONL events.
* **FR2**: Implement subprocess management in GUI to run scripts and parse JSONL.
* **FR3**: Provide UI for configuring each stage's parameters.
* **FR4**: Display real-time logs and progress bars per stage.
* **FR5**: Detect `ffmpeg` and `mkvextract` on startup and in settings.
* **FR6**: Allow manual override for tool paths.

## 6. Non-Functional Requirements

* **NFR1**: Cross-platform packaging (PyInstaller).
* **NFR2**: Minimal performance overhead; scripts run as in CLI.
* **NFR3**: Robust error handling and graceful termination.
* **NFR4**: Secure local storage of API keys.
* **NFR5**: Clear, responsive UI.

## 7. Constraints

* No major refactor of existing scripts.
* No bundled dependencies in MVP.
* No cloud sync or caching.

## 8. Acceptance Criteria

* Application runs on all supported OS with dependencies installed or configured.
* User can execute each stage individually or as a pipeline.
* JSONL output from scripts is parsed and displayed in real-time.
* Errors and warnings are clearly visible.
* Rename preview works with dry-run mode.
* Packaged app works out of the box when dependencies are present.

## 9. Future Enhancements

* Whisper integration for subtitle generation.
* OCR support for image-based subtitles.
* Direct-import execution mode.
* Advanced naming templates and TVDB/TMDb lookups.
* Auto-download of dependencies for Windows.

