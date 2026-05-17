"""
Subtitle Finder settings tab.

Allows the user to:
- Configure API keys for OpenSubtitles and SubDL
- Enable/disable/reorder subtitle providers
- Add custom scraper sites
- Set default and fallback subtitle language
- Configure AI fallback for NFO parsing
"""

import copy
from typing import Any, Dict, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QCheckBox, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QFormLayout,
    QAbstractItemView, QMessageBox, QSizePolicy, QFrame,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from app.config import ConfigManager
from app.config.settings_schema import SettingsSchema


_DEFAULT_PROVIDERS = SettingsSchema.get_default_settings()["subtitle_finder"]["providers"]


class SubtitleFinderTab(QWidget):
    """Settings tab for the subtitle finder feature."""

    settings_changed = Signal()

    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self._providers: List[Dict[str, Any]] = []
        self._init_ui()

    # ── UI Construction ──────────────────────────────────────────────────────

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        layout.addWidget(self._make_language_group())
        layout.addWidget(self._make_providers_group())
        layout.addWidget(self._make_nfo_ai_group())
        layout.addStretch()

    def _make_language_group(self) -> QGroupBox:
        box = QGroupBox("Default Language")
        form = QFormLayout(box)
        form.setSpacing(8)

        supported = SettingsSchema.get_supported_languages()
        codes = list(supported.keys())
        names = [f"{v} ({k})" for k, v in supported.items()]

        self.default_lang_combo = QComboBox()
        self.default_lang_combo.addItems(names)
        self.default_lang_combo.setToolTip(
            "Preferred language for found subtitles. "
            "The finder will try this language first on every site."
        )
        form.addRow("Preferred subtitle language:", self.default_lang_combo)

        self.fallback_lang_combo = QComboBox()
        self.fallback_lang_combo.addItem("Any language", "")
        for k, v in supported.items():
            self.fallback_lang_combo.addItem(f"{v} ({k})", k)
        self.fallback_lang_combo.setToolTip(
            "If no subtitles are found in the preferred language, "
            "try this language. 'Any language' accepts whatever is available."
        )
        form.addRow("Fallback language:", self.fallback_lang_combo)

        return box

    def _make_providers_group(self) -> QGroupBox:
        box = QGroupBox("Subtitle Providers")
        layout = QVBoxLayout(box)

        hint = QLabel(
            "Enable/disable providers, configure API keys, and add custom sites. "
            "Providers are queried in parallel."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #aaa; font-size: 11px;")
        layout.addWidget(hint)

        # Table
        self.providers_table = QTableWidget(0, 5)
        self.providers_table.setHorizontalHeaderLabels(
            ["Enabled", "Name", "Type", "URL / API Key", "Actions"]
        )
        self.providers_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.providers_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.providers_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.providers_table.setAlternatingRowColors(True)
        self.providers_table.verticalHeader().setVisible(False)
        self.providers_table.setMinimumHeight(200)
        layout.addWidget(self.providers_table)

        # Provider-level credentials (shown below table for selected API provider)
        self.credentials_frame = QFrame()
        cred_layout = QFormLayout(self.credentials_frame)
        cred_layout.setContentsMargins(0, 4, 0, 0)

        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setPlaceholderText("API key for selected provider")
        cred_layout.addRow("API Key:", self.api_key_edit)

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Username (OpenSubtitles only)")
        cred_layout.addRow("Username:", self.username_edit)

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText("Password (OpenSubtitles only)")
        cred_layout.addRow("Password:", self.password_edit)

        self.save_creds_btn = QPushButton("Apply credentials to selected provider")
        self.save_creds_btn.clicked.connect(self._apply_credentials)
        cred_layout.addRow("", self.save_creds_btn)

        layout.addWidget(self.credentials_frame)

        # Bottom buttons
        btn_row = QHBoxLayout()
        self.add_btn = QPushButton("+ Add Custom Site")
        self.remove_btn = QPushButton("Remove Selected")
        self.reset_btn = QPushButton("Reset to Defaults")
        btn_row.addWidget(self.add_btn)
        btn_row.addWidget(self.remove_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.reset_btn)
        layout.addLayout(btn_row)

        self.add_btn.clicked.connect(self._add_custom_provider)
        self.remove_btn.clicked.connect(self._remove_selected_provider)
        self.reset_btn.clicked.connect(self._reset_providers)
        self.providers_table.currentRowChanged.connect(self._on_row_changed)

        return box

    def _make_nfo_ai_group(self) -> QGroupBox:
        box = QGroupBox("NFO Parsing AI Fallback")
        form = QFormLayout(box)

        self.nfo_ai_enabled = QCheckBox("Use AI to parse unknown NFO formats")
        self.nfo_ai_enabled.setToolTip(
            "When the NFO file format is not recognized, "
            "send it to the configured AI provider for extraction."
        )
        form.addRow(self.nfo_ai_enabled)

        self.nfo_ai_provider_combo = QComboBox()
        self.nfo_ai_provider_combo.addItems(["openai", "anthropic"])
        form.addRow("AI provider:", self.nfo_ai_provider_combo)

        self.nfo_ai_model_edit = QLineEdit()
        self.nfo_ai_model_edit.setPlaceholderText("e.g. gpt-4o-mini")
        form.addRow("AI model:", self.nfo_ai_model_edit)

        note = QLabel(
            "API key is taken from the corresponding provider in the Translators tab."
        )
        note.setStyleSheet("color: #aaa; font-size: 11px;")
        form.addRow(note)

        return box

    # ── Table population ─────────────────────────────────────────────────────

    def _populate_table(self):
        self.providers_table.setRowCount(0)
        for p in self._providers:
            self._append_table_row(p)

    def _append_table_row(self, p: Dict[str, Any]):
        row = self.providers_table.rowCount()
        self.providers_table.insertRow(row)

        # Enabled checkbox
        chk = QCheckBox()
        chk.setChecked(p.get("enabled", True))
        chk.stateChanged.connect(lambda state, r=row: self._on_enabled_changed(r, state))
        cell_widget = QWidget()
        cell_layout = QHBoxLayout(cell_widget)
        cell_layout.addWidget(chk)
        cell_layout.setAlignment(Qt.AlignCenter)
        cell_layout.setContentsMargins(0, 0, 0, 0)
        self.providers_table.setCellWidget(row, 0, cell_widget)

        # Name (editable for custom)
        name_item = QTableWidgetItem(p.get("name", ""))
        if p.get("id", "").startswith("custom_"):
            name_item.setFlags(name_item.flags() | Qt.ItemIsEditable)
        else:
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
        self.providers_table.setItem(row, 1, name_item)

        # Type badge
        type_item = QTableWidgetItem(p.get("type", "scraper"))
        type_item.setFlags(type_item.flags() & ~Qt.ItemIsEditable)
        type_item.setTextAlignment(Qt.AlignCenter)
        self.providers_table.setItem(row, 2, type_item)

        # URL summary (show key masked for APIs)
        url = p.get("url", "")
        api_key = p.get("api_key", "")
        if api_key:
            display = f"{url}  [key: {'*' * min(len(api_key), 8)}]"
        else:
            display = url
        url_item = QTableWidgetItem(display)
        url_item.setFlags(url_item.flags() & ~Qt.ItemIsEditable)
        url_item.setToolTip(url)
        self.providers_table.setItem(row, 3, url_item)

        # Empty actions column placeholder
        self.providers_table.setItem(row, 4, QTableWidgetItem(""))

    def _refresh_row(self, row: int):
        if row < 0 or row >= len(self._providers):
            return
        p = self._providers[row]
        url = p.get("url", "")
        api_key = p.get("api_key", "")
        display = f"{url}  [key: {'*' * min(len(api_key), 8)}]" if api_key else url
        item = self.providers_table.item(row, 3)
        if item:
            item.setText(display)
            item.setToolTip(url)

    # ── Signals ──────────────────────────────────────────────────────────────

    def _on_enabled_changed(self, row: int, state: int):
        if 0 <= row < len(self._providers):
            self._providers[row]["enabled"] = state == Qt.Checked
            self.settings_changed.emit()

    def _on_row_changed(self, row: int):
        if row < 0 or row >= len(self._providers):
            self.credentials_frame.setVisible(False)
            return
        p = self._providers[row]
        self.api_key_edit.setText(p.get("api_key", ""))
        self.username_edit.setText(p.get("username", ""))
        self.password_edit.setText(p.get("password", ""))
        has_api = p.get("type") == "api"
        self.credentials_frame.setVisible(has_api)

    def _apply_credentials(self):
        row = self.providers_table.currentRow()
        if row < 0 or row >= len(self._providers):
            return
        p = self._providers[row]
        p["api_key"] = self.api_key_edit.text().strip()
        p["username"] = self.username_edit.text().strip()
        p["password"] = self.password_edit.text().strip()
        self._refresh_row(row)
        self.settings_changed.emit()

    def _add_custom_provider(self):
        import uuid
        new_id = f"custom_{uuid.uuid4().hex[:8]}"
        p = {
            "id": new_id,
            "name": "New Site",
            "type": "scraper",
            "enabled": True,
            "url": "https://",
            "api_key": "",
        }
        self._providers.append(p)
        self._append_table_row(p)
        self.providers_table.selectRow(len(self._providers) - 1)
        self.settings_changed.emit()

    def _remove_selected_provider(self):
        row = self.providers_table.currentRow()
        if row < 0:
            return
        p = self._providers[row]
        if not p.get("id", "").startswith("custom_"):
            QMessageBox.information(
                self, "Cannot Remove",
                "Built-in providers cannot be removed. Disable them instead."
            )
            return
        self._providers.pop(row)
        self.providers_table.removeRow(row)
        self.settings_changed.emit()

    def _reset_providers(self):
        reply = QMessageBox.question(
            self, "Reset Providers",
            "Reset all providers to defaults? API keys will be cleared.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._providers = copy.deepcopy(_DEFAULT_PROVIDERS)
            self._populate_table()
            self.settings_changed.emit()

    # ── Settings load / save ─────────────────────────────────────────────────

    def load_settings(self, settings: Dict[str, Any]):
        # settings is the subtitle_finder section dict directly
        defaults = SettingsSchema.get_default_settings()["subtitle_finder"]

        self._providers = copy.deepcopy(settings.get("providers", defaults["providers"]))
        self._populate_table()

        # Language combos
        supported = list(SettingsSchema.get_supported_languages().keys())
        default_lang = settings.get("default_language", defaults["default_language"])
        if default_lang in supported:
            self.default_lang_combo.setCurrentIndex(supported.index(default_lang))

        fallback_lang = settings.get("fallback_language", "")
        idx = 0  # "Any language"
        for i in range(self.fallback_lang_combo.count()):
            if self.fallback_lang_combo.itemData(i) == fallback_lang:
                idx = i
                break
        self.fallback_lang_combo.setCurrentIndex(idx)

        # NFO AI
        self.nfo_ai_enabled.setChecked(settings.get("nfo_ai_fallback", True))
        prov = settings.get("nfo_ai_provider", "openai")
        idx = self.nfo_ai_provider_combo.findText(prov)
        if idx >= 0:
            self.nfo_ai_provider_combo.setCurrentIndex(idx)
        self.nfo_ai_model_edit.setText(settings.get("nfo_ai_model", "gpt-4o-mini"))

    def get_settings(self) -> Dict[str, Any]:
        supported = list(SettingsSchema.get_supported_languages().keys())
        default_lang = supported[self.default_lang_combo.currentIndex()] if self.default_lang_combo.currentIndex() >= 0 else "bg"
        fallback_lang = self.fallback_lang_combo.currentData() or ""

        return {
            "default_language": default_lang,
            "fallback_language": fallback_lang,
            "nfo_ai_fallback": self.nfo_ai_enabled.isChecked(),
            "nfo_ai_provider": self.nfo_ai_provider_combo.currentText(),
            "nfo_ai_model": self.nfo_ai_model_edit.text().strip() or "gpt-4o-mini",
            "providers": copy.deepcopy(self._providers),
        }
