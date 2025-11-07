import time
import sys
import os

print('Starting Jarvis smoke tests...')

# Ensure project root is on sys.path so `from engine import ...` works
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    from engine import features
except Exception as e:
    print('Failed to import engine.features:', e)
    raise

# 1) Test openCommand for notepad
try:
    print('\n[1] openCommand("open notepad")')
    r1 = features.openCommand('open notepad')
    print('Result:', r1)
except Exception as e:
    print('open notepad failed:', e)

# small pause to let notepad open
time.sleep(1.0)

# 2) Test openCommand for calculator
try:
    print('\n[2] openCommand("open calculator")')
    r2 = features.openCommand('open calculator')
    print('Result:', r2)
except Exception as e:
    print('open calculator failed:', e)

# 3) Test openNotepadAndType
try:
    print('\n[3] openNotepadAndType("Test from Jarvis")')
    # Wait a bit to ensure notepad window is ready
    time.sleep(0.8)
    r3 = features.openNotepadAndType('Test from Jarvis')
    print('Typing result:', r3)
except Exception as e:
    print('openNotepadAndType failed:', e)

# 4) Test translation helper if available
try:
    print('\n[4] Translation test (detect_and_translate_telugu)')
    from engine.translator import detect_and_translate_telugu
    out = detect_and_translate_telugu('నేను బాగున్నాను')
    print('Translation output:', out)
except ImportError:
    print('Translation module not available (engine.translator ImportError)')
except Exception as e:
    print('Translation test failed:', e)

print('\nSmoke tests completed.')
