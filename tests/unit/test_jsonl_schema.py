#!/usr/bin/env python3
"""
Focused JSONL schema validation tests for SubtitleToolkit scripts.

Tests the JSONL output format specification:
- Required fields: ts, stage, type, msg
- Optional fields: progress, data
- Field type validation
- Timestamp format validation (ISO 8601 UTC)
- Stage values: "extract", "translate", "sync"  
- Event types: "info", "progress", "warning", "error", "result"
"""

import json
import re
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, List
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of JSONL validation"""
    is_valid: bool
    error_message: str = ""
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class JSONLSchemaValidator:
    """Validates JSONL events against SubtitleToolkit specification"""
    
    # Schema specification
    REQUIRED_FIELDS = {"ts", "stage", "type", "msg"}
    OPTIONAL_FIELDS = {"progress", "data"}
    ALL_FIELDS = REQUIRED_FIELDS | OPTIONAL_FIELDS
    
    VALID_STAGES = {"extract", "translate", "sync"}
    VALID_TYPES = {"info", "progress", "warning", "error", "result"}
    
    # Timestamp patterns
    ISO8601_PATTERNS = [
        r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$',  # 2024-01-01T12:00:00Z
        r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$',  # 2024-01-01T12:00:00.123Z
        r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$',  # 2024-01-01T12:00:00+00:00
        r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}\+00:00$'  # 2024-01-01T12:00:00.123+00:00
    ]
    
    @classmethod
    def validate_event(cls, event_dict: Dict[str, Any]) -> ValidationResult:
        """
        Validate a single JSONL event against the schema.
        
        Args:
            event_dict: Parsed JSON object representing an event
            
        Returns:
            ValidationResult with validation status and any errors/warnings
        """
        warnings = []
        
        # Check for required fields
        missing_fields = cls.REQUIRED_FIELDS - set(event_dict.keys())
        if missing_fields:
            return ValidationResult(
                is_valid=False,
                error_message=f"Missing required fields: {sorted(missing_fields)}"
            )
        
        # Check for unexpected fields
        unexpected_fields = set(event_dict.keys()) - cls.ALL_FIELDS
        if unexpected_fields:
            warnings.append(f"Unexpected fields found: {sorted(unexpected_fields)}")
        
        # Validate timestamp format
        ts_result = cls._validate_timestamp(event_dict["ts"])
        if not ts_result.is_valid:
            return ValidationResult(
                is_valid=False,
                error_message=f"Invalid timestamp: {ts_result.error_message}",
                warnings=warnings
            )
        
        # Validate stage
        stage = event_dict["stage"]
        if not isinstance(stage, str):
            return ValidationResult(
                is_valid=False,
                error_message=f"Stage must be string, got: {type(stage).__name__}",
                warnings=warnings
            )
        if stage not in cls.VALID_STAGES:
            return ValidationResult(
                is_valid=False,
                error_message=f"Invalid stage '{stage}'. Valid stages: {sorted(cls.VALID_STAGES)}",
                warnings=warnings
            )
        
        # Validate type
        event_type = event_dict["type"]
        if not isinstance(event_type, str):
            return ValidationResult(
                is_valid=False,
                error_message=f"Type must be string, got: {type(event_type).__name__}",
                warnings=warnings
            )
        if event_type not in cls.VALID_TYPES:
            return ValidationResult(
                is_valid=False,
                error_message=f"Invalid type '{event_type}'. Valid types: {sorted(cls.VALID_TYPES)}",
                warnings=warnings
            )
        
        # Validate message
        msg = event_dict["msg"]
        if not isinstance(msg, str):
            return ValidationResult(
                is_valid=False,
                error_message=f"Message must be string, got: {type(msg).__name__}",
                warnings=warnings
            )
        if not msg.strip():
            warnings.append("Message is empty or whitespace only")
        
        # Validate progress (if present)
        if "progress" in event_dict:
            progress_result = cls._validate_progress(event_dict["progress"])
            if not progress_result.is_valid:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Invalid progress: {progress_result.error_message}",
                    warnings=warnings
                )
            warnings.extend(progress_result.warnings)
        
        # Validate data (if present)
        if "data" in event_dict:
            data_result = cls._validate_data(event_dict["data"])
            if not data_result.is_valid:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Invalid data: {data_result.error_message}",
                    warnings=warnings
                )
            warnings.extend(data_result.warnings)
        
        return ValidationResult(is_valid=True, warnings=warnings)
    
    @classmethod
    def _validate_timestamp(cls, ts: Any) -> ValidationResult:
        """Validate timestamp format"""
        if not isinstance(ts, str):
            return ValidationResult(
                is_valid=False,
                error_message=f"Timestamp must be string, got: {type(ts).__name__}"
            )
        
        # Check against ISO 8601 patterns
        for pattern in cls.ISO8601_PATTERNS:
            if re.match(pattern, ts):
                # Try to parse to ensure it's a valid date
                try:
                    if ts.endswith('Z'):
                        datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    else:
                        datetime.fromisoformat(ts)
                    return ValidationResult(is_valid=True)
                except ValueError as e:
                    return ValidationResult(
                        is_valid=False,
                        error_message=f"Invalid datetime: {e}"
                    )
        
        return ValidationResult(
            is_valid=False,
            error_message=f"Timestamp '{ts}' does not match ISO 8601 UTC format"
        )
    
    @classmethod
    def _validate_progress(cls, progress: Any) -> ValidationResult:
        """Validate progress field"""
        warnings = []
        
        if progress is None:
            return ValidationResult(is_valid=True, warnings=warnings)
        
        if not isinstance(progress, (int, float)):
            return ValidationResult(
                is_valid=False,
                error_message=f"Progress must be number, got: {type(progress).__name__}"
            )
        
        if progress < 0 or progress > 100:
            return ValidationResult(
                is_valid=False,
                error_message=f"Progress must be between 0-100, got: {progress}"
            )
        
        if isinstance(progress, float) and not (progress % 1 == 0 or progress % 0.1 < 0.01):
            warnings.append(f"Progress has unusual precision: {progress}")
        
        return ValidationResult(is_valid=True, warnings=warnings)
    
    @classmethod
    def _validate_data(cls, data: Any) -> ValidationResult:
        """Validate data field"""
        warnings = []
        
        if data is None:
            return ValidationResult(is_valid=True, warnings=warnings)
        
        if not isinstance(data, dict):
            return ValidationResult(
                is_valid=False,
                error_message=f"Data must be dict or null, got: {type(data).__name__}"
            )
        
        # Check for reasonable data size
        try:
            data_str = json.dumps(data)
            if len(data_str) > 10000:  # Arbitrary large size warning
                warnings.append(f"Data field is very large: {len(data_str)} characters")
        except (TypeError, ValueError):
            return ValidationResult(
                is_valid=False,
                error_message="Data field contains non-serializable content"
            )
        
        return ValidationResult(is_valid=True, warnings=warnings)


def validate_jsonl_stream(jsonl_text: str) -> Tuple[List[ValidationResult], List[Dict[str, Any]]]:
    """
    Validate an entire JSONL stream.
    
    Args:
        jsonl_text: Raw JSONL text with one JSON object per line
        
    Returns:
        Tuple of (validation_results, parsed_events)
        - validation_results: List of ValidationResult for each line
        - parsed_events: List of successfully parsed event dictionaries
    """
    validation_results = []
    parsed_events = []
    
    lines = jsonl_text.strip().split('\n')
    
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            # Skip empty lines
            continue
        
        try:
            # Parse JSON
            event_dict = json.loads(line)
            parsed_events.append(event_dict)
            
            # Validate schema
            validation_result = JSONLSchemaValidator.validate_event(event_dict)
            validation_results.append(validation_result)
            
        except json.JSONDecodeError as e:
            validation_results.append(ValidationResult(
                is_valid=False,
                error_message=f"Line {line_num}: Invalid JSON - {e}"
            ))
    
    return validation_results, parsed_events


def analyze_jsonl_patterns(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze patterns in JSONL events for validation insights.
    
    Args:
        events: List of parsed event dictionaries
        
    Returns:
        Dictionary with analysis results
    """
    if not events:
        return {"error": "No events to analyze"}
    
    analysis = {
        "total_events": len(events),
        "stages": {},
        "types": {},
        "progress_events": [],
        "timestamp_range": {},
        "data_fields": set(),
        "warnings": []
    }
    
    # Count stages and types
    for event in events:
        stage = event.get("stage", "unknown")
        event_type = event.get("type", "unknown")
        
        analysis["stages"][stage] = analysis["stages"].get(stage, 0) + 1
        analysis["types"][event_type] = analysis["types"].get(event_type, 0) + 1
        
        # Collect progress events
        if event_type == "progress" and "progress" in event:
            analysis["progress_events"].append(event["progress"])
        
        # Collect data field keys
        if "data" in event and isinstance(event["data"], dict):
            analysis["data_fields"].update(event["data"].keys())
    
    # Analyze timestamp range
    timestamps = [event.get("ts") for event in events if event.get("ts")]
    if timestamps:
        analysis["timestamp_range"] = {
            "first": min(timestamps),
            "last": max(timestamps),
            "span_seconds": 0  # Could calculate if needed
        }
    
    # Analyze progress sequence
    if analysis["progress_events"]:
        progress_values = sorted(analysis["progress_events"])
        analysis["progress_analysis"] = {
            "min": min(progress_values),
            "max": max(progress_values), 
            "count": len(progress_values),
            "is_monotonic": progress_values == sorted(set(progress_values))
        }
        
        # Check for reasonable progress sequence
        if analysis["progress_analysis"]["max"] < 100 and "result" not in analysis["types"]:
            analysis["warnings"].append("Progress never reaches 100% and no result event found")
    
    # Convert data_fields set to list for JSON serialization
    analysis["data_fields"] = sorted(list(analysis["data_fields"]))
    
    return analysis


def run_schema_tests():
    """Run comprehensive schema validation tests"""
    print("Running JSONL Schema Validation Tests")
    print("=" * 50)
    
    # Test valid events
    valid_events = [
        {
            "ts": "2024-01-01T12:00:00Z",
            "stage": "extract",
            "type": "info",
            "msg": "Starting extraction"
        },
        {
            "ts": "2024-01-01T12:00:00.123Z",
            "stage": "translate", 
            "type": "progress",
            "msg": "Translation in progress",
            "progress": 50
        },
        {
            "ts": "2024-01-01T12:00:00+00:00",
            "stage": "sync",
            "type": "result",
            "msg": "Sync completed",
            "data": {"files": 3, "matches": 2}
        }
    ]
    
    print("\nTesting valid events:")
    for i, event in enumerate(valid_events):
        result = JSONLSchemaValidator.validate_event(event)
        status = "✅ PASS" if result.is_valid else "❌ FAIL"
        print(f"  Event {i+1}: {status}")
        if not result.is_valid:
            print(f"    Error: {result.error_message}")
        if result.warnings:
            print(f"    Warnings: {result.warnings}")
    
    # Test invalid events
    invalid_events = [
        ({}, "Empty event"),
        ({"ts": "invalid", "stage": "extract", "type": "info", "msg": "test"}, "Invalid timestamp"),
        ({"ts": "2024-01-01T12:00:00Z", "stage": "invalid", "type": "info", "msg": "test"}, "Invalid stage"),
        ({"ts": "2024-01-01T12:00:00Z", "stage": "extract", "type": "invalid", "msg": "test"}, "Invalid type"),
        ({"ts": "2024-01-01T12:00:00Z", "stage": "extract", "type": "info", "msg": ""}, "Empty message"),
        ({"ts": "2024-01-01T12:00:00Z", "stage": "extract", "type": "progress", "msg": "test", "progress": 150}, "Invalid progress"),
        ({"ts": "2024-01-01T12:00:00Z", "stage": "extract", "type": "info", "msg": "test", "data": "not-dict"}, "Invalid data type")
    ]
    
    print("\nTesting invalid events:")
    for i, (event, description) in enumerate(invalid_events):
        result = JSONLSchemaValidator.validate_event(event)
        expected_fail = "✅ PASS (correctly failed)" if not result.is_valid else "❌ FAIL (should have failed)"
        print(f"  {description}: {expected_fail}")
        if result.is_valid:
            print(f"    Should have failed but passed!")
        else:
            print(f"    Correctly failed: {result.error_message}")
    
    print("\n✅ Schema validation tests completed")


if __name__ == "__main__":
    run_schema_tests()