#!/usr/bin/env python3
import sys
import time
import json

print("Starting simple test script")
print(f"Python version: {sys.version}")
print(f"Arguments: {sys.argv}")

# Simulate the structure of the translation script
print('{"stage": "test", "type": "info", "msg": "Test script started"}')
sys.stdout.flush()

time.sleep(1)
print('{"stage": "test", "type": "info", "msg": "Test script running"}')
sys.stdout.flush()

time.sleep(1)
print('{"stage": "test", "type": "info", "msg": "Test script completed"}')
sys.stdout.flush()

print("Script finished successfully")