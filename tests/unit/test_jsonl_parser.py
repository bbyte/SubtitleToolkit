"""
Unit tests for JSONL parser robustness and functionality.

Tests the JSONLParser class for handling malformed JSON, partial lines,
stream interruptions, and various edge cases.

Following TDD principles:
1. Test malformed JSON recovery
2. Test partial line buffering
3. Test stream interruption handling
4. Test validation and error reporting
5. Test performance under load
"""

import json
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from app.runner.jsonl_parser import JSONLParser, StreamBuffer, JSONLValidator
from app.runner.events import Event, EventType, Stage


@pytest.mark.unit
class TestJSONLParser:
    """Test suite for JSONL parser core functionality."""
    
    def test_parser_initialization(self, qapp):
        """Test parser initializes correctly."""
        parser = JSONLParser()
        
        assert parser._buffer == ""
        assert parser._lines_processed == 0
        assert parser._events_parsed == 0
        assert parser._parse_errors == 0
        assert parser._logger is not None
    
    def test_parse_valid_jsonl_stream(self, qapp, sample_jsonl_events):
        """Test parsing valid JSONL stream data."""
        parser = JSONLParser()
        
        # Test parsing complete stream
        stream_data = '\n'.join(sample_jsonl_events) + '\n'
        events = list(parser.parse_stream_data(stream_data))
        
        # Should have parsed 5 events successfully
        successful_events = [event for event, error in events if event is not None]
        errors = [error for event, error in events if error is not None]
        
        assert len(successful_events) == 5
        assert len(errors) == 0
        
        # Verify event types and stages
        assert successful_events[0].event_type == EventType.INFO
        assert successful_events[1].event_type == EventType.PROGRESS
        assert successful_events[2].event_type == EventType.WARNING
        assert successful_events[3].event_type == EventType.ERROR
        assert successful_events[4].event_type == EventType.RESULT
        
        # All should be extract stage
        assert all(event.stage == Stage.EXTRACT for event in successful_events)
    
    def test_parse_malformed_jsonl_data(self, qapp, malformed_jsonl_data):
        """Test parser robustness with malformed JSONL data."""
        parser = JSONLParser()
        
        for malformed_line in malformed_jsonl_data:
            events = list(parser.parse_stream_data(malformed_line + '\n'))
            
            # Each malformed line should produce an error, not crash
            errors = [error for event, error in events if error is not None]
            successful_events = [event for event, error in events if event is not None]
            
            if malformed_line.strip():  # Non-empty lines should produce errors
                assert len(errors) >= 1 or len(successful_events) == 0
                if errors:
                    assert isinstance(errors[0], str)
                    assert len(errors[0]) > 0
    
    def test_partial_line_buffering(self, qapp):
        """Test handling of partial lines and buffering."""
        parser = JSONLParser()
        
        # Send partial JSON data
        partial_json = '{"ts": "2025-08-08T07:42:01Z", "stage": "extract"'
        events = list(parser.parse_stream_data(partial_json))
        
        # Should not parse anything yet
        assert len(events) == 0
        assert parser._buffer == partial_json
        
        # Complete the JSON
        remaining_json = ', "type": "info", "msg": "test"}\n'
        events = list(parser.parse_stream_data(remaining_json))
        
        # Should now parse successfully
        successful_events = [event for event, error in events if event is not None]
        assert len(successful_events) == 1
        assert successful_events[0].message == "test"
        
        # Buffer should be empty
        assert parser._buffer == ""
    
    def test_multiple_lines_in_single_stream(self, qapp):
        """Test parsing multiple complete lines in a single data chunk."""
        parser = JSONLParser()
        
        # Multiple complete JSON lines
        multi_line_data = """{"ts": "2025-08-08T07:42:01Z", "stage": "extract", "type": "info", "msg": "Line 1"}
{"ts": "2025-08-08T07:42:02Z", "stage": "extract", "type": "info", "msg": "Line 2"}
{"ts": "2025-08-08T07:42:03Z", "stage": "extract", "type": "info", "msg": "Line 3"}
"""
        
        events = list(parser.parse_stream_data(multi_line_data))
        successful_events = [event for event, error in events if event is not None]
        
        assert len(successful_events) == 3
        assert successful_events[0].message == "Line 1"
        assert successful_events[1].message == "Line 2"
        assert successful_events[2].message == "Line 3"
    
    def test_mixed_valid_invalid_lines(self, qapp):
        """Test stream with mix of valid and invalid JSON lines."""
        parser = JSONLParser()
        
        mixed_data = """{"ts": "2025-08-08T07:42:01Z", "stage": "extract", "type": "info", "msg": "Valid line 1"}
{invalid json}
{"ts": "2025-08-08T07:42:02Z", "stage": "extract", "type": "info", "msg": "Valid line 2"}
not json at all
{"ts": "2025-08-08T07:42:03Z", "stage": "extract", "type": "info", "msg": "Valid line 3"}
"""
        
        events = list(parser.parse_stream_data(mixed_data))
        successful_events = [event for event, error in events if event is not None]
        errors = [error for event, error in events if error is not None]
        
        # Should have 3 successful events and 2 errors
        assert len(successful_events) == 3
        assert len(errors) == 2
        
        # Verify successful events
        messages = [event.message for event in successful_events]
        assert "Valid line 1" in messages
        assert "Valid line 2" in messages
        assert "Valid line 3" in messages
    
    def test_flush_buffer_handling(self, qapp):
        """Test flushing remaining buffer data."""
        parser = JSONLParser()
        
        # Send incomplete data without newline
        incomplete_data = '{"ts": "2025-08-08T07:42:01Z", "stage": "extract", "type": "info", "msg": "test"}'
        events = list(parser.parse_stream_data(incomplete_data))
        
        # Should be buffered, not parsed
        assert len(events) == 0
        assert parser._buffer == incomplete_data
        
        # Flush buffer
        flush_events = list(parser.flush_buffer())
        successful_events = [event for event, error in flush_events if event is not None]
        
        # Should parse the buffered data
        assert len(successful_events) == 1
        assert successful_events[0].message == "test"
        assert parser._buffer == ""
    
    def test_empty_and_whitespace_lines(self, qapp):
        """Test handling of empty lines and whitespace-only lines."""
        parser = JSONLParser()
        
        data_with_empty_lines = """{"ts": "2025-08-08T07:42:01Z", "stage": "extract", "type": "info", "msg": "Line 1"}

   
\t
{"ts": "2025-08-08T07:42:02Z", "stage": "extract", "type": "info", "msg": "Line 2"}
"""
        
        events = list(parser.parse_stream_data(data_with_empty_lines))
        successful_events = [event for event, error in events if event is not None]
        
        # Should ignore empty lines and parse only valid JSON
        assert len(successful_events) == 2
        assert successful_events[0].message == "Line 1"
        assert successful_events[1].message == "Line 2"
    
    def test_parser_statistics(self, qapp, sample_jsonl_events):
        """Test parser statistics tracking."""
        parser = JSONLParser()
        
        # Initially all stats should be zero
        stats = parser.get_stats()
        assert stats['lines_processed'] == 0
        assert stats['events_parsed'] == 0
        assert stats['parse_errors'] == 0
        
        # Parse some data
        stream_data = '\n'.join(sample_jsonl_events) + '\n'
        list(parser.parse_stream_data(stream_data))  # Consume generator
        
        # Check updated stats
        stats = parser.get_stats()
        assert stats['lines_processed'] == 5
        assert stats['events_parsed'] == 5
        assert stats['parse_errors'] == 0
        assert stats['success_rate'] == 100.0
        
        # Parse some invalid data
        invalid_data = 'invalid json\n'
        list(parser.parse_stream_data(invalid_data))
        
        # Stats should reflect the error
        stats = parser.get_stats()
        assert stats['lines_processed'] == 6
        assert stats['events_parsed'] == 5
        assert stats['parse_errors'] == 1
        assert stats['success_rate'] < 100.0
    
    def test_parser_reset(self, qapp, sample_jsonl_events):
        """Test parser reset functionality."""
        parser = JSONLParser()
        
        # Parse some data and add to buffer
        stream_data = '\n'.join(sample_jsonl_events)  # No trailing newline
        list(parser.parse_stream_data(stream_data))
        
        # Should have some state
        assert parser._lines_processed > 0
        assert parser._events_parsed > 0
        assert len(parser._buffer) > 0
        
        # Reset parser
        parser.reset()
        
        # All state should be cleared
        assert parser._buffer == ""
        assert parser._lines_processed == 0
        assert parser._events_parsed == 0
        assert parser._parse_errors == 0
    
    @pytest.mark.performance
    def test_parser_performance_large_stream(self, qapp, performance_tracker):
        """Test parser performance with large data streams."""
        parser = JSONLParser()
        performance_tracker.start_timer("large_stream_parsing")
        
        # Generate large stream of valid JSON events
        large_stream_lines = []
        for i in range(1000):
            event_data = {
                "ts": "2025-08-08T07:42:01Z",
                "stage": "extract",
                "type": "progress",
                "msg": f"Processing item {i}",
                "progress": i % 101
            }
            large_stream_lines.append(json.dumps(event_data))
        
        large_stream = '\n'.join(large_stream_lines) + '\n'
        
        # Parse the large stream
        events = list(parser.parse_stream_data(large_stream))
        
        performance_tracker.end_timer("large_stream_parsing")
        
        # Verify all events parsed successfully
        successful_events = [event for event, error in events if event is not None]
        assert len(successful_events) == 1000
        
        # Should complete within reasonable time (2 seconds for 1000 events)
        performance_tracker.assert_duration_under("large_stream_parsing", 2.0)
    
    def test_unicode_and_encoding_handling(self, qapp):
        """Test handling of Unicode and various encodings."""
        parser = JSONLParser()
        
        # Unicode content in JSON
        unicode_events = [
            '{"ts": "2025-08-08T07:42:01Z", "stage": "extract", "type": "info", "msg": "测试中文字符"}',
            '{"ts": "2025-08-08T07:42:02Z", "stage": "extract", "type": "info", "msg": "Tëst ũnicödė"}',
            '{"ts": "2025-08-08T07:42:03Z", "stage": "extract", "type": "info", "msg": "🎬 Video processing 📽️"}',
        ]
        
        stream_data = '\n'.join(unicode_events) + '\n'
        events = list(parser.parse_stream_data(stream_data))
        successful_events = [event for event, error in events if event is not None]
        
        assert len(successful_events) == 3
        assert successful_events[0].message == "测试中文字符"
        assert successful_events[1].message == "Tëst ũnicödė"
        assert successful_events[2].message == "🎬 Video processing 📽️"


@pytest.mark.unit
class TestStreamBuffer:
    """Test suite for StreamBuffer utility class."""
    
    def test_buffer_initialization(self):
        """Test buffer initializes correctly."""
        buffer = StreamBuffer(max_buffer_size=1024)
        
        assert buffer.max_buffer_size == 1024
        assert buffer._total_size == 0
    
    def test_write_and_read_lines(self):
        """Test basic write and read operations."""
        buffer = StreamBuffer()
        
        # Write complete lines
        buffer.write("line1\nline2\nline3\n")
        
        lines = list(buffer.read_lines())
        assert lines == ["line1", "line2", "line3"]
        
        # Buffer should be empty after reading complete lines
        assert buffer._total_size == 0
    
    def test_partial_line_buffering(self):
        """Test buffering of incomplete lines."""
        buffer = StreamBuffer()
        
        # Write partial line
        buffer.write("partial_line_without_newline")
        
        # Should not yield anything
        lines = list(buffer.read_lines())
        assert lines == []
        
        # Buffer should contain the partial line
        assert buffer._total_size > 0
        
        # Complete the line
        buffer.write("_completed\n")
        
        lines = list(buffer.read_lines())
        assert lines == ["partial_line_without_newline_completed"]
    
    def test_buffer_overflow_protection(self):
        """Test buffer overflow protection mechanism."""
        # Small buffer for testing overflow
        buffer = StreamBuffer(max_buffer_size=100)
        
        # Write data exceeding buffer size
        large_data = "x" * 200 + "\n"
        buffer.write(large_data)
        
        # Buffer should not exceed max size significantly
        assert buffer._total_size <= buffer.max_buffer_size
    
    def test_flush_remaining_data(self):
        """Test flushing remaining buffered data."""
        buffer = StreamBuffer()
        
        # Write data without newline
        buffer.write("remaining_data")
        
        # Flush should return the data
        remaining = buffer.flush()
        assert remaining == "remaining_data"
        
        # Buffer should be empty after flush
        assert buffer._total_size == 0
        
        # Flush empty buffer should return None
        remaining = buffer.flush()
        assert remaining is None


@pytest.mark.unit
class TestJSONLValidator:
    """Test suite for JSONL validation utility."""
    
    def test_validate_valid_event_dict(self):
        """Test validation of valid event dictionaries."""
        valid_event = {
            "ts": "2025-08-08T07:42:01Z",
            "stage": "extract",
            "type": "info",
            "msg": "Test message"
        }
        
        is_valid, errors = JSONLValidator.validate_event_dict(valid_event)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_missing_required_fields(self):
        """Test validation fails for missing required fields."""
        test_cases = [
            # Missing timestamp
            {"stage": "extract", "type": "info", "msg": "test"},
            # Missing stage
            {"ts": "2025-08-08T07:42:01Z", "type": "info", "msg": "test"},
            # Missing type
            {"ts": "2025-08-08T07:42:01Z", "stage": "extract", "msg": "test"},
            # Missing message
            {"ts": "2025-08-08T07:42:01Z", "stage": "extract", "type": "info"},
        ]
        
        for incomplete_event in test_cases:
            is_valid, errors = JSONLValidator.validate_event_dict(incomplete_event)
            
            assert is_valid is False
            assert len(errors) > 0
            assert any("Missing required field" in error for error in errors)
    
    def test_validate_invalid_field_values(self):
        """Test validation fails for invalid field values."""
        test_cases = [
            # Invalid stage
            {"ts": "2025-08-08T07:42:01Z", "stage": "invalid", "type": "info", "msg": "test"},
            # Invalid type
            {"ts": "2025-08-08T07:42:01Z", "stage": "extract", "type": "invalid", "msg": "test"},
            # Invalid progress value
            {"ts": "2025-08-08T07:42:01Z", "stage": "extract", "type": "progress", "msg": "test", "progress": 150},
            # Wrong field types
            {"ts": 123, "stage": "extract", "type": "info", "msg": "test"},
        ]
        
        for invalid_event in test_cases:
            is_valid, errors = JSONLValidator.validate_event_dict(invalid_event)
            
            assert is_valid is False
            assert len(errors) > 0
    
    def test_validate_optional_fields(self):
        """Test validation of optional fields."""
        # Valid with optional fields
        event_with_optional = {
            "ts": "2025-08-08T07:42:01Z",
            "stage": "extract",
            "type": "progress",
            "msg": "Test message",
            "progress": 50,
            "data": {"key": "value"}
        }
        
        is_valid, errors = JSONLValidator.validate_event_dict(event_with_optional)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_progress_event_requirements(self):
        """Test validation of progress-specific requirements."""
        # Progress event without progress field should fail
        progress_without_field = {
            "ts": "2025-08-08T07:42:01Z",
            "stage": "extract",
            "type": "progress",
            "msg": "Test message"
        }
        
        is_valid, errors = JSONLValidator.validate_progress_event(progress_without_field)
        
        assert is_valid is False
        assert any("Progress events must include progress field" in error for error in errors)
    
    def test_validate_result_event_requirements(self):
        """Test validation of result-specific requirements."""
        # Result event without data field should fail
        result_without_data = {
            "ts": "2025-08-08T07:42:01Z",
            "stage": "extract",
            "type": "result",
            "msg": "Test message"
        }
        
        is_valid, errors = JSONLValidator.validate_result_event(result_without_data)
        
        assert is_valid is False
        assert any("Result events must include data field" in error for error in errors)
    
    def test_validate_unexpected_fields(self):
        """Test validation detects unexpected fields."""
        event_with_extra = {
            "ts": "2025-08-08T07:42:01Z",
            "stage": "extract",
            "type": "info",
            "msg": "Test message",
            "unexpected_field": "value"
        }
        
        is_valid, errors = JSONLValidator.validate_event_dict(event_with_extra)
        
        assert is_valid is False
        assert any("Unexpected field: unexpected_field" in error for error in errors)


@pytest.mark.unit
class TestJSONLParserErrorRecovery:
    """Test suite focusing on error recovery and resilience."""
    
    def test_recovery_after_parse_errors(self, qapp):
        """Test parser continues after encountering parse errors."""
        parser = JSONLParser()
        
        # Stream with errors followed by valid data
        mixed_stream = """invalid json line 1
{"ts": "2025-08-08T07:42:01Z", "stage": "extract", "type": "info", "msg": "valid after error"}
malformed { json
{"ts": "2025-08-08T07:42:02Z", "stage": "extract", "type": "info", "msg": "another valid line"}
"""
        
        events = list(parser.parse_stream_data(mixed_stream))
        successful_events = [event for event, error in events if event is not None]
        errors = [error for event, error in events if error is not None]
        
        # Should have 2 successful events and 2 errors
        assert len(successful_events) == 2
        assert len(errors) == 2
        
        # Parser should continue functioning
        assert successful_events[0].message == "valid after error"
        assert successful_events[1].message == "another valid line"
    
    def test_graceful_handling_of_corrupted_streams(self, qapp):
        """Test handling of severely corrupted data streams."""
        parser = JSONLParser()
        
        # Completely corrupted data
        corrupted_streams = [
            "\\x00\\x01\\xff binary data",
            "{'python': 'dict'} not json",
            "xml<tag>content</tag>",
            "random text without structure",
            "",  # Empty stream
        ]
        
        for corrupted_data in corrupted_streams:
            events = list(parser.parse_stream_data(corrupted_data + '\n'))
            
            # Should not crash, might produce errors for non-empty data
            for event, error in events:
                if error:
                    assert isinstance(error, str)
                    assert len(error) > 0
    
    def test_stream_interruption_simulation(self, qapp):
        """Test handling of simulated stream interruptions."""
        parser = JSONLParser()
        
        # Simulate stream that gets cut off mid-JSON
        interrupted_stream = '{"ts": "2025-08-08T07:42:01Z", "stage": "extract", "type": "info", "msg":'
        
        # First chunk
        events1 = list(parser.parse_stream_data(interrupted_stream))
        assert len(events1) == 0  # Incomplete, should be buffered
        
        # Resume with remaining data (simulate network recovery)
        resume_stream = ' "stream resumed successfully"}\n'
        events2 = list(parser.parse_stream_data(resume_stream))
        
        successful_events = [event for event, error in events2 if event is not None]
        assert len(successful_events) == 1
        assert successful_events[0].message == "stream resumed successfully"