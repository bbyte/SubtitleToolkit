#!/usr/bin/env python3
"""
Test script to verify the SIGTERM race condition fix in ScriptRunner.

This test simulates the scenario where a process completes successfully
but Qt emits both finished() and errorOccurred() signals.
"""

import sys
import time
import logging
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtCore import QTimer, QCoreApplication
from PySide6.QtWidgets import QApplication

from app.runner.script_runner import ScriptRunner
from app.runner.config_models import TranslateConfig
from app.runner.events import Stage

def setup_logging():
    """Set up logging for the test."""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S'
    )

def test_signal_race_condition():
    """Test that our signal handling prevents race conditions."""
    print("Testing ScriptRunner signal race condition fix...")
    
    setup_logging()
    
    # Create Qt application
    app = QApplication(sys.argv)
    
    # Create script runner
    runner = ScriptRunner()
    
    # Track signals received
    signals_received = []
    
    def on_process_started(stage):
        signals_received.append(f"STARTED: {stage.value}")
        print(f"✓ Process started: {stage.value}")
    
    def on_process_finished(result):
        signals_received.append(f"FINISHED: success={result.success}, exit_code={result.exit_code}")
        print(f"✓ Process finished: success={result.success}, exit_code={result.exit_code}")
        
    def on_process_failed(stage, error):
        signals_received.append(f"FAILED: {stage.value} - {error}")
        print(f"✗ Process failed: {stage.value} - {error}")
        
    def on_info_received(stage, message):
        if "DEBUG:" in message:
            print(f"🔍 {stage.value}: {message}")
            if "RACE CONDITION PREVENTED" in message:
                signals_received.append("RACE_PREVENTED")
                print("🛡️  Race condition successfully prevented!")
    
    # Connect signals
    runner.signals.process_started.connect(on_process_started)
    runner.signals.process_finished.connect(on_process_finished) 
    runner.signals.process_failed.connect(on_process_failed)
    runner.signals.info_received.connect(on_info_received)
    
    # Create a test translation config (this will likely fail, but that's ok for testing)
    test_file = Path(__file__).parent / "test_sample.srt"
    if not test_file.exists():
        # Create a minimal test SRT file
        test_file.write_text("""1
00:00:01,000 --> 00:00:02,000
Test subtitle

2  
00:00:03,000 --> 00:00:04,000
Another test
""")
    
    config = TranslateConfig(
        input_files=[str(test_file)],
        provider="openai",
        model="gpt-4o-mini",
        target_language="spanish",
        source_language="english"
    )
    
    try:
        # Start the process
        print("\nStarting translation process...")
        process = runner.run_translate(config)
        
        # Set up a timer to stop the test after reasonable time
        def stop_test():
            print("\nTest timeout - stopping...")
            if runner.is_running:
                runner.terminate_process()
            QTimer.singleShot(1000, app.quit)
        
        timer = QTimer()
        timer.setSingleShot(True)  
        timer.timeout.connect(stop_test)
        timer.start(30000)  # 30 second timeout
        
        # Run the event loop
        app.exec()
        
        # Analyze results
        print("\n" + "="*50)
        print("SIGNAL ANALYSIS:")
        print("="*50)
        
        for signal in signals_received:
            print(f"  {signal}")
            
        # Check for success
        race_prevented = any("RACE_PREVENTED" in s for s in signals_received)
        finished_signals = [s for s in signals_received if "FINISHED:" in s]
        failed_signals = [s for s in signals_received if "FAILED:" in s]
        
        print(f"\nRESULTS:")
        print(f"  Race condition prevented: {race_prevented}")
        print(f"  Finished signals: {len(finished_signals)}")  
        print(f"  Failed signals: {len(failed_signals)}")
        print(f"  Total completion signals: {len(finished_signals) + len(failed_signals)}")
        
        if race_prevented:
            print("\n✅ SUCCESS: Race condition was detected and prevented!")
        elif len(finished_signals) + len(failed_signals) <= 1:
            print("\n✅ SUCCESS: Only one completion signal received (no race condition)")
        else:
            print("\n❌ FAILURE: Multiple completion signals received - race condition occurred!")
            return False
            
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        return False
    finally:
        # Clean up test file
        if test_file.exists():
            test_file.unlink()

if __name__ == "__main__":
    success = test_signal_race_condition()
    sys.exit(0 if success else 1)