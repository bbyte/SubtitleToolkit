# Subtitle Toolkit — MVP Specification

## 1. Overview

A cross-platform desktop app (macOS, Windows, Linux) that chains three existing Python scripts into a simple pipeline:

1. **Extract** subtitles from MKV files
2. **Translate** SRT files via existing AI translators
3. **Name/Sync** subtitle files to match media files

**Key constraint:** preserve each script’s core logic and behavior. We only add a **JSONL output mode** and very thin wrappers to drive them from a GUI.

---

## 2. Goals

* Provide a **PySide6** desktop UI to run Extract → Translate → Name Sync.
* Keep scripts **as-is**; no refactors to algorithmic logic.
* Add stable, structured **JSON Lines (JSONL)** output for live progress/errors/results.
* Run each step as a **subprocess** (isolation, robustness).
* **Detect-only** strategy for external deps (e.g., `ffmpeg`, `mkvextract`) with optional manual path overrides.
* Minimal naming scheme in MVP: **`{base}.{lang}.srt`**.

### Non-Goals (MVP)

* No OCR (PGS image subtitles) and no Whisper alignment/generation.
* No translation caching, databases, or cloud sync.
* No auto-download/bundling of external binaries in MVP.

---

## 3. Platforms & Distribution

* **OS:** macOS (Intel/Apple Silicon), Windows 10/11, Linux (x86\_64; common distros).
* **Packaging:** PyInstaller for all three; optional Nuitka post-MVP.
* **Dependencies:** Installed by user (detect and guide):

  * `ffmpeg` (where required by scripts)
  * `mkvextract` (MKVToolNix)
* **Config storage:** Per-OS user config dir (JSON/YAML), no DB.

---

## 4. High-Level Architecture

```
/app
  /ui_qt            # PySide6 app: views, controllers, models, settings
  /runner           # Subprocess orchestration, JSONL reader, progress bus
  /checks           # Dependency detection (PATH scanning, version)
  /models           # Data models: Job, Step, Results
  /spec             # JSONL event schema, error codes (reference only)
  /settings         # Config IO, schema, validation
/scripts            # Existing CLI scripts (preserved)
  extract_mkv_subtitles.py
  srtTranslateWhole.py
  srt_names_sync.py
```

* **GUI → Runner:** Start step as `QProcess`, pass CLI args & `--jsonl`.
* **Runner → GUI:** Read `stdout` line-by-line, parse JSON, emit Qt signals for log/progress/result.
* **Settings:** tool paths, translator creds/keys (if used by scripts), default languages, naming template.

---

## 5. User Flows (MVP)

### 5.1 Project Flow

1. **Select Folder** (project root).
2. **Detection:**

   * Scan for `*.srt/ass` and `*.mkv`.
   * If SRTs exist → offer **Translate** and **Name Sync**.
   * If no SRTs but MKVs exist → offer **Extract** → then **Translate** → **Name Sync**.
3. **Configure Steps:**

   * **Extract:** choose track language(s) to extract (if supported by script), output dir.
   * **Translate:** source/target lang, engine, per-engine options (exactly as script supports).
   * **Name Sync:** dry-run, preview rename mapping, minimal template `{base}.{lang}.srt`.
4. **Run Pipeline:** show live logs & progress. Allow cancel.
5. **Results:** show summary (counts, output paths) and open folder button.

### 5.2 Settings

* **Tools:** autodetect `ffmpeg`, `mkvextract` with status chips; fields to override paths.
* **Translators:** API keys, model/engine options (same names as scripts).
* **Language Defaults:** preferred source/target.
* **General:** concurrency (if script supports), log level.

---

## 6. Subprocess Integration

All three scripts add a flag `--jsonl`:

* When **absent** → behave exactly like today (ANSI, human logs).
* When **present** → **suppress ANSI** and emit structured JSONL events to `stdout`.

### 6.1 Invocation (examples)

* Extract:
  `python extract_mkv_subtitles.py --input <folder> --jsonl [other existing flags...]`

* Translate:
  `python srtTranslateWhole.py --input <folder_or_file> --from en --to bg --engine openai --jsonl [engine flags...]`

* Name Sync:
  `python srt_names_sync.py --video <folder> --subs <folder> --template "{base}.{lang}.srt" --dry-run --jsonl`

> Exact flags remain whatever the scripts currently support; we only add `--jsonl` (and possibly `--template` / `--dry-run` if not present).

---

## 7. JSONL Event Schema

Each line is a standalone JSON object. Minimal required fields:

```json
{
  "ts": "2025-08-08T07:42:01Z",
  "stage": "extract|translate|sync",
  "type": "info|progress|warning|error|result",
  "msg": "human-readable message",
  "progress": 0,
  "data": {}
}
```

### Field semantics

* **ts**: ISO 8601 UTC timestamp.
* **stage**: pipeline stage id.
* **type**:

  * `info`: state updates, detections, start/finish of sub-steps
  * `progress`: must include `progress` (0–100) when meaningful; use `msg` for “N/M files”
  * `warning`: recoverable issues (rate limit, skipped file)
  * `error`: unrecoverable for the current file or global; include `data.code` and optional `data.file`
  * `result`: final summary for a stage (paths, counts, mapping)
* **msg**: short, user-facing text.
* **progress**: int 0–100 (omit if unknown).
* **data**: stage-specific payload.

### Suggested payloads

**extract/result**

```json
{
  "stage":"extract","type":"result","msg":"Extracted 9/9",
  "data":{"outputs":["/path/a.srt","/path/b.srt"],"skipped":["/path/c.mkv"],"track_lang":"en"}
}
```

**translate/info|progress|warning|error|result**

```json
{"stage":"translate","type":"info","msg":"Engine=openai from=en to=bg"}
{"stage":"translate","type":"progress","progress":40,"msg":"20/50 lines"}
{"stage":"translate","type":"warning","msg":"Rate-limited, retrying...","data":{"retryInSec":5}}
{"stage":"translate","type":"error","msg":"Quota exceeded","data":{"code":"QUOTA","file":"s01e03.srt"}}
{"stage":"translate","type":"result","msg":"Translated 5 files","data":{"outputs":["..."],"failed":["fileX.srt"]}}
```

**sync/result (dry-run and apply)**

```json
{
  "stage":"sync","type":"result","msg":"Dry-run mapping ready",
  "data":{"renames":[["old1.srt","new1.bg.srt"],["old2.srt","new2.bg.srt"]],"dryRun":true}
}
```

**Global start/finish hints (optional)**

```json
{"stage":"extract","type":"info","msg":"START"}
{"stage":"extract","type":"info","msg":"END"}
```

---

## 8. Error Handling & Cancelation

* **Per-file errors** (e.g., one subtitle fails): emit `type:error` with a `data.file`; continue to next file if the script currently does.
* **Global errors**: emit `type:error` without `data.file` and exit with non-zero code.
* **Cancelation**: GUI sends an OS signal to the subprocess (`terminate` → `kill` if needed). Script should exit gracefully if possible.
* **Timeouts**: configurable per stage (optional in MVP; default: no timeout).

---

## 9. UI Design (MVP)

* **Main Window**:

  * Project selector (folder)
  * Stage toggles: Extract, Translate, Sync
  * Stage configs (expanders)
  * **Run** / **Cancel** buttons
  * **Progress bar** (indeterminate fallback + step % when available)
  * **Log panel** (filter by info/warn/error)
  * **Results panel** (tabular, especially for rename preview)
  * **Open Output** button

* **Settings Dialog**:

  * **Tools**: autodetect status + path overrides, “Test” buttons
  * **Translators**: keys/options mirroring script flags
  * **Languages**: defaults
  * **Advanced**: keep temp files, concurrency (if supported)

---

## 10. Dependency Detection

* On app start and in Settings:

  * Search PATH for `ffmpeg`, `mkvextract`.
  * If not found, show **status chips** and **OS-specific instructions**:

    * macOS: `brew install ffmpeg mkvtoolnix`
    * Windows: link to official binaries + hint to add to PATH or set explicit path
    * Linux: `apt/dnf/pacman` commands (generic help)
  * Allow manual override of absolute paths. Persist in config.

---

## 11. Configuration

* Stored as `config.json` (or `.yaml`) in platform-appropriate user config dir:

  * `tools.ffmpegPath`, `tools.mkvextractPath`
  * `translator.defaultEngine`, per-engine keys/options
  * `languages.from`, `languages.to`
  * `naming.template` (default: `{base}.{lang}.srt`)
* Validate on save. Provide “Restore defaults”.

---

## 12. Security & Privacy

* API keys stored locally in config; mark as sensitive in UI (password field).
* No telemetry in MVP.
* Logs reside locally; include a “Clear logs” option.
* No network calls beyond what existing scripts already perform for translation.

---

## 13. Internationalization (Nice-to-Have)

* UI text via simple string table for future localization.
* For MVP, English UI. (Translations later.)

---

## 14. Testing Strategy

* **Unit-ish**: JSONL parser (robust against partial lines, invalid JSON).
* **Integration**: End-to-end runs on small sample folders per stage:

  * Extract only (with MKV samples)
  * Translate only (with 1–2 tiny SRTs)
  * Sync dry-run/apply (mock folder with mismatched names)
* **Cross-OS smoke tests**: run packaged app to validate subprocess spawning and path handling.
* **Error cases**: missing deps, invalid API key, rate limit (simulate via script flags if available).

---

## 15. Release Plan (MVP)

1. **Add `--jsonl`** to each script, emitting the schema above.
2. **Build Runner** (QProcess + JSONL stream reader).
3. **Implement GUI** (PySide6) with the three stages, settings, and results.
4. **Dependency checks** and OS-specific instructions.
5. **Packaging** via PyInstaller for Win/macOS/Linux.
6. **Smoke tests** on real machines/VMs.
7. **Open-source** (MIT/Apache-2.0; include attributions and a short README).

---

## 16. Future Work (Post-MVP)

* **Whisper** integration for generating subtitles or re-sync.
* **OCR** (PGS → SRT) via Tesseract or Subtitle Edit CLI.
* **Direct-import mode** (no subprocess) as an optional fast path.
* **Advanced naming templates** (`{show}.S{season}E{episode}.{lang}.srt`) + TMDb/TVDB lookup.
* **Optional auto-download** of deps on Windows.
* **Parallelization** controls for translation batches.
* **Theming** (dark mode), localization of the UI.

---

## 17. Acceptance Criteria

* Runs on Win/macOS/Linux with installed deps or configured paths.
* Drives each script via subprocess + `--jsonl` and shows live progress/logs.
* Can:

  * Extract subs from MKVs (when present),
  * Translate existing or extracted SRTs with chosen engine,
  * Preview and apply rename with `{base}.{lang}.srt`.
* Handles errors gracefully (visible in log; pipeline stops or continues per script behavior).
* Packaged binaries launch cleanly and complete the pipeline on sample data.


**End of spec.**
