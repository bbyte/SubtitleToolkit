#!/usr/bin/env python3
"""
Test script to verify broken pipe fixes work correctly.

This script simulates the JSONL output pattern that was causing SIGTERM crashes.
"""

import json
import sys
import signal
import time
from datetime import datetime, timezone

def handle_sigpipe(signum, frame):
    """Handle SIGPIPE signal gracefully."""
    print("DEBUG: Received SIGPIPE, exiting gracefully", file=sys.stderr, flush=True)
    sys.exit(0)

def emit_jsonl(event_type, msg, progress=None, data=None):
    """Emit a JSONL event to stdout"""
    event = {
        "ts": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "stage": "test",
        "type": event_type,
        "msg": msg
    }
    
    if progress is not None:
        event["progress"] = progress
    
    if data is not None:
        event["data"] = data
    
    try:
        print(json.dumps(event), flush=True)
    except BrokenPipeError:
        print("DEBUG: Broken pipe during JSONL emit, exiting", file=sys.stderr, flush=True)
        sys.exit(0)
    except Exception as e:
        print(f"DEBUG: Error emitting JSONL: {e}", file=sys.stderr, flush=True)

if __name__ == "__main__":
    # Handle SIGPIPE gracefully
    signal.signal(signal.SIGPIPE, handle_sigpipe)
    
    print("DEBUG: Test script starting", file=sys.stderr, flush=True)
    
    # Simulate the pattern from srtTranslateWhole.py
    emit_jsonl("info", "Starting test simulation")
    
    # Simulate progress updates
    for i in range(10):
        time.sleep(0.1)  # Small delay
        progress = (i + 1) * 10
        emit_jsonl("progress", f"Processing step {i+1}/10", progress)
    
    # Simulate large output that might cause buffer overflow
    large_data = {"outputs": [f"/path/to/file_{i}.srt" for i in range(100)]}
    emit_jsonl("info", "Generated large output data", data=large_data)
    
    # Simulate final result
    emit_jsonl("result", "Test completed successfully", 100, {
        "test_file": "/path/with/[brackets]/test.srt",
        "output_file": "/path/with/[brackets]/test.bg.srt",
        "duration": 2.5,
        "outputs": ["/path/with/[brackets]/test.bg.srt"]
    })
    
    # Force flush before exit
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    except BrokenPipeError:
        sys.exit(0)
    
    print("DEBUG: Test script completed normally", file=sys.stderr, flush=True)