"""
Calibration data persistence for SubtitleToolkit.

Stores per-model calibration results in QSettings under the same
"SubtitleToolkit / ModelProfiles" namespace used for per-model settings,
so _load_model_settings() picks up calibrated values automatically.
"""

from datetime import datetime
from typing import Optional, Dict, Any

from PySide6.QtCore import QSettings

_APP    = "SubtitleToolkit"
_GROUP  = "ModelProfiles"


def _model_key(model: str) -> str:
    """Sanitize model name into a safe QSettings group key."""
    safe = ''.join(c if c.isalnum() or c in '._-' else '_' for c in model)
    return safe or '__unknown__'


def save_calibration(model: str, data: Dict[str, Any]) -> None:
    """
    Persist calibration results for *model*.

    Two things are written:
    1. ``calibration/`` sub-group  – metadata (date, latency, version).
    2. Main model group             – chunk_size and max_workers so that
       _load_model_settings() picks them up with no extra code.
    """
    qs = QSettings(_APP, _GROUP)
    key = _model_key(model)

    qs.beginGroup(key)

    # Calibration metadata
    qs.beginGroup("calibration")
    qs.setValue("date",           datetime.now().isoformat()[:10])
    qs.setValue("max_chunk_size", int(data.get("max_chunk_size", 20)))
    qs.setValue("max_workers",    int(data.get("max_workers", 2)))
    qs.setValue("latency_avg_ms", float(data.get("latency_avg_ms", 0.0)))
    qs.setValue("version",        1)
    qs.endGroup()

    # Push calibrated values into the main profile so the translate widget
    # loads them automatically on next model selection.
    qs.setValue("chunk_size",  int(data.get("max_chunk_size", 20)))
    qs.setValue("max_workers", int(data.get("max_workers", 2)))

    qs.endGroup()


def load_calibration(model: str) -> Optional[Dict[str, Any]]:
    """Return the calibration dict for *model*, or None if not calibrated."""
    qs = QSettings(_APP, _GROUP)
    key = _model_key(model)

    qs.beginGroup(key)
    qs.beginGroup("calibration")
    has = qs.contains("max_chunk_size")
    if has:
        result: Dict[str, Any] = {
            "date":           qs.value("date",           ""),
            "max_chunk_size": int(qs.value("max_chunk_size", 20)),
            "max_workers":    int(qs.value("max_workers",    2)),
            "latency_avg_ms": float(qs.value("latency_avg_ms", 0.0)),
            "version":        int(qs.value("version",        1)),
        }
    else:
        result = None
    qs.endGroup()
    qs.endGroup()
    return result


def is_calibrated(model: str) -> bool:
    """Return True if *model* has saved calibration data."""
    return load_calibration(model) is not None


def clear_calibration(model: str) -> None:
    """Remove calibration data for *model* (does not reset main profile)."""
    qs = QSettings(_APP, _GROUP)
    key = _model_key(model)
    qs.beginGroup(key)
    qs.remove("calibration")
    qs.endGroup()
