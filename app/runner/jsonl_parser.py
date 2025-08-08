"""
JSONL stream parser for SubtitleToolkit script output.

Provides robust parsing of JSONL events from subprocess stdout with
error handling, partial line buffering, and recovery mechanisms.
"""

import json
import logging
from typing import Iterator, Optional, List, Tuple
from io import StringIO

from PySide6.QtCore import QObject, QTextStream, QIODevice
from PySide6.QtNetwork import QTcpSocket

from .events import Event, EventType, Stage


class JSONLParser(QObject):
    """
    Robust JSONL stream parser with error recovery.
    
    Handles:
    - Partial lines and incomplete JSON
    - Invalid JSON recovery
    - Stream interruptions
    - Buffer management
    - Event validation
    """
    
    def __init__(self, parent: QObject = None):
        super().__init__(parent)
        
        # Buffer for partial lines
        self._buffer = ""
        
        # Parsing statistics
        self._lines_processed = 0
        self._events_parsed = 0
        self._parse_errors = 0
        
        # Logger for debugging
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def parse_stream_data(self, data: str) -> Iterator[Tuple[Event, Optional[str]]]:
        """
        Parse incoming stream data and yield events.
        
        Args:
            data: Raw string data from subprocess stdout
            
        Yields:
            Tuple[Event, Optional[str]]: (parsed_event, error_message)
            If parsing fails, event will be None and error_message will contain details.
        """
        # Add data to buffer
        self._buffer += data
        
        # Process complete lines
        while '\n' in self._buffer:
            line, self._buffer = self._buffer.split('\n', 1)
            self._lines_processed += 1
            
            # Skip empty lines
            if not line.strip():
                continue
            
            # Parse the line
            event, error = self._parse_line(line)
            yield (event, error)
    
    def _parse_line(self, line: str) -> Tuple[Optional[Event], Optional[str]]:
        """
        Parse a single line of JSONL data.
        
        Args:
            line: Complete line from the stream
            
        Returns:
            Tuple[Optional[Event], Optional[str]]: (parsed_event, error_message)
        """
        try:
            # Try to parse as JSON
            json_data = json.loads(line.strip())
            
            # Validate it has the expected structure
            if not isinstance(json_data, dict):
                self._parse_errors += 1
                return None, f"JSONL line is not a JSON object: {line[:100]}..."
            
            # Create Event object
            event = Event.from_jsonl(json_data)
            self._events_parsed += 1
            
            return event, None
            
        except json.JSONDecodeError as e:
            self._parse_errors += 1
            error_msg = f"JSON decode error: {e}. Line: {line[:100]}..."
            self._logger.warning(error_msg)
            return None, error_msg
            
        except ValueError as e:
            self._parse_errors += 1
            error_msg = f"Event validation error: {e}. Line: {line[:100]}..."
            self._logger.warning(error_msg)
            return None, error_msg
            
        except Exception as e:
            self._parse_errors += 1
            error_msg = f"Unexpected parsing error: {e}. Line: {line[:100]}..."
            self._logger.error(error_msg)
            return None, error_msg
    
    def flush_buffer(self) -> Iterator[Tuple[Optional[Event], Optional[str]]]:
        """
        Flush any remaining data in the buffer.
        
        This should be called when the stream is closed to handle
        any incomplete lines.
        
        Yields:
            Tuple[Optional[Event], Optional[str]]: Any events parsed from buffer
        """
        if self._buffer.strip():
            # Try to parse any remaining data
            event, error = self._parse_line(self._buffer)
            yield (event, error)
            self._buffer = ""
    
    def reset(self):
        """Reset parser state for reuse."""
        self._buffer = ""
        self._lines_processed = 0
        self._events_parsed = 0
        self._parse_errors = 0
    
    def get_stats(self) -> dict:
        """Get parsing statistics."""
        return {
            'lines_processed': self._lines_processed,
            'events_parsed': self._events_parsed,
            'parse_errors': self._parse_errors,
            'buffer_size': len(self._buffer),
            'success_rate': (self._events_parsed / max(self._lines_processed, 1)) * 100
        }


class StreamBuffer:
    """
    Helper class for managing stream data buffering.
    
    Handles line-based buffering with size limits and overflow protection.
    """
    
    def __init__(self, max_buffer_size: int = 1024 * 1024):  # 1MB default
        self.max_buffer_size = max_buffer_size
        self.buffer = StringIO()
        self._total_size = 0
    
    def write(self, data: str) -> None:
        """Write data to the buffer."""
        if self._total_size + len(data) > self.max_buffer_size:
            # Buffer overflow protection - keep only the most recent data
            self._truncate_buffer()
        
        self.buffer.write(data)
        self._total_size += len(data)
    
    def read_lines(self) -> Iterator[str]:
        """Read complete lines from the buffer."""
        # Get current buffer content
        content = self.buffer.getvalue()
        
        # Split into lines
        lines = content.split('\n')
        
        # Keep the last incomplete line in buffer
        if lines:
            incomplete_line = lines[-1]
            complete_lines = lines[:-1]
            
            # Reset buffer with incomplete line
            self.buffer = StringIO()
            if incomplete_line:
                self.buffer.write(incomplete_line)
                self._total_size = len(incomplete_line)
            else:
                self._total_size = 0
            
            # Yield complete lines
            for line in complete_lines:
                if line:  # Skip empty lines
                    yield line
    
    def flush(self) -> Optional[str]:
        """Flush any remaining data from buffer."""
        content = self.buffer.getvalue()
        self.buffer = StringIO()
        self._total_size = 0
        
        return content if content.strip() else None
    
    def _truncate_buffer(self):
        """Truncate buffer to prevent memory issues."""
        content = self.buffer.getvalue()
        
        # Keep only the last half of the buffer
        keep_size = self.max_buffer_size // 2
        truncated_content = content[-keep_size:]
        
        # Find the start of a complete line
        newline_pos = truncated_content.find('\n')
        if newline_pos != -1:
            truncated_content = truncated_content[newline_pos + 1:]
        
        # Reset buffer
        self.buffer = StringIO()
        self.buffer.write(truncated_content)
        self._total_size = len(truncated_content)


class JSONLValidator:
    """
    Utility class for validating JSONL event structure.
    
    Provides detailed validation of events according to the schema.
    """
    
    REQUIRED_FIELDS = {'ts', 'stage', 'type', 'msg'}
    OPTIONAL_FIELDS = {'progress', 'data'}
    VALID_STAGES = {'extract', 'translate', 'sync'}
    VALID_TYPES = {'info', 'progress', 'warning', 'error', 'result'}
    
    @classmethod
    def validate_event_dict(cls, event_data: dict) -> Tuple[bool, List[str]]:
        """
        Validate a parsed JSON object as a valid event.
        
        Args:
            event_data: Dictionary from parsed JSON
            
        Returns:
            Tuple[bool, List[str]]: (is_valid, list_of_errors)
        """
        errors = []
        
        # Check required fields
        for field in cls.REQUIRED_FIELDS:
            if field not in event_data:
                errors.append(f"Missing required field: {field}")
        
        # Check field types and values
        if 'ts' in event_data:
            if not isinstance(event_data['ts'], str):
                errors.append("Field 'ts' must be a string")
        
        if 'stage' in event_data:
            if not isinstance(event_data['stage'], str):
                errors.append("Field 'stage' must be a string")
            elif event_data['stage'] not in cls.VALID_STAGES:
                errors.append(f"Invalid stage: {event_data['stage']}")
        
        if 'type' in event_data:
            if not isinstance(event_data['type'], str):
                errors.append("Field 'type' must be a string")
            elif event_data['type'] not in cls.VALID_TYPES:
                errors.append(f"Invalid type: {event_data['type']}")
        
        if 'msg' in event_data:
            if not isinstance(event_data['msg'], str):
                errors.append("Field 'msg' must be a string")
        
        # Check optional fields
        if 'progress' in event_data:
            progress = event_data['progress']
            if progress is not None:
                if not isinstance(progress, int):
                    errors.append("Field 'progress' must be an integer or null")
                elif not (0 <= progress <= 100):
                    errors.append("Field 'progress' must be between 0 and 100")
        
        if 'data' in event_data:
            if event_data['data'] is not None and not isinstance(event_data['data'], dict):
                errors.append("Field 'data' must be an object or null")
        
        # Check for unexpected fields
        all_valid_fields = cls.REQUIRED_FIELDS | cls.OPTIONAL_FIELDS
        for field in event_data:
            if field not in all_valid_fields:
                errors.append(f"Unexpected field: {field}")
        
        return len(errors) == 0, errors
    
    @classmethod
    def validate_progress_event(cls, event_data: dict) -> Tuple[bool, List[str]]:
        """Validate a progress-type event has required progress field."""
        is_valid, errors = cls.validate_event_dict(event_data)
        
        if is_valid and event_data.get('type') == 'progress':
            if 'progress' not in event_data or event_data['progress'] is None:
                errors.append("Progress events must include progress field")
                is_valid = False
        
        return is_valid, errors
    
    @classmethod
    def validate_result_event(cls, event_data: dict) -> Tuple[bool, List[str]]:
        """Validate a result-type event has required data field."""
        is_valid, errors = cls.validate_event_dict(event_data)
        
        if is_valid and event_data.get('type') == 'result':
            if 'data' not in event_data or event_data['data'] is None:
                errors.append("Result events must include data field")
                is_valid = False
        
        return is_valid, errors