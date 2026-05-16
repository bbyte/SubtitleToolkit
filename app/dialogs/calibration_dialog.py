"""
Calibration Dialog for SubtitleToolkit.

Provides a UI to probe an AI model and find optimal chunk-size and
concurrent-worker settings.  Results are saved per-model in QSettings
and displayed as a calibration indicator in the Translate Configuration panel.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QTabWidget, QWidget, QLabel, QComboBox, QLineEdit,
    QPushButton, QTextEdit, QProgressBar, QFrame,
    QStackedWidget, QSizePolicy, QMessageBox, QScrollArea,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QTextCursor

from app.calibration.worker import (
    CalibrationWorker, CHUNK_SIZES, WORKER_COUNTS, TOTAL_PROBES,
)
from app.calibration.store import load_calibration


# ── Documentation HTML ────────────────────────────────────────────────────────

_DOCUMENTATION_HTML = """
<h2 style="color:#4dabf7;">Model Calibration</h2>

<p>Calibration probes your selected model with small real translation requests
to determine the <b>optimal chunk size</b> and <b>worker concurrency</b> for
reliable, efficient subtitle translation.</p>

<h3 style="color:#ffa726;">What gets calibrated?</h3>
<ul>
  <li>
    <b>Chunk Size</b> — The number of subtitle lines sent per API request.<br>
    Too large → the model truncates its response and translated lines are lost.<br>
    Calibration finds the <em>largest</em> chunk that always returns a
    complete response.
  </li>
  <li style="margin-top:6px;">
    <b>Concurrent Workers</b> — How many API requests run simultaneously.<br>
    Too many → your plan's rate-limit is hit, causing errors and slow retries.<br>
    Calibration finds the <em>highest</em> concurrency your account supports.
  </li>
</ul>

<h3 style="color:#ffa726;">How does it work?</h3>

<p><b>Phase 1 — Chunk Size</b></p>
<p>Sends translation batches of increasing size:
<code>5 → 10 → 20 → 30 → 50 → 75 → 100</code> subtitles per request.
Each response is checked for completeness (≥ 90 % of items returned).
The process stops at the first failure; the last successful size is saved.</p>

<p><b>Phase 2 — Concurrency</b></p>
<p>Fires 1, 2, 3, 4, then 5 <em>identical</em> small requests simultaneously.
A rate-limit error terminates the sweep; the last fully-successful
concurrency level is saved.</p>

<h3 style="color:#ffa726;">What does calibration cost?</h3>
<table>
  <tr><th align="left">Model</th><th align="left">Typical cost</th></tr>
  <tr><td>GPT-4o-mini</td><td>&lt; $0.01</td></tr>
  <tr><td>GPT-4o</td><td>~$0.03 – $0.05</td></tr>
  <tr><td>Claude Haiku</td><td>&lt; $0.01</td></tr>
  <tr><td>Claude Sonnet</td><td>~$0.03 – $0.05</td></tr>
  <tr><td>Groq / DeepSeek / Mistral</td><td>~$0.001 – $0.01</td></tr>
</table>
<p>
Actual cost depends on how many probes complete before a limit is found.
Best case (all sizes pass): ~&thinsp;6 000 input + 4 000 output tokens.
Set model prices in the Translate Configuration panel for a dollar estimate.
</p>

<h3 style="color:#ffa726;">When should I calibrate?</h3>
<ul>
  <li>After adding a new model or provider</li>
  <li>After upgrading your API plan (higher rate limits → more workers)</li>
  <li>If translated SRT files have missing subtitle lines
      (chunk size may be too large)</li>
  <li>If the log shows frequent rate-limit retries
      (worker count may be too high)</li>
</ul>

<h3 style="color:#ffa726;">Notes</h3>
<ul>
  <li>Calibration is <em>optional</em> — the defaults (chunk&nbsp;20, 2&nbsp;workers)
      work for most models.</li>
  <li>Results are stored per-model and applied automatically when that model
      is selected in the Translate Configuration panel.</li>
  <li>You can re-calibrate at any time; previous results are replaced.</li>
  <li>The calibration uses a fixed 80-sentence English→Spanish test set,
      unrelated to your actual subtitle content.</li>
  <li>Running calibration from the <em>Translate Configuration</em> panel
      pre-fills the provider, model, and API key from your current settings.</li>
</ul>
"""


# ── Provider name mappings ────────────────────────────────────────────────────

_DISPLAY_PROVIDERS = [
    "OpenAI", "Claude", "OpenRouter", "xAI",
    "Mistral", "Groq", "DeepSeek", "Kimi", "Gemini", "Z.ai", "LM Studio",
]

_DISPLAY_TO_ID = {
    "OpenAI":    "openai",
    "Claude":    "claude",
    "OpenRouter":"openrouter",
    "xAI":       "xai",
    "Mistral":   "mistral",
    "Groq":      "groq",
    "DeepSeek":  "deepseek",
    "Kimi":      "kimi",
    "Gemini":    "gemini",
    "Z.ai":      "zai",
    "LM Studio": "local",
}

_ID_TO_DISPLAY = {v: k for k, v in _DISPLAY_TO_ID.items()}
_ID_TO_DISPLAY["moonshot"] = "Kimi"
_ID_TO_DISPLAY["lm_studio"] = "LM Studio"


# ── Dialog ────────────────────────────────────────────────────────────────────

# Per-provider default model lists (mirrors stage_configurators.py)
_PROVIDER_MODELS = {
    "OpenAI":      ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
    "Claude":      ["claude-sonnet-4-5-20250929", "claude-haiku-4-5-20251001",
                    "claude-opus-4-5-20251101"],
    "OpenRouter":  ["anthropic/claude-sonnet-4-5-20250929",
                    "anthropic/claude-haiku-4-5-20251001",
                    "openai/gpt-4o", "openai/gpt-4o-mini",
                    "google/gemini-pro-1.5",
                    "meta-llama/llama-3.1-405b-instruct"],
    "xAI":         ["grok-2-latest", "grok-2-mini-latest", "grok-beta"],
    "Mistral":     ["mistral-large-latest", "mistral-small-latest", "codestral-latest"],
    "Groq":        ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
    "DeepSeek":    ["deepseek-chat", "deepseek-reasoner"],
    "Kimi":        ["moonshot-v1-128k", "moonshot-v1-32k", "moonshot-v1-8k"],
    "Gemini":      ["gemini-2.0-flash", "gemini-2.0-flash-lite",
                    "gemini-1.5-pro", "gemini-1.5-flash"],
    "Z.ai":        ["glm-4.7", "glm-5", "glm-4.5-air", "glm-4-flash"],
    "LM Studio":   ["Local Model (LM Studio)"],
}

_PROVIDER_KEY_PLACEHOLDER = {
    "OpenAI":     "OpenAI API key",
    "Claude":     "Anthropic API key",
    "OpenRouter": "OpenRouter API key",
    "xAI":        "xAI API key",
    "Mistral":    "Mistral API key",
    "Groq":       "Groq API key",
    "DeepSeek":   "DeepSeek API key",
    "Kimi":       "Kimi (Moonshot) API key",
    "Gemini":     "Google Gemini API key (AIza...)",
    "Z.ai":       "Z.ai API key",
    "LM Studio":  "Optional: API key for custom endpoint",
}

# Settings provider key used to look up API key / default model / custom models
# Must match the keys used in stage_configurators._update_model_options
_DISPLAY_TO_SETTINGS_KEY = {
    "OpenAI":     "openai",
    "Claude":     "anthropic",   # stored under 'anthropic' in settings
    "OpenRouter": "openrouter",
    "xAI":        "xai",
    "Mistral":    "mistral",
    "Groq":       "groq",
    "DeepSeek":   "deepseek",
    "Kimi":       "moonshot",
    "Gemini":     "gemini",
    "Z.ai":       "zai",
    "LM Studio":  "lm_studio",
}


class CalibrationDialog(QDialog):
    """
    Modal dialog for calibrating AI model settings.

    Can be opened from:
    - The "Calibrate…" button next to the model selector  (pre-filled)
    - Tools → Calibrate Model…                            (empty form)

    Signals
    -------
    calibration_saved(model_name)
        Emitted after successful calibration so the caller can refresh the
        calibration status indicator.
    """

    calibration_saved = Signal(str)

    def __init__(
        self,
        model:          str = "",
        provider:       str = "",
        api_key:        str = "",
        base_url:       str = "",
        config_manager=None,
        parent=None,
    ):
        super().__init__(parent)

        self._init_model    = model
        self._init_provider = provider
        self._init_api_key  = api_key
        self._init_base_url = base_url
        self._config_manager = config_manager

        self._worker: CalibrationWorker | None = None

        self.setWindowTitle("Calibrate Model")
        self.setMinimumSize(640, 540)
        self.resize(700, 580)

        self._setup_ui()
        self._prefill()

    # ── UI construction ───────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        tabs = QTabWidget()
        root.addWidget(tabs)

        # ── Tab 1: Calibrate ─────────────────────────────────────────────────
        cal_widget = QWidget()
        tabs.addTab(cal_widget, "  Calibrate  ")
        cal_layout = QVBoxLayout(cal_widget)
        cal_layout.setContentsMargins(14, 14, 14, 14)
        cal_layout.setSpacing(10)

        self._stack = QStackedWidget()
        cal_layout.addWidget(self._stack)

        self._stack.addWidget(self._build_configure_page())  # index 0
        self._stack.addWidget(self._build_running_page())    # index 1
        self._stack.addWidget(self._build_results_page())    # index 2

        # ── Tab 2: Raw Log ───────────────────────────────────────────────────
        raw_widget = QWidget()
        tabs.addTab(raw_widget, "  Raw Log  ")
        raw_layout = QVBoxLayout(raw_widget)
        raw_layout.setContentsMargins(14, 14, 14, 14)
        raw_layout.setSpacing(6)

        raw_header = QHBoxLayout()
        raw_title = QLabel("API request / response details")
        raw_title.setStyleSheet("color: #888; font-size: 10pt; font-style: italic;")
        raw_header.addWidget(raw_title)
        raw_header.addStretch()
        clear_raw_btn = QPushButton("Clear")
        clear_raw_btn.setMaximumWidth(60)
        clear_raw_btn.setFixedHeight(22)
        raw_header.addWidget(clear_raw_btn)
        raw_layout.addLayout(raw_header)

        self._raw_log_edit = QTextEdit()
        self._raw_log_edit.setReadOnly(True)
        raw_mono = QFont("Courier New", 9)
        raw_mono.setStyleHint(QFont.Monospace)
        self._raw_log_edit.setFont(raw_mono)
        self._raw_log_edit.setStyleSheet(
            "background: #060610; color: #aaa; border-radius: 4px;"
        )
        raw_layout.addWidget(self._raw_log_edit)
        clear_raw_btn.clicked.connect(self._raw_log_edit.clear)

        # ── Tab 3: Documentation ─────────────────────────────────────────────
        doc_widget = QWidget()
        tabs.addTab(doc_widget, "  Documentation  ")
        doc_layout = QVBoxLayout(doc_widget)
        doc_layout.setContentsMargins(14, 14, 14, 14)

        doc_view = QTextEdit()
        doc_view.setReadOnly(True)
        doc_view.setHtml(_DOCUMENTATION_HTML)
        doc_layout.addWidget(doc_view)

    # ── Page 0: Configure ─────────────────────────────────────────────────────

    def _build_configure_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)

        # Form
        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(_DISPLAY_PROVIDERS)
        self.provider_combo.currentTextChanged.connect(self._on_provider_changed)
        form.addRow("Provider:", self.provider_combo)

        self.model_combo = QComboBox()
        self.model_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.model_combo.currentTextChanged.connect(self._refresh_cost_estimate)
        form.addRow("Model:", self.model_combo)

        api_row = QHBoxLayout()
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setPlaceholderText(
            "Loaded from Settings — enter here to override"
        )
        self._show_key_btn = QPushButton("Show")
        self._show_key_btn.setMaximumWidth(56)
        self._show_key_btn.setCheckable(True)
        self._show_key_btn.toggled.connect(self._toggle_key_visibility)
        api_row.addWidget(self.api_key_edit)
        api_row.addWidget(self._show_key_btn)
        form.addRow("API Key:", api_row)

        self.base_url_edit = QLineEdit()
        self.base_url_edit.setPlaceholderText(
            "Optional — only needed for custom / local endpoints"
        )
        form.addRow("Base URL:", self.base_url_edit)

        layout.addLayout(form)

        # Cost estimate label
        self._cost_label = QLabel()
        self._cost_label.setWordWrap(True)
        self._cost_label.setStyleSheet(
            "color: #888; font-size: 10pt; font-style: italic;"
        )
        layout.addWidget(self._cost_label)

        # Warning banner
        warn = QFrame()
        warn.setStyleSheet("""
            QFrame {
                background: #2b1a00;
                border: 1px solid #a06000;
                border-radius: 6px;
            }
        """)
        warn_inner = QVBoxLayout(warn)
        warn_inner.setContentsMargins(12, 8, 12, 8)
        warn_lbl = QLabel(
            "⚠  Calibration makes real API calls and will incur charges "
            "based on your plan and selected model.  Typical cost is under $0.05."
        )
        warn_lbl.setWordWrap(True)
        warn_lbl.setStyleSheet("color: #ffcc66; font-size: 10pt;")
        warn_inner.addWidget(warn_lbl)
        layout.addWidget(warn)

        layout.addStretch()

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.start_btn = QPushButton("Start Calibration")
        self.start_btn.setMinimumWidth(160)
        self.start_btn.setMinimumHeight(34)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background: #1565c0; color: white;
                border: none; border-radius: 4px;
                padding: 6px 18px; font-weight: bold;
            }
            QPushButton:hover   { background: #1976d2; }
            QPushButton:pressed { background: #0d47a1; }
        """)
        self.start_btn.clicked.connect(self._start)
        btn_row.addWidget(self.start_btn)

        close_btn = QPushButton("Close")
        close_btn.setMinimumWidth(80)
        close_btn.setMinimumHeight(34)
        close_btn.clicked.connect(self.reject)
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)
        return page

    # ── Page 1: Running ───────────────────────────────────────────────────────

    def _build_running_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(8)

        self._phase_label = QLabel("Initializing…")
        self._phase_label.setStyleSheet(
            "font-weight: bold; color: #ffa726; font-size: 11pt;"
        )
        layout.addWidget(self._phase_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, TOTAL_PROBES)
        self._progress_bar.setValue(0)
        self._progress_bar.setFixedHeight(16)
        self._progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #555; border-radius: 4px;
                background: #2a2a3a; color: white;
                text-align: center; font-size: 10px; font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #1565c0, stop:1 #4dabf7);
                border-radius: 3px;
            }
        """)
        layout.addWidget(self._progress_bar)

        self._run_log = QTextEdit()
        self._run_log.setReadOnly(True)
        mono = QFont("Courier New", 10)
        mono.setStyleHint(QFont.Monospace)
        self._run_log.setFont(mono)
        self._run_log.setStyleSheet("background: #0d0d1a; color: #ccc; border-radius: 4px;")
        layout.addWidget(self._run_log, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setMinimumWidth(80)
        self._stop_btn.setMinimumHeight(30)
        self._stop_btn.setStyleSheet("""
            QPushButton { background:#b71c1c; color:white; border:none; border-radius:4px; }
            QPushButton:hover { background:#d32f2f; }
            QPushButton:disabled { background:#555; color:#888; }
        """)
        self._stop_btn.clicked.connect(self._stop)
        btn_row.addWidget(self._stop_btn)
        layout.addLayout(btn_row)

        return page

    # ── Page 2: Results ───────────────────────────────────────────────────────

    def _build_results_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        self._result_title = QLabel("Calibration Complete ✓")
        self._result_title.setStyleSheet(
            "font-weight: bold; color: #66bb6a; font-size: 13pt;"
        )
        layout.addWidget(self._result_title)

        self._result_text = QTextEdit()
        self._result_text.setReadOnly(True)
        self._result_text.setMaximumHeight(160)
        self._result_text.setStyleSheet(
            "background: #111; color: #ddd; border-radius: 4px; font-family: monospace;"
        )
        layout.addWidget(self._result_text)

        note = QLabel(
            "Settings have been saved and will be applied automatically "
            "when this model is selected in the Translate Configuration panel."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #888; font-size: 10pt; font-style: italic;")
        layout.addWidget(note)

        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        recal_btn = QPushButton("Re-calibrate")
        recal_btn.setMinimumWidth(120)
        recal_btn.setMinimumHeight(32)
        recal_btn.clicked.connect(lambda: self._stack.setCurrentIndex(0))
        btn_row.addWidget(recal_btn)

        done_btn = QPushButton("Done")
        done_btn.setMinimumWidth(80)
        done_btn.setMinimumHeight(32)
        done_btn.setStyleSheet("""
            QPushButton { background:#1565c0; color:white; border:none;
                          border-radius:4px; padding:4px 16px; font-weight:bold; }
            QPushButton:hover { background:#1976d2; }
        """)
        done_btn.clicked.connect(self.accept)
        btn_row.addWidget(done_btn)

        layout.addLayout(btn_row)
        return page

    # ── Prefill & estimate ────────────────────────────────────────────────────

    def _prefill(self) -> None:
        if self._init_provider:
            display = _ID_TO_DISPLAY.get(self._init_provider.lower(), self._init_provider)
            idx = self.provider_combo.findText(display, Qt.MatchFixedString)
            if idx >= 0:
                # Block signals so _on_provider_changed doesn't fire yet — we call
                # _populate_models explicitly below, avoiding a double-populate.
                self.provider_combo.blockSignals(True)
                self.provider_combo.setCurrentIndex(idx)
                self.provider_combo.blockSignals(False)

        # Always populate models for whichever provider is now current.
        current_provider = self.provider_combo.currentText()
        self._populate_models(current_provider)
        self.api_key_edit.setPlaceholderText(
            _PROVIDER_KEY_PLACEHOLDER.get(current_provider, "API key")
        )

        # Select the pre-filled model, overriding the settings default if provided
        if self._init_model:
            idx = self.model_combo.findText(self._init_model, Qt.MatchFixedString)
            if idx >= 0:
                self.model_combo.setCurrentIndex(idx)
            else:
                self.model_combo.insertItem(0, self._init_model)
                self.model_combo.setCurrentIndex(0)

        # API key: load from settings; _init_api_key is shown only as a manual override
        settings_key, _, _, _ = self._load_provider_settings(current_provider)
        self.api_key_edit.setText(settings_key)
        self.base_url_edit.setText(self._init_base_url)

        self._refresh_cost_estimate()

    def _load_provider_settings(self, provider_display: str) -> tuple:
        """Return (api_key, default_model, selected_models, custom_models) from config."""
        if not self._config_manager:
            return "", "", [], []
        settings_key = _DISPLAY_TO_SETTINGS_KEY.get(provider_display, "")
        if not settings_key:
            return "", "", [], []
        try:
            prov = (
                self._config_manager.get_settings()
                .get("translators", {})
                .get(settings_key, {})
            )
            return (
                prov.get("api_key", "").strip(),
                prov.get("default_model", "").strip(),
                prov.get("selected_models", []),
                prov.get("custom_models", []),
            )
        except Exception:
            return "", "", [], []

    def _on_provider_changed(self, provider_display: str) -> None:
        """Repopulate the model list and reload API key when the provider changes."""
        self._populate_models(provider_display)
        self.api_key_edit.setPlaceholderText(
            _PROVIDER_KEY_PLACEHOLDER.get(provider_display, "API key")
        )
        api_key, _, _, _ = self._load_provider_settings(provider_display)
        self.api_key_edit.setText(api_key)

    def _populate_models(self, provider_display: str) -> None:
        """Fill model_combo with built-in + custom models for *provider_display*
        and select the configured default model."""
        self.model_combo.blockSignals(True)
        self.model_combo.clear()

        _, default_model, selected_models, custom_models = (
            self._load_provider_settings(provider_display)
        )

        builtin = selected_models if selected_models else list(
            _PROVIDER_MODELS.get(provider_display, [])
        )

        self.model_combo.addItems(builtin)
        if custom_models:
            self.model_combo.insertSeparator(len(builtin))
            for m in custom_models:
                self.model_combo.addItem(f"★ {m}")

        # Select the configured default model, falling back to the first item
        if default_model:
            idx = self.model_combo.findText(default_model, Qt.MatchFixedString)
            if idx >= 0:
                self.model_combo.setCurrentIndex(idx)
            else:
                # Default model not in list — add it at the top
                self.model_combo.insertItem(0, default_model)
                self.model_combo.setCurrentIndex(0)
        elif self.model_combo.count() > 0:
            self.model_combo.setCurrentIndex(0)

        self.model_combo.blockSignals(False)
        self._refresh_cost_estimate()

    def _get_model_name(self) -> str:
        """Return the current model name, stripping the ★ prefix if present."""
        text = self.model_combo.currentText().strip()
        if text.startswith("★ "):
            text = text[2:].strip()
        return text

    def _refresh_cost_estimate(self, *_) -> None:
        """Update the estimated calibration cost label using stored model prices."""
        model = self._get_model_name()
        if not model:
            self._cost_label.setText(
                f"Calibration runs {len(CHUNK_SIZES)} chunk probes + "
                f"{len(WORKER_COUNTS)} worker probes ≈ 6,000 input + 4,000 output tokens."
            )
            return

        from PySide6.QtCore import QSettings
        safe = ''.join(c if c.isalnum() or c in '._-' else '_' for c in model) or '__unknown__'
        qs = QSettings("SubtitleToolkit", "ModelProfiles")
        qs.beginGroup(safe)
        p_in  = float(qs.value("price_input",  0.0))
        p_out = float(qs.value("price_output", 0.0))
        qs.endGroup()

        est_in  = 6_000
        est_out = 4_000
        base = (
            f"{len(CHUNK_SIZES)} chunk probes + {len(WORKER_COUNTS)} worker probes  "
            f"≈ {est_in:,} input + {est_out:,} output tokens"
        )

        if p_in > 0 or p_out > 0:
            cost = (est_in / 1_000_000) * p_in + (est_out / 1_000_000) * p_out
            cost_str = "< $0.01" if cost < 0.01 else f"${cost:.3f}"
            self._cost_label.setText(f"Est. calibration cost: {base}  ·  {cost_str}")
            self._cost_label.setStyleSheet("color: #ffa726; font-size: 10pt;")
        else:
            self._cost_label.setText(
                f"Est. calibration: {base}.\n"
                "Set model prices in the Translate panel for a dollar estimate."
            )
            self._cost_label.setStyleSheet(
                "color: #888; font-size: 10pt; font-style: italic;"
            )

    # ── Actions ───────────────────────────────────────────────────────────────

    def _toggle_key_visibility(self, show: bool) -> None:
        self.api_key_edit.setEchoMode(
            QLineEdit.Normal if show else QLineEdit.Password
        )
        self._show_key_btn.setText("Hide" if show else "Show")

    def _start(self) -> None:
        model = self._get_model_name()
        if not model:
            QMessageBox.warning(self, "Missing Model", "Please enter a model name.")
            return

        provider_display = self.provider_combo.currentText()
        provider = _DISPLAY_TO_ID.get(provider_display, "openai")
        api_key  = self.api_key_edit.text().strip()
        # If the field is empty, fall back to the key stored in Settings
        if not api_key:
            api_key, _, _, _ = self._load_provider_settings(provider_display)
        base_url = self.base_url_edit.text().strip()

        # Reset running page
        self._run_log.clear()
        self._phase_label.setText("Starting calibration…")
        self._phase_label.setStyleSheet(
            "font-weight: bold; color: #ffa726; font-size: 11pt;"
        )
        self._progress_bar.setValue(0)
        self._stop_btn.setEnabled(True)
        self._stack.setCurrentIndex(1)

        self._worker = CalibrationWorker(
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=base_url,
            parent=self,
        )
        self._worker.phase_started.connect(self._on_phase_started)
        self._worker.log_message.connect(self._on_log_message)
        self._worker.progress.connect(self._progress_bar.setValue)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.raw_log.connect(self._on_raw_log)
        self._worker.start()

    def _stop(self) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self._stop_btn.setEnabled(False)
            self._append_log("⚑  Calibration stopped by user.", "#ff9800")

    # ── Worker signal handlers ────────────────────────────────────────────────

    def _on_phase_started(self, _phase_id: str, description: str) -> None:
        self._phase_label.setText(description)
        self._append_log(f"\n▶  {description}", "#4dabf7")

    def _on_log_message(self, level: str, text: str) -> None:
        color = {"info": "#66bb6a", "warning": "#ffa726", "error": "#ff6b6b"}.get(
            level, "#cccccc"
        )
        self._append_log(f"   {text}", color)

    def _on_finished(self, results: dict) -> None:
        model   = self._get_model_name()
        chunk   = results["max_chunk_size"]
        workers = results["max_workers"]
        latency = results.get("latency_avg_ms", 0.0)

        self._append_log("\n✓  Calibration complete — results saved.", "#66bb6a")

        self._result_title.setText("Calibration Complete ✓")
        self._result_title.setStyleSheet(
            "font-weight: bold; color: #66bb6a; font-size: 13pt;"
        )
        lines = (
            f"  Model              :  {model}\n"
            f"  Max chunk size     :  {chunk} subtitles per request\n"
            f"  Max workers        :  {workers} concurrent requests\n"
            f"  Avg response time  :  {latency:.0f} ms"
        )
        self._result_text.setPlainText(lines)

        # Check if existing calibration was replaced
        existing = load_calibration(model)
        if existing and existing.get("date"):
            note_extra = f"\n(Previous calibration from {existing['date']} has been replaced.)"
            self._result_text.setPlainText(lines + note_extra)

        self._stack.setCurrentIndex(2)
        self.calibration_saved.emit(model)

    def _on_raw_log(self, label: str, content: str) -> None:
        safe_label = (
            label.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )
        safe_content = (
            content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace("\n", "<br>").replace(" ", "&nbsp;")
        )
        color = "#ff6b6b" if "ERROR" in label or "EXCEPTION" in label else (
            "#ffa726" if "strip" in label or "wrong type" in label else "#4dabf7"
        )
        self._raw_log_edit.append(
            f'<span style="color:{color};font-weight:bold;">─── {safe_label} ───</span><br>'
            f'<span style="color:#ccc;">{safe_content}</span><br>'
        )
        self._raw_log_edit.moveCursor(QTextCursor.End)
        self._raw_log_edit.ensureCursorVisible()

    def _on_error(self, error_msg: str) -> None:
        self._append_log(f"\n✗  Error: {error_msg}", "#ff6b6b")
        self._phase_label.setText("Calibration failed")
        self._phase_label.setStyleSheet(
            "font-weight: bold; color: #ff6b6b; font-size: 11pt;"
        )
        QMessageBox.critical(
            self,
            "Calibration Error",
            f"Calibration failed:\n\n{error_msg}\n\n"
            "Check your API key and model name, then try again.",
        )
        self._stack.setCurrentIndex(0)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _append_log(self, text: str, color: str = "#cccccc") -> None:
        # Escape HTML special chars in the message
        safe = (
            text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br>")
        )
        self._run_log.append(f'<span style="color:{color};">{safe}</span>')
        self._run_log.moveCursor(QTextCursor.End)
        self._run_log.ensureCursorVisible()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self._worker.wait(3000)
        super().closeEvent(event)
