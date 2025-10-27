#!/usr/bin/env python3
"""Test script to debug QProcess signal handling."""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PySide6.QtCore import QCoreApplication
from app.runner.script_runner import ScriptRunner
from app.runner.config_models import TranslateConfig

def test_translation_process():
    """Test a translation process to see the signal flow."""
    app = QCoreApplication(sys.argv)
    
    # Create script runner
    runner = ScriptRunner()
    
    # Set up signal debugging
    def debug_process_started(stage):
        print(f"[SIGNAL] process_started: {stage}")
    
    def debug_process_finished(result):
        print(f"[SIGNAL] process_finished: success={result.success}, exit_code={result.exit_code}")
    
    def debug_process_failed(stage, error_msg):
        print(f"[SIGNAL] process_failed: {stage}, error={error_msg}")
    
    def debug_info_received(stage, message):
        if "DEBUG:" in message:
            print(f"[DEBUG] {message}")
    
    # Connect signals
    runner.signals.process_started.connect(debug_process_started)
    runner.signals.process_finished.connect(debug_process_finished)
    runner.signals.process_failed.connect(debug_process_failed)
    runner.signals.info_received.connect(debug_info_received)
    
    # Create a translation config for the problematic file
    config = TranslateConfig(
        input_files=["/Volumes/all/torrents/downloaded/The.Sandman.S01.COMPLETE.1080p.NF.WEBRip.DDP5.1.Atmos.x264-SMURF[rartv]/The.Sandman.S01E01.Sleep.of.the.Just.1080p.NF.WEB-DL.DDP5.1.Atmos.H.264-SMURF.srt"],
        source_language="auto",
        target_language="bg",
        provider="claude",
        model="claude-3-5-haiku-20241022",
        api_key="sk-ant-api03-vWj7F4iKoC_B7Sg3CL8L3BtZqBNq1bMHnvOv8b4wf3vYRFXNnTLSO-K3_t8oVu-kVTJOJ9MKCUzBLNpvAAA",  # This will be masked in debug
        max_workers=1,
        chunk_size=5
    )
    
    print("Starting translation test...")
    
    try:
        # Start the translation
        process = runner.run_translate(config)
        
        # Wait for completion
        def on_completion():
            print("Process completed, quitting application")
            app.quit()
        
        runner.signals.process_finished.connect(lambda result: on_completion())
        runner.signals.process_failed.connect(lambda stage, error: on_completion())
        
        # Run the application
        app.exec()
        
    except Exception as e:
        print(f"Test failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = test_translation_process()
    print(f"Test {'PASSED' if success else 'FAILED'}")