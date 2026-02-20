"""
Runner module for subprocess orchestration in SubtitleToolkit.

This module provides the ScriptRunner system for executing the CLI scripts
with JSONL event streaming and process management.
"""

from .script_runner import ScriptRunner
from .config_models import ExtractConfig, TranslateConfig, SyncConfig, FpsSyncConfig
from .events import Event, EventType, Stage, ScriptRunnerSignals
from .jsonl_parser import JSONLParser

__all__ = [
    'ScriptRunner',
    'ExtractConfig',
    'TranslateConfig',
    'SyncConfig',
    'FpsSyncConfig',
    'Event',
    'EventType',
    'Stage',
    'ScriptRunnerSignals',
    'JSONLParser',
]