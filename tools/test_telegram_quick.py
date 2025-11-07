#!/usr/bin/env python3
"""Quick test of Telegram messaging functionality"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

print("=" * 60)
print("Testing Telegram Messaging Functions")
print("=" * 60)

# Test 1: Headless mode test (should work without credentials)
print("\n1. Testing send_telegram() in HEADLESS mode:")
os.environ['JARVIS_HEADLESS'] = '1'
from engine.features import send_telegram

result1 = send_telegram('@test_user', 'Test message')
print(f"   Result: {result1}")
assert result1 == True, "Headless test should return True"
print("   ✓ Headless mode test PASSED")

# Test 2: Without credentials (should return False gracefully)
print("\n2. Testing send_telegram() WITHOUT credentials:")
del os.environ['JARVIS_HEADLESS']
if 'TELEGRAM_API_ID' in os.environ:
    del os.environ['TELEGRAM_API_ID']
if 'TELEGRAM_API_HASH' in os.environ:
    del os.environ['TELEGRAM_API_HASH']

result2 = send_telegram('@test_user', 'Test message')
print(f"   Result: {result2}")
print(f"   Expected: False (no credentials)")
assert result2 == False, "Should return False without credentials"
print("   ✓ No credentials test PASSED")

# Test 3: telegram_desktop_send in headless mode
print("\n3. Testing telegram_desktop_send() in HEADLESS mode:")
os.environ['JARVIS_HEADLESS'] = '1'
from engine.features import telegram_desktop_send

result3 = telegram_desktop_send('test_contact', 'Test message')
print(f"   Result: {result3}")
assert result3 == True, "Headless test should return True"
print("   ✓ telegram_desktop_send headless test PASSED")

print("\n" + "=" * 60)
print("ALL TESTS PASSED ✓")
print("=" * 60)
print("\nNote: For real Telegram messaging, you need to:")
print("  1. Install: pip install telethon")
print("  2. Set TELEGRAM_API_ID and TELEGRAM_API_HASH environment variables")
print("  3. Authenticate on first run")

