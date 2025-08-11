"""
Main ScriptRunner class for subprocess orchestration in SubtitleToolkit.

Manages QProcess execution of CLI scripts with JSONL event streaming,
process lifecycle management, and Qt signal integration.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from PySide6.QtCore import QObject, QProcess, QTimer, QThread
from PySide6.QtWidgets import QApplication

from .config_models import ExtractConfig, TranslateConfig, SyncConfig
from .events import Event, EventType, Stage, ProcessResult, EventAggregator, ScriptRunnerSignals
from .jsonl_parser import JSONLParser


class ScriptRunner(QObject):
    """
    Main orchestrator for running SubtitleToolkit CLI scripts.
    
    Features:
    - QProcess management with proper lifecycle handling
    - Real-time JSONL stream parsing
    - Qt signal emission for UI updates
    - Process state tracking and monitoring
    - Error handling and recovery
    - Thread-safe operations
    """
    
    def __init__(self, parent: QObject = None):
        super().__init__(parent)
        
        # Signal object for Qt communication
        self.signals = ScriptRunnerSignals(self)
        
        # Current process tracking
        self._current_process: Optional[QProcess] = None
        self._current_stage: Optional[Stage] = None
        self._current_config: Optional[Any] = None
        
        # JSONL parser
        self._parser = JSONLParser(self)
        
        # Event aggregator for progress tracking
        self._aggregator: Optional[EventAggregator] = None
        
        # Process start time for duration tracking
        self._process_start_time: Optional[datetime] = None
        
        # Termination timeout timer
        self._termination_timer = QTimer(self)
        self._termination_timer.setSingleShot(True)
        self._termination_timer.timeout.connect(self._force_kill_process)
        
        # Logger
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Determine script paths
        self._script_dir = self._find_script_directory()
    
    def _find_script_directory(self) -> Path:
        """Find the scripts directory relative to the application."""
        # Try different possible locations
        possible_paths = [
            # Development environment
            Path(__file__).parent.parent.parent / "scripts",
            # Packaged application
            Path(sys.executable).parent / "scripts",
            Path(QApplication.applicationDirPath()) / "scripts",
            # Fallback - current directory
            Path.cwd() / "scripts"
        ]
        
        for path in possible_paths:
            if path.exists() and path.is_dir():
                # Check if required scripts exist
                required_scripts = [
                    "extract_mkv_subtitles.py",
                    "srtTranslateWhole.py", 
                    "srt_names_sync.py"
                ]
                
                if all((path / script).exists() for script in required_scripts):
                    self._logger.info(f"Found scripts directory: {path}")
                    return path
        
        # Fallback to assuming scripts are in parent directory
        fallback_path = Path(__file__).parent.parent.parent / "scripts"
        self._logger.warning(f"Scripts directory not found, using fallback: {fallback_path}")
        return fallback_path
    
    @property
    def is_running(self) -> bool:
        """Check if a process is currently running."""
        return (self._current_process is not None and 
                self._current_process.state() == QProcess.Running)
    
    @property
    def current_stage(self) -> Optional[Stage]:
        """Get the currently running stage."""
        return self._current_stage
    
    def run_extract(self, config: ExtractConfig) -> QProcess:
        """
        Run MKV subtitle extraction script.
        
        Args:
            config: Extract configuration
            
        Returns:
            QProcess: The started process
            
        Raises:
            RuntimeError: If another process is already running or config is invalid
        """
        if self.is_running:
            raise RuntimeError("Another process is already running")
        
        # Validate configuration
        is_valid, error_msg = config.validate()
        if not is_valid:
            raise RuntimeError(f"Configuration validation failed: {error_msg}")
        
        # Set up for extraction
        self._current_stage = Stage.EXTRACT
        self._current_config = config
        
        # Build command
        script_path = self._script_dir / "extract_mkv_subtitles.py"
        command = [sys.executable, str(script_path)] + config.to_cli_args()
        
        # Start process
        return self._start_process(command, config.get_env_vars() if hasattr(config, 'get_env_vars') else {})
    
    def run_translate(self, config: TranslateConfig) -> QProcess:
        """
        Run SRT translation script.
        
        Args:
            config: Translation configuration
            
        Returns:
            QProcess: The started process
            
        Raises:
            RuntimeError: If another process is already running or config is invalid
        """
        if self.is_running:
            raise RuntimeError("Another process is already running")
        
        # Validate configuration
        is_valid, error_msg = config.validate()
        if not is_valid:
            raise RuntimeError(f"Configuration validation failed: {error_msg}")
        
        # Set up for translation
        self._current_stage = Stage.TRANSLATE
        self._current_config = config
        
        # Handle multiple input files by running script multiple times
        # For now, handle single file or directory mode
        cli_args = config.to_cli_args()
        if not cli_args:  # Multiple files case
            raise RuntimeError("Multiple file translation not yet implemented")
        
        # Build command
        script_path = self._script_dir / "srtTranslateWhole.py"
        command = [sys.executable, str(script_path)] + cli_args
        
        # Start process
        return self._start_process(command, config.get_env_vars())
    
    def run_sync(self, config: SyncConfig) -> QProcess:
        """
        Run SRT name synchronization script.
        
        Args:
            config: Sync configuration
            
        Returns:
            QProcess: The started process
            
        Raises:
            RuntimeError: If another process is already running or config is invalid
        """
        if self.is_running:
            raise RuntimeError("Another process is already running")
        
        # Validate configuration
        is_valid, error_msg = config.validate()
        if not is_valid:
            raise RuntimeError(f"Configuration validation failed: {error_msg}")
        
        # Set up for sync
        self._current_stage = Stage.SYNC
        self._current_config = config
        
        # Build command
        script_path = self._script_dir / "srt_names_sync.py"
        command = [sys.executable, str(script_path)] + config.to_cli_args()
        
        # Start process
        return self._start_process(command, config.get_env_vars())
    
    def _start_process(self, command: List[str], env_vars: Dict[str, str]) -> QProcess:
        """
        Start a new QProcess with the given command.
        
        Args:
            command: Command and arguments to execute
            env_vars: Environment variables to set
            
        Returns:
            QProcess: The started process
        """
        # Create new process
        process = QProcess(self)
        self._current_process = process
        
        # Set up environment
        env = QProcess.systemEnvironment()
        for key, value in env_vars.items():
            env.append(f"{key}={value}")
        process.setEnvironment(env)
        
        # Set working directory to script directory
        process.setWorkingDirectory(str(self._script_dir))
        
        # Connect signals
        process.readyReadStandardOutput.connect(self._on_stdout_ready)
        process.readyReadStandardError.connect(self._on_stderr_ready)
        process.finished.connect(self._on_process_finished)
        process.errorOccurred.connect(self._on_process_error)
        process.started.connect(self._on_process_started)
        
        # Set up parser and aggregator
        self._parser.reset()
        if self._current_stage:
            self._aggregator = EventAggregator(self._current_stage)
        
        # Start process
        command_str = ' '.join(command)
        self._logger.info(f"Starting process: {command_str}")
        
        # Emit debug info to UI
        if self._current_stage:
            self.signals.info_received.emit(self._current_stage, f"DEBUG: Executing command: {command_str}")
            self.signals.info_received.emit(self._current_stage, f"DEBUG: Working directory: {self._script_dir}")
            self.signals.info_received.emit(self._current_stage, f"DEBUG: Environment variables: {len(env_vars)} custom vars")
            
            # Show ALL environment variables (including system ones for debugging)
            full_env = QProcess.systemEnvironment()
            for env_entry in full_env:
                if '=' in env_entry:
                    key, value = env_entry.split('=', 1)
                    if key in env_vars:
                        # This is one of our custom env vars
                        if 'api_key' in key.lower() or 'key' in key.lower():
                            masked_value = f"{value[:8]}***{value[-4:]}" if len(value) > 12 else "***"
                            self.signals.info_received.emit(self._current_stage, f"DEBUG: CUSTOM_ENV: {key}={masked_value}")
                        else:
                            self.signals.info_received.emit(self._current_stage, f"DEBUG: CUSTOM_ENV: {key}={value}")
            
            # Show environment variable details (without showing actual API keys)
            for key, value in env_vars.items():
                if 'api_key' in key.lower() or 'key' in key.lower():
                    masked_value = f"{value[:8]}***{value[-4:]}" if len(value) > 12 else "***"
                    self.signals.info_received.emit(self._current_stage, f"DEBUG: SET_ENV: {key}={masked_value}")
                else:
                    self.signals.info_received.emit(self._current_stage, f"DEBUG: SET_ENV: {key}={value}")
            
            self.signals.info_received.emit(self._current_stage, f"DEBUG: Starting process with PID will be assigned...")
        
        self._process_start_time = datetime.now()
        
        # Add immediate debugging right before starting process
        if self._current_stage:
            self.signals.info_received.emit(self._current_stage, f"DEBUG: About to start: {command[0]} with {len(command)-1} arguments")
        
        process.start(command[0], command[1:])
        
        if not process.waitForStarted(5000):  # 5 second timeout
            error_msg = f"Failed to start process: {process.errorString()}"
            self._logger.error(error_msg)
            if self._current_stage:
                self.signals.info_received.emit(self._current_stage, f"DEBUG: FAILED TO START: {error_msg}")
            self._cleanup_process()
            raise RuntimeError(error_msg)
        
        # Add debugging right after successful start
        if self._current_stage:
            self.signals.info_received.emit(self._current_stage, f"DEBUG: Process started successfully, waiting for first output...")
        
        return process
    
    def _on_process_started(self):
        """Handle process started signal."""
        if self._current_stage:
            self._logger.info(f"Process started for stage: {self._current_stage.value}")
            
            # Get process ID for debugging
            if self._current_process:
                process_id = self._current_process.processId()
                self.signals.info_received.emit(self._current_stage, f"DEBUG: Process started with PID: {process_id}")
                self.signals.info_received.emit(self._current_stage, f"DEBUG: Process state: {self._current_process.state()}")
                
                # Set up periodic output checking for early crash detection
                self._setup_output_monitoring()
            
            self.signals.process_started.emit(self._current_stage)
    
    def _setup_output_monitoring(self):
        """Set up periodic monitoring for process output."""
        if hasattr(self, '_output_monitor_timer'):
            self._output_monitor_timer.stop()
            
        self._output_monitor_timer = QTimer(self)
        self._output_monitor_timer.timeout.connect(self._check_process_output)
        self._output_monitor_timer.start(100)  # Check every 100ms
    
    def _check_process_output(self):
        """Periodically check for process output."""
        if not self._current_process or self._current_process.state() != QProcess.Running:
            if hasattr(self, '_output_monitor_timer'):
                self._output_monitor_timer.stop()
            return
        
        # Force check for available output
        if self._current_process.bytesAvailable() > 0:
            self._on_stdout_ready()
            
        # Check stderr too
        try:
            stderr_data = self._current_process.readAllStandardError()
            if stderr_data and len(stderr_data.data()) > 0:
                self._on_stderr_ready()
        except Exception as e:
            # Ignore stderr checking errors
            pass
    
    def _on_stdout_ready(self):
        """Handle stdout data from process."""
        if not self._current_process:
            return
        
        data = self._current_process.readAllStandardOutput().data().decode('utf-8', errors='replace')
        
        # Emit raw output signal
        self.signals.process_output_received.emit(data)
        
        # Send ALL stdout to debug log immediately - don't filter anything
        if self._current_stage and data:
            # Log the raw data first
            self.signals.info_received.emit(self._current_stage, f"DEBUG: RAW_STDOUT: {repr(data)}")
            
            # Then split by lines for readability
            lines = data.split('\n')
            for i, line in enumerate(lines):
                # Include empty lines to preserve structure
                self.signals.info_received.emit(self._current_stage, f"DEBUG: STDOUT[{i}]: {repr(line)}")
        
        # Parse JSONL events
        try:
            for event, error in self._parser.parse_stream_data(data):
                if event:
                    self._handle_event(event)
                elif error:
                    self.signals.parse_error.emit(data, error)
                    # Also send parse errors to debug log
                    if self._current_stage:
                        self.signals.info_received.emit(self._current_stage, f"DEBUG: PARSE ERROR: {error}")
                    
        except Exception as e:
            self._logger.error(f"Error processing stdout: {e}")
            self.signals.parse_error.emit(data, str(e))
            if self._current_stage:
                self.signals.info_received.emit(self._current_stage, f"DEBUG: PROCESSING ERROR: {str(e)}")
    
    def _on_stderr_ready(self):
        """Handle stderr data from process."""
        if not self._current_process:
            return
        
        data = self._current_process.readAllStandardError().data().decode('utf-8', errors='replace')
        
        # Emit stderr signal
        self.signals.process_error_received.emit(data)
        
        # Send ALL stderr to UI for debugging - don't filter anything
        if self._current_stage and data:
            # Log the raw data first
            self.signals.info_received.emit(self._current_stage, f"DEBUG: RAW_STDERR: {repr(data)}")
            
            # Then split by lines for readability
            lines = data.split('\n')
            for i, line in enumerate(lines):
                # Include empty lines to preserve structure
                self.signals.info_received.emit(self._current_stage, f"DEBUG: STDERR[{i}]: {repr(line)}")
        
        # Log stderr data
        self._logger.warning(f"Process stderr: {data}")
    
    def _on_process_finished(self, exit_code: int, exit_status: QProcess.ExitStatus):
        """Handle process finished signal."""
        if not self._current_stage:
            return
        
        # Capture any remaining stdout/stderr data before finishing
        if self._current_process:
            remaining_stdout = self._current_process.readAllStandardOutput().data().decode('utf-8', errors='replace')
            remaining_stderr = self._current_process.readAllStandardError().data().decode('utf-8', errors='replace')
            
            if remaining_stdout:
                self.signals.info_received.emit(self._current_stage, f"DEBUG: FINAL_STDOUT: {repr(remaining_stdout)}")
                
            if remaining_stderr:
                self.signals.info_received.emit(self._current_stage, f"DEBUG: FINAL_STDERR: {repr(remaining_stderr)}")
        
        # Flush any remaining parser buffer
        try:
            for event, error in self._parser.flush_buffer():
                if event:
                    self._handle_event(event)
                elif error:
                    self.signals.parse_error.emit("", error)
        except Exception as e:
            self._logger.error(f"Error flushing parser buffer: {e}")
        
        # Create process result
        duration = 0.0
        if self._process_start_time:
            duration = (datetime.now() - self._process_start_time).total_seconds()
        
        # Get summary from aggregator
        summary = {}
        if self._aggregator:
            summary = self._aggregator.get_summary()
        
        # Create result object
        result = ProcessResult(
            success=(exit_code == 0 and exit_status == QProcess.NormalExit),
            exit_code=exit_code,
            stage=self._current_stage,
            duration_seconds=duration,
            result_data=summary.get('result_data')
        )
        
        # Extract file statistics from result data if available
        if result.result_data:
            result.files_processed = result.result_data.get('files_processed', 0)
            result.files_successful = result.result_data.get('files_successful', 0) 
            result.files_failed = result.result_data.get('files_failed', 0)
            result.output_files = result.result_data.get('outputs', [])
        
        # Set error message if process failed
        if not result.success:
            if self._aggregator and self._aggregator.errors:
                result.error_message = '; '.join(self._aggregator.errors)
            else:
                result.error_message = f"Process exited with code {exit_code}"
        
        # Emit result signal
        self.signals.process_finished.emit(result)
        
        # Log completion
        status = "successfully" if result.success else "with errors"
        self._logger.info(f"Process completed {status} in {duration:.1f}s")
        
        # Send debug info to UI
        if self._current_stage:
            self.signals.info_received.emit(self._current_stage, f"DEBUG: Process completed {status} in {duration:.1f}s")
            self.signals.info_received.emit(self._current_stage, f"DEBUG: Exit code: {exit_code}, Exit status: {exit_status}")
            
            if result.output_files:
                self.signals.info_received.emit(self._current_stage, f"DEBUG: Output files: {result.output_files}")
            
            if hasattr(result, 'files_processed') and result.files_processed:
                self.signals.info_received.emit(self._current_stage, f"DEBUG: Files processed: {result.files_processed}, Successful: {result.files_successful}")
        
        # Cleanup
        self._cleanup_process()
    
    def _on_process_error(self, error: QProcess.ProcessError):
        """Handle process error signal."""
        # Stop output monitoring immediately
        if hasattr(self, '_output_monitor_timer'):
            self._output_monitor_timer.stop()
            
        error_messages = {
            QProcess.FailedToStart: "Failed to start process",
            QProcess.Crashed: "Process crashed",
            QProcess.Timedout: "Process timed out", 
            QProcess.WriteError: "Write error",
            QProcess.ReadError: "Read error",
            QProcess.UnknownError: "Unknown error"
        }
        
        error_msg = error_messages.get(error, f"Process error: {error}")
        self._logger.error(error_msg)
        
        if self._current_stage:
            # Send detailed error information to debug log
            self.signals.info_received.emit(self._current_stage, f"DEBUG: PROCESS ERROR: {error_msg}")
            if self._current_process:
                # Try to read any final output before the process dies
                try:
                    final_stdout = self._current_process.readAllStandardOutput().data().decode('utf-8', errors='replace')
                    final_stderr = self._current_process.readAllStandardError().data().decode('utf-8', errors='replace')
                    
                    if final_stdout:
                        self.signals.info_received.emit(self._current_stage, f"DEBUG: CRASH_FINAL_STDOUT: {repr(final_stdout)}")
                    if final_stderr:
                        self.signals.info_received.emit(self._current_stage, f"DEBUG: CRASH_FINAL_STDERR: {repr(final_stderr)}")
                        
                except Exception as e:
                    self.signals.info_received.emit(self._current_stage, f"DEBUG: Error reading final output: {e}")
                
                self.signals.info_received.emit(self._current_stage, f"DEBUG: Process exit code: {self._current_process.exitCode()}")
                self.signals.info_received.emit(self._current_stage, f"DEBUG: Process exit status: {self._current_process.exitStatus()}")
                self.signals.info_received.emit(self._current_stage, f"DEBUG: Process state: {self._current_process.state()}")
            
            self.signals.process_failed.emit(self._current_stage, error_msg)
        
        self._cleanup_process()
    
    def _handle_event(self, event: Event):
        """
        Handle a parsed JSONL event.
        
        Args:
            event: Parsed event object
        """
        # Add to aggregator
        if self._aggregator:
            self._aggregator.add_event(event)
        
        # Emit appropriate signals
        self.signals.event_received.emit(event)
        
        if event.event_type == EventType.INFO:
            self.signals.info_received.emit(event.stage, event.message)
            
        elif event.event_type == EventType.PROGRESS:
            progress = event.progress if event.progress is not None else 0
            self.signals.progress_updated.emit(event.stage, progress, event.message)
            
        elif event.event_type == EventType.WARNING:
            self.signals.warning_received.emit(event.stage, event.message)
            
        elif event.event_type == EventType.ERROR:
            self.signals.error_received.emit(event.stage, event.message)
            
        elif event.event_type == EventType.RESULT:
            data = event.data if event.data is not None else {}
            self.signals.result_received.emit(event.stage, data)
    
    def terminate_process(self, timeout: int = 5) -> bool:
        """
        Terminate the current process gracefully.
        
        Args:
            timeout: Timeout in seconds for graceful termination
            
        Returns:
            bool: True if process was terminated successfully
        """
        if not self.is_running:
            return True
        
        self._logger.info(f"Terminating process for stage: {self._current_stage}")
        
        # Try graceful termination first
        self._current_process.terminate()
        
        # Set up force kill timer
        self._termination_timer.start(timeout * 1000)
        
        # Wait for termination
        if self._current_process.waitForFinished(timeout * 1000):
            self._termination_timer.stop()
            self._logger.info("Process terminated gracefully")
            return True
        
        # If graceful termination failed, force kill
        return self._force_kill_process()
    
    def _force_kill_process(self) -> bool:
        """Force kill the current process."""
        if not self._current_process:
            return True
        
        self._logger.warning("Force killing process")
        self._current_process.kill()
        
        if self._current_process.waitForFinished(3000):  # 3 second timeout
            self._logger.info("Process force killed")
            return True
        
        self._logger.error("Failed to kill process")
        return False
    
    def _cleanup_process(self):
        """Clean up process-related state."""
        self._termination_timer.stop()
        
        # Stop output monitoring
        if hasattr(self, '_output_monitor_timer'):
            self._output_monitor_timer.stop()
        
        if self._current_process:
            # Ensure process is properly terminated before cleanup
            if self._current_process.state() == QProcess.Running:
                self._current_process.terminate()
                if not self._current_process.waitForFinished(3000):  # 3 second timeout
                    self._current_process.kill()
                    self._current_process.waitForFinished(1000)  # 1 second timeout for kill
            
            # Safely delete the process
            process = self._current_process
            self._current_process = None  # Clear reference first
            if process:
                process.deleteLater()
        
        self._current_stage = None
        self._current_config = None
        self._aggregator = None
        self._process_start_time = None
    
    def get_process_info(self) -> Dict[str, Any]:
        """Get information about the current process."""
        if not self.is_running:
            return {
                'running': False,
                'stage': None,
                'duration': 0,
                'progress': {}
            }
        
        duration = 0.0
        if self._process_start_time:
            duration = (datetime.now() - self._process_start_time).total_seconds()
        
        progress_info = {}
        if self._aggregator:
            progress_info = self._aggregator.get_progress_info()
        
        return {
            'running': True,
            'stage': self._current_stage.value if self._current_stage else None,
            'duration': duration,
            'progress': progress_info,
            'parser_stats': self._parser.get_stats()
        }
    
    def cancel_current_process(self):
        """Cancel the currently running process."""
        if self.is_running:
            if self._current_stage:
                self.signals.process_cancelled.emit(self._current_stage)
            self.terminate_process()